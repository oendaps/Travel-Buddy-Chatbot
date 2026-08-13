"""Travel Buddy versi Streamlit.

Versi ini dipakai untuk deploy ke Streamlit Community Cloud. Aplikasi utamanya
ada di client/ dan server/ (Express + vanilla JS); yang ini memakai persona dan
aturan model yang sama lewat buddy_core.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from buddy_core import GAYA, GAYA_DEFAULT, MODEL_KANDIDAT, Buddy

st.set_page_config(
    page_title="Travel Buddy — Asisten Perjalanan AI",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="expanded",
)

SAPAAN = (
    "Halo! Aku **Travel Buddy** 🧭\n\n"
    "Tanya soal destinasi, itinerary, atau budget. Kamu juga bisa melampirkan foto "
    "tempat, dokumen rencana perjalanan, atau rekaman suara lewat sidebar."
)

CONTOH = [
    "Itinerary Yogyakarta 3 hari",
    "Bali vs Lombok untuk honeymoon",
    "Pertama kali ke Jepang",
    "Kuliner malam murah di Bandung",
]

PROMPT_PENUH = {
    "Itinerary Yogyakarta 3 hari": "Buatkan itinerary 3 hari di Yogyakarta dengan budget 1,5 juta.",
    "Bali vs Lombok untuk honeymoon": "Bandingkan Bali dan Lombok untuk honeymoon 5 hari.",
    "Pertama kali ke Jepang": "Apa saja yang perlu disiapkan untuk pertama kali ke Jepang saat musim semi?",
    "Kuliner malam murah di Bandung": "Rekomendasi kuliner malam murah di Bandung beserta perkiraan harganya.",
}

MIME_EKSTENSI = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".heic": "image/heic",
    ".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/md",
    ".csv": "text/csv", ".json": "text/plain",
    ".mp3": "audio/mp3", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".aac": "audio/aac", ".ogg": "audio/ogg", ".flac": "audio/flac",
}

TIPE_DITERIMA = ["png", "jpg", "jpeg", "webp", "gif", "pdf", "txt", "md", "csv", "mp3", "wav", "m4a", "ogg"]


def api_key_tersimpan() -> str:
    """Urutan: secrets Streamlit Cloud, environment, lalu kosong.

    API key tidak pernah ditulis di dalam kode. Repo ini publik, dan bot pemindai
    GitHub akan menemukan key yang ter-commit dalam hitungan menit.
    """
    try:
        nilai = st.secrets.get("GEMINI_API_KEY", "")
        if nilai:
            return str(nilai)
    except Exception:
        pass  # .streamlit/secrets.toml memang belum ada saat jalan lokal
    return os.environ.get("GEMINI_API_KEY", "")


def tebak_mime(berkas) -> str:
    """Browser kadang mengirim application/octet-stream, dan Gemini menolaknya."""
    bawaan = (berkas.type or "").strip()
    if bawaan and "octet-stream" not in bawaan:
        return bawaan

    ekstensi = Path(berkas.name).suffix.lower()
    if ekstensi in MIME_EKSTENSI:
        return MIME_EKSTENSI[ekstensi]

    raise ValueError(f'Tipe berkas "{berkas.name}" tidak dikenali. Pakai gambar, PDF, teks, atau audio.')


def siapkan_sesi() -> None:
    st.session_state.setdefault("riwayat", [])
    st.session_state.setdefault("gaya", GAYA_DEFAULT)
    st.session_state.setdefault("antre", None)
    st.session_state.setdefault("buddy", None)
    st.session_state.setdefault("sidik", None)


def reset_percakapan() -> None:
    st.session_state.riwayat = []
    st.session_state.antre = None


siapkan_sesi()

with st.sidebar:
    st.markdown("### 🧭 Travel Buddy")
    st.caption("JELAJAH · RENCANA · NIKMATI")

    key_bawaan = api_key_tersimpan()

    with st.expander("⚙️ Pengaturan", expanded=not key_bawaan):
        if key_bawaan:
            st.success("API key terbaca dari secrets/environment.", icon="🔑")
            api_key = key_bawaan
        else:
            api_key = st.text_input(
                "Google AI API Key",
                type="password",
                placeholder="Tempel API key di sini",
                help="Gratis di https://aistudio.google.com → Get API Key",
            )

        model_awal = st.selectbox(
            "Model Gemini",
            MODEL_KANDIDAT,
            index=0,
            help="Kalau kuota model ini habis, aplikasi otomatis pindah ke kandidat berikutnya.",
        )

    st.divider()

    label_gaya = [g.label for g in GAYA.values()]
    kunci_gaya = list(GAYA.keys())
    pilihan = st.radio(
        "Gaya bahasa",
        label_gaya,
        index=kunci_gaya.index(st.session_state.gaya),
        horizontal=False,
    )
    st.session_state.gaya = kunci_gaya[label_gaya.index(pilihan)]
    gaya = GAYA[st.session_state.gaya]
    st.caption(gaya.deskripsi)

    with st.expander("🎛️ Parameter", expanded=False):
        temperature = st.slider("Temperature", 0.0, 2.0, gaya.temperature, 0.1)
        top_p = st.slider("Top P", 0.0, 1.0, gaya.top_p, 0.05)
        top_k = st.slider("Top K", 1, 40, gaya.top_k, 1)
        st.caption("Nilai awal mengikuti preset gaya bahasa. Geser untuk menimpanya.")

    st.divider()

    lampiran = st.file_uploader(
        "Lampiran (opsional)",
        type=TIPE_DITERIMA,
        help="Foto tempat, dokumen rencana, atau rekaman suara. Ikut dibaca model.",
    )

    st.divider()

    st.metric("Giliran percakapan", len(st.session_state.riwayat))

    if st.button("🔄 Percakapan Baru", use_container_width=True):
        reset_percakapan()
        st.rerun()

    st.caption("Dibuat dengan Streamlit + Google Gemini")

st.title("🧭 Travel Buddy")
st.caption("Asisten perjalanan berbahasa Indonesia — rencanakan destinasi, itinerary, dan budget")

if not api_key:
    st.info(
        "Masukkan **Google AI API Key** di sidebar untuk mulai mengobrol.\n\n"
        "Key gratis bisa diambil di [aistudio.google.com](https://aistudio.google.com) "
        "→ **Get API Key**.",
        icon="🔑",
    )
    st.stop()

# Client dibuat ulang hanya kalau key atau model awalnya berubah.
sidik = (api_key, model_awal)
if st.session_state.sidik != sidik:
    st.session_state.buddy = Buddy(api_key, model_awal)
    st.session_state.sidik = sidik

buddy: Buddy = st.session_state.buddy

if not st.session_state.riwayat:
    with st.chat_message("assistant", avatar="🧭"):
        st.markdown(SAPAAN)

    kolom = st.columns(2)
    for i, judul in enumerate(CONTOH):
        if kolom[i % 2].button(judul, use_container_width=True, key=f"contoh-{i}"):
            st.session_state.antre = PROMPT_PENUH[judul]
            st.rerun()

for pesan in st.session_state.riwayat:
    peran = "user" if pesan["peran"] == "user" else "assistant"
    with st.chat_message(peran, avatar=None if peran == "user" else "🧭"):
        st.markdown(pesan["teks"])
        if pesan.get("berkas"):
            st.caption(f"📎 {pesan['berkas']}")
        if pesan.get("model"):
            st.caption(f"model: {pesan['model']}")

diketik = st.chat_input("Mau ke mana kali ini?")
prompt = diketik or st.session_state.antre
st.session_state.antre = None

if prompt:
    berkas = None
    if lampiran is not None:
        try:
            berkas = (lampiran.getvalue(), tebak_mime(lampiran))
        except ValueError as err:
            st.error(str(err))
            st.stop()

    st.session_state.riwayat.append({
        "peran": "user",
        "teks": prompt,
        "berkas": lampiran.name if lampiran is not None else None,
    })

    with st.chat_message("user"):
        st.markdown(prompt)
        if lampiran is not None:
            st.caption(f"📎 {lampiran.name}")

    with st.chat_message("assistant", avatar="🧭"):
        try:
            aliran = buddy.alirkan(
                st.session_state.riwayat,
                berkas,
                st.session_state.gaya,
                temperature,
                top_p,
                top_k,
            )
            jawaban = st.write_stream(aliran)
        except RuntimeError as err:
            pesan = str(err)
            st.error(pesan, icon="⚠️")

            if "429" in pesan or "quota" in pesan.lower():
                st.info(
                    "Kuota Gemini free tier dihitung **per model per hari**. Coba ganti "
                    "model di sidebar, atau pakai API key sendiri lewat Pengaturan.",
                    icon="💡",
                )

            # Pesan yang gagal dijawab dibuang, biar tidak menggantung di konteks.
            st.session_state.riwayat.pop()
            st.stop()

    st.session_state.riwayat.append({
        "peran": "model",
        "teks": jawaban,
        "berkas": None,
        "model": buddy.model_aktif,
    })

    # Sidebar sudah dirender di atas dengan riwayat versi lama, jadi hitungannya
    # tertinggal satu giliran. Rerun bikin angkanya ikut jawaban yang baru masuk.
    st.rerun()

st.caption("Dijawab oleh AI. Harga, jadwal, dan syarat dokumen tetap perlu dicek di sumber resmi.")
