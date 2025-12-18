const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

const state = {
  baseUrl: "",
  token: "",
  openapi: null,
};

function pretty(x) {
  try { return JSON.stringify(x, null, 2); } catch { return String(x); }
}

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2600);
}

function setStatus(text) {
  $("#statusLine").textContent = text;
}

function normalizeBaseUrl(v) {
  v = (v || "").trim();
  // empty means same origin
  if (!v) return "";
  return v.replace(/\/$/, "");
}

function setToken(token) {
  state.token = token || "";
  localStorage.setItem("restify_token", state.token);
  $("#tokenState").textContent = state.token ? "есть" : "нет";
}

function setBaseUrl(url) {
  state.baseUrl = normalizeBaseUrl(url);
  localStorage.setItem("restify_baseUrl", state.baseUrl);
  $("#baseUrl").value = state.baseUrl;
}

function apiUrl(path) {
  const base = state.baseUrl || "";
  if (!path.startsWith("/")) path = "/" + path;
  return base + path;
}

async function apiFetch(path, options = {}) {
  const url = apiUrl(path);
  const headers = new Headers(options.headers || {});

  if (state.token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }

  // if body is plain object, serialize as JSON
  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) {
    if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    options.body = JSON.stringify(options.body);
  }

  options.headers = headers;

  setStatus(`${options.method || "GET"} ${path}`);
  const res = await fetch(url, options);

  const ctype = (res.headers.get("content-type") || "").toLowerCase();
  let data = null;

  if (res.status === 204) {
    data = { ok: true, status: 204 };
  } else if (ctype.includes("application/json")) {
    data = await res.json().catch(() => null);
  } else {
    data = await res.text().catch(() => "");
  }

  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

function bindTabs() {
  $$(".navitem").forEach(btn => {
    btn.addEventListener("click", () => {
      $$(".navitem").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const tab = btn.dataset.tab;
      $$(".tab").forEach(t => t.classList.remove("active"));
      $(`#tab-${tab}`).classList.add("active");
    });
  });
}

function fillOut(el, value) {
  el.textContent = typeof value === "string" ? value : pretty(value);
}

function formToObject(form) {
  const fd = new FormData(form);
  const obj = {};
  for (const [k, v] of fd.entries()) obj[k] = v;
  return obj;
}

function qs(params) {
  const out = new URLSearchParams();
  Object.entries(params).forEach(([k,v]) => {
    if (v === undefined || v === null) return;
    const s = String(v).trim();
    if (!s) return;
    out.set(k, s);
  });
  const q = out.toString();
  return q ? `?${q}` : "";
}

/* ---------- Auth / Profile ---------- */

async function onRegister(e) {
  e.preventDefault();
  const out = $("#registerOut");
  fillOut(out, "");
  try {
    const { email, password } = formToObject(e.currentTarget);
    const data = await apiFetch("/auth/register", {
      method: "POST",
      body: { email, password },
    });
    fillOut(out, data);
    toast("Зарегистрировано");
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка регистрации");
  }
}

async function onLogin(e) {
  e.preventDefault();
  const out = $("#loginOut");
  fillOut(out, "");
  try {
    const { username, password } = formToObject(e.currentTarget);
    // Most FastAPI OAuth2 token endpoints expect x-www-form-urlencoded (OAuth2PasswordRequestForm)
    const body = new URLSearchParams();
    body.set("username", username);
    body.set("password", password);

    const data = await apiFetch("/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });

    if (data?.access_token) setToken(data.access_token);
    fillOut(out, data);
    toast("Токен получен");
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка логина");
  }
}

async function onMe() {
  const out = $("#meOut");
  fillOut(out, "");
  try {
    const data = await apiFetch("/me");
    fillOut(out, data);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка /me");
  }
}

async function onProfile(e) {
  e.preventDefault();
  const out = $("#profileOut");
  fillOut(out, "");
  try {
    const { categories } = formToObject(e.currentTarget);
    const preferred_categories = (categories || "")
      .split(",")
      .map(s => s.trim())
      .filter(Boolean);

    const data = await apiFetch("/me/profile", {
      method: "PUT",
      body: { preferred_categories },
    });
    fillOut(out, data);
    toast("Профиль обновлён");
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка профиля");
  }
}

/* ---------- Places ---------- */

async function onPlacesSearch(e) {
  e.preventDefault();
  const out = $("#placesOut");
  fillOut(out, "");
  try {
    const params = formToObject(e.currentTarget);
    const data = await apiFetch(`/places${qs(params)}`);
    fillOut(out, data);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка /places");
  }
}

async function onCreatePlace(e) {
  e.preventDefault();
  const out = $("#createPlaceOut");
  fillOut(out, "");
  try {
    const { name, category, city, description } = formToObject(e.currentTarget);
    const data = await apiFetch("/places", {
      method: "POST",
      body: { name, category, city, description },
    });
    fillOut(out, data);
    toast("Место отправлено");
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка создания места");
  }
}

async function onAddReview(e) {
  e.preventDefault();
  const out = $("#addReviewOut");
  fillOut(out, "");
  try {
    const { place_id, rating, text } = formToObject(e.currentTarget);
    const data = await apiFetch(`/places/${place_id}/reviews`, {
      method: "POST",
      body: { rating: Number(rating), text },
    });
    fillOut(out, data);
    toast("Отзыв отправлен");
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка отзыва");
  }
}

async function onSummary(e) {
  e.preventDefault();
  const out = $("#summaryOut");
  fillOut(out, "");
  try {
    const { place_id } = formToObject(e.currentTarget);
    const data = await apiFetch(`/places/${place_id}/reviews/summary`);
    fillOut(out, data);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка summary");
  }
}

/* ---------- Recs ---------- */

async function onRecs() {
  const out = $("#recsOut");
  fillOut(out, "");
  try {
    const data = await apiFetch("/recommendations");
    fillOut(out, data);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка /recommendations");
  }
}

/* ---------- Chat ---------- */

async function onChat(e) {
  e.preventDefault();
  const out = $("#chatOut");
  fillOut(out, "");
  try {
    const { message } = formToObject(e.currentTarget);
    const data = await apiFetch("/chat", {
      method: "POST",
      body: { message },
    });
    fillOut(out, data);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка /chat");
  }
}

/* ---------- Moderation ---------- */

async function onPendingPlaces() {
  const out = $("#pendingPlacesOut");
  fillOut(out, "");
  try {
    const data = await apiFetch("/moderation/places/pending");
    fillOut(out, data);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка pending places");
  }
}

async function onPendingReviews() {
  const out = $("#pendingReviewsOut");
  fillOut(out, "");
  try {
    const data = await apiFetch("/moderation/reviews/pending");
    fillOut(out, data);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка pending reviews");
  }
}

async function onModeratePlace(e) {
  e.preventDefault();
  const out = $("#moderatePlaceOut");
  fillOut(out, "");
  const action = e.submitter?.dataset?.action || "approve";
  try {
    const { place_id } = formToObject(e.currentTarget);
    const data = await apiFetch(`/moderation/places/${place_id}/${action}`, { method: "POST" });
    fillOut(out, data);
    toast(`Place ${action}`);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка модерации места");
  }
}

async function onModerateReview(e) {
  e.preventDefault();
  const out = $("#moderateReviewOut");
  fillOut(out, "");
  const action = e.submitter?.dataset?.action || "approve";
  try {
    const { review_id } = formToObject(e.currentTarget);
    const data = await apiFetch(`/moderation/reviews/${review_id}/${action}`, { method: "POST" });
    fillOut(out, data);
    toast(`Review ${action}`);
  } catch (err) {
    fillOut(out, { error: err.message, details: err.data });
    toast("Ошибка модерации отзыва");
  }
}

/* ---------- OpenAPI Explorer ---------- */

function schemaToExample(schema) {
  if (!schema) return {};
  if (schema.example !== undefined) return schema.example;

  if (schema.default !== undefined) return schema.default;

  if (schema.type === "object" && schema.properties) {
    const o = {};
    for (const [k, s] of Object.entries(schema.properties)) {
      o[k] = schemaToExample(s);
    }
    return o;
  }
  if (schema.type === "array" && schema.items) return [schemaToExample(schema.items)];
  if (schema.type === "string") return "";
  if (schema.type === "integer" || schema.type === "number") return 0;
  if (schema.type === "boolean") return false;
  return {};
}

function resolveRef(openapi, ref) {
  // only local refs like "#/components/schemas/..."
  const p = ref.replace(/^#\//, "").split("/");
  let cur = openapi;
  for (const part of p) cur = cur?.[part];
  return cur;
}

function getRequestBodySchema(openapi, op) {
  const rb = op.requestBody;
  if (!rb) return null;

  const content = rb.content || {};
  const entry = content["application/json"] || content["application/*+json"] || content["application/x-www-form-urlencoded"] || null;
  if (!entry) return null;

  let schema = entry.schema || null;
  if (schema?.$ref) schema = resolveRef(openapi, schema.$ref);
  return { schema, contentType: Object.keys(content)[0] };
}

function getResponseSchema(openapi, op) {
  const r = op.responses?.["200"] || op.responses?.["201"] || null;
  if (!r) return null;
  const content = r.content || {};
  const entry = content["application/json"] || content["application/*+json"] || null;
  if (!entry) return null;
  let schema = entry.schema || null;
  if (schema?.$ref) schema = resolveRef(openapi, schema.$ref);
  return schema;
}

function buildEndpointCard(path, method, op) {
  const el = document.createElement("div");
  el.className = "endpoint";

  const summary = op.summary || op.operationId || "";
  const pill = `${method.toUpperCase()} ${path}`;

  el.innerHTML = `
    <div class="endpointHeader">
      <div>
        <span class="pill method">${pill}</span>
        <div style="margin-top:6px; font-weight:700">${escapeHtml(summary)}</div>
      </div>
      <button class="btn btn-ghost" data-toggle>Открыть</button>
    </div>
    <div class="endpointBody">
      <div class="muted">${escapeHtml(op.description || "")}</div>

      <div class="divider"></div>

      <div class="kv" data-fields></div>

      <label class="field" style="margin-top:10px">
        <span>Body (JSON)</span>
        <textarea rows="6" data-body placeholder="{}"></textarea>
      </label>

      <div class="row" style="margin-top:10px">
        <button class="btn" data-call>Вызвать</button>
      </div>

      <pre class="out" data-out></pre>
    </div>
  `;

  const btn = el.querySelector("[data-toggle]");
  btn.addEventListener("click", () => {
    el.classList.toggle("open");
    btn.textContent = el.classList.contains("open") ? "Закрыть" : "Открыть";
  });

  const fields = el.querySelector("[data-fields]");
  const bodyTa = el.querySelector("[data-body]");
  const out = el.querySelector("[data-out]");

  // Path params
  const pathParams = Array.from(path.matchAll(/\{([^}]+)\}/g)).map(m => m[1]);
  for (const p of pathParams) {
    fields.appendChild(makeField(`path:${p}`, p));
  }

  // Query params from OpenAPI
  const params = op.parameters || [];
  for (const prm of params) {
    if (prm?.$ref) continue;
    if (prm.in === "query") {
      fields.appendChild(makeField(`query:${prm.name}`, prm.name));
    }
  }

  // Request body example
  const rb = getRequestBodySchema(state.openapi, op);
  if (rb?.schema) {
    const example = schemaToExample(rb.schema);
    bodyTa.value = pretty(example);
  } else {
    bodyTa.value = "{}";
  }

  // If no request body expected, hide textarea a bit
  if (!rb) {
    bodyTa.value = "{}";
    bodyTa.closest(".field").style.opacity = "0.75";
  }

  el.querySelector("[data-call]").addEventListener("click", async () => {
    fillOut(out, "");
    try {
      // build final path with params
      let finalPath = path;
      for (const p of pathParams) {
        const v = el.querySelector(`[name="path:${p}"]`)?.value?.trim();
        if (!v) throw new Error(`path param '${p}' is required`);
        finalPath = finalPath.replace(`{${p}}`, encodeURIComponent(v));
      }

      // query
      const q = new URLSearchParams();
      for (const prm of params) {
        if (prm?.$ref) continue;
        if (prm.in === "query") {
          const v = el.querySelector(`[name="query:${prm.name}"]`)?.value?.trim();
          if (v) q.set(prm.name, v);
        }
      }
      const qstr = q.toString() ? `?${q.toString()}` : "";

      // body
      let body = undefined;
      const hasBody = !!rb;
      if (hasBody) {
        const raw = bodyTa.value.trim();
        if (raw && raw !== "{}") {
          try { body = JSON.parse(raw); }
          catch { throw new Error("Body is not valid JSON"); }
        } else {
          body = {};
        }
      }

      const data = await apiFetch(`${finalPath}${qstr}`, {
        method: method.toUpperCase(),
        body: hasBody ? body : undefined,
      });

      fillOut(out, data);
    } catch (err) {
      fillOut(out, { error: err.message, details: err.data });
      toast("Ошибка вызова");
    }
  });

  return el;
}

function makeField(name, label) {
  const wrap = document.createElement("label");
  wrap.className = "field";
  wrap.innerHTML = `<span>${escapeHtml(label)}</span><input type="text" name="${escapeHtml(name)}" />`;
  return wrap;
}

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, c => ({
    "&":"&amp;",
    "<":"&lt;",
    ">":"&gt;",
    '"':"&quot;",
    "'":"&#39;",
  }[c]));
}

async function loadOpenAPI() {
  const list = $("#openapiList");
  const info = $("#openapiInfo");
  list.innerHTML = "";
  info.textContent = "";
  try {
    const spec = await apiFetch("/openapi.json");
    state.openapi = spec;

    const title = spec?.info?.title || "API";
    const version = spec?.info?.version || "";
    info.textContent = `${title} ${version}`;

    const filter = $("#filterOpenapi").value.trim();

    const entries = [];
    for (const [path, methods] of Object.entries(spec.paths || {})) {
      if (filter && !path.includes(filter)) continue;
      for (const [method, op] of Object.entries(methods || {})) {
        if (!["get","post","put","delete","patch","head","options"].includes(method)) continue;
        entries.push({ path, method, op });
      }
    }

    // sort stable: path then method
    entries.sort((a,b) => (a.path === b.path ? a.method.localeCompare(b.method) : a.path.localeCompare(b.path)));

    for (const { path, method, op } of entries) {
      list.appendChild(buildEndpointCard(path, method, op));
    }

    toast("OpenAPI загружен");
  } catch (err) {
    info.textContent = "Не получилось загрузить /openapi.json (проверь base URL и CORS)";
    toast("Ошибка OpenAPI");
  }
}

/* ---------- Init ---------- */

function init() {
  bindTabs();

  setBaseUrl(localStorage.getItem("restify_baseUrl") || "");
  setToken(localStorage.getItem("restify_token") || "");

  $("#saveBaseUrl").addEventListener("click", () => {
    setBaseUrl($("#baseUrl").value);
    toast("Base URL сохранён");
  });

  $("#clearAuth").addEventListener("click", () => {
    setToken("");
    toast("Токен удалён");
  });

  $("#registerForm").addEventListener("submit", onRegister);
  $("#loginForm").addEventListener("submit", onLogin);
  $("#meBtn").addEventListener("click", onMe);
  $("#profileForm").addEventListener("submit", onProfile);

  $("#placesSearchForm").addEventListener("submit", onPlacesSearch);
  $("#createPlaceForm").addEventListener("submit", onCreatePlace);
  $("#addReviewForm").addEventListener("submit", onAddReview);
  $("#summaryForm").addEventListener("submit", onSummary);

  $("#recsBtn").addEventListener("click", onRecs);
  $("#chatForm").addEventListener("submit", onChat);

  $("#pendingPlacesBtn").addEventListener("click", onPendingPlaces);
  $("#pendingReviewsBtn").addEventListener("click", onPendingReviews);
  $("#moderatePlaceForm").addEventListener("submit", onModeratePlace);
  $("#moderateReviewForm").addEventListener("submit", onModerateReview);

  $("#loadOpenapiBtn").addEventListener("click", loadOpenAPI);
  $("#filterOpenapi").addEventListener("input", () => {
    // simple debounce
    if (state._filterTimer) clearTimeout(state._filterTimer);
    state._filterTimer = setTimeout(() => {
      if (state.openapi) loadOpenAPI();
    }, 250);
  });
}

document.addEventListener("DOMContentLoaded", init);
