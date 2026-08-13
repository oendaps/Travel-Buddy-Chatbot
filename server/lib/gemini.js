import '../env.js';
import { GoogleGenAI } from '@google/genai';

export const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const PRIMARY_MODEL = process.env.GEMINI_MODEL || 'gemini-2.5-flash';

export const MODEL_CANDIDATES = [
  PRIMARY_MODEL,
  'gemini-2.5-flash',
  'gemini-flash-latest',
  'gemini-flash-lite-latest',
  'gemini-2.5-flash-lite',
  'gemini-2.5-pro',
].filter((model, i, all) => all.indexOf(model) === i);

let activeModel = PRIMARY_MODEL;

export function getActiveModel() {
  return activeModel;
}

// Error dari SDK datang sebagai JSON string di dalam message. Dibuka dulu.
export function parseGeminiError(err) {
  const raw = err?.message ?? String(err);

  try {
    const parsed = JSON.parse(raw);
    if (parsed?.error?.message) return { status: parsed.error.code, message: parsed.error.message };
  } catch {
    // bukan JSON, pakai apa adanya
  }

  return { status: err?.status, message: raw };
}

// 429 ikut di sini karena kuota free tier dihitung per model, bukan per API key.
// Kalau satu model habis jatahnya, model lain biasanya masih bisa dipakai.
function shouldTryNextModel(status, message) {
  if (status === 404) return true;
  if (status === 403 && /denied access|not supported|permission/i.test(message)) return true;
  if (status === 429 || status === 503) return true;
  return false;
}

export function extractText(response) {
  const text = response?.text;
  if (text && text.trim()) return text;

  const blocked = response?.promptFeedback?.blockReason;
  if (blocked) {
    throw Object.assign(new Error(`Prompt diblokir safety filter Gemini (${blocked}).`), { status: 400 });
  }

  const finish = response?.candidates?.[0]?.finishReason;
  if (finish && finish !== 'STOP') {
    throw Object.assign(new Error(`Model berhenti sebelum selesai (${finish}).`), { status: 502 });
  }

  throw Object.assign(new Error('Model tidak mengembalikan teks apa pun.'), { status: 502 });
}

function allModelsFailed(attempts) {
  const detail = attempts.map((a) => `${a.model}: [${a.status}] ${a.message}`).join(' | ');
  return Object.assign(
    new Error(`Tidak ada model Gemini yang bisa diakses API key ini. ${detail}`),
    { status: 502, attempts },
  );
}

function candidateOrder() {
  return [activeModel, ...MODEL_CANDIDATES.filter((m) => m !== activeModel)];
}

function rememberWorkingModel(model) {
  if (model === activeModel) return;
  console.warn(`[model] ${activeModel} tidak bisa dipakai, pindah ke ${model}`);
  activeModel = model;
}

export async function generate({ contents, config }) {
  const attempts = [];

  for (const model of candidateOrder()) {
    try {
      const response = await ai.models.generateContent({ model, contents, config });
      rememberWorkingModel(model);
      return { text: extractText(response), model };
    } catch (err) {
      const { status, message } = parseGeminiError(err);
      attempts.push({ model, status, message });

      if (shouldTryNextModel(status, message)) continue;
      throw Object.assign(new Error(message), { status: status || 500 });
    }
  }

  throw allModelsFailed(attempts);
}

export async function generateStream({ contents, config }) {
  const attempts = [];

  for (const model of candidateOrder()) {
    try {
      const raw = await ai.models.generateContentStream({ model, contents, config });
      const iterator = raw[Symbol.asyncIterator]();

      // Potongan pertama ditarik di sini supaya error model muncul selagi
      // response header belum dikirim. Setelah stream jalan, model tidak
      // mungkin diganti lagi di tengah jalan.
      const first = await iterator.next();
      rememberWorkingModel(model);

      // Diisi potongan terakhir. MAX_TOKENS bikin jawaban putus di tengah kata,
      // dan tanpa ini user cuma lihat kalimat menggantung tanpa penjelasan.
      const state = { finishReason: null };

      async function* stream() {
        const take = (chunk) => {
          const reason = chunk?.candidates?.[0]?.finishReason;
          if (reason) state.finishReason = reason;
          return chunk?.text;
        };

        if (!first.done) {
          const text = take(first.value);
          if (text) yield text;
        }

        while (true) {
          const next = await iterator.next();
          if (next.done) break;
          const text = take(next.value);
          if (text) yield text;
        }
      }

      return { model, stream: stream(), state };
    } catch (err) {
      const { status, message } = parseGeminiError(err);
      attempts.push({ model, status, message });

      if (shouldTryNextModel(status, message)) continue;
      throw Object.assign(new Error(message), { status: status || 500 });
    }
  }

  throw allModelsFailed(attempts);
}

export async function listUsableModels() {
  const models = [];

  for await (const model of await ai.models.list()) {
    if (model.supportedActions?.includes('generateContent')) {
      models.push(model.name?.replace(/^models\//, ''));
    }
  }

  return models;
}
