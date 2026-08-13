import path from 'node:path';

// curl dan sebagian versi Postman mengirim file sebagai application/octet-stream,
// dan Gemini menolak MIME segeneral itu. Jadi tipenya ditebak dari ekstensi.
const MIME_BY_EXT = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.heic': 'image/heic',
  '.heif': 'image/heif',

  '.pdf': 'application/pdf',
  '.txt': 'text/plain',
  '.md': 'text/md',
  '.csv': 'text/csv',
  '.html': 'text/html',
  '.htm': 'text/html',
  '.xml': 'text/xml',
  '.rtf': 'text/rtf',
  '.json': 'text/plain',
  '.js': 'text/plain',
  '.py': 'text/plain',

  '.mp3': 'audio/mp3',
  '.wav': 'audio/wav',
  '.m4a': 'audio/mp4',
  '.aac': 'audio/aac',
  '.ogg': 'audio/ogg',
  '.flac': 'audio/flac',
  '.aiff': 'audio/aiff',
};

const UNSUPPORTED_EXT = {
  '.docx': 'Word (.docx)',
  '.doc': 'Word (.doc)',
  '.xlsx': 'Excel (.xlsx)',
  '.xls': 'Excel (.xls)',
  '.pptx': 'PowerPoint (.pptx)',
  '.zip': 'arsip ZIP',
};

const GENERIC_MIME = /^(application|binary)\/octet-stream$/i;

const httpError = (status, message) => Object.assign(new Error(message), { status });

export function resolveMimeType(file) {
  const ext = path.extname(file.originalname || '').toLowerCase();

  if (UNSUPPORTED_EXT[ext]) {
    throw httpError(415, `Format ${UNSUPPORTED_EXT[ext]} tidak didukung Gemini. Konversi dulu ke PDF atau TXT.`);
  }

  if (!file.mimetype || GENERIC_MIME.test(file.mimetype)) {
    const guess = MIME_BY_EXT[ext];
    if (guess) return guess;

    throw httpError(415, `Tidak bisa menentukan tipe file "${file.originalname}". Pakai ekstensi yang jelas.`);
  }

  return file.mimetype;
}

export function fileToInlinePart(file) {
  return {
    inlineData: {
      mimeType: resolveMimeType(file),
      data: file.buffer.toString('base64'),
    },
  };
}

export function describeFile(file, mimeType) {
  return {
    name: file.originalname,
    mimeType: mimeType ?? file.mimetype,
    sizeBytes: file.size,
  };
}
