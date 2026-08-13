"""Persona Travel Buddy dan pemanggilan Gemini untuk versi Streamlit.

Isinya sama dengan server/lib/persona.js dan server/lib/gemini.js pada versi
Node, supaya dua versi aplikasi ini menjawab dengan cara yang sama.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from google import genai
from google.genai import types

CORE_PERSONA = """
Kamu adalah "Travel Buddy", asisten perjalanan untuk wisatawan Indonesia.
Kamu paham destinasi domestik maupun luar negeri, budget travelling,
transportasi, kuliner lokal, dan tips perjalanan praktis.

Aturan menjawab:
- Selalu jawab dalam Bahasa Indonesia.
- Kalau ditanya destinasi, sertakan perkiraan budget, waktu terbaik berkunjung,
  dan 2-3 rekomendasi aktivitas.
- Semua harga, durasi, dan jadwal adalah perkiraan. Katakan itu dengan jelas.
- Jangan mengarang nama hotel, nomor penerbangan, atau kontak yang tidak kamu
  ketahui pasti. Kalau tidak tahu, bilang tidak tahu.
- Ingat isi percakapan sebelumnya. Kalau user sudah menyebut destinasi, tanggal,
  atau budget, pakai informasi itu tanpa bertanya ulang.
- Kalau user mengirim lampiran, bahas isinya dulu baru kaitkan dengan rencana
  perjalanannya.
- Kalau pertanyaannya jauh dari topik perjalanan, jawab seperlunya lalu arahkan
  kembali ke rencana jalan-jalan.
- Jangan memberi nasihat medis, hukum, atau keuangan. Untuk syarat visa dan
  dokumen resmi, ingatkan user mengecek sumber resmi.
""".strip()


@dataclass(frozen=True)
class Gaya:
    label: str
    deskripsi: str
    instruksi: str
    temperature: float
    top_p: float
    top_k: int


GAYA: dict[str, Gaya] = {
    "santai": Gaya(
        label="Santai",
        deskripsi="Ngobrol akrab, cocok buat brainstorming ide liburan.",
        instruksi=(
            'Gaya bicara: santai dan akrab seperti teman jalan-jalan. Boleh pakai "kamu" '
            'dan "aku". Sesekali pakai emoji secukupnya, maksimal dua per jawaban. '
            "Kalimat pendek, tidak kaku, tidak bertele-tele."
        ),
        temperature=0.9,
        top_p=0.95,
        top_k=40,
    ),
    "formal": Gaya(
        label="Formal",
        deskripsi="Bahasa rapi untuk proposal atau perjalanan dinas.",
        instruksi=(
            'Gaya bicara: formal dan profesional. Gunakan "Anda". Tanpa emoji dan tanpa '
            "slang. Susun jawaban terstruktur dengan poin bernomor bila perlu. Cocok "
            "untuk keperluan perjalanan dinas dan laporan."
        ),
        # top_k dipersempit biar pilihan katanya konsisten dan tidak melebar.
        temperature=0.35,
        top_p=0.85,
        top_k=24,
    ),
    "hemat": Gaya(
        label="Mode Hemat",
        deskripsi="Fokus angka dan efisiensi biaya, jawaban padat.",
        instruksi=(
            "Gaya bicara: ringkas dan berorientasi angka. Prioritaskan opsi termurah "
            "yang masih masuk akal. Selalu sertakan rincian estimasi biaya dalam bentuk "
            "daftar (transport, penginapan, makan, tiket masuk) beserta totalnya. "
            "Hindari basa-basi."
        ),
        temperature=0.2,
        top_p=0.9,
        top_k=32,
    ),
}

GAYA_DEFAULT = "santai"

MODEL_KANDIDAT = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

MAX_RIWAYAT = 20
MAX_OUTPUT_TOKENS = 4096


def instruksi_sistem(kunci: str) -> str:
    gaya = GAYA.get(kunci, GAYA[GAYA_DEFAULT])
    return f"{CORE_PERSONA}\n\n{gaya.instruksi}"


def baca_error(err: Exception) -> tuple[int | None, str]:
    """Error dari SDK membungkus JSON di dalam pesannya. Dibuka dulu."""
    mentah = str(err)
    try:
        isi = json.loads(mentah).get("error", {})
        return isi.get("code"), isi.get("message", mentah)
    except (ValueError, AttributeError):
        return getattr(err, "code", None), mentah


def coba_model_lain(kode: int | None, pesan: str) -> bool:
    """Kuota free tier dihitung per model per hari, jadi 429 bukan akhir cerita."""
    if kode in (404, 429, 503):
        return True
    if kode == 403 and any(k in pesan.lower() for k in ("denied access", "not supported", "permission")):
        return True
    return False


def _konfigurasi(gaya_kunci: str, temperature: float, top_p: float, top_k: int) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=instruksi_sistem(gaya_kunci),
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )


def susun_isi(riwayat: list[dict], lampiran: tuple[bytes, str] | None) -> list[types.Content]:
    """Riwayat percakapan jadi format contents milik Gemini.

    Riwayat dipotong ke MAX_RIWAYAT pesan terakhir supaya biaya token tidak terus
    naik. Lampiran ditempel ke pesan user paling akhir.
    """
    dipakai = riwayat[-MAX_RIWAYAT:]
    terakhir = len(dipakai) - 1
    isi = []

    for i, pesan in enumerate(dipakai):
        parts = [types.Part.from_text(text=pesan["teks"])]

        if lampiran and i == terakhir and pesan["peran"] == "user":
            data, mime = lampiran
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))

        isi.append(types.Content(role=pesan["peran"], parts=parts))

    return isi


class Buddy:
    """Pembungkus client Gemini dengan fallback model."""

    def __init__(self, api_key: str, model_awal: str = MODEL_KANDIDAT[0]) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model_aktif = model_awal

    def _urutan(self) -> list[str]:
        sisa = [m for m in MODEL_KANDIDAT if m != self.model_aktif]
        return [self.model_aktif, *sisa]

    def alirkan(self, riwayat, lampiran, gaya_kunci, temperature, top_p, top_k):
        """Generator potongan teks. Model diganti kalau kandidat sekarang ditolak.

        Potongan pertama sengaja ditarik di dalam try, supaya error "model tidak
        tersedia" masih sempat memindahkan ke kandidat berikutnya sebelum ada
        satu pun teks yang terlanjur ditampilkan.
        """
        isi = susun_isi(riwayat, lampiran)
        config = _konfigurasi(gaya_kunci, temperature, top_p, top_k)
        gagal = []

        for model in self._urutan():
            try:
                aliran = self.client.models.generate_content_stream(
                    model=model, contents=isi, config=config
                )
                iterator = iter(aliran)
                pertama = next(iterator, None)

                self.model_aktif = model

                def keluaran():
                    for potongan in (p for p in (pertama, *iterator) if p is not None):
                        if potongan.text:
                            yield potongan.text

                return keluaran()

            except Exception as err:  # noqa: BLE001 - pesan aslinya diteruskan ke UI
                kode, pesan = baca_error(err)
                gagal.append(f"{model}: [{kode}] {pesan.splitlines()[0][:120]}")
                if coba_model_lain(kode, pesan):
                    continue
                raise RuntimeError(pesan) from err

        raise RuntimeError(
            "Tidak ada model Gemini yang bisa diakses API key ini.\n\n" + "\n".join(gagal)
        )
