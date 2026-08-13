"""Travel Buddy versi Streamlit.

Tampilan dan persona dibuat mengikuti versi web di client/ dan server/, supaya
dua-duanya terasa seperti aplikasi yang sama. Versi ini dipakai untuk deploy ke
Streamlit Community Cloud, yang hanya menjalankan Python.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import streamlit as st

import buddy_ui as ui
from buddy_core import GAYA, GAYA_DEFAULT, MAX_RIWAYAT, MODEL_KANDIDAT, Buddy

st.set_page_config(
    page_title="Travel Buddy — Asisten Perjalanan AI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

MENU = ["Percakapan", "Uji Multimodal", "Tentang"]

CONTOH = {
    "Itinerary Yogyakarta 3 hari": "Buatkan itinerary 3 hari di Yogyakarta dengan budget 1,5 juta.",
    "Bali vs Lombok": "Bandingkan Bali dan Lombok untuk honeymoon 5 hari.",
    "Pertama kali ke Jepang": "Apa saja yang perlu disiapkan untuk pertama kali ke Jepang saat musim semi?",
    "Kuliner malam Bandung": "Rekomendasi kuliner malam murah di Bandung beserta perkiraan harganya.",
}

MODE_UJI = {
    "Teks": ("Rekomendasi liburan 3 hari di Bali dengan budget 2 juta", None),
    "Gambar": ("Deskripsikan gambar ini dan berikan tips wisatanya", ["png", "jpg", "jpeg", "webp", "gif"]),
    "Dokumen": ("Ringkas dokumen ini dalam poin-poin penting", ["pdf", "txt", "md", "csv"]),
    "Audio": ("Transkrip audio ini lalu ringkas isinya", ["mp3", "wav", "m4a", "ogg"]),
}

MIME_EKSTENSI = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif",
    ".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/md",
    ".csv": "text/csv",
    ".mp3": "audio/mp3", ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg",
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
    st.session_state.setdefault("durasi", [])
    st.session_state.setdefault("karakter", 0)
    st.session_state.setdefault("lampiran_terkirim", 0)
    st.session_state.setdefault("mulai", time.time())


def reset_percakapan() -> None:
    st.session_state.riwayat = []
    st.session_state.antre = None
    st.session_state.durasi = []
    st.session_state.karakter = 0
    st.session_state.lampiran_terkirim = 0


siapkan_sesi()
st.markdown(ui.CSS, unsafe_allow_html=True)

riwayat = st.session_state.riwayat
gaya = GAYA[st.session_state.gaya]
pesan_user = sum(1 for p in riwayat if p["peran"] == "user")
menit = int((time.time() - st.session_state.mulai) // 60)

with st.sidebar:
    st.markdown(
        ui.sidebar_profil(gaya.label, pesan_user, menit, st.session_state.lampiran_terkirim),
        unsafe_allow_html=True,
    )

    menu = st.radio("Menu", MENU, label_visibility="collapsed", key="menu")

    key_bawaan = api_key_tersimpan()

    with st.expander("Pengaturan", expanded=not key_bawaan):
        if key_bawaan:
            st.caption("API key terbaca dari secrets server.")
            api_key = key_bawaan
        else:
            api_key = st.text_input(
                "Google AI API Key",
                type="password",
                placeholder="Tempel API key di sini",
                help="Gratis di https://aistudio.google.com → Get API Key",
            )

        model_awal = st.selectbox("Model Gemini", MODEL_KANDIDAT, index=0)

    lampiran = st.file_uploader("Lampiran", type=TIPE_DITERIMA, label_visibility="collapsed")
    st.caption("Foto tempat, dokumen rencana, atau rekaman suara. Ikut dibaca model.")

    if st.button("Percakapan baru", use_container_width=True):
        reset_percakapan()
        st.rerun()

    # Diisi belakangan: model aktif baru diketahui setelah client dibuat.
    slot_model = st.empty()

# Client cuma dibuat kalau key-nya ada. Tanpa key aplikasi tetap tampil utuh,
# hanya kotak kirimnya yang dimatikan.
buddy: Buddy | None = None
if api_key:
    sidik = (api_key, model_awal)
    if st.session_state.sidik != sidik:
        st.session_state.buddy = Buddy(api_key, model_awal)
        st.session_state.sidik = sidik
    buddy = st.session_state.buddy

slot_model.markdown(
    f'<p class="tb-chip"><span class="tb-dot{"" if buddy else " tb-dot-off"}"></span>'
    f'{buddy.model_aktif if buddy else "API key belum diisi"}</p>',
    unsafe_allow_html=True,
)

kolom_chat, kolom_rail = st.columns([2.15, 1], gap="medium")

with kolom_rail:
    st.markdown(ui.gauge(gaya.temperature), unsafe_allow_html=True)

    label = [g.label for g in GAYA.values()]
    kunci = list(GAYA.keys())
    dipilih = st.radio(
        "Gaya Bahasa",
        label,
        captions=[g.deskripsi for g in GAYA.values()],
        index=kunci.index(st.session_state.gaya),
    )
    if kunci[label.index(dipilih)] != st.session_state.gaya:
        st.session_state.gaya = kunci[label.index(dipilih)]
        st.rerun()

    with st.expander("Parameter", expanded=False):
        temperature = st.slider("Temperature", 0.0, 2.0, gaya.temperature, 0.1)
        top_p = st.slider("Top P", 0.0, 1.0, gaya.top_p, 0.05)
        top_k = st.slider("Top K", 1, 40, gaya.top_k, 1)
        st.caption("Nilai awal mengikuti preset gaya bahasa.")

    st.markdown(ui.bar_respons(st.session_state.durasi), unsafe_allow_html=True)
    st.markdown(
        ui.kartu_sesi(len(riwayat), min(len(riwayat), MAX_RIWAYAT), st.session_state.karakter),
        unsafe_allow_html=True,
    )

with kolom_chat:
    if menu == "Percakapan":
        if not riwayat:
            st.markdown(ui.HERO, unsafe_allow_html=True)

            tombol = st.columns(2)
            for i, judul in enumerate(CONTOH):
                if tombol[i % 2].button(judul, use_container_width=True, key=f"contoh-{i}", disabled=not buddy):
                    st.session_state.antre = CONTOH[judul]
                    st.rerun()

        for pesan in riwayat:
            peran = "user" if pesan["peran"] == "user" else "assistant"
            with st.chat_message(peran, avatar=None if peran == "user" else "🧭"):
                # Penanda tersembunyi ini yang dipakai CSS untuk membedakan gelembung
                # user dan bot, karena Streamlit tidak menandai perannya di DOM.
                st.markdown(f'<span class="tb-{"user" if peran == "user" else "bot"}"></span>', unsafe_allow_html=True)
                st.markdown(pesan["teks"])
                if pesan.get("berkas"):
                    st.caption(f"📎 {pesan['berkas']}")
                if pesan.get("model"):
                    st.caption(f"model: {pesan['model']}")

        if not api_key:
            st.info(
                "Masukkan **Google AI API Key** di sidebar untuk mulai mengobrol. "
                "Key gratis bisa diambil di [aistudio.google.com](https://aistudio.google.com) → **Get API Key**.",
                icon="🔑",
            )

        st.markdown(
            '<p class="tb-disclaimer">Dijawab oleh AI. Harga, jadwal, dan syarat dokumen '
            'tetap perlu dicek di sumber resmi.</p>',
            unsafe_allow_html=True,
        )

    elif menu == "Uji Multimodal":
        st.markdown(ui.panel_judul(
            "Uji Multimodal",
            "Empat jenis input diuji satu per satu, terpisah dari percakapan.",
        ), unsafe_allow_html=True)

        jenis = st.radio("Jenis input", list(MODE_UJI), horizontal=True, label_visibility="collapsed")
        contoh_prompt, tipe = MODE_UJI[jenis]

        berkas_uji = None
        if tipe:
            berkas_uji = st.file_uploader(f"Berkas {jenis.lower()}", type=tipe, key=f"uji-{jenis}")

        prompt_uji = st.text_area("Prompt", value=contoh_prompt, height=90)

        if st.button("Jalankan", disabled=not buddy):
            if tipe and berkas_uji is None:
                st.warning(f"Pilih berkas {jenis.lower()} dulu.")
            else:
                lampiran_uji = None
                if berkas_uji is not None:
                    lampiran_uji = (berkas_uji.getvalue(), tebak_mime(berkas_uji))

                with st.chat_message("assistant", avatar="🧭"):
                    st.markdown('<span class="tb-bot"></span>', unsafe_allow_html=True)
                    try:
                        st.write_stream(buddy.alirkan(
                            [{"peran": "user", "teks": prompt_uji}],
                            lampiran_uji,
                            st.session_state.gaya,
                            temperature, top_p, top_k,
                        ))
                        st.caption(f"model: {buddy.model_aktif}")
                    except RuntimeError as err:
                        st.error(str(err), icon="⚠️")

        if not api_key:
            st.info("Isi API key di sidebar untuk menjalankan pengujian.", icon="🔑")

    else:
        st.markdown(ui.panel_judul(
            "Tentang Proyek",
            "Chatbot asisten perjalanan berbasis Google Gemini.",
        ), unsafe_allow_html=True)
        st.markdown(ui.tentang(GAYA), unsafe_allow_html=True)

if menu == "Percakapan":
    diketik = st.chat_input(
        "Mau ke mana kali ini?" if buddy else "Isi API key di sidebar dulu",
        disabled=not buddy,
    )
    prompt = diketik or st.session_state.antre
    st.session_state.antre = None
else:
    prompt = None

if prompt and buddy:
    berkas = None
    if lampiran is not None:
        try:
            berkas = (lampiran.getvalue(), tebak_mime(lampiran))
        except ValueError as err:
            st.error(str(err))
            st.stop()

    riwayat.append({
        "peran": "user",
        "teks": prompt,
        "berkas": lampiran.name if lampiran is not None else None,
    })

    with kolom_chat:
        with st.chat_message("user"):
            st.markdown('<span class="tb-user"></span>', unsafe_allow_html=True)
            st.markdown(prompt)
            if lampiran is not None:
                st.caption(f"📎 {lampiran.name}")

        with st.chat_message("assistant", avatar="🧭"):
            st.markdown('<span class="tb-bot"></span>', unsafe_allow_html=True)
            mulai = time.time()
            try:
                jawaban = st.write_stream(
                    buddy.alirkan(riwayat, berkas, st.session_state.gaya, temperature, top_p, top_k)
                )
            except RuntimeError as err:
                catatan = str(err)
                st.error(catatan, icon="⚠️")

                if "429" in catatan or "quota" in catatan.lower():
                    st.info(
                        "Kuota Gemini free tier dihitung **per model per hari**. Coba ganti model "
                        "di sidebar, atau pakai API key sendiri lewat Pengaturan.",
                        icon="💡",
                    )

                # Pesan yang gagal dijawab dibuang, biar tidak menggantung di konteks.
                riwayat.pop()
                st.stop()

    st.session_state.durasi.append(time.time() - mulai)
    st.session_state.karakter += len(jawaban)
    if lampiran is not None:
        st.session_state.lampiran_terkirim += 1

    riwayat.append({
        "peran": "model",
        "teks": jawaban,
        "berkas": None,
        "model": buddy.model_aktif,
    })

    # Sidebar dan panel kanan sudah dirender dengan riwayat versi lama, jadi
    # angkanya tertinggal satu giliran tanpa rerun.
    st.rerun()
