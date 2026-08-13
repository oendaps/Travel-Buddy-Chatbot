// Cek cepat: API key-nya yang bermasalah, atau kodenya?
// Jalankan dengan: npm run check
import '../env.js';
import { GoogleGenAI } from '@google/genai';

const API_KEY = process.env.GEMINI_API_KEY;

if (!API_KEY) {
  console.error('GEMINI_API_KEY tidak ada di server/.env');
  process.exit(1);
}

console.log(`API key: ${API_KEY.slice(0, 6)}...${API_KEY.slice(-4)} (${API_KEY.length} karakter)\n`);

const ai = new GoogleGenAI({ apiKey: API_KEY });

const CANDIDATES = [
  process.env.GEMINI_MODEL,
  'gemini-2.5-flash',
  'gemini-3.5-flash-lite',
  'gemini-3.5-flash',
  'gemini-flash-latest',
  'gemini-flash-lite-latest',
].filter(Boolean).filter((m, i, all) => all.indexOf(m) === i);

function readError(err) {
  const raw = err?.message ?? String(err);

  try {
    const parsed = JSON.parse(raw);
    return { code: parsed?.error?.code, message: parsed?.error?.message ?? raw, raw };
  } catch {
    return { code: err?.status, message: raw, raw };
  }
}

function explain(code, message, raw) {
  if (code === 403) return 'API key ditolak Google, perlu key baru.';
  if (code === 404) return 'Model ini tidak dibuka untuk key kamu.';
  if (code === 503) return 'Model lagi penuh di sisi Google, coba lagi nanti.';
  if (code === 400 && /API key not valid/i.test(message)) return 'API key salah ketik atau sudah dihapus.';

  if (code === 429) {
    const limit = message.match(/limit: (\d+)/)?.[1];
    const perDay = /PerDay/i.test(raw);
    return `Kuota habis${limit ? ` (batas ${limit} request${perDay ? '/hari' : '/menit'})` : ''}. Kuota dihitung per model.`;
  }

  return 'Lihat pesan aslinya di atas.';
}

const usable = [];
const outOfQuota = [];

for (const model of CANDIDATES) {
  process.stdout.write(`${model.padEnd(26)} `);

  try {
    const response = await ai.models.generateContent({ model, contents: 'Balas satu kata: OK' });
    console.log(`OK  "${(response.text || '').trim().slice(0, 20)}"`);
    usable.push(model);
  } catch (err) {
    const { code, message, raw } = readError(err);
    console.log(`GAGAL [${code}] ${message.split('\n')[0].slice(0, 80)}`);
    console.log(`${' '.repeat(27)}${explain(code, message, raw)}`);
    if (code === 429) outOfQuota.push(model);
  }
}

console.log();

if (usable.length) {
  console.log(`API key valid. Model yang siap: ${usable.join(', ')}`);
  console.log(`Pakai GEMINI_MODEL=${usable[0]} di server/.env`);

  if (outOfQuota.length) {
    console.log(`Kuota harian habis untuk ${outOfQuota.join(', ')}, server akan otomatis pindah model.`);
  }

  process.exit(0);
}

if (outOfQuota.length === CANDIDATES.length) {
  console.log('API key valid tapi kuota harian semua model sudah habis.');
  console.log('Tunggu reset harian, aktifkan billing, atau pakai key dari akun lain.');
  process.exit(1);
}

console.log('Tidak ada model yang bisa diakses key ini.');
console.log('Bikin API key baru di https://aistudio.google.com/apikey');
process.exit(1);
