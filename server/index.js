import 'dotenv/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import cors from 'cors';
import multer from 'multer';

import { generate, generateStream, getActiveModel, listUsableModels, MODEL_CANDIDATES } from './lib/gemini.js';
import { buildGenerationConfig, buildSystemInstruction, DEFAULT_STYLE, STYLES } from './lib/persona.js';
import { describeFile, fileToInlinePart } from './lib/files.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CLIENT_DIR = path.resolve(__dirname, '..', 'client');

const PORT = process.env.PORT || 3000;
const MAX_HISTORY = Number(process.env.MAX_HISTORY_MESSAGES ?? 20);
const MAX_FILE_MB = Number(process.env.MAX_FILE_MB ?? 20);
const MAX_FILE_SIZE = MAX_FILE_MB * 1024 * 1024;

if (!process.env.GEMINI_API_KEY) {
  console.error('GEMINI_API_KEY kosong. Salin server/.env.example jadi server/.env lalu isi API key-nya.');
  process.exit(1);
}

const app = express();

app.use(cors());
app.use(express.json({ limit: '5mb' }));
app.use(express.static(CLIENT_DIR));

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: MAX_FILE_SIZE },
});

const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
const httpError = (status, message) => Object.assign(new Error(message), { status });

const VALID_ROLES = new Set(['user', 'model']);

// Kalau ada lampiran, request datang sebagai form-data dan tiap field jadi string.
// Body JSON biasa dibiarkan apa adanya biar salah tipe ketahuan di validator.
function readJsonField(value, fieldName, isMultipart) {
  if (value === undefined || value === null || value === '') return undefined;
  if (!isMultipart || typeof value !== 'string') return value;

  try {
    return JSON.parse(value);
  } catch {
    throw httpError(400, `Field "${fieldName}" harus berupa JSON string yang valid.`);
  }
}

function validateConversation(conversation) {
  if (!Array.isArray(conversation)) {
    throw httpError(400, 'Field "conversation" harus berupa array. Contoh: [{ "role": "user", "text": "Halo" }]');
  }
  if (conversation.length === 0) {
    throw httpError(400, 'Field "conversation" tidak boleh kosong.');
  }

  return conversation.map((message, i) => {
    if (typeof message !== 'object' || message === null) {
      throw httpError(400, `conversation[${i}] harus berupa object { role, text }.`);
    }

    const { role, text } = message;

    if (!VALID_ROLES.has(role)) {
      throw httpError(400, `conversation[${i}].role harus "user" atau "model", bukan "${role}".`);
    }
    if (typeof text !== 'string' || !text.trim()) {
      throw httpError(400, `conversation[${i}].text harus berupa string dan tidak boleh kosong.`);
    }

    return { role, text: text.trim() };
  });
}

function buildContents(conversation, attachment) {
  const history = conversation.slice(-MAX_HISTORY);
  const last = history.length - 1;

  return history.map(({ role, text }, i) => {
    const parts = [{ text }];
    if (attachment && i === last && role === 'user') parts.push(fileToInlinePart(attachment));
    return { role, parts };
  });
}

function readSettings(raw, isMultipart) {
  const settings = readJsonField(raw, 'settings', isMultipart) ?? {};
  const style = typeof settings.style === 'string' && STYLES[settings.style] ? settings.style : DEFAULT_STYLE;

  const config = buildGenerationConfig(style, {
    temperature: Number(settings.temperature),
    topP: Number(settings.topP),
    topK: Number(settings.topK),
  });

  return { style, config: { ...config, systemInstruction: buildSystemInstruction(style) } };
}

function prepareChatRequest(req) {
  const isMultipart = Boolean(req.is('multipart/form-data'));
  const conversation = validateConversation(readJsonField(req.body?.conversation, 'conversation', isMultipart));
  const { style, config } = readSettings(req.body?.settings, isMultipart);
  const attachment = req.file ?? null;

  if (attachment && conversation.at(-1).role !== 'user') {
    throw httpError(400, 'Lampiran hanya bisa dikirim bersama pesan terakhir dari role "user".');
  }

  return { style, config, attachment, contents: buildContents(conversation, attachment) };
}

app.post('/api/chat', upload.single('attachment'), asyncHandler(async (req, res) => {
  const { contents, config, style, attachment } = prepareChatRequest(req);
  const { text, model } = await generate({ contents, config });

  const payload = { result: text, model, style };

  if (attachment) {
    const inlinePart = contents.at(-1).parts.find((part) => part.inlineData);
    payload.file = describeFile(attachment, inlinePart?.inlineData?.mimeType);
  }

  res.status(200).json(payload);
}));

// Versi SSE dari /api/chat. Event-nya: {delta}, {done}, atau {error}.
app.post('/api/chat/stream', asyncHandler(async (req, res) => {
  const { contents, config, style } = prepareChatRequest(req);

  // Sengaja dipanggil sebelum writeHead: selama header belum keluar,
  // error masih bisa dibalas sebagai JSON biasa.
  const { model, stream, state } = await generateStream({ contents, config });

  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  const send = (payload) => res.write(`data: ${JSON.stringify(payload)}\n\n`);

  let aborted = false;
  req.on('close', () => { aborted = true; });

  try {
    let full = '';

    for await (const delta of stream) {
      if (aborted) return;
      full += delta;
      send({ delta });
    }

    if (full.trim()) {
      send({ done: true, model, style, truncated: state.finishReason === 'MAX_TOKENS' });
    } else {
      send({ error: 'Model tidak mengembalikan jawaban.' });
    }
  } catch (err) {
    console.error('[stream]', err.message);
    send({ error: err.message });
  } finally {
    res.end();
  }
}));

function fileEndpoint({ field, defaultPrompt }) {
  return asyncHandler(async (req, res) => {
    if (!req.file) {
      throw httpError(400, `File "${field}" wajib diisi. Kirim lewat Body -> form-data dengan key "${field}" bertipe File.`);
    }

    const prompt = req.body?.prompt?.trim() || defaultPrompt;
    const inlinePart = fileToInlinePart(req.file);

    const { text, model } = await generate({
      contents: [{ role: 'user', parts: [{ text: prompt }, inlinePart] }],
      config: {
        ...buildGenerationConfig(DEFAULT_STYLE),
        systemInstruction: buildSystemInstruction(DEFAULT_STYLE),
      },
    });

    res.status(200).json({
      result: text,
      model,
      file: describeFile(req.file, inlinePart.inlineData.mimeType),
    });
  });
}

app.post('/generate-text', asyncHandler(async (req, res) => {
  const prompt = typeof req.body?.prompt === 'string' ? req.body.prompt.trim() : '';

  if (!prompt) {
    throw httpError(400, 'Field "prompt" wajib diisi dan berupa string. Contoh body: { "prompt": "Rekomendasi 3 hari di Bali" }');
  }

  const { text, model } = await generate({
    contents: prompt,
    config: {
      ...buildGenerationConfig(DEFAULT_STYLE),
      systemInstruction: buildSystemInstruction(DEFAULT_STYLE),
    },
  });

  res.status(200).json({ result: text, model });
}));

app.post('/generate-from-image', upload.single('image'), fileEndpoint({
  field: 'image',
  defaultPrompt: 'Jelaskan gambar ini dan berikan tips wisata yang relevan.',
}));

app.post('/generate-from-document', upload.single('document'), fileEndpoint({
  field: 'document',
  defaultPrompt: 'Ringkas dokumen ini dalam poin-poin penting.',
}));

app.post('/generate-from-audio', upload.single('audio'), fileEndpoint({
  field: 'audio',
  defaultPrompt: 'Transkrip audio ini, lalu ringkas maksud pembicaranya.',
}));

app.get('/api', (req, res) => {
  res.json({
    name: 'Travel Buddy',
    status: 'ok',
    model: getActiveModel(),
    endpoints: [
      'POST /api/chat',
      'POST /api/chat/stream',
      'POST /generate-text',
      'POST /generate-from-image',
      'POST /generate-from-document',
      'POST /generate-from-audio',
      'GET /api/health',
      'GET /api/config',
      'GET /api/models',
    ],
  });
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    model: getActiveModel(),
    apiKeyLoaded: Boolean(process.env.GEMINI_API_KEY),
    maxHistoryMessages: MAX_HISTORY,
    uptimeSeconds: Math.round(process.uptime()),
  });
});

// Dipakai frontend buat bikin pilihan gaya bahasa, biar daftarnya nggak dobel.
app.get('/api/config', (req, res) => {
  res.json({
    defaultStyle: DEFAULT_STYLE,
    styles: Object.entries(STYLES).map(([key, style]) => ({
      key,
      label: style.label,
      description: style.description,
      ...style.config,
    })),
    maxFileSizeMB: MAX_FILE_MB,
  });
});

app.get('/api/models', asyncHandler(async (req, res) => {
  res.json({
    active: getActiveModel(),
    candidates: MODEL_CANDIDATES,
    available: await listUsableModels(),
  });
}));

app.use((req, res) => {
  res.status(404).json({ message: `Route ${req.method} ${req.originalUrl} tidak ditemukan.` });
});

// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    const message = err.code === 'LIMIT_FILE_SIZE'
      ? `Ukuran file melebihi batas ${MAX_FILE_MB} MB.`
      : `Gagal memproses upload: ${err.message}`;

    return res.status(400).json({ message, code: err.code });
  }

  const status = Number(err.status) || 500;
  console.error(`[${status}]`, err.message);

  if (res.headersSent) return res.end();

  const body = { message: err.message };

  if (status === 403) body.hint = 'API key ditolak Google. Buat key baru di https://aistudio.google.com/apikey';
  else if (status === 429) body.hint = 'Kuota habis. Kuota Gemini dihitung per model per hari.';
  else if (status === 404) body.hint = 'Nama model tidak valid. Cek GET /api/models.';
  else if (status === 415) body.hint = 'Gemini cuma menerima gambar, PDF, teks polos, dan audio umum.';
  else if (status === 502 && err.attempts) body.hint = 'Semua model kandidat ditolak. Jalankan npm run check.';

  res.status(status).json(body);
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Travel Buddy jalan di port ${PORT} (model ${getActiveModel()})`);
});
