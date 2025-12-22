const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

const state = {
  baseUrl: "",         // оставлено на будущее; в UI не показываем
  token: "",
  me: null,
  activePlace: null,
  chat: [],
  theme: "dark",
};

function pretty(x){ try { return JSON.stringify(x, null, 2); } catch { return String(x); } }
function escapeHtml(s){
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

// Safe Markdown-ish renderer (no raw HTML from the model).
// Supports: fenced code blocks, inline code, bold/italic, links, lists, newlines.
function renderMarkdownSafe(input){
  const raw = String(input ?? "");

  // 1) Extract fenced code blocks first.
  const codeBlocks = [];
  let tmp = raw.replace(/```([\w-]+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    const i = codeBlocks.length;
    codeBlocks.push({ lang: (lang || "").trim(), code: String(code || "") });
    return `\u0000CODEBLOCK_${i}\u0000`;
  });

  // 2) Extract markdown links to safely validate URL scheme.
  const links = [];
  tmp = tmp.replace(/\[([^\]]+)]\(([^)]+)\)/g, (_, text, url) => {
    const u = String(url || "").trim();
    // Only allow http/https links.
    if (!/^https?:\/\//i.test(u)) return `[${text}](${url})`;
    const i = links.length;
    links.push({ text: String(text || ""), url: u });
    return `\u0000LINK_${i}\u0000`;
  });

  // 3) Escape everything (prevents XSS), then apply lightweight formatting.
  let s = escapeHtml(tmp);

  // Inline code
  s = s.replace(/`([^`\n]+)`/g, (_, code) => `<code>${code}</code>`);

  // Bold / italic (keep it simple)
  s = s.replace(/\*\*([^*\n]+)\*\*/g, (_, t) => `<strong>${t}</strong>`);
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, (_, pre, t) => `${pre}<em>${t}</em>`);

  // Lists (unordered/ordered) line-based
  const lines = s.split(/\n/);
  let out = "";
  let inUl = false;
  let inOl = false;

  const closeLists = () => {
    if (inUl) { out += "</ul>"; inUl = false; }
    if (inOl) { out += "</ol>"; inOl = false; }
  };

  for (const line of lines){
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    const ol = line.match(/^\s*(\d+)\.\s+(.*)$/);

    if (ul){
      if (inOl) { out += "</ol>"; inOl = false; }
      if (!inUl) { out += "<ul>"; inUl = true; }
      out += `<li>${ul[1]}</li>`;
      continue;
    }
    if (ol){
      if (inUl) { out += "</ul>"; inUl = false; }
      if (!inOl) { out += "<ol>"; inOl = true; }
      out += `<li>${ol[2]}</li>`;
      continue;
    }

    closeLists();
    // Preserve empty lines as paragraph breaks.
    out += line.length ? (line + "<br>") : "<br>";
  }
  closeLists();

  // Remove last <br> if present
  out = out.replace(/(<br>)+$/, "");

  // 4) Put back safe links.
  out = out.replace(/\u0000LINK_(\d+)\u0000/g, (_, i) => {
    const link = links[Number(i)];
    if (!link) return "";
    const t = escapeHtml(link.text);
    const u = escapeHtml(link.url);
    return `<a href="${u}" target="_blank" rel="noopener noreferrer">${t}</a>`;
  });

  // 5) Put back safe code blocks.
  out = out.replace(/\u0000CODEBLOCK_(\d+)\u0000/g, (_, i) => {
    const b = codeBlocks[Number(i)];
    if (!b) return "";
    const code = escapeHtml(b.code).replace(/\n$/, "");
    const lang = b.lang ? ` data-lang="${escapeHtml(b.lang)}"` : "";
    return `<pre${lang}><code>${code}</code></pre>`;
  });

  return out;
}

function toast(msg){
  const el = $("#toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(state._t);
  state._t = setTimeout(() => el.classList.add("hidden"), 2400);
}

function setNotice(id, text, kind){
  const el = $("#"+id);
  el.classList.remove("hidden", "ok", "err");
  el.classList.add(kind === "ok" ? "ok" : "err");
  el.textContent = text;
}

function clearNotice(id){
  const el = $("#"+id);
  el.classList.add("hidden");
  el.textContent = "";
  el.classList.remove("ok", "err");
}

function normalizeBaseUrl(v){
  v = (v||"").trim();
  if (!v) return "";
  return v.replace(/\/$/, "");
}
function apiUrl(path){
  const base = state.baseUrl || "";
  if (!path.startsWith("/")) path = "/" + path;
  return base + path;
}

async function apiFetch(path, options={}){
  const url = apiUrl(path);
  const headers = new Headers(options.headers || {});
  if (state.token && !headers.has("Authorization")){
    headers.set("Authorization", `Bearer ${state.token}`);
  }
  if (options.body && typeof options.body === "object" &&
      !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)){
    if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    options.body = JSON.stringify(options.body);
  }
  options.headers = headers;

  const res = await fetch(url, options);
  const ctype = (res.headers.get("content-type") || "").toLowerCase();
  let data = null;

  if (res.status === 204) data = { ok:true, status:204 };
  else if (ctype.includes("application/json")) data = await res.json().catch(()=>null);
  else data = await res.text().catch(()=> "");

  if (!res.ok){
    const e = new Error(`HTTP ${res.status}`);
    e.status = res.status;
    e.data = data;
    throw e;
  }
  return data;
}

function openTab(name){
  $$(".nav").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  $$(".tab").forEach(t => t.classList.toggle("active", t.id === `tab-${name}`));
  if (name === "places") loadPlaces();
  if (name === "recs") loadRecs();
}

function openModal(id){
  const el = $("#"+id);
  el.classList.remove("hidden");
  el.setAttribute("aria-hidden", "false");
}
function closeModal(el){
  el.classList.add("hidden");
  el.setAttribute("aria-hidden", "true");
}

function bindModals(){
  $$("[data-close]").forEach(btn => btn.addEventListener("click", () => closeModal(btn.closest(".modal"))));
  $$(".modal").forEach(m => m.addEventListener("click", (e) => { if (e.target === m) closeModal(m); }));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      $$(".modal:not(.hidden)").forEach(closeModal);
      closeUserMenu();
    }
  });
}

function normList(data){
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.items)) return data.items;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

function pickPlace(p){
  const id = p.id ?? p.place_id ?? p.pk ?? null;
  const name = p.name ?? p.title ?? "Без названия";
  const category = p.category ?? p.type ?? "—";
  const city = p.city ?? p.location_city ?? "—";
  const description = p.description ?? p.about ?? "";
  const avg = p.avg_rating ?? p.rating_avg ?? p.rating ?? p.average_rating ?? null;
  const reviews = p.reviews_count ?? p.review_count ?? p.n_reviews ?? null;
  return { id, name, category, city, description, avg, reviews, raw:p };
}

function fmtRating(x){
  if (x === null || x === undefined) return null;
  const n = Number(x);
  if (Number.isNaN(n)) return null;
  return Math.round(n * 10) / 10;
}

function placeCard(place){
  const el = document.createElement("div");
  el.className = "place";

  const r = fmtRating(place.avg);
  const rating = r !== null ? `${r} ★` : "— ★";

  el.innerHTML = `
    <div class="place-title">${escapeHtml(place.name)}</div>
    <div class="place-sub">${escapeHtml(place.category)} • ${escapeHtml(place.city)}</div>
    <div class="badges">
      <span class="rating">${escapeHtml(rating)}</span>
      <span class="tag">${escapeHtml(place.category)}</span>
      <span class="tag">${escapeHtml(place.city)}</span>
      ${place.reviews !== null && place.reviews !== undefined ? `<span class="pill">${place.reviews} отзывов</span>` : ""}
    </div>
    ${place.description ? `<div class="desc">${escapeHtml(place.description)}</div>` : ""}
  `;
  el.addEventListener("click", () => openPlace(place));
  return el;
}

function setKPIs(places){
  $("#kpiPlaces").textContent = String(places.length);
  const cities = new Set(places.map(p => (p.city||"").toLowerCase()).filter(Boolean));
  const cats = new Set(places.map(p => (p.category||"").toLowerCase()).filter(Boolean));
  $("#kpiCities").textContent = String(cities.size);
  $("#kpiCats").textContent = String(cats.size);
}

function renderLastPlaces(places){
  const box = $("#lastPlaces");
  box.innerHTML = "";
  const slice = places.slice(0, 5);
  $("#lastPlacesPill").textContent = slice.length ? `${slice.length}` : "0";

  if (!slice.length){
    box.innerHTML = `<div class="muted">Пока нет мест. Они появятся после импорта.</div>`;
    return;
  }
  for (const p of slice){
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = `
      <div class="item-main">
        <div class="item-title">${escapeHtml(p.name)}</div>
        <div class="item-meta">${escapeHtml(p.category)} • ${escapeHtml(p.city)}</div>
      </div>
      <div class="item-actions">
        <button class="btn ghost" data-open>Открыть</button>
      </div>
    `;
    item.querySelector("[data-open]").addEventListener("click", () => openPlace(p));
    box.appendChild(item);
  }
}

/* THEME */
function applyTheme(theme){
  state.theme = (theme === "light") ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", state.theme);
  localStorage.setItem("restify_theme", state.theme);
  $("#themeToggle").querySelector(".btnicon").textContent = state.theme === "light" ? "☀" : "◐";
}
function toggleTheme(){
  applyTheme(state.theme === "light" ? "dark" : "light");
  toast(state.theme === "light" ? "Светлая тема" : "Тёмная тема");
}

/* USER MENU */
function openUserMenu(){
  const menu = $("#userMenu");
  menu.classList.remove("hidden");
  $("#userMenuBtn").setAttribute("aria-expanded", "true");
}
function closeUserMenu(){
  const menu = $("#userMenu");
  menu.classList.add("hidden");
  $("#userMenuBtn").setAttribute("aria-expanded", "false");
}
function toggleUserMenu(){
  const menu = $("#userMenu");
  if (menu.classList.contains("hidden")) openUserMenu();
  else closeUserMenu();
}
function updateUserMenu(){
  const isAuth = !!state.token && !!state.me;
  const role = (state.me?.role || "—").toLowerCase();

  $("#menuLogin").classList.toggle("hidden", isAuth);
  $("#menuRegister").classList.toggle("hidden", isAuth);

  $("#menuProfile").classList.toggle("hidden", !isAuth);
  $("#menuLogout").classList.toggle("hidden", !isAuth);
}

/* AUTH STATE */
function setToken(tok){
  state.token = tok || "";
  localStorage.setItem("restify_token", state.token);
}
function setUserHeader(){
  const email = state.me?.email || "Гость";
  const role = state.me?.role || "—";

  $("#userEmail").textContent = email;
  $("#userRole").textContent = role;

  const letter = (email && email !== "Гость") ? email.trim()[0].toUpperCase() : "?";
  $("#userAvatar").textContent = letter;

  $("#menuTitle").textContent = email;
  $("#menuDesc").textContent = email === "Гость"
    ? "Войдите, чтобы оставлять отзывы и общаться с помощником"
    : "Управляйте профилем и своими рекомендациями";

  $("#authCallout").classList.toggle("hidden", !!state.token);
  $("#chatNeedAuth").classList.toggle("hidden", !!state.token);
  $("#chatForm").classList.toggle("hidden", !state.token);
}

async function refreshMe(){
  if (!state.token){
    state.me = null;
    setUserHeader();
    updateUserMenu();
    return;
  }
  try{
    const me = await apiFetch("/me");
    state.me = me;
  } catch {
    setToken("");
    state.me = null;
  }
  setUserHeader();
  updateUserMenu();
}

/* QUERY */
function qs(params){
  const q = new URLSearchParams();
  for (const [k,v] of Object.entries(params)){
    if (v === null || v === undefined) continue;
    const s = String(v).trim();
    if (!s) continue;
    q.set(k, s);
  }
  const out = q.toString();
  return out ? `?${out}` : "";
}

/* PLACES */
async function loadPlaces(){
  const params = {
    q: $("#f_q").value,
    city: $("#f_city").value,
    category: $("#f_category").value,
    min_rating: $("#f_min_rating").value,
  };

  $("#placesCount").textContent = "Загрузка…";
  $("#placesGrid").innerHTML = "";
  $("#placesEmpty").classList.add("hidden");

  try{
    const data = await apiFetch(`/places${qs(params)}`);
    const places = normList(data).map(pickPlace).filter(p => p.id !== null);

    $("#placesCount").textContent = places.length ? `Найдено: ${places.length}` : "Ничего не найдено";
    if (!places.length){
      $("#placesEmpty").classList.remove("hidden");
      setKPIs([]);
      renderLastPlaces([]);
      return;
    }

    for (const p of places) $("#placesGrid").appendChild(placeCard(p));
    setKPIs(places);
    renderLastPlaces(places);
  } catch (e){
    $("#placesCount").textContent = "Не удалось загрузить";
    toast("Не удалось загрузить места");
    console.error(e);
  }
}

async function loadRecs(){
  $("#recsGrid").innerHTML = "";
  $("#recsEmpty").classList.add("hidden");

  try{
    const data = await apiFetch("/recommendations");
    const recs = normList(data).map(pickPlace).filter(p => p.id !== null);

    if (!recs.length) $("#recsEmpty").classList.remove("hidden");
    else for (const p of recs) $("#recsGrid").appendChild(placeCard(p));
  } catch (e){
    $("#recsEmpty").classList.remove("hidden");
    toast("Не удалось загрузить рекомендации");
    console.error(e);
  }
}

function openPlace(place){
  state.activePlace = place;
  $("#placeTitle").textContent = place.name;
  $("#placeSub").textContent = `${place.category} • ${place.city}`;
  $("#placeDesc").textContent = place.description || "Описание не указано.";

  const r = fmtRating(place.avg);
  $("#placeBadges").innerHTML = `
    <span class="tag">${escapeHtml(place.category)}</span>
    <span class="tag">${escapeHtml(place.city)}</span>
    <span class="rating">${escapeHtml(r !== null ? (r + " ★") : "— ★")}</span>
  `;

  clearNotice("sumMsg");
  clearNotice("reviewMsg");
  $("#reviewForm [name='place_id']").value = place.id;

  openModal("placeModal");
}

async function onSummary(){
  clearNotice("sumMsg");
  setNotice("sumMsg", "Готовим краткую выжимку…", "ok");

  try{
    const id = state.activePlace?.id;
    const data = await apiFetch(`/places/${id}/reviews/summary`);
    const text = typeof data === "string" ? data : (data.summary ?? data.text ?? pretty(data));
    setNotice("sumMsg", text, "ok");
  } catch (e){
    const msg = e.status === 401 ? "Войдите в аккаунт, чтобы использовать эту функцию." : "Не удалось сформировать выжимку.";
    setNotice("sumMsg", msg, "err");
    console.error(e);
  }
}

async function onReview(e){
  e.preventDefault();
  clearNotice("reviewMsg");

  const fd = new FormData(e.currentTarget);
  const place_id = fd.get("place_id");
  const rating = Number(fd.get("rating"));
  const text = fd.get("text") || "";

  try{
    await apiFetch(`/places/${place_id}/reviews`, { method:"POST", body:{rating, text} });
    setNotice("reviewMsg", "Спасибо! Отзыв отправлен.", "ok");
    toast("Отзыв отправлен");
    e.currentTarget.reset();
  } catch (e2){
    const msg = e2.status === 401 ? "Сначала войдите в аккаунт." : "Не удалось отправить отзыв.";
    setNotice("reviewMsg", msg, "err");
    console.error(e2);
  }
}


/* AUTH */
function switchAuthTab(name){
  $$(".tabbtn").forEach(b => b.classList.toggle("active", b.dataset.atab === name));
  $$(".atab").forEach(t => t.classList.toggle("active", t.id === `atab-${name}`));
}

async function onRegister(e){
  e.preventDefault();
  clearNotice("registerMsg");

  const fd = new FormData(e.currentTarget);
  try{
    await apiFetch("/auth/register", { method:"POST", body:{ email: fd.get("email"), password: fd.get("password") } });
    setNotice("registerMsg", "Аккаунт создан. Теперь выполните вход.", "ok");
    toast("Аккаунт создан");
    switchAuthTab("login");
  } catch (err){
    const msg = "Не удалось зарегистрироваться. Проверьте email и пароль.";
    setNotice("registerMsg", msg, "err");
    console.error(err);
  }
}

async function onLogin(e){
  e.preventDefault();
  clearNotice("loginMsg");

  const fd = new FormData(e.currentTarget);
  const form = new URLSearchParams();
  form.set("username", fd.get("username"));
  form.set("password", fd.get("password"));

  try{
    const data = await apiFetch("/auth/token", {
      method:"POST",
      headers:{ "Content-Type":"application/x-www-form-urlencoded" },
      body: form,
    });
    if (data?.access_token){
      setToken(data.access_token);
      await refreshMe();
      setNotice("loginMsg", "Вход выполнен.", "ok");
      toast("Добро пожаловать!");
      closeModal($("#authModal"));
    } else {
      setNotice("loginMsg", "Не удалось выполнить вход.", "err");
    }
  } catch (err){
    setNotice("loginMsg", "Неверный email или пароль.", "err");
    console.error(err);
  }
}

async function onProfile(e){
  e.preventDefault();
  clearNotice("profileMsg");

  const fd = new FormData(e.currentTarget);
  const cats = (fd.get("categories") || "").split(",").map(s => s.trim()).filter(Boolean);
  const city = String(fd.get("city") || "").trim() || null;

  try{
    await apiFetch("/me/profile", { method:"PUT", body:{ preferred_categories: cats, city } });
    setNotice("profileMsg", "Профиль сохранён.", "ok");
    toast("Профиль обновлён");
  } catch (e2){
    const msg = e2.status === 401 ? "Сначала войдите в аккаунт." : "Не удалось сохранить профиль.";
    setNotice("profileMsg", msg, "err");
    console.error(e2);
  }
}


/* CHAT */
function renderChat(){
  const log = $("#chatLog");
  log.innerHTML = "";

  if (!state.chat.length){
    log.innerHTML = `<div class="muted">Напишите сообщение — я подскажу идеи.</div>`;
    return;
  }

  for (const m of state.chat){
    const row = document.createElement("div");
    row.className = "msg " + (m.role === "user" ? "user" : "bot");
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    // Bot messages may contain Markdown formatting.
    // User messages are also rendered safely (escaped), so formatting can't inject HTML.
    bubble.innerHTML = `<div class="md">${renderMarkdownSafe(m.content)}</div>`;

    const meta = document.createElement("div");
    meta.className = "mmeta";
    meta.textContent = m.role === "user" ? "Вы" : "Restify";

    const wrap = document.createElement("div");
    wrap.appendChild(bubble);
    wrap.appendChild(meta);

    row.appendChild(wrap);
    log.appendChild(row);
  }

  log.scrollTop = log.scrollHeight;
}

function autosize(ta){
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
}

async function onChat(e){
  e.preventDefault();
  const ta = $("#chatMsg");
  const message = ta.value.trim();
  if (!message) return;

  state.chat.push({ role:"user", content: message });
  renderChat();
  ta.value = "";
  autosize(ta);

  try{
    const data = await apiFetch("/chat", { method:"POST", body:{ message } });
    const reply = typeof data === "string" ? data : (data.reply ?? data.message ?? pretty(data));
    state.chat.push({ role:"bot", content: reply });
    renderChat();
  } catch (err){
    const msg = err.status === 401 ? "Пожалуйста, войдите в аккаунт, чтобы пользоваться чатом." : "Не удалось получить ответ.";
    state.chat.push({ role:"bot", content: msg });
    renderChat();
    toast("Ошибка чата");
  }
}

/* INIT */
function init(){
  bindModals();

  // theme from storage
  applyTheme(localStorage.getItem("restify_theme") || "dark");

  // baseUrl (скрыто от UI), токен
  state.baseUrl = normalizeBaseUrl(localStorage.getItem("restify_baseUrl") || "");
  setToken(localStorage.getItem("restify_token") || "");

  // nav
  $$(".nav").forEach(b => b.addEventListener("click", () => openTab(b.dataset.tab)));

  // top actions
  $("#goHome").addEventListener("click", () => openTab("dashboard"));
  $("#themeToggle").addEventListener("click", toggleTheme);

  // user menu
  $("#userMenuBtn").addEventListener("click", (e) => { e.stopPropagation(); toggleUserMenu(); });
  document.addEventListener("click", () => closeUserMenu());

  $("#menuLogin").addEventListener("click", () => { closeUserMenu(); openModal("authModal"); switchAuthTab("login"); });
  $("#menuRegister").addEventListener("click", () => { closeUserMenu(); openModal("authModal"); switchAuthTab("register"); });
  $("#menuProfile").addEventListener("click", () => { closeUserMenu(); openModal("authModal"); switchAuthTab("profile"); });
  $("#menuLogout").addEventListener("click", async () => {
    closeUserMenu();
    setToken("");
    state.me = null;
    await refreshMe();
    toast("Вы вышли из аккаунта");
    openTab("dashboard");
  });

  // dashboard ctas
  $("#ctaPlaces").addEventListener("click", () => openTab("places"));
  $("#ctaRecs").addEventListener("click", () => openTab("recs"));
  $("#ctaChat").addEventListener("click", () => openTab("chat"));
  $("#ctaLogin").addEventListener("click", () => { openModal("authModal"); switchAuthTab("login"); });
  $("#ctaRegister").addEventListener("click", () => { openModal("authModal"); switchAuthTab("register"); });

  // quick profile
  $("#openProfileQuick").addEventListener("click", () => { openModal("authModal"); switchAuthTab("profile"); });

  // global search -> places
  $("#globalSearchBtn").addEventListener("click", () => { $("#f_q").value = $("#globalSearch").value; openTab("places"); });
  $("#globalSearch").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); $("#globalSearchBtn").click(); } });

  // places
  $("#applyFilters").addEventListener("click", loadPlaces);
  $("#resetFilters").addEventListener("click", () => {
    $("#f_q").value=""; $("#f_city").value=""; $("#f_category").value=""; $("#f_min_rating").value="";
    loadPlaces();
  });

  // place modal
  $("#sumBtn").addEventListener("click", onSummary);
  $("#reviewForm").addEventListener("submit", onReview);

  // recs
  $("#refreshRecs").addEventListener("click", loadRecs);


  // chat
  $("#chatForm").addEventListener("submit", onChat);
  $("#clearChat").addEventListener("click", () => { state.chat = []; renderChat(); toast("Чат очищен"); });
  $("#chatMsg").addEventListener("input", (e) => autosize(e.target));
  // Enter to send, Shift+Enter for a new line
  $("#chatMsg").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    if (e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.isComposing) return;
    e.preventDefault();
    const form = $("#chatForm");
    if (form?.requestSubmit) form.requestSubmit();
    else form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  $("#chatLoginBtn").addEventListener("click", () => { openModal("authModal"); switchAuthTab("login"); });

  // auth
  $("#registerForm").addEventListener("submit", onRegister);
  $("#loginForm").addEventListener("submit", onLogin);
  $("#profileForm").addEventListener("submit", onProfile);

  // initial
  refreshMe().finally(() => {
    loadPlaces();
    renderChat();
    updateUserMenu();
  });
}

document.addEventListener("DOMContentLoaded", init);
