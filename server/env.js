import path from 'node:path';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';

// dotenv/config membaca .env dari cwd, dan aplikasi ini juga dijalankan dari
// root repo (node server/index.js). Jadi path-nya dikunci ke folder server/.
dotenv.config({ path: path.join(path.dirname(fileURLToPath(import.meta.url)), '.env') });

// Number('') itu 0, jadi env var yang diisi kosong atau salah ketik akan
// diam-diam jadi nol. Nilai tidak masuk akal dikembalikan ke default.
export function num(name, fallback) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}
