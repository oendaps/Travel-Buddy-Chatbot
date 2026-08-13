const $ = (id) => document.getElementById(id);

const SLIDERS = ['temperature', 'topP', 'topK'];
const GAUGE_CIRCUMFERENCE = 314;
const MAX_BARS = 12;

let conversation = [];
let presets = {};
let pendingFile = null;
let busy = false;
let contextLimit = 20;
let maxFileMB = 20;

function announce(text) {
  $('sr-status').textContent = text;
}

const startedAt = Date.now();
const latencies = [];
const counters = { sent: 0, files: 0, chars: 0 };

// tema

const savedTheme = localStorage.getItem('tb-theme');
if (savedTheme) document.documentElement.dataset.theme = savedTheme;
paintThemeButton();

$('theme-toggle').addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('tb-theme', next);
  paintThemeButton();
});

function paintThemeButton() {
  const dark = document.documentElement.dataset.theme === 'dark';
  $('theme-icon').firstElementChild.setAttribute('href', dark ? '#i-sun' : '#i-moon');
  $('theme-label').textContent = dark ? 'Terang' : 'Gelap';
}

// navigasi panel

document.querySelectorAll('.nav-item').forEach((btn) => {
  btn.addEventListener('click', () => showPanel(btn.dataset.panel));
});

function showPanel(name) {
  document.querySelectorAll('.nav-item').forEach((b) => {
    const on = b.dataset.panel === name;
    b.classList.toggle('is-active', on);
    if (on) b.setAttribute('aria-current', 'page');
    else b.removeAttribute('aria-current');
  });

  document.querySelectorAll('.panel').forEach((p) => {
    const on = p.dataset.panel === name;
    p.classList.toggle('is-active', on);
    p.hidden = !on;
  });

  closeDrawer();
}

const drawerBtn = $('drawer-toggle');

drawerBtn.addEventListener('click', () => {
  const open = $('sidebar').classList.toggle('open');
  drawerBtn.setAttribute('aria-expanded', String(open));
  syncDrawerState();
  if (open) $('sidebar').querySelector('.nav-item')?.focus();
  else drawerBtn.focus();
});

function closeDrawer() {
  if (!$('sidebar').classList.contains('open')) return;
  $('sidebar').classList.remove('open');
  drawerBtn.setAttribute('aria-expanded', 'false');
  syncDrawerState();
}

// Sidebar yang tertutup masih di luar layar tapi tetap bisa di-Tab, jadi
// isinya dinonaktifkan lewat inert selama drawer ditutup di layar kecil.
function syncDrawerState() {
  const sidebar = $('sidebar');
  const mobile = window.matchMedia('(max-width: 860px)').matches;
  sidebar.inert = mobile && !sidebar.classList.contains('open');
}

window.addEventListener('resize', syncDrawerState);

document.addEventListener('click', (e) => {
  if (window.innerWidth > 860) return;
  if (e.target.closest('#sidebar') || e.target.closest('#drawer-toggle')) return;
  closeDrawer();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeDrawer();
});

// render teks

function esc(text) {
  return text.replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function inline(text) {
  return esc(text)
    .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s.,!?)]|$)/g, '$1<em>$2</em>')
    .replace(/`([^`\n]+)`/g, '<code>$1</code>');
}

// Markdown seadanya: heading, bullet, paragraf. Cukup untuk output Gemini.
function render(text) {
  const blocks = [];
  let list = null;

  const flush = () => {
    if (list) { blocks.push(`<ul>${list.join('')}</ul>`); list = null; }
  };

  for (const raw of text.split('\n')) {
    const line = raw.trim();

    if (!line) { flush(); continue; }

    if (/^#{1,6}\s/.test(line)) {
      flush();
      blocks.push(`<h4>${inline(line.replace(/^#{1,6}\s+/, ''))}</h4>`);
      continue;
    }

    if (/^([*-]|\d+\.)\s+/.test(line)) {
      const item = line.replace(/^([*-]|\d+\.)\s+/, '');
      (list ??= []).push(`<li>${inline(item)}</li>`);
      continue;
    }

    if (/^([-*_])\1{2,}$/.test(line)) { flush(); continue; }

    flush();
    blocks.push(`<p>${inline(line)}</p>`);
  }

  flush();
  return blocks.join('');
}

// gelembung pesan

function icon(name) {
  return `<svg class="ico"><use href="#${name}"/></svg>`;
}

function addMessage(role, text, { file = null, error = false } = {}) {
  $('hero').hidden = true;

  const wrap = document.createElement('div');
  wrap.className = `msg ${role === 'user' ? 'user' : 'bot'}${error ? ' error' : ''}`;

  const meta = document.createElement('div');
  meta.className = 'msg-meta';
  meta.innerHTML = role === 'user'
    ? 'Kamu'
    : 'Travel Buddy <span class="ai-badge">AI</span>';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  if (role === 'user') {
    bubble.textContent = text;
    if (file) {
      const tag = document.createElement('span');
      tag.className = 'file-tag';
      tag.innerHTML = `${icon(fileIcon(file))}<span></span>`;
      tag.lastElementChild.textContent = file.name;
      bubble.append(tag);
    }
  } else {
    bubble.innerHTML = render(text);
  }

  wrap.append(meta, bubble);
  $('chat-box').append(wrap);
  scrollDown();

  return { wrap, bubble };
}

function addBotActions(wrap, getText) {
  // Regenerate selalu mengulang giliran terakhir, jadi tombolnya cuma boleh ada
  // di balasan paling bawah. Kalau tidak, klik di balasan lama diam-diam
  // mengubah yang lain.
  document.querySelectorAll('.msg-actions').forEach((old) => old.remove());

  const bar = document.createElement('div');
  bar.className = 'msg-actions';

  const copy = document.createElement('button');
  copy.type = 'button';
  copy.title = 'Salin jawaban';
  copy.setAttribute('aria-label', 'Salin jawaban');
  copy.innerHTML = icon('i-copy');
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(getText());
      copy.innerHTML = icon('i-check');
      toast('Jawaban disalin');
      setTimeout(() => { copy.innerHTML = icon('i-copy'); }, 1600);
    } catch {
      toast('Browser menolak akses clipboard');
    }
  });

  const again = document.createElement('button');
  again.type = 'button';
  again.title = 'Minta jawaban lain';
  again.setAttribute('aria-label', 'Minta jawaban lain');
  again.innerHTML = icon('i-refresh');
  again.addEventListener('click', regenerate);

  bar.append(copy, again);
  wrap.append(bar);
}

function truncationNote() {
  const note = document.createElement('p');
  note.className = 'cut-note';
  note.textContent = 'Jawaban terpotong karena batas panjang. Minta lanjutannya kalau perlu.';
  return note;
}

function typingBubble() {
  const { wrap, bubble } = addMessage('model', '');
  bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
  return { wrap, bubble };
}

function scrollDown() {
  const box = $('chat-box');
  box.scrollTop = box.scrollHeight;
}

function fileIcon(file) {
  if (file.type.startsWith('image/')) return 'i-image';
  if (file.type.startsWith('audio/')) return 'i-audio';
  return 'i-doc';
}

// panel kanan

function settings() {
  const out = { style: currentStyle };
  for (const name of SLIDERS) out[name] = Number($(name).value);
  return out;
}

let currentStyle = 'santai';

function applyPreset(key) {
  const preset = presets[key];
  if (!preset) return;

  for (const name of SLIDERS) {
    if (!Number.isFinite(preset[name])) continue;
    $(name).value = preset[name];
    $(`${name}-value`).textContent = preset[name];
  }

  $('style-desc').textContent = preset.description ?? '';
  $('style-pill').textContent = preset.label ?? key;
  paintGauge();
}

// Radiogroup butuh roving tabindex: cuma pilihan aktif yang masuk urutan Tab,
// sisanya dijangkau pakai panah.
function markRadios(container, isOn) {
  container.querySelectorAll('button').forEach((b) => {
    const on = isOn(b);
    b.setAttribute('aria-checked', String(on));
    b.tabIndex = on ? 0 : -1;
  });
}

function wireRadioKeys(container, pick) {
  container.addEventListener('keydown', (e) => {
    const keys = ['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'];
    if (!keys.includes(e.key)) return;

    const buttons = [...container.querySelectorAll('button')];
    const current = buttons.indexOf(document.activeElement);
    if (current < 0) return;

    e.preventDefault();

    let next;
    if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = buttons.length - 1;
    else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (current + 1) % buttons.length;
    else next = (current - 1 + buttons.length) % buttons.length;

    pick(buttons[next]);
    buttons[next].focus();
  });
}

function selectStyle(key) {
  currentStyle = key;
  markRadios($('style-seg'), (b) => b.dataset.style === key);
  applyPreset(key);
}

function paintGauge() {
  const temp = Number($('temperature').value);
  const pct = Math.round((temp / 2) * 100);

  $('gauge-fill').style.strokeDashoffset = String(
    GAUGE_CIRCUMFERENCE - (GAUGE_CIRCUMFERENCE * pct) / 100,
  );
  $('gauge-value').textContent = pct;
  $('gauge-label').textContent = temp <= 0.5 ? 'Presisi' : temp <= 1 ? 'Seimbang' : 'Kreatif';
}

for (const name of SLIDERS) {
  $(name).addEventListener('input', () => {
    $(`${name}-value`).textContent = $(name).value;
    if (name === 'temperature') paintGauge();
  });
}

$('reset-params').addEventListener('click', () => {
  applyPreset(currentStyle);
  toast('Parameter dikembalikan ke preset');
});

function paintStats() {
  const minutes = Math.floor((Date.now() - startedAt) / 60000);

  $('stat-messages').textContent = counters.sent;
  $('stat-minutes').textContent = minutes;
  $('stat-files').textContent = counters.files;

  $('kv-turns').textContent = conversation.length;
  $('kv-context').textContent = Math.min(conversation.length, contextLimit);
  $('kv-chars').textContent = counters.chars.toLocaleString('id-ID');
}

setInterval(paintStats, 20000);

function paintBars() {
  const box = $('bars');
  if (!latencies.length) return;

  const recent = latencies.slice(-MAX_BARS);
  const peak = Math.max(...recent);

  box.replaceChildren(...recent.map((ms) => {
    const bar = document.createElement('span');
    bar.style.height = `${Math.max(6, (ms / peak) * 100)}%`;
    bar.title = `${(ms / 1000).toFixed(1)} detik`;
    return bar;
  }));

  const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;
  $('avg-latency').textContent = `${(avg / 1000).toFixed(1)} detik`;
}

// toast

let toastTimer;
function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
}

// panggilan API

async function errorFrom(res) {
  try {
    const data = await res.json();
    const message = data.message || data.error || `HTTP ${res.status}`;
    return data.hint ? `${message}\n\n${data.hint}` : message;
  } catch {
    return `Server tidak membalas dengan benar (HTTP ${res.status}).`;
  }
}

async function streamReply(bubble) {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation, settings: settings() }),
  });

  if (!res.ok || !res.body) throw new Error(await errorFrom(res));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let answer = '';
  let truncated = false;

  bubble.textContent = '';
  bubble.classList.add('streaming');

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';

      for (const event of events) {
        const line = event.split('\n').find((l) => l.startsWith('data:'));
        if (!line) continue;

        const payload = JSON.parse(line.slice(5).trim());
        if (payload.error) throw new Error(payload.error);
        if (payload.truncated) truncated = true;

        if (payload.delta) {
          answer += payload.delta;
          bubble.innerHTML = render(answer);
          scrollDown();
        }
      }
    }
  } finally {
    bubble.classList.remove('streaming');
  }

  if (!answer.trim()) throw new Error('Model tidak mengembalikan jawaban.');
  return { answer, truncated };
}

async function plainReply(file) {
  let options;

  if (file) {
    const body = new FormData();
    body.append('conversation', JSON.stringify(conversation));
    body.append('settings', JSON.stringify(settings()));
    body.append('attachment', file);
    options = { method: 'POST', body };
  } else {
    options = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation, settings: settings() }),
    };
  }

  const res = await fetch('/api/chat', options);
  if (!res.ok) throw new Error(await errorFrom(res));

  const data = await res.json();
  if (!data.result) throw new Error('Model tidak mengembalikan jawaban.');
  return data.result;
}

// alur kirim

function setBusy(state) {
  busy = state;
  $('send-btn').disabled = state;
  $('file-input').disabled = state;
}

async function send(text, file) {
  addMessage('user', text, { file });
  conversation.push({ role: 'user', text });

  counters.sent += 1;
  if (file) counters.files += 1;
  paintStats();

  const { wrap, bubble } = typingBubble();
  setBusy(true);
  announce('Travel Buddy sedang menjawab');

  const startedRequest = Date.now();

  try {
    let answer;
    let truncated = false;

    if (file) {
      answer = await plainReply(file);
    } else {
      try {
        ({ answer, truncated } = await streamReply(bubble));
      } catch (streamError) {
        console.warn('streaming gagal, pakai mode biasa:', streamError.message);
        bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
        answer = await plainReply(null);
      }
    }

    bubble.innerHTML = render(answer);
    if (truncated) bubble.append(truncationNote());
    conversation.push({ role: 'model', text: answer });

    counters.chars += answer.length;
    latencies.push(Date.now() - startedRequest);
    paintBars();

    addBotActions(wrap, () => answer);
    announce(truncated ? 'Jawaban selesai tapi terpotong.' : `Jawaban selesai. ${answer}`);
  } catch (err) {
    wrap.classList.add('error');
    bubble.setAttribute('role', 'alert');
    bubble.textContent = err.message || 'Gagal menghubungi server.';
    conversation.pop();
    announce('Gagal mendapat jawaban.');
  } finally {
    setBusy(false);
    paintStats();
    scrollDown();
    $('user-input').focus();
  }
}

async function regenerate() {
  if (busy || conversation.length < 2) return;

  const last = conversation.at(-1);
  if (last.role !== 'model') return;

  conversation.pop();
  const previous = conversation.pop();

  const bubbles = document.querySelectorAll('.msg');
  bubbles[bubbles.length - 1]?.remove();
  bubbles[bubbles.length - 2]?.remove();

  counters.sent -= 1;
  await send(previous.text, null);
}

// input

const input = $('user-input');

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 168)}px`;
});

input.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
  e.preventDefault();
  $('chat-form').requestSubmit();
});

$('chat-form').addEventListener('submit', (e) => {
  e.preventDefault();
  if (busy) return;

  const text = input.value.trim();
  const file = pendingFile;
  if (!text && !file) return;

  input.value = '';
  input.style.height = 'auto';
  clearAttachment();

  send(text || 'Tolong bahas lampiran ini.', file);
});

$('file-input').addEventListener('change', () => {
  const file = $('file-input').files[0];
  if (!file) return;

  if (file.size > maxFileMB * 1024 * 1024) {
    toast(`Ukuran berkas melebihi ${maxFileMB} MB`);
    $('file-input').value = '';
    return;
  }

  pendingFile = file;
  $('attach-name').textContent = file.name;
  $('attach-icon').firstElementChild.setAttribute('href', `#${fileIcon(file)}`);
  $('attach-chip').hidden = false;
});

function clearAttachment() {
  pendingFile = null;
  $('file-input').value = '';
  $('attach-chip').hidden = true;
}

$('attach-remove').addEventListener('click', clearAttachment);

$('suggestions').addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-prompt]');
  if (btn && !busy) send(btn.dataset.prompt, null);
});

$('reset-chat').addEventListener('click', () => {
  if (busy) return;

  conversation = [];
  counters.chars = 0;
  clearAttachment();

  document.querySelectorAll('.msg').forEach((m) => m.remove());
  $('hero').hidden = false;

  paintStats();
  showPanel('chat');
  input.focus();
});

// multimodal

const MODES = {
  text: { path: '/generate-text', field: null, accept: '', placeholder: 'Rekomendasi liburan 3 hari di Bali dengan budget 2 juta' },
  image: { path: '/generate-from-image', field: 'image', accept: 'image/*', placeholder: 'Deskripsikan gambar ini' },
  document: { path: '/generate-from-document', field: 'document', accept: '.pdf,.txt,.md,.csv', placeholder: 'Ringkas dokumen ini' },
  audio: { path: '/generate-from-audio', field: 'audio', accept: 'audio/*', placeholder: 'Transkrip audio ini' },
};

let mmMode = 'text';

$('mm-tabs').addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-mode]');
  if (btn) setMode(btn.dataset.mode);
});

function setMode(mode) {
  mmMode = mode;
  const cfg = MODES[mode];

  markRadios($('mm-tabs'), (b) => b.dataset.mode === mode);
  document.querySelectorAll('#mm-tabs button').forEach((b) => {
    b.classList.toggle('is-active', b.dataset.mode === mode);
  });

  $('mm-endpoint').textContent = `POST ${cfg.path}`;
  $('mm-file-field').hidden = !cfg.field;
  $('mm-prompt').placeholder = cfg.placeholder;

  if (cfg.field) {
    $('mm-file-label').textContent = `Berkas — key "${cfg.field}"`;
    $('mm-file').accept = cfg.accept;
    $('mm-file').value = '';
  }
}

$('mm-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const cfg = MODES[mmMode];
  const prompt = $('mm-prompt').value.trim();
  const file = $('mm-file').files[0];
  const out = $('mm-output');

  if (!cfg.field && !prompt) return showResult('Prompt tidak boleh kosong.', true);
  if (cfg.field && !file) return showResult(`Pilih berkas untuk key "${cfg.field}" dulu.`, true);

  $('mm-send').disabled = true;
  out.classList.remove('is-error');
  out.textContent = 'Memproses…';

  let options;
  if (cfg.field) {
    const body = new FormData();
    body.append(cfg.field, file);
    if (prompt) body.append('prompt', prompt);
    options = { method: 'POST', body };
  } else {
    options = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    };
  }

  try {
    const res = await fetch(cfg.path, options);
    const data = await res.json();

    if (!res.ok) {
      showResult(`${data.message}${data.hint ? `\n\n${data.hint}` : ''}`, true);
    } else {
      showResult(data.result, false, data);
    }
  } catch (err) {
    showResult(`Gagal menghubungi server: ${err.message}`, true);
  } finally {
    $('mm-send').disabled = false;
  }
});

function showResult(text, isError, data) {
  const out = $('mm-output');
  out.classList.toggle('is-error', Boolean(isError));
  out.replaceChildren();

  if (data?.file || data?.model) {
    const meta = document.createElement('p');
    meta.className = 'mm-filemeta';
    meta.textContent = [
      data.model && `model ${data.model}`,
      data.file && `${data.file.name} · ${data.file.mimeType} · ${(data.file.sizeBytes / 1024).toFixed(1)} KB`,
    ].filter(Boolean).join('  ·  ');
    out.append(meta);
  }

  const body = document.createElement('div');
  if (isError) body.textContent = text;
  else body.innerHTML = render(text);
  out.append(body);
}

// muat konfigurasi

async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const config = await res.json();
    if (Number.isFinite(config.maxFileSizeMB)) maxFileMB = config.maxFileSizeMB;

    const seg = $('style-seg');
    const about = $('about-styles');

    seg.replaceChildren();
    about.replaceChildren();

    for (const style of config.styles) {
      presets[style.key] = style;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.role = 'radio';
      btn.dataset.style = style.key;
      btn.textContent = style.label;
      btn.setAttribute('aria-checked', 'false');
      btn.addEventListener('click', () => selectStyle(style.key));
      seg.append(btn);

      const card = document.createElement('div');
      card.className = 'about-style';
      card.innerHTML = `<b></b><small></small><div class="nums"></div>`;
      card.querySelector('b').textContent = style.label;
      card.querySelector('small').textContent = style.description;
      card.querySelector('.nums').textContent =
        `temperature ${style.temperature} · top_p ${style.topP} · top_k ${style.topK}`;
      about.append(card);
    }

    selectStyle(config.defaultStyle);
  } catch (err) {
    console.error('konfigurasi gagal dimuat', err);
    $('style-desc').textContent = 'Gagal memuat gaya bahasa dari server.';
  }
}

async function loadHealth() {
  try {
    const res = await fetch('/api/health');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const health = await res.json();
    contextLimit = health.maxHistoryMessages ?? contextLimit;

    $('model-name').textContent = health.model;
    $('health-dot').className = 'dot ok';
  } catch {
    $('model-name').textContent = 'server tidak merespons';
    $('health-dot').className = 'dot bad';
  }
}

wireRadioKeys($('mm-tabs'), (btn) => setMode(btn.dataset.mode));
wireRadioKeys($('style-seg'), (btn) => selectStyle(btn.dataset.style));

setMode('text');
paintStats();
syncDrawerState();
loadConfig();
loadHealth();
