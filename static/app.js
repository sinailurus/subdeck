/* SubDeck 前端逻辑（原生 JS，无外部依赖）
 * 结构：i18n 字典 → 工具函数 → API 封装 → 状态 → 渲染 → 表单/上传 → 设置 → 启动
 * 多语言：v1 仅中文；加英文时在 STR 里补 en 字典并把 LANG 改成可切换即可。
 */
"use strict";

/* ---------------- i18n ---------------- */
const STR = {
  zh: {
    today: "今天", tomorrow: "明天", daysLater: (n) => `${n} 天后`,
    saved: "已保存", deleted: "已删除", confirmDel: (n) => `确认删除订阅「${n}」？此操作不可恢复。`,
    ratesRefreshed: "汇率已更新", ratesFail: "汇率刷新失败，请检查 NAS 网络后重试",
    settingsSaved: "设置已保存", copied: "已复制到剪贴板",
    logoInvalid: "仅支持 PNG / JPG / WebP 图片", logoTooBig: "图片不能超过 2MB",
    logoCleared: "已恢复字母头像", logoUploaded: "图标已更新",
    noRate: "部分币种暂无汇率数据，相关金额未计入统计",
    needNameAmount: "请填写名称和金额", loading: "加载中…",
    noPending: "近几天没有需要付款的订阅 🎉",
    noSubs: "还没有订阅，点「添加订阅」开始记录", noSubsHome: "还没有订阅，去「订阅」页点「添加订阅」开始记录",
    loginFail: "密码错误，请重试", logoutOk: "已退出登录",
  },
};
const LANG = "zh";
const t = (k, ...a) => { const v = STR[LANG][k]; return typeof v === "function" ? v(...a) : v; };

/* ---------------- 常量 ---------------- */
const PALETTE = ["#ef5350", "#ab63f6", "#5c9dff", "#26a69a", "#66bb6a",
  "#ffa726", "#ff7043", "#ec407a", "#8d6e63", "#78909c"];
const CYCLE_LABEL = { weekly: "每周", monthly: "每月", quarterly: "每季度", semiannual: "每半年", yearly: "每年" };
const CAT_LABEL = { video: "视频", music: "音乐", cloud: "云服务", software: "软件", network: "网络",
  game: "游戏", news: "资讯", shopping: "购物", other: "其他" };
const SYMBOL = { CNY: "¥", USD: "$", EUR: "€", JPY: "¥", GBP: "£", KRW: "₩", HKD: "HK$", TWD: "NT$" };
const sym = (c) => SYMBOL[c] || c + " ";

/* ---------------- 工具 ---------------- */
const $ = (sel) => document.querySelector(sel);
const fmtMoney = (v, cur) => `${sym(cur)}${Number(v).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtDate = (iso) => { const d = new Date(iso + "T00:00:00"); return `${d.getMonth() + 1}-${String(d.getDate()).padStart(2, "0")}`; };
const dueLabel = (n) => n === 0 ? t("today") : n === 1 ? t("tomorrow") : t("daysLater", n);
const dueClass = (n) => n <= 1 ? "due-soon" : n <= 3 ? "due-warn" : "due-ok";
const catLabel = (c) => CAT_LABEL[c] || c || "—";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (ch) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
const hashPick = (s) => PALETTE[[...String(s)].reduce((a, ch) => a + ch.charCodeAt(0), 0) % PALETTE.length];

function toast(msg, ms = 2200) {
  const el = $("#toast");
  el.textContent = msg; el.classList.remove("hidden");
  clearTimeout(toast._tm);
  toast._tm = setTimeout(() => el.classList.add("hidden"), ms);
}

/* ---------------- API ---------------- */
async function api(path, opts = {}) {
  const resp = await fetch(path, {
    headers: opts.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...opts,
    body: opts.body instanceof FormData ? opts.body : opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (resp.status === 401) { showLogin(); throw new Error("unauthorized"); }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || resp.status);
  return data;
}

/* ---------------- 状态 ---------------- */
const state = {
  me: null, settings: null, ratesInfo: null,
  subs: [], stats: null,
  filter: "all", search: "",
  view: "dashboard",
  form: { logoFile: null, logoPreview: null, clearLogo: false, color: PALETTE[0] },
};

/* ---------------- 启动 / 登录 ---------------- */
async function boot() {
  state.me = await api("/api/me");
  if (state.me.auth_required && !state.me.logged_in) { showLogin(); return; }
  $("#login-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  $("#about-version").textContent = "v" + state.me.version;
  $("#btn-logout").classList.toggle("hidden", !state.me.auth_required);
  $("#auth-note").textContent = state.me.auth_required
    ? "" : "当前未启用密码保护（.env 中 AUTH_PASSWORD 为空）。若会暴露到公网，建议设置密码。";
  await loadAll();
  renderAll();
}

function showLogin() {
  $("#app-view").classList.add("hidden");
  $("#login-view").classList.remove("hidden");
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/login", { method: "POST", body: { password: $("#login-password").value } });
    $("#login-password").value = "";
    await boot();
  } catch { $("#login-error").classList.remove("hidden"); }
});

/* ---------------- 数据加载 ---------------- */
async function loadAll() {
  const [settings, rates] = await Promise.all([api("/api/settings"), api("/api/rates")]);
  state.settings = settings;
  state.ratesInfo = rates;
  fillCurrencyOptions();   // 表单币种下拉
  await refreshData();
}

let currencyOptionsReady = false;
async function fillCurrencyOptions() {
  if (currencyOptionsReady) return;
  const sel = $("#f-currency");
  if (!sel || sel.options.length) { currencyOptionsReady = true; return; }
  try {
    const r = await api("/api/currencies");
    sel.innerHTML = r.currencies.map((c) => `<option value="${c}">${c}</option>`).join("");
    currencyOptionsReady = true;
  } catch { /* 失败时保留空表，打开表单时再试 */ }
}

async function refreshData() {
  [state.subs, state.stats] = await Promise.all([api("/api/subscriptions"), api("/api/stats")]);
  if (state.stats.missing_rate_currencies.length) toast(t("noRate"));
}

function renderAll() {
  renderTopbar();
  renderStats();
  renderPending();
  renderCategoryBars();
  renderSubs();
  renderSettings();
}

/* ---------------- 导航 ---------------- */
function switchView(name) {
  state.view = name;
  for (const v of ["dashboard", "subs", "settings"])
    $("#view-" + v).classList.toggle("hidden", v !== name);
  document.querySelectorAll(".nav-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.nav === name));
}
document.querySelectorAll(".nav-btn").forEach((b) =>
  b.addEventListener("click", () => switchView(b.dataset.nav)));

/* ---------------- 顶栏 ---------------- */
function renderTopbar() {
  $("#rates-updated").textContent =
    state.ratesInfo.updated_at ? `汇率 ${state.ratesInfo.updated_at}` : "汇率未同步";
}

async function refreshRates() {
  const btns = [$("#refresh-rates"), $("#btn-refresh-rates")];
  btns.forEach((b) => b && (b.disabled = true));
  try {
    const r = await api("/api/rates/refresh", { method: "POST" });
    if (r.ok) { toast(t("ratesRefreshed")); await refreshData(); renderAll(); }
    else toast(t("ratesFail"));
  } catch { toast(t("ratesFail")); }
  btns.forEach((b) => b && (b.disabled = false));
}
$("#refresh-rates").addEventListener("click", refreshRates);
$("#btn-refresh-rates").addEventListener("click", refreshRates);

/* ---------------- 主题 ---------------- */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("subdeck-theme", theme);
}
applyTheme(localStorage.getItem("subdeck-theme") ||
  (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
$("#theme-toggle").addEventListener("click", () =>
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));

/* ---------------- 概览 ---------------- */
function renderStats() {
  const s = state.stats, base = state.settings.base_currency;
  $("#stat-monthly").textContent = fmtMoney(s.monthly_total, base);
  $("#stat-yearly").textContent = fmtMoney(s.yearly_total, base);
  $("#stat-count").textContent = s.active_count;
  $("#stat-pending").textContent = s.pending_count;
  $("#stat-pending-card").classList.toggle("alarm", s.pending_count > 0);
}

function avatarHTML(sub, cls = "avatar") {
  if (sub.logo_url)
    return `<span class="${cls}"><img src="${esc(sub.logo_url)}" alt=""></span>`;
  const color = sub.color || hashPick(sub.name);
  return `<span class="${cls}" style="background:${esc(color)}">${esc(sub.name[0] || "?").toUpperCase()}</span>`;
}

function renderPending() {
  const base = state.settings.base_currency;
  const list = state.stats.pending;
  $("#pending-list").innerHTML = list.length
    ? list.map((s) => `
      <div class="pending-item">
        ${avatarHTML(s)}
        <div>
          <div class="n">${esc(s.name)}</div>
          <div class="muted small">${fmtMoney(s.amount, s.currency)} · ${CYCLE_LABEL[s.cycle]}</div>
        </div>
        <div class="pending-when">
          <div class="d ${s.days_until <= 1 ? "soon" : ""}">${dueLabel(s.days_until)}</div>
          <div class="date">${fmtDate(s.next_billing_date)}</div>
        </div>
      </div>`).join("")
    : `<div class="pending-empty">${t("noPending")}</div>`;
}

function renderCategoryBars() {
  const cats = state.stats.by_category, base = state.settings.base_currency;
  const max = Math.max(...cats.map((c) => c.monthly), 0.0001);
  $("#category-bars").innerHTML = cats.length
    ? cats.map((c) => `
      <div class="cat-row">
        <span class="cat-name">${esc(catLabel(c.category))}</span>
        <span class="cat-track"><span class="cat-fill" style="width:${Math.max(c.monthly / max * 100, 4)}%"></span></span>
        <span class="cat-amount">${fmtMoney(c.monthly, base)}</span>
      </div>`).join("")
    : `<div class="pending-empty">${t("noSubsHome")}</div>`;
}

/* ---------------- 订阅列表 ---------------- */
async function reloadSubs() {
  const q = state.search ? `&search=${encodeURIComponent(state.search)}` : "";
  state.subs = await api(`/api/subscriptions?filter=${state.filter}${q}`);
  renderSubs();
}

function renderSubs() {
  const base = state.settings.base_currency;
  const subs = state.subs;
  // 桌面表格
  $("#subs-tbody").innerHTML = subs.length ? subs.map((s) => `
    <tr>
      <td><div class="sub-name">${avatarHTML(s, "avatar sub-table-logo")}
        <div><div class="n">${esc(s.name)}</div>
        ${s.category ? `<div class="cat-tag">${esc(catLabel(s.category))}</div>` : ""}</div></div></td>
      <td class="ta-r amount-cell">${fmtMoney(s.amount, s.currency)}
        ${s.currency !== base && s.amount_converted != null
          ? `<small>≈ ${fmtMoney(s.amount_converted, base)}</small>` : ""}</td>
      <td>${CYCLE_LABEL[s.cycle]}</td>
      <td><span class="due-badge ${dueClass(s.days_until)}">${fmtDate(s.next_billing_date)} · ${dueLabel(s.days_until)}</span></td>
      <td><span class="pay-tag pay-${s.payment_method}">${s.payment_method === "auto" ? "自动" : "手动"}</span></td>
      <td class="muted">${esc(catLabel(s.category))}</td>
      <td class="ta-r"><div class="row-actions">
        <button class="icon-btn" data-act="edit" data-id="${s.id}" title="编辑"><svg viewBox="0 0 24 24"><path d="m16.5 3.5 4 4L8 20l-5 1 1-5Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg></button>
        <button class="icon-btn" data-act="del" data-id="${s.id}" title="删除"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      </div></td>
    </tr>`).join("")
    : `<tr><td colspan="7"><div class="pending-empty">${t("noSubs")}</div></td></tr>`;
  // 手机卡片
  $("#subs-cards").innerHTML = subs.length ? subs.map((s) => `
    <div class="sub-card">
      ${avatarHTML(s)}
      <div class="mid">
        <div class="n">${esc(s.name)}
          <span class="pay-tag pay-${s.payment_method}" style="font-size:11.5px">${s.payment_method === "auto" ? "自动" : "手动"}</span></div>
        <div class="meta">
          <span>${CYCLE_LABEL[s.cycle]}</span>
          ${s.category ? `<span>${esc(catLabel(s.category))}</span>` : ""}
          ${s.currency !== base && s.amount_converted != null ? `<span>≈ ${fmtMoney(s.amount_converted, base)}/期</span>` : ""}
        </div>
        <div class="card-actions">
          <button class="icon-btn" data-act="edit" data-id="${s.id}"><svg viewBox="0 0 24 24" width="15" height="15"><path d="m16.5 3.5 4 4L8 20l-5 1 1-5Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg></button>
          <button class="icon-btn" data-act="del" data-id="${s.id}"><svg viewBox="0 0 24 24" width="15" height="15"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        </div>
      </div>
      <div class="right">
        <div class="amt">${fmtMoney(s.amount, s.currency)}</div>
        <span class="due-badge ${dueClass(s.days_until)} due">${dueLabel(s.days_until)}</span>
        <div class="muted small" style="margin-top:3px">${fmtDate(s.next_billing_date)}</div>
      </div>
    </div>`).join("")
    : `<div class="panel"><div class="pending-empty">${t("noSubs")}</div></div>`;
}

// 列表操作（事件委托，表格/卡片共用）
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-act]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const sub = state.subs.find((s) => s.id === id);
  if (!sub) return;
  if (btn.dataset.act === "edit") openModal(sub);
  if (btn.dataset.act === "del" && confirm(t("confirmDel", sub.name))) {
    await api(`/api/subscriptions/${id}`, { method: "DELETE" });
    toast(t("deleted"));
    await refreshData(); renderAll();
  }
});

$("#search-input").addEventListener("input", (e) => {
  state.search = e.target.value; reloadSubs();
});
$("#filter-chips").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  state.filter = chip.dataset.filter;
  document.querySelectorAll("#filter-chips .chip").forEach((c) =>
    c.classList.toggle("active", c === chip));
  reloadSubs();
});

/* ---------------- 添加/编辑弹窗 ---------------- */
function openModal(sub = null) {
  const f = state.form = { logoFile: null, logoPreview: null, clearLogo: false,
    color: sub?.color || hashPick(sub?.name || "S") };
  fillCurrencyOptions().then(() => {   // 确保下拉已填充再赋值
    $("#f-currency").value = sub?.currency || state.settings.base_currency;
  });
  $("#modal-title").textContent = sub ? "编辑订阅" : "添加订阅";
  $("#f-id").value = sub?.id || "";
  $("#f-name").value = sub?.name || "";
  $("#f-amount").value = sub ? sub.amount : "";
  $("#f-cycle").value = sub?.cycle || "monthly";
  $("#f-date").value = sub?.next_billing_date || new Date().toISOString().slice(0, 10);
  document.querySelector(`input[name="f-pay"][value="${sub?.payment_method || "auto"}"]`).checked = true;
  $("#f-category").value = sub?.category || "";
  $("#f-url").value = sub?.url || "";
  $("#f-notes").value = sub?.notes || "";
  $("#btn-delete").classList.toggle("hidden", !sub);
  $("#f-logo").value = "";
  renderLogoPreview(sub);
  renderSwatches(f.color);
  $("#modal-mask").classList.remove("hidden");
  setTimeout(() => $("#f-name").focus(), 60);
}

function renderLogoPreview(sub) {
  const f = state.form, el = $("#logo-preview");
  if (f.logoPreview) { el.innerHTML = `<img src="${f.logoPreview}" alt="">`; return; }
  if (f.clearLogo || !(sub?.logo_url)) {
    el.style.background = f.color;
    el.textContent = ($("#f-name").value || "S")[0].toUpperCase();
    el.innerHTML = el.textContent; el.style.background = f.color;
    return;
  }
  el.innerHTML = `<img src="${esc(sub.logo_url)}" alt="">`;
}

function renderSwatches(active) {
  $("#color-swatches").innerHTML = PALETTE.map((c) =>
    `<button type="button" class="swatch ${c === active ? "active" : ""}" data-color="${c}"
      style="background:${c}" title="${c}"></button>`).join("");
}
$("#color-swatches").addEventListener("click", (e) => {
  const sw = e.target.closest(".swatch");
  if (!sw) return;
  state.form.color = sw.dataset.color;
  state.form.clearLogo = true; state.form.logoFile = null; state.form.logoPreview = null;
  renderSwatches(state.form.color);
  renderLogoPreview(currentSub());
});
$("#f-name").addEventListener("input", () => {
  if (!state.form.logoPreview && !state.form.logoFile) renderLogoPreview(currentSub());
});

function currentSub() {
  const id = Number($("#f-id").value);
  return id ? state.subs.find((s) => s.id === id) : null;
}

$("#btn-add").addEventListener("click", () => openModal());
$("#btn-cancel").addEventListener("click", () => $("#modal-mask").classList.add("hidden"));
$("#modal-mask").addEventListener("click", (e) => {
  if (e.target === e.currentTarget) $("#modal-mask").classList.add("hidden");
});

$("#btn-clear-logo").addEventListener("click", () => {
  state.form.logoFile = null; state.form.logoPreview = null; state.form.clearLogo = true;
  $("#f-logo").value = "";
  renderLogoPreview(currentSub());
  toast(t("logoCleared"));
});

$("#f-logo").addEventListener("change", () => {
  const file = $("#f-logo").files[0];
  if (!file) return;
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) { toast(t("logoInvalid")); return; }
  if (file.size > 2 * 1024 * 1024) { toast(t("logoTooBig")); return; }
  state.form.logoFile = file;
  state.form.clearLogo = false;
  const reader = new FileReader();
  reader.onload = () => { state.form.logoPreview = reader.result; renderLogoPreview(currentSub()); };
  reader.readAsDataURL(file);
});

$("#sub-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = $("#f-id").value;
  const name = $("#f-name").value.trim(), amount = $("#f-amount").value;
  if (!name || amount === "") { toast(t("needNameAmount")); return; }
  const body = {
    name, amount: Number(amount),
    currency: $("#f-currency").value,
    cycle: $("#f-cycle").value,
    next_billing_date: $("#f-date").value,
    payment_method: document.querySelector('input[name="f-pay"]:checked').value,
    category: $("#f-category").value.trim(),
    url: $("#f-url").value.trim(),
    notes: $("#f-notes").value,
    color: state.form.color,
  };
  try {
    let saved;
    if (id) saved = await api(`/api/subscriptions/${id}`, { method: "PUT", body });
    else saved = await api("/api/subscriptions", { method: "POST", body });
    if (state.form.logoFile)
      await api(`/api/subscriptions/${saved.id}/logo`,
        { method: "POST", body: (() => { const fd = new FormData(); fd.append("file", state.form.logoFile); return fd; })() });
    else if (state.form.clearLogo && id)
      await api(`/api/subscriptions/${id}/logo`, { method: "DELETE" });
    $("#modal-mask").classList.add("hidden");
    toast(t("saved"));
    await refreshData(); renderAll();
  } catch (err) { if (err.message !== "unauthorized") toast("保存失败：" + err.message); }
});

$("#btn-delete").addEventListener("click", async () => {
  const sub = currentSub();
  if (!sub || !confirm(t("confirmDel", sub.name))) return;
  await api(`/api/subscriptions/${sub.id}`, { method: "DELETE" });
  $("#modal-mask").classList.add("hidden");
  toast(t("deleted"));
  await refreshData(); renderAll();
});

/* ---------------- 设置 ---------------- */
function renderSettings() {
  const sel = $("#set-base-currency");
  if (!sel.options.length)
    sel.innerHTML = state.ratesInfo.rates && Object.keys(state.ratesInfo.rates).length
      ? Object.keys(state.ratesInfo.rates).sort().map((c) => `<option value="${c}">${c}</option>`).join("")
      : ["CNY", "USD", "EUR", "JPY", "GBP", "HKD", "TWD", "KRW", "SGD"].map((c) => `<option value="${c}">${c}</option>`).join("");
  sel.value = state.settings.base_currency;
  $("#set-remind-days").value = state.settings.remind_days;
  $("#rates-status").textContent = state.ratesInfo.updated_at
    ? `上次更新：${state.ratesInfo.updated_at}。` : "尚未同步过汇率。";
  api("/api/ics-url").then((r) => { $("#ics-url").value = location.origin + r.url; })
    .catch(() => { $("#ics-url").value = location.origin + "/api/calendar.ics"; });
}

$("#btn-save-settings").addEventListener("click", async () => {
  try {
    state.settings = await api("/api/settings", { method: "PUT", body: {
      base_currency: $("#set-base-currency").value,
      remind_days: Number($("#set-remind-days").value),
    }});
    toast(t("settingsSaved"));
    await refreshData(); renderAll();
  } catch (err) { if (err.message !== "unauthorized") toast("保存失败：" + err.message); }
});

$("#btn-copy-ics").addEventListener("click", async () => {
  const url = $("#ics-url").value;
  try { await navigator.clipboard.writeText(url); toast(t("copied")); }
  catch {
    const ta = document.createElement("textarea");
    ta.value = url; document.body.appendChild(ta); ta.select();
    document.execCommand("copy"); ta.remove(); toast(t("copied"));
  }
});

$("#btn-logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  toast(t("logoutOk"));
  showLogin();
});

/* ---------------- 启动 ---------------- */
boot().catch((err) => {
  if (err.message !== "unauthorized") toast("加载失败：" + err.message);
});
