// ── State ──────────────────────────────────────────────────────────────────

const state = {
  token: localStorage.getItem("token") || null,
  user: JSON.parse(localStorage.getItem("user") || "null"),
  today: null,        // { due: [], new: [] }
  queue: [],          // current study queue
  queueIdx: 0,
  flipped: false,
  allWords: [],
  currentKat: "all",
};

// Russian letters absent from Serbian Cyrillic — highlight for Dominika
const RUSSIAN_ONLY = /([ЁёЙйЩщЪъЫыЭэЮюЯя])/g;

// ── Bootstrap ──────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  if (state.token && state.user) {
    enterApp();
  } else {
    show("screen-login");
  }
});

// ── Auth ───────────────────────────────────────────────────────────────────

let selectedUserName = null;

function selectUser(el) {
  document.querySelectorAll(".user-card").forEach(c => c.classList.remove("selected"));
  el.classList.add("selected");
  selectedUserName = el.dataset.name;
  onPinInput();
}

function onPinInput() {
  const pin = document.getElementById("pin-input").value;
  const btn = document.getElementById("login-btn");
  btn.disabled = !(selectedUserName && pin.length === 4);
}

async function doLogin() {
  const pin = document.getElementById("pin-input").value;
  const btn = document.getElementById("login-btn");
  document.getElementById("login-error").textContent = "";
  btn.disabled = true;
  btn.textContent = "Logowanie…";
  try {
    const data = await api("POST", "/auth/login", { name: selectedUserName, pin });
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));
    enterApp();
  } catch (e) {
    document.getElementById("login-error").textContent = e.message || "Błędny PIN";
    btn.disabled = false;
    btn.textContent = "Zaloguj się";
  }
}

function doLogout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  document.getElementById("pin-input").value = "";
  document.getElementById("login-error").textContent = "";
  document.querySelectorAll(".user-card").forEach(c => c.classList.remove("selected"));
  selectedUserName = null;
  document.getElementById("login-btn").disabled = true;
  document.getElementById("nav").classList.remove("visible");
  show("screen-login");
}

// ── App entry ──────────────────────────────────────────────────────────────

function enterApp() {
  document.getElementById("nav").classList.add("visible");
  showScreen("home");
}

// ── Navigation ─────────────────────────────────────────────────────────────

function show(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  // Explicitly force login screen off — CSS specificity can't fight inline style
  const login = document.getElementById("screen-login");
  login.style.display = (id === "screen-login") ? "flex" : "none";
  if (id !== "screen-login") document.getElementById(id).classList.add("active");
}

function setNavActive(name) {
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById("nav-" + name);
  if (btn) btn.classList.add("active");
}

function showScreen(name) {
  show("screen-" + name);
  setNavActive(name);
  if (name === "home") loadHome();
  if (name === "browse") loadBrowse();
  if (name === "stats") loadStats();
}

// ── Home ───────────────────────────────────────────────────────────────────

async function loadHome() {
  document.getElementById("home-greeting").textContent =
    "Cześć, " + state.user.name + "!";
  document.getElementById("home-date").textContent = fmtDate(new Date());

  const [statsData, todayData] = await Promise.all([
    api("GET", "/stats"),
    api("GET", "/today"),
  ]);
  state.today = todayData;

  document.getElementById("streak-num").textContent = statsData.streak;
  document.getElementById("stat-known").textContent = statsData.known;
  document.getElementById("stat-started").textContent = statsData.started;
  document.getElementById("stat-total").textContent = statsData.total_words;

  const total = todayData.due.length + todayData.new.length;
  const cta = document.getElementById("study-cta");
  if (total === 0) {
    cta.innerHTML = `<div class="nothing-today">✅ Na dziś wszystko zrobione!<br>Wróć jutro po nowe słówka.</div>`;
  } else {
    const due = todayData.due.length;
    const newW = todayData.new.length;
    const sub = [
      due > 0 ? `${due} powtórek` : null,
      newW > 0 ? `${newW} nowych` : null,
    ].filter(Boolean).join(" + ");
    cta.innerHTML = `
      <button class="study-card-btn" onclick="startStudy()">
        <div class="left">
          <div class="title">Zacznij naukę</div>
          <div class="sub">${sub} — ${total} słówek</div>
        </div>
        <span class="arrow">→</span>
      </button>`;
  }
}

// ── Study ──────────────────────────────────────────────────────────────────

async function startStudy() {
  setNavActive("study");
  show("screen-study");
  if (!state.today) {
    state.today = await api("GET", "/today");
  }
  state.queue = [...state.today.due, ...state.today.new];
  if (state.queue.length === 0) {
    document.getElementById("study-content").innerHTML = `
      <div class="session-done">
        <div class="done-icon">🎉</div>
        <h2>Wszystko zrobione!</h2>
        <p>Na dziś nie ma więcej słówek.</p>
        <button class="btn-primary" onclick="showScreen('home')">Wróć do ekranu głównego</button>
      </div>`;
    return;
  }
  state.queueIdx = 0;
  renderCard();
}

function renderCard() {
  const total = state.queue.length;
  const idx = state.queueIdx;

  if (idx >= total) {
    state.today = null; // force reload next time
    document.getElementById("study-content").innerHTML = `
      <div class="session-done">
        <div class="done-icon">🎉</div>
        <h2>Sesja ukończona!</h2>
        <p>Opracowałeś/aś ${total} słówek. Dobra robota!</p>
        <button class="btn-primary" onclick="showScreen('home')">Wróć do ekranu głównego</button>
      </div>`;
    return;
  }

  const pct = Math.round((idx / total) * 100);
  document.getElementById("study-progress-bar").style.width = pct + "%";
  document.getElementById("study-progress-text").textContent = `${idx}/${total}`;

  const word = state.queue[idx];
  state.flipped = false;

  const ruHtml = highlightCyr(word.ru);

  document.getElementById("study-content").innerHTML = `
    <div class="card-scene" onclick="flipCard()">
      <div class="card-flip" id="card-flip">
        <div class="card-face front">
          <span class="card-kategoria">${word.kategoria}</span>
          <button class="card-tts" onclick="event.stopPropagation(); speak('${esc(word.ru)}')" title="Wymowa">🔊</button>
          <div class="card-ru">${ruHtml}</div>
          <div class="card-translit">${esc(word.translit)}</div>
        </div>
        <div class="card-face back">
          <span class="card-kategoria">${word.kategoria}</span>
          <button class="card-tts" onclick="event.stopPropagation(); speak('${esc(word.ru)}')" title="Wymowa">🔊</button>
          <div class="card-pl">${esc(word.pl)}</div>
          <div class="card-hint">${ruHtml} · ${esc(word.translit)}</div>
        </div>
      </div>
    </div>
    <div class="show-hint" id="show-hint">Kliknij kartę, żeby zobaczyć tłumaczenie</div>
    <div class="grade-buttons hidden" id="grade-buttons">
      <button class="grade-btn grade-0" onclick="grade(0)">
        <span class="g-icon">✗</span> Nie znam
      </button>
      <button class="grade-btn grade-1" onclick="grade(1)">
        <span class="g-icon">~</span> Średnio
      </button>
      <button class="grade-btn grade-2" onclick="grade(2)">
        <span class="g-icon">✓</span> Znam
      </button>
    </div>`;

  speak(word.ru);
}

function flipCard() {
  if (state.flipped) return;
  state.flipped = true;
  document.getElementById("card-flip").classList.add("flipped");
  document.getElementById("show-hint").style.display = "none";
  document.getElementById("grade-buttons").classList.remove("hidden");
}

async function grade(g) {
  const word = state.queue[state.queueIdx];
  try {
    await api("POST", "/review", { word_id: word.id, grade: g });
  } catch (e) {
    toast("Błąd zapisu: " + e.message);
  }
  // if "nie znam" re-add to end of queue (max once)
  if (g === 0 && !word._retry) {
    const clone = { ...word, _retry: true };
    state.queue.push(clone);
  }
  state.queueIdx++;
  renderCard();
}

// ── Browse ─────────────────────────────────────────────────────────────────

async function loadBrowse() {
  if (!state.allWords.length) {
    state.allWords = await api("GET", "/words");
  }
  const cats = ["all", ...new Set(state.allWords.map(w => w.kategoria))];

  const tabs = document.getElementById("kategoria-tabs");
  tabs.innerHTML = cats.map(c => `
    <button class="tab-btn ${c === state.currentKat ? "active" : ""}"
            onclick="setKat('${c}')">${c === "all" ? "Wszystkie" : c}</button>
  `).join("");

  renderWordList();
}

function setKat(kat) {
  state.currentKat = kat;
  loadBrowse();
}

function renderWordList() {
  const words = state.currentKat === "all"
    ? state.allWords
    : state.allWords.filter(w => w.kategoria === state.currentKat);

  document.getElementById("word-list").innerHTML = words.map(w => `
    <div class="word-item">
      <div>
        <div class="ru">${highlightCyr(w.ru)}</div>
        <div class="translit">${esc(w.translit)}</div>
      </div>
      <div class="pl">${esc(w.pl)}</div>
    </div>
  `).join("");
}

// ── Stats ──────────────────────────────────────────────────────────────────

async function loadStats() {
  document.getElementById("stats-user-name").textContent =
    "Statystyki — " + state.user.name;
  const s = await api("GET", "/stats");
  document.getElementById("big-known").textContent = s.known;
  document.getElementById("big-streak").textContent = s.streak;
  document.getElementById("big-started").textContent = s.started;
  document.getElementById("big-total").textContent = s.total_words;
}

// ── Utilities ──────────────────────────────────────────────────────────────

function highlightCyr(text) {
  if (!state.user || state.user.name !== "Dominika") return esc(text);
  return esc(text).replace(RUSSIAN_ONLY, '<span class="new-cyr">$1</span>');
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function speak(text) {
  if (!window.speechSynthesis) return;
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang = "ru-RU";
  utt.rate = 0.9;
  speechSynthesis.cancel();
  speechSynthesis.speak(utt);
}

async function api(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (state.token) opts.headers["Authorization"] = "Bearer " + state.token;
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) { doLogout(); return; }
    throw new Error(data.detail || "Błąd serwera");
  }
  return data;
}

function fmtDate(d) {
  return d.toLocaleDateString("pl-PL", { weekday: "long", day: "numeric", month: "long" });
}

let toastTimer;
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2500);
}
