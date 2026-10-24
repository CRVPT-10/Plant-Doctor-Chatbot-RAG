/* =========================================================
   Plant Doctor — frontend logic (vanilla JS -> FastAPI)
   ========================================================= */

// Backend base URL.
// - When the FastAPI backend serves this UI (production, single origin), use
//   same-origin relative requests (empty string).
// - When running the static dev server on :8502 separately, talk to :8000.
// - Override anytime with ?backend=... or window.BACKEND_URL.
const BACKEND_URL = (
  new URLSearchParams(location.search).get("backend") ||
  window.BACKEND_URL ||
  (location.port === "8502" ? "http://127.0.0.1:8000" : "")
).replace(/\/$/, "");

const SESSION_ID = (() => {
  let s = localStorage.getItem("pd_session");
  if (!s) { s = crypto.randomUUID(); localStorage.setItem("pd_session", s); }
  return s;
})();

const state = {
  lang: "en",
  history: [],        // {farmer, doctor, sources, confidence, metrics, audio_url, time}
  voiceMode: false,
  busy: false,
};

/* ---------------- element refs ---------------- */
const $ = (id) => document.getElementById(id);
const chatLog = $("chat-log");
const chatInput = $("chat-input");
const typing = $("typing");

/* ---------------- helpers ---------------- */
function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Minimal markdown -> HTML (bold, italics, lists, paragraphs, tables)
function mdToHtml(text) {
  if (!text) return "";
  const lines = text.split("\n");
  const out = [];
  let list = [];
  const inline = (t) => escapeHtml(t)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*(?!\s)([^*]+?)\*(?!\*)/g, "$1<em>$2</em>");
  const flush = () => {
    if (list.length) { out.push("<ul>" + list.map(i => `<li>${inline(i)}</li>`).join("") + "</ul>"); list = []; }
  };
  const isSep = (l) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l);
  const cells = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());

  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();
    // Markdown table: a row with pipes followed by a |---|---| separator
    if (line.includes("|") && i + 1 < lines.length && isSep(lines[i + 1])) {
      flush();
      const header = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().includes("|") && lines[i].trim()) {
        rows.push(cells(lines[i])); i++;
      }
      const thead = "<thead><tr>" + header.map(h => `<th>${inline(h)}</th>`).join("") + "</tr></thead>";
      const tbody = "<tbody>" + rows.map(r =>
        "<tr>" + header.map((_, c) => `<td>${inline(r[c] || "")}</td>`).join("") + "</tr>").join("") + "</tbody>";
      out.push(`<div class="md-table-wrap"><table class="md-table">${thead}${tbody}</table></div>`);
      continue;
    }
    if (!line) { flush(); i++; continue; }
    const m = line.match(/^([-*•]|\d+[.)])\s+(.*)$/);
    if (m) { list.push(m[2]); i++; }
    else { flush(); out.push(`<p>${inline(line)}</p>`); i++; }
  }
  flush();
  return out.join("");
}

// Split out a trailing "Note:/గమనిక:/ध्यान दें:/குறிப்பு:" line into an info box
function parseNotice(answer) {
  const lines = answer.split("\n");
  for (const line of lines) {
    const c = line.trim();
    if (/^(Note:|గమనిక[:：]?|ध्यान दें:|குறிப்பு:)/.test(c)) {
      return { main: answer.replace(line, ""), notice: c };
    }
  }
  return { main: answer, notice: null };
}

/* ---------------- confidence gauge (270° arc) ---------------- */
function renderGauge(conf, hasTurn) {
  const pct = Math.round((conf || 0) * 100);
  let color = "#8a9aa3", label = "No Response Yet",
      sub = "Ask a question to see semantic score diagnostics.";
  if (hasTurn) {
    if (conf >= 0.7) { color = "#25e39e"; label = "High Confidence"; sub = "The response is well supported by the retrieved documents."; }
    else if (conf >= 0.4) { color = "#ffb02e"; label = "Medium Confidence"; sub = "The response is well supported by the retrieved documents."; }
    else { color = "#ff4d5e"; label = "Low Confidence"; sub = "This response is grounded, but check the documents for details."; }
  }
  const C = 314, frac = 0.75, track = C * frac, prog = track * (conf || 0), rot = "rotate(135 60 60)";
  $("gauge").innerHTML =
    `<circle cx="60" cy="60" r="50" fill="none" stroke="#16242c" stroke-width="11" stroke-linecap="round"
             stroke-dasharray="${track.toFixed(1)} ${C}" transform="${rot}"/>
     <circle cx="60" cy="60" r="50" fill="none" stroke="${color}" stroke-width="11" stroke-linecap="round"
             stroke-dasharray="${prog.toFixed(1)} ${C}" transform="${rot}"/>
     <text x="60" y="60" text-anchor="middle" font-size="25" fill="#fff" font-weight="800"
           font-family="'Plus Jakarta Sans',sans-serif">${hasTurn ? pct + "%" : "--%"}</text>
     <text x="60" y="78" text-anchor="middle" font-size="9" fill="#8a9aa3"
           font-family="'Plus Jakarta Sans',sans-serif">confidence</text>`;
  $("conf-label").textContent = label;
  $("conf-label").style.color = color;
  $("conf-sub").textContent = sub;
}

/* ---------------- diagnostics ---------------- */
function renderDiagnostics(m) {
  const ms = (v) => (v || v === 0) ? `${(v * 1000).toFixed(1)} ms` : "— ms";
  $("d-retrieval").textContent = m ? ms(m.retrieval_time_sec) : "— ms";
  $("d-rerank").textContent = m && m.rerank_time_sec ? ms(m.rerank_time_sec) : "— ms";
  $("d-llm").textContent = m ? ms(m.llm_inference_time_sec) : "— ms";
  $("d-total").textContent = m ? `${(m.total_time_sec || 0).toFixed(2)} s` : "— s";
}

/* ---------------- recent conversations ---------------- */
function renderRecent() {
  const list = $("recent-list");
  if (!state.history.length) {
    list.innerHTML = `<p class="recent-empty">No interactions recorded yet.</p>`;
    return;
  }
  list.innerHTML = state.history.slice(-6).reverse().map(t => {
    const txt = t.farmer.length > 28 ? t.farmer.slice(0, 28) + "…" : t.farmer;
    return `<div class="recent-item" title="${escapeHtml(t.farmer)}">
      <span class="recent-text">${escapeHtml(txt)}</span>
      <span class="recent-time">${t.time || ""}</span></div>`;
  }).join("");
}

/* ---------------- chat rendering ---------------- */
function msgUserHtml(turn) {
  return `<div class="msg user">
    <div class="msg-col">
      <div class="meta"><span class="name">You</span><span class="time">${turn.time || ""}</span></div>
      <div class="bubble-user">${escapeHtml(turn.farmer)}</div>
    </div>
    <div class="avatar user">🧑‍🌾</div>
  </div>`;
}

const LANGS = { en: "English", hi: "हिंदी", te: "తెలుగు", ta: "தமிழ்" };

function msgBotHtml(turn, idx) {
  const { main, notice } = parseNotice(turn.doctor || "");
  const body = mdToHtml(main);
  const noticeHtml = notice
    ? `<div class="notice"><span>ℹ️</span><span>${escapeHtml(notice)}</span></div>` : "";

  let sourcesHtml = "";
  const sources = turn.sources || [];
  if (sources.length) {
    const cards = sources.slice(0, 3).map((s, i) => {
      let score = s.rerank_score; if (score == null) score = s.score; if (score == null) score = 0;
      return `<div class="src-card">
        <div class="src-head">
          <span class="src-title">${i + 1}. ${escapeHtml(s.source || "Unknown")}</span>
          <span class="src-book">📖</span>
        </div>
        <div class="src-foot">
          <span class="src-page">Page ${s.page ?? "N/A"}</span>
          <span class="src-score">Score: ${Number(score).toFixed(2)}</span>
        </div>
      </div>`;
    }).join("");
    sourcesHtml = `<div class="sources-title">Sources (${sources.length})</div>
      <div class="sources-grid">${cards}</div>`;
  }

  const curLang = turn.curLang || turn.origLang || "en";
  const langOpts = Object.entries(LANGS)
    .map(([c, n]) => `<option value="${c}"${c === curLang ? " selected" : ""}>${n}</option>`).join("");

  const audioHtml = turn.audio_url
    ? `<audio class="reply-audio" data-turn="${idx}" controls src="${BACKEND_URL + turn.audio_url}"></audio>` : "";

  return `<div class="msg bot">
    <div class="avatar bot">🤖</div>
    <div class="msg-col">
      <div class="meta"><span class="name">Plant Doctor</span><span class="time">${turn.time || ""}</span></div>
      <div class="bubble-bot">
        ${body}${noticeHtml}${sourcesHtml}
        <div class="actions">
          <button class="act-btn act-speak" data-turn="${idx}" title="Play voice">🔊</button>
          <button class="act-btn act-copy" data-turn="${idx}" title="Copy">📋</button>
          <select class="reply-lang" data-turn="${idx}" title="Answer language">${langOpts}</select>
          <button class="reply-translate ca-btn" data-turn="${idx}">🌐 Translate</button>
        </div>
        ${audioHtml}
      </div>
    </div>
  </div>`;
}

function renderChat() {
  // Pending turns show only the user bubble; the bot bubble appears when the reply lands.
  chatLog.innerHTML = state.history.map((t, i) => msgUserHtml(t) + (t.pending ? "" : msgBotHtml(t, i))).join("");
  chatLog.scrollTop = chatLog.scrollHeight;

  // wire per-reply action buttons (data-turn = index into state.history)
  chatLog.querySelectorAll(".act-copy").forEach((b) => {
    b.onclick = () => navigator.clipboard?.writeText(state.history[+b.dataset.turn]?.doctor || "");
  });
  chatLog.querySelectorAll(".act-speak").forEach((b) => {
    b.onclick = () => { const a = chatLog.querySelector(`.reply-audio[data-turn="${b.dataset.turn}"]`); if (a) a.play().catch(() => {}); };
  });
  chatLog.querySelectorAll(".reply-translate").forEach((b) => {
    b.onclick = () => {
      const sel = chatLog.querySelector(`.reply-lang[data-turn="${b.dataset.turn}"]`);
      translateTurn(+b.dataset.turn, sel ? sel.value : state.lang);
    };
  });

  // Autoplay the most recently generated reply/translation audio, once.
  const ap = state.history.findIndex(t => t._autoplay);
  if (ap >= 0) {
    const a = chatLog.querySelector(`.reply-audio[data-turn="${ap}"]`);
    if (a) a.play().catch(() => {});
    state.history[ap]._autoplay = false;
  }

  const lastDone = [...state.history].reverse().find(t => !t.pending);
  renderGauge(lastDone ? lastDone.confidence : 0, !!lastDone);
  renderDiagnostics(lastDone ? lastDone.metrics : null);
  renderRecent();
}

function setBusy(b) {
  state.busy = b;
  $("send-btn").disabled = b;
  typing.classList.toggle("hidden", !b);
  if (b) chatLog.scrollTop = chatLog.scrollHeight;
}

/* ---------------- API calls ---------------- */
async function sendText(query) {
  if (!query.trim() || state.busy) return;
  // Show the user's message immediately; the bot bubble fills in when the reply arrives.
  const turn = {
    farmer: query, doctor: "", origAnswer: "", origLang: state.lang,
    sources: [], confidence: 0, metrics: {}, audio_url: null,
    time: nowLabel(), pending: true,
  };
  state.history.push(turn);
  chatInput.value = "";
  renderChat();
  setBusy(true);
  try {
    const res = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, session_id: SESSION_ID, language: state.lang, kb_type: "agriculture" }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    Object.assign(turn, {
      doctor: data.answer || "",
      origAnswer: data.answer || "",
      origAudio: data.audio_url || null,
      curLang: state.lang,
      sources: data.sources || [],
      confidence: data.confidence || 0,
      metrics: data.metrics || {},
      audio_url: data.audio_url || null,
      pending: false,
      _autoplay: !!data.audio_url,
    });
    renderChat();
  } catch (e) {
    Object.assign(turn, { doctor: `⚠️ Could not reach the backend (${e.message}). Make sure the API server is running.`, pending: false });
    renderChat();
  } finally {
    setBusy(false);
  }
}

async function sendVoice(blob) {
  if (state.busy) return;
  // Provisional turn so the user sees their voice message is being processed.
  const turn = {
    farmer: "🎤 Voice message…", doctor: "", origAnswer: "", origLang: state.lang,
    sources: [], confidence: 0, metrics: {}, audio_url: null,
    time: nowLabel(), pending: true,
  };
  state.history.push(turn);
  renderChat();
  setBusy(true);
  try {
    const fd = new FormData();
    fd.append("file", blob, "query.webm");
    fd.append("session_id", SESSION_ID);
    fd.append("language", state.lang);
    fd.append("kb_type", "agriculture");
    const res = await fetch(`${BACKEND_URL}/voice`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.transcription) {
      state.history.pop();
      renderChat();
      setBusy(false);
      return;
    }
    Object.assign(turn, {
      farmer: data.transcription,
      doctor: data.answer || "",
      origAnswer: data.answer || "",
      origAudio: data.audio_url || null,
      curLang: state.lang,
      sources: data.sources || [],
      confidence: data.confidence || 0,
      metrics: data.metrics || {},
      audio_url: data.audio_url || null,
      pending: false,
      _autoplay: !!data.audio_url,
    });
    renderChat();
  } catch (e) {
    Object.assign(turn, { farmer: "🎤 Voice message", doctor: `⚠️ Voice request failed: ${e.message}`, pending: false });
    renderChat();
  } finally {
    setBusy(false);
  }
}

// Translate one reply into `target`, always from its ORIGINAL answer so repeated
// translations never compound (e.g. en->hi then en->te, not hi->te).
async function translateTurn(idx, target) {
  const turn = state.history[idx];
  if (!turn || state.busy) return;
  const source = turn.origLang || "en";
  const original = turn.origAnswer != null ? turn.origAnswer : turn.doctor;

  if (target === source) {
    turn.doctor = original;
    turn.curLang = target;
    turn.audio_url = turn.origAudio || null;
    renderChat();
    return;
  }

  setBusy(true);
  try {
    const res = await fetch(`${BACKEND_URL}/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: original, source_lang: source, target_lang: target }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    turn.doctor = data.translated_text || turn.doctor;
    turn.audio_url = data.audio_url || turn.audio_url;
    turn.curLang = target;
    turn._autoplay = !!data.audio_url;
    renderChat();
  } catch (e) {
    alert("Translation failed: " + e.message);
  } finally {
    setBusy(false);
  }
}

async function refreshHealth() {
  try {
    const res = await fetch(`${BACKEND_URL}/health`, { signal: AbortSignal.timeout(8000) });
    const h = await res.json();
    const set = (id, ok, okText) => {
      const el = $(id);
      el.textContent = ok ? okText : "Offline";
      el.className = ok ? "st-ready" : "st-off";
    };
    set("st-faiss", h.faiss_index_ready, "Ready");
    set("st-llm", h.ollama_ready, "Connected");
    set("st-embed", h.faiss_index_ready, "Ready");
    set("st-voice", h.asr_ready, "Ready");
    const docs = h.documents_indexed || [];
    $("qs-docs").textContent = docs.length;
    $("qs-chunks").textContent = docs.reduce((a, d) => a + (d.chunks_count || 0), 0).toLocaleString();
    $("qs-updated").textContent = new Date().toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
    $("qs-model").textContent = "qwen2.5:7b";
  } catch {
    ["st-faiss", "st-llm", "st-embed", "st-voice"].forEach(id => { $(id).textContent = "Offline"; $(id).className = "st-off"; });
  }
}

async function clearConversation() {
  try { await fetch(`${BACKEND_URL}/history?session_id=${SESSION_ID}`, { method: "DELETE" }); } catch {}
  state.history = [];
  renderChat();
}

/* ---------------- voice recording (reusable) ---------------- */
let mediaRecorder = null, recChunks = [];
async function startStopRecording(btn, onBlob) {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    recChunks = [];
    const origLabel = btn.innerHTML;
    mediaRecorder.ondataavailable = (e) => { if (e.data.size) recChunks.push(e.data); };
    mediaRecorder.onstop = () => {
      btn.classList.remove("recording");
      btn.innerHTML = origLabel;
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(recChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      if (blob.size) onBlob(blob);
    };
    mediaRecorder.start();
    btn.classList.add("recording");
    btn.innerHTML = "⏹️ Stop";
  } catch (e) {
    alert("Microphone access denied or unavailable: " + e.message);
  }
}
function toggleRecording() { startStopRecording($("voice-btn"), sendVoice); }

/* ---------------- page switching ---------------- */
const PAGE_META = {
  chat:     { title: "Hello, Farmer! 🌱", sub: "I'm Plant Doctor, your multilingual AI assistant for all agricultural queries." },
  schemes:  { title: "Government Schemes 🏛️", sub: "Discover subsidies, insurance, credit and more — filter or ask the assistant." },
  ingest:   { title: "Ingestion Panel 📤", sub: "Add new agricultural manuals and guidelines to the knowledge base." },
  library:  { title: "Document Library 📄", sub: "Reference texts indexed in the vector database." },
  history:  { title: "Conversation History 🕘", sub: "Your full question-and-answer history for this session." },
  settings: { title: "Settings ⚙️", sub: "Models, endpoints and configuration." },
};

function showPage(page) {
  state.page = page;
  document.querySelectorAll(".nav-item").forEach(n => n.classList.toggle("active", n.dataset.page === page));
  const meta = PAGE_META[page] || PAGE_META.chat;
  $("hero-title").textContent = meta.title;
  $("hero-sub").textContent = meta.sub;

  const isChat = page === "chat";
  $("view-chat").classList.toggle("hidden", !isChat);
  $("view-page").classList.toggle("hidden", isChat);
  $("topbar-actions").classList.toggle("hidden", !isChat);
  document.body.classList.toggle("no-right", !isChat); // right panel only on chat

  if (!isChat) renderPage(page);
}

function renderPage(page) {
  const el = $("view-page");
  el.innerHTML = "";
  if (page === "schemes") renderSchemes(el);
  else if (page === "ingest") renderIngest(el);
  else if (page === "library") renderLibrary(el);
  else if (page === "history") renderHistory(el);
  else if (page === "settings") renderSettings(el);
}

/* ---------------- Document Library ---------------- */
let _libState = "agri";
async function renderLibrary(el) {
  el.innerHTML = `<div class="card"><div class="card-head">📄 Loading indexed documents…</div></div>`;
  let h;
  try { h = await (await fetch(`${BACKEND_URL}/health`)).json(); }
  catch { el.innerHTML = `<div class="card"><div class="card-head">⚠️ Backend unreachable</div></div>`; return; }

  const bases = {
    agri: { label: "🌱 Agricultural Reference Base", docs: h.documents_indexed || [] },
    govt: { label: "🏛️ Government Schemes Base", docs: h.govt_schemes_indexed || [] },
  };

  const drawList = () => {
    const docs = bases[_libState].docs;
    const chunks = docs.reduce((a, d) => a + (d.chunks_count || 0), 0);
    const rows = docs.length ? docs.map(d => `
      <div class="lib-row">
        <div class="lib-row-main">
          <span class="lib-name">📄 ${escapeHtml(d.source)}</span>
          <span class="lib-id">ID: ${escapeHtml(d.doc_id)}</span>
        </div>
        <div class="lib-row-meta">
          <span class="lib-lang">${escapeHtml((d.language || "en").toUpperCase())}</span>
          <span class="lib-chunks">${d.chunks_count} chunks</span>
        </div>
      </div>`).join("")
      : `<p class="recent-empty">No documents indexed yet.</p>`;
    el.querySelector("#lib-list").innerHTML = `
      <div class="card">
        <div class="card-head">${bases[_libState].label}
          <span class="count-pill">${docs.length} docs</span>
          <span class="count-pill">${chunks.toLocaleString()} chunks</span>
        </div>
        ${rows}
      </div>`;
    el.querySelectorAll(".lib-tab").forEach(t => t.classList.toggle("active", t.dataset.base === _libState));
  };

  el.innerHTML = `
    <div class="lib-tabs">
      <button class="lib-tab" data-base="agri">
        <span class="lib-tab-ic">🌱</span>
        <span class="lib-tab-text">Agricultural Reference Base</span>
        <span class="count-pill">${bases.agri.docs.length}</span>
      </button>
      <button class="lib-tab" data-base="govt">
        <span class="lib-tab-ic">🏛️</span>
        <span class="lib-tab-text">Government Schemes Base</span>
        <span class="count-pill">${bases.govt.docs.length}</span>
      </button>
    </div>
    <div id="lib-list"></div>`;

  el.querySelectorAll(".lib-tab").forEach(t => t.onclick = () => { _libState = t.dataset.base; drawList(); });
  drawList();
}

/* ---------------- Conversation History ---------------- */
async function renderHistory(el) {
  const turns = state.history.filter(t => !t.pending);
  const total = turns.length;
  const avg = total ? Math.round(turns.reduce((a, t) => a + (t.confidence || 0), 0) / total * 100) : 0;

  const entries = total ? turns.slice().reverse().map(t => `
    <div class="card history-entry">
      <div class="history-head">
        <span class="history-q">🧑‍🌾 ${escapeHtml(t.farmer)}</span>
        <span class="history-time">${t.time || ""}</span>
      </div>
      <div class="history-a">🤖 ${mdToHtml(t.doctor || "")}</div>
      <div class="history-foot"><span class="src-score">Confidence: ${Math.round((t.confidence || 0) * 100)}%</span></div>
    </div>`).join("")
    : `<div class="card"><p class="recent-empty">No conversation history yet. Ask a question on the Chat Assistant page.</p></div>`;

  el.innerHTML = `
    <div class="page-grid">
      <div class="page-main">${entries}</div>
      <div class="page-side">
        <div class="card">
          <div class="card-head">📊 Session Summary</div>
          <div class="status-row"><span>Total Queries</span><span class="qs-val">${total}</span></div>
          <div class="status-row"><span>Avg. Confidence</span><span class="diag-val">${avg}%</span></div>
          <button id="hist-clear" class="clear-btn" style="margin-top:16px;">🧹 Clear All History</button>
        </div>
      </div>
    </div>`;
  $("hist-clear").onclick = async () => { await clearConversation(); renderHistory(el); };
}

/* ---------------- Settings ---------------- */
async function renderSettings(el) {
  let h = {};
  try { h = await (await fetch(`${BACKEND_URL}/health`)).json(); } catch {}
  const badge = (ok) => ok ? `<span class="st-ready">●</span>` : `<span class="st-off">●</span>`;
  el.innerHTML = `
    <div class="card">
      <div class="card-head">🔌 Backend Connection</div>
      <div class="status-row"><span>API Base URL</span><span class="qs-val">${escapeHtml(BACKEND_URL)}</span></div>
      <div class="status-row"><span>FAISS Index</span><span>${badge(h.faiss_index_ready)} ${h.faiss_index_ready ? "Ready" : "Offline"}</span></div>
      <div class="status-row"><span>Ollama (LLM)</span><span>${badge(h.ollama_ready)} ${h.ollama_ready ? "Connected" : "Offline"}</span></div>
      <div class="status-row"><span>Voice Engine (ASR)</span><span>${badge(h.asr_ready)} ${h.asr_ready ? "Ready" : "Offline"}</span></div>
    </div>
    <div class="card">
      <div class="card-head">🧠 Models</div>
      <div class="status-row"><span>LLM</span><span class="qs-val model">qwen2.5:7b</span></div>
      <div class="status-row"><span>Embeddings</span><span class="qs-val">BAAI/bge-small-en-v1.5</span></div>
      <div class="status-row"><span>Reranker</span><span class="qs-val">BAAI/bge-reranker-base</span></div>
    </div>
    <div class="card">
      <div class="card-head">🔍 Retrieval</div>
      <div class="status-row"><span>Search Type</span><span class="qs-val">Hybrid (FAISS + BM25)</span></div>
      <div class="status-row"><span>Top-K / Rerank</span><span class="qs-val">15 → 5</span></div>
      <div class="status-row"><span>Languages</span><span class="qs-val">EN · HI · TE · TA</span></div>
    </div>`;
}

/* ---------------- Ingestion Panel ---------------- */
function renderIngest(el) {
  el.innerHTML = `
    <div class="card">
      <div class="card-head">📤 Upload New Document</div>
      <p class="muted">Add a manual (PDF, DOCX, TXT, MD). It is parsed, chunked, embedded and indexed immediately.</p>
      <input id="ing-file" type="file" accept=".pdf,.docx,.txt,.md" class="file-input" />
      <button id="ing-upload" class="btn-primary" disabled>🚀 Parse & Index Document</button>
      <div id="ing-result" class="ing-result"></div>
    </div>
    <div class="card">
      <div class="card-head">🔄 Rebuild Vector Store</div>
      <p class="muted">Rebuild the full FAISS index and metadata from files in <code>data/documents/</code>. This can take a minute.</p>
      <button id="ing-rebuild" class="btn-secondary">🔄 Rebuild Full Index</button>
      <div id="ing-rebuild-result" class="ing-result"></div>
    </div>`;

  const fileInput = $("ing-file"), uploadBtn = $("ing-upload"), result = $("ing-result");
  fileInput.onchange = () => { uploadBtn.disabled = !fileInput.files.length; };
  uploadBtn.onclick = async () => {
    const f = fileInput.files[0]; if (!f) return;
    uploadBtn.disabled = true; result.innerHTML = `<span class="muted">Processing “${escapeHtml(f.name)}”…</span>`;
    try {
      const fd = new FormData(); fd.append("file", f, f.name);
      const res = await fetch(`${BACKEND_URL}/upload`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      result.innerHTML = `<span class="ok">✅ Indexed “${escapeHtml(f.name)}” into ${data.chunks_created} chunks.</span>`;
      refreshHealth();
    } catch (e) { result.innerHTML = `<span class="err">❌ ${escapeHtml(e.message)}</span>`; }
    finally { uploadBtn.disabled = false; }
  };

  const rebuildBtn = $("ing-rebuild"), rResult = $("ing-rebuild-result");
  rebuildBtn.onclick = async () => {
    rebuildBtn.disabled = true; rResult.innerHTML = `<span class="muted">Rebuilding index… this may take a minute.</span>`;
    try {
      const res = await fetch(`${BACKEND_URL}/embed`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      rResult.innerHTML = `<span class="ok">✅ Index and metadata rebuilt successfully.</span>`;
      refreshHealth();
    } catch (e) { rResult.innerHTML = `<span class="err">❌ ${escapeHtml(e.message)}</span>`; }
    finally { rebuildBtn.disabled = false; }
  };
}

/* ---------------- Govt Schemes ---------------- */
const SCHEME_FILTERS = {
  states: ["All", "Telangana", "Andhra Pradesh", "Uttar Pradesh", "Maharashtra", "Karnataka", "Tamil Nadu", "Gujarat"],
  crops: ["All", "Paddy", "Cotton", "Wheat", "Maize", "Groundnut", "Sugarcane", "Potato", "Onion"],
  cats: ["All", "Income Support", "Insurance", "Irrigation", "Soil Health", "Agricultural Marketing", "Credit & Loans", "Horticulture", "Mechanization & Allied", "Farmer Groups", "Infrastructure", "Natural Farming"],
};
let _schemes = null;

async function renderSchemes(el) {
  if (!_schemes) {
    try { _schemes = await (await fetch("assets/schemes.json")).json(); }
    catch { _schemes = []; }
  }
  const opt = (arr) => arr.map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join("");
  el.innerHTML = `
    <div class="card">
      <div class="card-head">🔍 Filter Schemes</div>
      <div class="filter-row">
        <label>State<select id="f-state">${opt(SCHEME_FILTERS.states)}</select></label>
        <label>Crop<select id="f-crop">${opt(SCHEME_FILTERS.crops)}</select></label>
        <label>Category<select id="f-cat">${opt(SCHEME_FILTERS.cats)}</select></label>
      </div>
      <div class="filter-tags">
        <label><input type="checkbox" id="f-small"> Small Farmers</label>
        <label><input type="checkbox" id="f-marginal"> Marginal Farmers</label>
        <label><input type="checkbox" id="f-tenant"> Tenant Farmers</label>
        <label><input type="checkbox" id="f-fpo"> FPOs / Groups</label>
      </div>
    </div>
    <div id="scheme-count" class="section-title"></div>
    <div id="scheme-cards" class="scheme-grid"></div>

    <div class="card scheme-ask">
      <div class="card-head">💬 Ask AI about Govt Schemes</div>
      <p class="muted">Ask about eligibility, documents required, subsidy amounts and how to apply.</p>
      <div class="ask-row">
        <div class="composer-input">
          <span class="attach">💬</span>
          <input id="scheme-q" type="text" placeholder="e.g. Who is eligible for PM-KISAN and how do I apply?" />
        </div>
        <button id="scheme-voice" class="ca-btn voice">🎤 Voice</button>
        <button id="scheme-ask-btn" class="btn-primary">Ask</button>
      </div>
      <div id="scheme-answer" class="scheme-answer"></div>
    </div>`;

  const applyFilters = () => {
    const st = $("f-state").value, cr = $("f-crop").value, ct = $("f-cat").value;
    const small = $("f-small").checked, marg = $("f-marginal").checked, ten = $("f-tenant").checked, fpo = $("f-fpo").checked;
    const list = _schemes.filter(s => {
      if (st !== "All" && !s.states.includes("All") && !s.states.includes(st)) return false;
      if (cr !== "All" && !s.crops.includes("All") && !s.crops.includes(cr)) return false;
      if (ct !== "All" && s.category !== ct) return false;
      if (small && !s.eligibility.includes("Small Farmers")) return false;
      if (marg && !s.eligibility.includes("Marginal Farmers")) return false;
      if (ten && !s.eligibility.includes("Tenant Farmers")) return false;
      if (fpo && !s.eligibility.includes("FPOs") && s.category !== "Farmer Groups") return false;
      return true;
    });
    $("scheme-count").textContent = `Available Matching Schemes (${list.length})`;
    $("scheme-cards").innerHTML = list.length ? list.map(s => `
      <div class="scheme-card">
        <div class="scheme-card-top">
          <span class="scheme-ic">🏛️</span>
          <span class="scheme-title">${escapeHtml(s.title)}</span>
        </div>
        <div class="scheme-full">${escapeHtml(s.fullName)}</div>
        <p class="scheme-desc">${escapeHtml(s.description)}</p>
        <div class="scheme-badges">${s.eligibility.slice(0, 3).map(t => `<span class="badge">${escapeHtml(t)}</span>`).join("")}</div>
        <div class="scheme-foot"><a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">Know More →</a></div>
      </div>`).join("")
      : `<p class="recent-empty">No schemes match the selected filters.</p>`;
  };

  ["f-state", "f-crop", "f-cat"].forEach(id => $(id).onchange = applyFilters);
  ["f-small", "f-marginal", "f-tenant", "f-fpo"].forEach(id => $(id).onchange = applyFilters);
  applyFilters();

  const askBtn = $("scheme-ask-btn"), qInput = $("scheme-q"), ansEl = $("scheme-answer"), voiceBtn = $("scheme-voice");
  const spinner = `<div class="typing-dots"><span></span><span></span><span></span></div>`;

  const showSchemeAnswer = (data, question) => {
    const { main, notice } = parseNotice(data.answer || "");
    const srcs = (data.sources || []).slice(0, 3).map((s, i) =>
      `<span class="src-chip">${i + 1}. ${escapeHtml(s.source || "")} · p${s.page ?? "—"}</span>`).join("");
    const qEcho = question ? `<div class="scheme-q-echo">🧑‍🌾 ${escapeHtml(question)}</div>` : "";
    ansEl.innerHTML = `${qEcho}<div class="bubble-bot">${mdToHtml(main)}
      ${notice ? `<div class="notice"><span>ℹ️</span><span>${escapeHtml(notice)}</span></div>` : ""}
      ${srcs ? `<div class="scheme-srcs">${srcs}</div>` : ""}
      ${data.audio_url ? `<audio class="reply-audio" controls autoplay src="${BACKEND_URL + data.audio_url}"></audio>` : ""}
    </div>`;
  };

  const ask = async () => {
    const q = qInput.value.trim(); if (!q) return;
    askBtn.disabled = true; ansEl.innerHTML = spinner;
    try {
      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, session_id: SESSION_ID, language: state.lang, kb_type: "govt_schemes" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      showSchemeAnswer(data, null);
    } catch (e) { ansEl.innerHTML = `<span class="err">❌ ${escapeHtml(e.message)}</span>`; }
    finally { askBtn.disabled = false; }
  };

  const askVoice = async (blob) => {
    ansEl.innerHTML = spinner;
    try {
      const fd = new FormData();
      fd.append("file", blob, "query.webm");
      fd.append("session_id", SESSION_ID);
      fd.append("language", state.lang);
      fd.append("kb_type", "govt_schemes");
      const res = await fetch(`${BACKEND_URL}/voice`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      if (!data.transcription) { ansEl.innerHTML = `<span class="muted">Could not hear anything. Please try again.</span>`; return; }
      showSchemeAnswer(data, data.transcription);
    } catch (e) { ansEl.innerHTML = `<span class="err">❌ ${escapeHtml(e.message)}</span>`; }
  };

  askBtn.onclick = ask;
  qInput.addEventListener("keydown", e => { if (e.key === "Enter") ask(); });
  voiceBtn.onclick = () => startStopRecording(voiceBtn, askVoice);
}

/* ---------------- wire up events ---------------- */
function init() {
  $("send-btn").onclick = () => sendText(chatInput.value);
  chatInput.addEventListener("keydown", (e) => { if (e.key === "Enter") sendText(chatInput.value); });
  $("voice-btn").onclick = toggleRecording;
  $("clear-btn").onclick = clearConversation;
  $("view-all").onclick = () => showPage("history");

  $("language-select").onchange = (e) => { state.lang = e.target.value; };

  $("voice-mode-btn").onclick = () => {
    state.voiceMode = !state.voiceMode;
    const b = $("voice-mode-btn");
    b.classList.toggle("on", state.voiceMode);
    if (state.voiceMode) toggleRecording();
  };

  document.querySelectorAll(".nav-item").forEach(n => n.onclick = () => showPage(n.dataset.page));

  renderGauge(0, false);
  renderDiagnostics(null);
  refreshHealth();
  setInterval(refreshHealth, 30000);
}

document.addEventListener("DOMContentLoaded", init);
