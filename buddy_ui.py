"""Potongan CSS dan HTML supaya versi Streamlit tampil seperti versi web.

Warna dan radiusnya diambil dari client/style.css. Gradient dipisah dua: yang
cerah cuma untuk dekorasi, yang gelap untuk apa pun yang memuat teks putih,
karena versi cerahnya cuma 2.8:1 kontrasnya lawan putih.
"""

from __future__ import annotations

from html import escape

BG = "#080A14"
CARD = "#131829"
CARD_2 = "#1A2038"
CARD_3 = "#222A47"
LINE = "#262E4C"
LINE_SOFT = "#1D2440"
TEXT = "#F0F2FA"
TEXT_DIM = "#A8AECB"
TEXT_FAINT = "#8990B0"
BRAND_INK = "#A98CFF"

GRAD = "linear-gradient(135deg,#7C5CFC 0%,#E94FA1 55%,#F97316 100%)"
GRAD_INK = "linear-gradient(135deg,#5B3FD6 0%,#B32E77 55%,#B4520E 100%)"
GRAD_DIM = "linear-gradient(135deg,rgba(124,92,252,.22),rgba(233,79,161,.14))"

CSS = f"""
<style>
.stApp {{ background: {BG}; }}

[data-testid="stMainBlockContainer"] {{ padding-top: 2.2rem; max-width: 100%; }}
[data-testid="stHeader"] {{ background: transparent; }}

/* sidebar jadi kartu seperti versi web */
[data-testid="stSidebar"] {{ background: {CARD}; border-right: 1px solid {LINE_SOFT}; }}
[data-testid="stSidebarContent"] {{ padding-top: .6rem; }}

.tb-brand {{ display:flex; align-items:center; gap:10px; margin-bottom:18px; }}
.tb-mark {{
  width:32px; height:32px; border-radius:10px; background:{GRAD_INK};
  display:grid; place-items:center; color:#fff; font-size:16px; flex:none;
}}
.tb-brand-name {{ font-size:12px; font-weight:800; letter-spacing:.14em; color:{TEXT}; }}

.tb-profile {{ text-align:center; margin-bottom:16px; }}
.tb-avatar {{ width:104px; margin:0 auto 10px; }}
.tb-name {{ font-size:19px; font-weight:700; color:{TEXT}; }}
.tb-tag {{ font-size:10px; font-weight:600; letter-spacing:.13em; color:{TEXT_FAINT}; margin-top:4px; }}
.tb-pill {{
  display:inline-block; margin-top:10px; padding:5px 15px; border-radius:999px;
  background:{GRAD_INK}; color:#fff; font-size:11.5px; font-weight:700;
}}

.tb-stats {{
  display:grid; grid-template-columns:repeat(3,1fr); gap:4px;
  padding:14px 0; margin-bottom:6px;
  border-top:1px solid {LINE_SOFT}; border-bottom:1px solid {LINE_SOFT};
}}
.tb-stat {{ text-align:center; }}
.tb-stat span {{
  display:block; font-size:9.5px; font-weight:600; letter-spacing:.09em;
  text-transform:uppercase; color:{TEXT_FAINT};
}}
.tb-stat strong {{ display:block; margin-top:3px; font-size:19px; font-weight:700; color:{TEXT}; }}

.tb-chip {{
  display:flex; align-items:center; gap:8px; margin-top:14px;
  font-size:11.5px; color:{TEXT_FAINT};
}}
.tb-dot {{ width:7px; height:7px; border-radius:50%; background:#34D77F;
  box-shadow:0 0 0 3px rgba(52,215,127,.18); flex:none; }}
.tb-dot-off {{ background:#FF6B68; box-shadow:0 0 0 3px rgba(255,107,104,.18); }}

/* radio menu di sidebar dibuat seperti daftar navigasi versi web */
[data-testid="stSidebar"] [data-testid="stRadio"] {{
  background:transparent; border:0; padding:0; margin-bottom:14px;
}}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {{
  padding:9px 11px; border-radius:11px;
}}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) {{
  background:{GRAD_DIM}; box-shadow:inset 0 0 0 1px {LINE};
}}

/* kartu panel kanan */
.tb-card {{
  background:{CARD}; border:1px solid {LINE_SOFT}; border-radius:22px;
  padding:18px; margin-bottom:14px;
}}
.tb-card-title {{
  font-size:11px; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
  color:{TEXT_FAINT}; margin-bottom:14px;
}}
.tb-note {{ font-size:12px; color:{TEXT_FAINT}; line-height:1.5; margin-top:12px; }}

/* hero */
.tb-hero {{
  position:relative; overflow:hidden; padding:40px 36px;
  background:{CARD}; border:1px solid {LINE_SOFT}; border-radius:26px;
}}
.tb-orb {{ position:absolute; border-radius:50%; filter:blur(46px); }}
.tb-orb-a {{ width:260px; height:260px; top:-110px; right:-60px; background:#7C5CFC; opacity:.5; }}
.tb-orb-b {{ width:200px; height:200px; bottom:-100px; left:12%; background:#E94FA1; opacity:.35; }}
.tb-orb-c {{ width:160px; height:160px; top:32%; right:26%; background:#F97316; opacity:.22; }}
.tb-hero > *:not(.tb-orb) {{ position:relative; }}
.tb-kicker {{ font-size:10.5px; font-weight:700; letter-spacing:.16em; color:{BRAND_INK}; }}
.tb-title {{
  margin-top:14px; font-size:clamp(24px,3vw,38px); font-weight:800;
  letter-spacing:-.03em; line-height:1.2; color:{TEXT};
}}
.tb-title em {{
  font-style:normal; background:{GRAD};
  -webkit-background-clip:text; background-clip:text; color:transparent;
}}
.tb-sub {{ margin-top:14px; max-width:46ch; font-size:14.5px; color:{TEXT_DIM}; }}

/* gelembung pesan */
[data-testid="stChatMessage"] {{ background:transparent; padding:.2rem 0; gap:.6rem; }}

[data-testid="stChatMessage"]:has(.tb-user) {{ flex-direction:row-reverse; }}
[data-testid="stChatMessage"]:has(.tb-user) [data-testid="stChatMessageContent"] {{
  display:flex; justify-content:flex-end;
}}
[data-testid="stChatMessage"]:has(.tb-user) [data-testid="stMarkdownContainer"] {{
  background:{GRAD_INK}; color:#fff; padding:12px 17px;
  border-radius:18px 18px 6px 18px; max-width:78%;
}}
[data-testid="stChatMessage"]:has(.tb-bot) [data-testid="stMarkdownContainer"] {{
  background:{CARD}; border:1px solid {LINE_SOFT}; color:{TEXT};
  padding:12px 17px; border-radius:18px 18px 18px 6px;
}}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p:last-child {{ margin-bottom:0; }}
.tb-user, .tb-bot {{ display:none; }}

/* input chat */
[data-testid="stBottomBlockContainer"] {{ background:{BG}; padding-bottom:1.2rem; }}
[data-testid="stChatInput"] {{
  background:{CARD}; border:1px solid {LINE}; border-radius:22px;
}}
[data-testid="stChatInput"]:focus-within {{ border-color:#8B6DFF; }}
[data-testid="stChatInputTextArea"] {{ color:{TEXT}; }}

/* radio gaya bahasa dijadikan kartu, labelnya jadi judul kartu */
[data-testid="stRadio"] {{
  background:{CARD}; border:1px solid {LINE_SOFT}; border-radius:22px;
  padding:18px; margin-bottom:14px;
}}
[data-testid="stRadio"] > label p {{
  font-size:11px !important; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; color:{TEXT_FAINT};
}}
[data-testid="stRadioGroup"] {{ gap:2px; }}
[data-testid="stRadioOption"] p {{ color:{TEXT}; }}
[data-testid="stSliderThumbValue"] {{ color:{BRAND_INK}; }}
[data-testid="stExpander"] {{ border-color:{LINE_SOFT}; border-radius:14px; background:{CARD_2}; }}
[data-testid="stFileUploaderDropzone"] {{
  background:{CARD_2}; border:1px dashed {LINE}; border-radius:14px;
}}
[data-testid="stButton"] button {{ border-radius:11px; border:1px solid {LINE_SOFT}; }}
[data-testid="stMetricValue"] {{ font-size:22px; }}

/* bar waktu respons */
.tb-bars {{ display:flex; align-items:flex-end; justify-content:center; gap:6px; height:76px; }}
.tb-bars i {{
  flex:1; max-width:26px; background:{GRAD};
  border-radius:999px 999px 4px 4px; display:block;
}}
.tb-empty {{ font-size:12px; color:{TEXT_FAINT}; text-align:center; padding:28px 0 4px; margin:0; }}

.tb-disclaimer {{
  font-size:11.5px; color:{TEXT_FAINT}; text-align:center; margin-top:10px;
}}

/* daftar key-value */
.tb-kv {{ margin:0; padding:0; list-style:none; }}
.tb-kv li {{
  display:flex; justify-content:space-between; gap:12px; padding:9px 0;
  border-bottom:1px solid {LINE_SOFT}; font-size:13px; color:{TEXT_DIM};
}}
.tb-kv li:last-child {{ border-bottom:0; }}
.tb-kv strong {{ color:{TEXT}; font-weight:700; }}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration:.01ms !important; transition-duration:.01ms !important; }}
}}
</style>
"""

AVATAR_SVG = """
<div class="tb-avatar"><svg viewBox="0 0 96 96" width="104" height="104" aria-hidden="true">
  <defs><linearGradient id="tbav" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#7C5CFC"/><stop offset="55%" stop-color="#E94FA1"/>
    <stop offset="100%" stop-color="#F97316"/></linearGradient></defs>
  <circle cx="48" cy="48" r="46" fill="none" stroke="url(#tbav)" stroke-width="3"/>
  <circle cx="48" cy="48" r="38" fill="rgba(124,92,252,.14)"/>
  <g fill="none" stroke="url(#tbav)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="48" cy="48" r="21"/><path d="m57 39-5 14-14 5 5-14z"/>
  </g></svg></div>
"""

HERO = """
<div class="tb-hero">
  <span class="tb-orb tb-orb-a"></span><span class="tb-orb tb-orb-b"></span><span class="tb-orb tb-orb-c"></span>
  <p class="tb-kicker">ASISTEN PERJALANAN</p>
  <h2 class="tb-title">Rencana matang<br>bikin jalan-jalan <em>tenang.</em></h2>
  <p class="tb-sub">Tanya destinasi, itinerary, atau budget. Lampirkan foto tempat,
  dokumen rencana, atau rekaman suara lewat sidebar &mdash; semuanya dibaca.</p>
</div>
"""


def sidebar_profil(gaya_label: str, pesan: int, menit: int, lampiran: int) -> str:
    return f"""
<div class="tb-brand"><span class="tb-mark">&#129517;</span>
  <span class="tb-brand-name">TRAVEL BUDDY</span></div>
<div class="tb-profile">
  {AVATAR_SVG}
  <div class="tb-name">Travel Buddy</div>
  <div class="tb-tag">JELAJAH &middot; RENCANA &middot; NIKMATI</div>
  <span class="tb-pill">{escape(gaya_label)}</span>
</div>
<div class="tb-stats">
  <div class="tb-stat"><span>Pesan</span><strong>{pesan}</strong></div>
  <div class="tb-stat"><span>Menit</span><strong>{menit}</strong></div>
  <div class="tb-stat"><span>Lampiran</span><strong>{lampiran}</strong></div>
</div>
"""


def panel_judul(judul: str, sub: str) -> str:
    return (
        f'<h2 style="font-size:23px;font-weight:700;color:{TEXT};margin:0">{escape(judul)}</h2>'
        f'<p style="margin:6px 0 16px;color:{TEXT_DIM};font-size:14px">{escape(sub)}</p>'
    )


def tentang(gaya_semua) -> str:
    kartu_gaya = "".join(
        f'<div style="padding:11px 13px;background:{CARD_2};border-radius:11px;margin-bottom:8px">'
        f'<b style="font-size:13.5px;color:{TEXT}">{escape(g.label)}</b>'
        f'<small style="display:block;margin-top:3px;font-size:12px;color:{TEXT_FAINT}">{escape(g.deskripsi)}</small>'
        f'<div style="margin-top:7px;font-size:11.5px;color:{BRAND_INK}">'
        f'temperature {g.temperature} &middot; top_p {g.top_p} &middot; top_k {g.top_k}</div></div>'
        for g in gaya_semua.values()
    )

    return f"""
<div class="tb-card">
  <h3 style="font-size:15.5px;color:{TEXT};margin:0 0 10px">Cara kerjanya</h3>
  <p style="color:{TEXT_DIM};font-size:13.5px;margin:0 0 10px">Seluruh riwayat percakapan dikirim
  ulang ke Gemini tiap giliran, jadi bot ingat destinasi dan budget yang sudah disebut.
  System instruction dan preset parameter menyesuaikan gaya bahasa yang dipilih.</p>
  <p style="color:{TEXT_DIM};font-size:13.5px;margin:0">API key disimpan di secrets server,
  tidak pernah ikut ke dalam repo.</p>
</div>
<div class="tb-card">
  <h3 style="font-size:15.5px;color:{TEXT};margin:0 0 10px">Gaya bahasa</h3>
  {kartu_gaya}
</div>
<div class="tb-card">
  <h3 style="font-size:15.5px;color:{TEXT};margin:0 0 10px">Dua versi</h3>
  <p style="color:{TEXT_DIM};font-size:13.5px;margin:0">Aplikasi ini punya versi Express + vanilla JS
  (folder <code>client/</code> dan <code>server/</code>) dan versi Streamlit ini. Keduanya memakai
  persona, preset parameter, dan urutan fallback model yang sama.</p>
</div>
"""


def gauge(temperature: float) -> str:
    """Ring kreativitas, sama seperti panel kanan versi web."""
    persen = round(temperature / 2 * 100)
    keliling = 314
    offset = keliling - keliling * persen / 100
    label = "Presisi" if temperature <= 0.5 else "Seimbang" if temperature <= 1 else "Kreatif"

    return f"""
<div class="tb-card">
  <div class="tb-card-title">Kreativitas</div>
  <div style="position:relative;width:152px;margin:0 auto;">
    <svg viewBox="0 0 120 120" width="152" height="152" style="transform:rotate(-90deg);display:block">
      <defs><linearGradient id="tbring" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#7C5CFC"/><stop offset="55%" stop-color="#E94FA1"/>
        <stop offset="100%" stop-color="#F97316"/></linearGradient></defs>
      <circle cx="60" cy="60" r="50" fill="none" stroke="{CARD_3}" stroke-width="9"/>
      <circle cx="60" cy="60" r="50" fill="none" stroke="url(#tbring)" stroke-width="9"
              stroke-linecap="round" stroke-dasharray="{keliling}" stroke-dashoffset="{offset}"/>
    </svg>
    <div style="position:absolute;inset:0;display:grid;place-content:center;justify-items:center;gap:3px">
      <div style="display:flex;align-items:baseline;gap:2px">
        <strong style="font-size:31px;font-weight:700;color:{TEXT};line-height:1">{persen}</strong>
        <span style="font-size:13px;color:{TEXT_FAINT}">%</span>
      </div>
      <em style="font-style:normal;font-size:10px;font-weight:600;letter-spacing:.09em;
                 text-transform:uppercase;color:{TEXT_FAINT}">{label}</em>
    </div>
  </div>
  <p class="tb-note">Dihitung dari <code>temperature</code> aktif.</p>
</div>
"""


def bar_respons(detik: list[float]) -> str:
    if not detik:
        isi = '<p class="tb-empty">Belum ada balasan.</p>'
        rata = "&mdash;"
    else:
        pakai = detik[-12:]
        puncak = max(pakai)
        batang = "".join(
            f'<i style="height:{max(6, d / puncak * 100):.0f}%"></i>' for d in pakai
        )
        isi = f'<div class="tb-bars">{batang}</div>'
        rata = f"{sum(detik) / len(detik):.1f} detik"

    return f"""
<div class="tb-card">
  <div class="tb-card-title">Waktu Respons</div>
  {isi}
  <p class="tb-note">{rata} rata-rata per balasan</p>
</div>
"""


def kartu_sesi(giliran: int, konteks: int, karakter: int) -> str:
    return f"""
<div class="tb-card">
  <div class="tb-card-title">Sesi Ini</div>
  <ul class="tb-kv">
    <li><span>Giliran percakapan</span><strong>{giliran}</strong></li>
    <li><span>Konteks terkirim</span><strong>{konteks}</strong></li>
    <li><span>Karakter dibalas</span><strong>{karakter:,}</strong></li>
  </ul>
</div>
""".replace(",", ".")
