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
    themeSaved: "主题色已更新", skinSaved: "界面风格已切换", chartSaved: "图表样式已切换",
    nameSaved: "应用名称已更新", nameInvalid: "应用名称需为 1-12 个字",
    colorInvalid: "颜色格式应为 #RRGGBB",
    bgUploaded: "背景图已更新", bgCleared: "已关闭背景图", bgTooBig: "图片不能超过 4MB",
    iconUploaded: "图标已更新", iconCleared: "已恢复默认图标",
    uploadFail: "上传失败：", noUpcoming: "未来 30 天没有扣费计划 🎉",
    catMonthly: "月合计", bgPresetSaved: "预设背景已应用",
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
// 整数金额省略 .00（仅手机卡片小字行用，缩短宽度给名称行让位）
const fmtMoneyShort = (v, cur) => {
  const n = Number(v);
  return Number.isInteger(n)
    ? `${sym(cur)}${n.toLocaleString("zh-CN")}`
    : fmtMoney(n, cur);
};
const fmtDate = (iso) => { const d = new Date(iso + "T00:00:00"); return `${d.getMonth() + 1}-${String(d.getDate()).padStart(2, "0")}`; };
const dueLabel = (n) => n === 0 ? t("today") : n === 1 ? t("tomorrow") : t("daysLater", n);
const dueClass = (n) => n <= 1 ? "due-soon" : n <= 3 ? "due-warn" : "due-ok";
const catLabel = (c) => CAT_LABEL[c] || c || "—";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (ch) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
const hashPick = (s) => PALETTE[[...String(s)].reduce((a, ch) => a + ch.charCodeAt(0), 0) % PALETTE.length];

/* 主题色工具：hex → HSL；图表色阶从主题色轮转派生（换主题色图表跟着变，不写死蓝紫） */
function hexToHsl(hex) {
  const m = hex.replace("#", "");
  const r = parseInt(m.slice(0, 2), 16) / 255, g = parseInt(m.slice(2, 4), 16) / 255, b = parseInt(m.slice(4, 6), 16) / 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  let h = 0, s = 0;
  if (mx !== mn) {
    const d = mx - mn;
    s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn);
    h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    h *= 60;
  }
  return [h, s * 100, l * 100];
}
function accentHsl() {
  const cur = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#4f6ef7";
  return hexToHsl(cur.startsWith("#") ? cur : "#4f6ef7");
}
function catColor(i, n) {
  const [h, s, l] = accentHsl();
  const hue = (h + i * (n > 6 ? 26 : 34)) % 360;
  const sat = Math.min(Math.max(s, 42), 68);
  const lig = Math.min(Math.max(l, 36), 56);
  return `hsl(${h + i * (n > 6 ? 26 : 34) | 0} ${sat | 0}% ${lig | 0}%)`;
}
const THEME_PRESETS = ["#7c5cff", "#e5484d", "#f59f0a", "#2f9e6e", "#0ea5a4", "#3b82f6", "#d6409f", "#8b5a2b", "#475569"];

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
  payDim: null, statusDim: null,   // v1.6.14 双维筛选：null=无筛选档；付款方式循环 manual→auto，订阅状态循环 active→paused
  search: "", sort: "",
  view: "dashboard",
  cal: { ym: null, byDate: {}, selected: null },
  form: { logoFile: null, logoPreview: null, clearLogo: false, color: PALETTE[0] },
  loginBrand: {},   // v1.5.0 登录页装饰配置（公开端点 / settings 双来源）
};

/* ---------------- 启动 / 登录 ---------------- */
async function boot() {
  // 登录页装饰配置公开可读（v1.5.0）：未登录也能看到自定义标题/背景/图标
  try { applyLoginBrand(await api("/api/brand/login-page")); } catch { /* 失败不阻塞登录流程 */ }
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
    await api("/api/login", { method: "POST", body: { password: ($("#login-password").value || "").trim() } });
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
  const list = $("#currency-list");
  if (!list || list.options.length) { currencyOptionsReady = true; return; }
  try {
    const r = await api("/api/currencies");
    // v1.6.1 币种放开：ECB 30 种作为 datalist 提示项，其余小众币种可自由输入
    list.innerHTML = r.currencies.map((c) => `<option value="${c}"></option>`).join("");
    currencyOptionsReady = true;
  } catch { /* 失败时保留空表，打开表单时再试 */ }
}

async function refreshData() {
  [state.subs, state.stats] = await Promise.all([api("/api/subscriptions"), api("/api/stats")]);
  if (state.stats.missing_rate_currencies.length) toast(t("noRate"));
}

function renderAll() {
  applyAppearance();      // 品牌（名称/图标/favicon/主题色/皮肤/背景层）
  renderRateCard();
  renderStats();
  renderPending();
  renderCategoryChart();
  renderTimeline();
  renderSubs();
  renderSettings();
}

/* ---------------- 导航 ---------------- */
function switchView(name) {
  state.view = name;
  for (const v of ["dashboard", "subs", "calendar", "settings"])
    $("#view-" + v).classList.toggle("hidden", v !== name);
  document.querySelectorAll(".nav-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.nav === name));
  if (name === "calendar") refreshCalendar();   // 每次切入拉最新推算数据
  if (name === "subs") updateChipsOverflow();   // v1.6.14：hidden 时 scrollWidth=0，切入订阅页后重检渐隐兜底
}
document.querySelectorAll(".nav-btn").forEach((b) =>
  b.addEventListener("click", () => switchView(b.dataset.nav)));

/* ---------------- 顶栏 / 外观应用 ---------------- */
function renderRateCard() {
  $("#rates-updated").textContent = state.ratesInfo.updated_at || "未同步";
}

/* 外观应用：品牌名 / 自定义图标 / favicon / 皮肤 / 主题色 / 背景图层（多端同步的设置驱动） */
function applyAppearance() {
  const s = state.settings || {};
  const name = s.app_name || "SubDeck";
  $("#brand-name").textContent = name;
  document.title = `${name} · 订阅管理`;
  // 登录页装饰（标题/图标/背景）统一走 applyLoginBrandFromSettings（v1.5.0）
  const setBrand = (el) => {
    el.innerHTML = s.brand_icon ? `<img src="/api/brand/icon" alt="">` : "S";
  };
  [$("#brand-mark"), $("#icon-preview")].forEach(setBrand);
  const iconHref = s.brand_icon ? `/api/brand/icon` : "/assets/icons/icon-192.png";
  document.querySelector('link[rel="icon"]').href = iconHref;
  document.querySelector('link[rel="apple-touch-icon"]').href = iconHref;
  document.body.dataset.skin = s.skin || "glass";
  applyAccent();
  const bg = $("#bg-layer");
  if (s.bg_image) {
    bg.classList.add("has-bg-img");
    // 预设背景走静态资源（preset:aurora → /assets/bg/aurora.jpg），上传走鉴权端点
    const url = s.bg_image.startsWith("preset:")
      ? `/assets/bg/${s.bg_image.slice(7)}.jpg`
      : "/api/brand/background";
    bg.style.setProperty("--bg-img", `url("${url}")`);
    bg.style.setProperty("--bg-mask-a", (s.bg_mask ?? 35) / 100);
  } else {
    bg.classList.remove("has-bg-img");
    bg.style.removeProperty("--bg-img");
    bg.style.removeProperty("--bg-mask-a");
  }
  applyLoginBrandFromSettings();
}

/* 主题色注入：深色模式自动提亮（L+8），并同步浏览器地址栏 theme-color */
function applyAccentColor(color) {
  const rootStyle = document.documentElement.style;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (!color) { rootStyle.removeProperty("--accent"); meta.content = "#4f6ef7"; return; }
  const [h, sa, l] = hexToHsl(color);
  const lig = document.documentElement.dataset.theme === "dark" ? Math.min(l + 8, 78) : l;
  rootStyle.setProperty("--accent", `hsl(${h | 0} ${sa | 0}% ${lig | 0}%)`);
  meta.content = color;
}
function applyAccent() { applyAccentColor(state.settings?.theme_color); }

/* ---------------- 登录页品牌渲染（v1.5.0，登录前公开生效） ----------------
   数据来源二选一：公开端点 /api/brand/login-page（未登录）或 settings（登录后），
   渲染函数统一走 applyLoginBrand。 */
function applyLoginBrand(d) {
  state.loginBrand = d || {};
  const b = state.loginBrand;
  const title = (b.login_title || b.app_name || "SubDeck").trim();
  $("#login-title").textContent = title;
  const welcome = $("#login-welcome");
  const w = (b.login_welcome || "").trim();
  if (w) { welcome.textContent = w; welcome.classList.remove("hidden"); }
  else welcome.classList.add("hidden");
  applyAccentColor(b.theme_color);
  const lv = $("#login-view");
  lv.classList.remove("bg-grad", "has-bg-img");
  const bg = b.login_bg || "";
  if (bg.startsWith("preset:")) {
    lv.classList.add("has-bg-img");
    lv.style.setProperty("--login-bg-img", `url("/assets/bg/${bg.slice(7)}.jpg")`);
  } else if (/^(loginbg|bg)_\d+\.(png|jpg|webp)$/.test(bg)) {
    lv.classList.add("has-bg-img");
    lv.style.setProperty("--login-bg-img", `url("/api/brand/login-background?v=${encodeURIComponent(b.icon_ver || bg)}")`);
  } else if (!bg) {
    lv.classList.add("bg-grad");   // "" 主题渐变；"none" → 纯底色，不加任何装饰层
  }
  lv.style.setProperty("--login-mask-a", String((b.login_bg_mask ?? 45) / 100));
  const logo = $("#login-logo");
  if (b.icon_ver) {
    logo.innerHTML = `<img src="/api/brand/login-icon?v=${encodeURIComponent(b.icon_ver)}" alt="">`;
  } else {
    logo.textContent = title.charAt(0).toUpperCase() || "S";   // 回落：登录页标题首字母
  }
}
function applyLoginBrandFromSettings() {
  const s = state.settings;
  if (!s) return;
  applyLoginBrand({
    app_name: s.app_name, login_title: s.login_title, login_welcome: s.login_welcome,
    login_bg: s.login_bg, login_bg_mask: s.login_bg_mask, theme_color: s.theme_color,
    icon_ver: s.login_icon || s.brand_icon || "",
  });
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
  if (state.settings) applyAccent();   // 用户主题色随深浅微调
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
  // v1.6.20 回血口径：有拼车/回收时，月均支出卡加净口径副行
  const netEl = $("#stat-monthly-net");
  if (netEl) {
    const net = s.monthly_total_net;
    if (net != null && net < s.monthly_total) {
      netEl.hidden = false;
      $("#stat-monthly-net-val").textContent = fmtMoney(net, base);
    } else netEl.hidden = true;
  }
  // v1.6.3：活跃订阅数旁提示已暂停数量（暂停数 = 列表总数 - 活跃数）
  const pausedN = (state.subs || []).length - s.active_count;
  const hint = $("#stat-paused-hint");
  if (pausedN > 0) { hint.textContent = `另有 ${pausedN} 个已暂停`; hint.style.display = ""; }
  else { hint.style.display = "none"; }
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

function renderCategoryChart() {
  const cats = state.stats.by_category, base = state.settings.base_currency;
  const box = $("#category-chart");
  if (!cats.length) { box.innerHTML = `<div class="chart-empty">${t("noSubsHome")}</div>`; return; }
  const style = state.settings.chart_style || "bars";
  if (style === "bars") { renderBarsInto(box, cats, base); return; }

  const total = cats.reduce((a, c) => a + c.monthly, 0) || 1;
  const size = 148, r = 56, cx = size / 2, cy = size / 2;
  const single = cats.length === 1;
  let segs = "", acc = 0;
  cats.forEach((c, i) => {
    const frac = c.monthly / total;
    const color = c._color = catColor(i, cats.length);
    if (single) return;   // 单分类由整圆兜底（弧线端点重合时 path 会退化）
    const a0 = acc * 2 * Math.PI - Math.PI / 2, a1 = (acc + frac) * 2 * Math.PI - Math.PI / 2;
    const x0 = (cx + r * Math.cos(a0)).toFixed(2), y0 = (cy + r * Math.sin(a0)).toFixed(2);
    const x1 = (cx + r * Math.cos(a1)).toFixed(2), y1 = (cy + r * Math.sin(a1)).toFixed(2);
    const large = frac > .5 ? 1 : 0;
    segs += style === "donut"
      ? `<path d="M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}" fill="none" stroke="${color}" stroke-width="17"></path>`
      : `<path d="M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z" fill="${color}"></path>`;
    acc += frac;
  });
  const firstColor = catColor(0, cats.length);
  const svgBody = single
    ? (style === "donut"
        ? `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${firstColor}" stroke-width="17"></circle>`
        : `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${firstColor}"></circle>`)
    : segs;
  const center = style === "donut"
    ? `<text x="${cx}" y="${cy - 3}" text-anchor="middle" class="donut-center-label">${t("catMonthly")}</text>
       <text x="${cx}" y="${cy + 15}" text-anchor="middle" font-weight="700" font-size="13" fill="var(--text)">${fmtMoney(total, base)}</text>`
    : "";
  box.innerHTML = `
    <div class="chart-flex">
      <div class="chart-svg"><svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="分类月度占比${style === "donut" ? "环形" : "饼"}图">${svgBody}${center}</svg></div>
      <div class="chart-legend">
        ${cats.map((c) => `
          <div class="legend-row">
            <span class="legend-dot" style="background:${c._color || catColor(0, 1)}"></span>
            <span class="legend-name">${esc(catLabel(c.category))}</span>
            <span class="legend-val">${fmtMoney(c.monthly, base)} · ${(c.monthly / total * 100).toFixed(0)}%</span>
          </div>`).join("")}
      </div>
    </div>`;
}

function renderBarsInto(box, cats, base) {
  const max = Math.max(...cats.map((c) => c.monthly), 0.0001);
  box.innerHTML = `<div class="category-bars">` + cats.map((c, i) => `
      <div class="cat-row">
        <span class="cat-name">${esc(catLabel(c.category))}</span>
        <span class="cat-track"><span class="cat-fill" style="width:${Math.max(c.monthly / max * 100, 4)}%;--row-color:${catColor(i, cats.length)}"></span></span>
        <span class="cat-amount">${fmtMoney(c.monthly, base)}</span>
      </div>`).join("") + `</div>`;
}

function renderTimeline() {
  const list = (state.stats.upcoming || []).filter((s) => s.days_until <= 30);
  $("#timeline").innerHTML = list.length
    ? list.map((s) => `
      <div class="tl-item ${s.days_until === 0 ? "today" : s.days_until === 1 ? "tomorrow" : ""}">
        <span class="tl-dot"></span>
        <div class="tl-date">
          <span class="d">${fmtDate(s.next_billing_date)}</span>
          <span class="rel">${dueLabel(s.days_until)}</span>
        </div>
        <div class="tl-body">
          ${avatarHTML(s)}
          <span class="tl-name">${esc(s.name)}</span>
          <span class="tl-amount">${fmtMoney(s.amount, s.currency)}</span>
        </div>
      </div>`).join("")
    : `<div class="tl-empty">${t("noUpcoming")}</div>`;
}

/* ---------------- 扣费日历 ---------------- */
const localISO = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const todayISO = () => localISO(new Date());

async function refreshCalendar() {
  try {
    const r = await api("/api/billing-calendar?months=12");
    state.cal.byDate = {};
    for (const e of r.entries) (state.cal.byDate[e.date] ||= []).push(e);
    if (!state.cal.ym) state.cal.ym = todayISO().slice(0, 7);
    if (!state.cal.selected) {
      // 默认选中下一个有续费的日期（第一眼看到内容），否则今天
      state.cal.selected = r.entries.length ? r.entries[0].date : todayISO();
    }
    renderCalendar();
    renderCalDetail(state.cal.selected);
  } catch (err) { if (err.message !== "unauthorized") $("#cal-detail").innerHTML = `<div class="cal-detail-empty">加载失败：${esc(err.message)}</div>`; }
}

function renderCalendar() {
  const [y, m] = state.cal.ym.split("-").map(Number);
  $("#cal-title").textContent = `${y} 年 ${m} 月`;
  const cur = state.settings.base_currency;
  const first = new Date(y, m - 1, 1);
  const offset = (first.getDay() + 6) % 7;              // 周一开头
  const daysIn = new Date(y, m, 0).getDate();
  const today = todayISO();
  let html = "";
  for (let i = 0; i < offset; i++) html += `<span class="cal-cell dim" aria-hidden="true"></span>`;
  for (let day = 1; day <= daysIn; day++) {
    const ds = `${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const list = state.cal.byDate[ds] || [];
    const isToday = ds === today;
    const isSel = state.cal.selected === ds;
    const currencies = new Set(list.map((e) => e.currency));
    const total = list.reduce((a, e) => a + e.amount, 0);
    const amt = list.length && currencies.size === 1
      ? `<span class="amt">${sym(list[0].currency)}${total % 1 ? total.toFixed(1) : total}</span>` : "";
    const cls = ["cal-cell", isToday ? "today" : "", isSel && !isToday ? "selected" : ""].join(" ");
    html += `<button type="button" class="${cls}" data-date="${ds}" aria-label="${ds}${list.length ? `，${list.length} 笔续费` : ""}">
      <span class="d">${day}</span>
      ${list.length ? `<span class="dots">${list.map(() => `<span class="dot"></span>`).join("")}</span>` : ""}
      ${amt}
    </button>`;
  }
  $("#cal-grid").innerHTML = html;
  // 月合计（同币种才显示）
  const monthPrefix = `${y}-${String(m).padStart(2, "0")}`;
  const monthList = Object.entries(state.cal.byDate).filter(([d]) => d.startsWith(monthPrefix)).flatMap(([, l]) => l);
  const mc = new Set(monthList.map((e) => e.currency));
  const mt = $("#cal-month-total");
  if (monthList.length && mc.size === 1) {
    const sum = monthList.reduce((a, e) => a + e.amount, 0);
    mt.innerHTML = `本月共 ${monthList.length} 笔 · 合计 <strong>${fmtMoney(sum, monthList[0].currency)}</strong>`;
    mt.classList.remove("hidden");
  } else mt.classList.add("hidden");
}

function renderCalDetail(ds) {
  const list = state.cal.byDate[ds] || [];
  $("#cal-detail-title").textContent =
    `${Number(ds.slice(5, 7))} 月 ${Number(ds.slice(8, 10))} 日 · ${list.length} 笔续费`;
  $("#cal-detail").innerHTML = list.length
    ? list.map((e) => {
        const s = state.subs.find((x) => x.id === e.id) || e;
        const conv = s.currency !== state.settings.base_currency && s.amount_converted != null
          ? `<small> ≈ ${fmtMoney(s.amount_converted, state.settings.base_currency)}</small>` : "";
        return `<div class="cal-item">
          ${avatarHTML(s)}
          <div><div class="tl-name">${esc(e.name)}</div>
          ${e.category ? `<span class="cat-tag">${esc(catLabel(e.category))}</span>` : ""}</div>
          <span class="tl-amount">${fmtMoney(e.amount, e.currency)}${conv}</span>
        </div>`;
      }).join("")
    : `<div class="cal-detail-empty">该日没有续费计划</div>`;
}

function shiftMonth(n) {
  const [y, m] = state.cal.ym.split("-").map(Number);
  const d = new Date(y, m - 1 + n, 1);
  state.cal.ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  renderCalendar();
}
$("#cal-prev").addEventListener("click", () => shiftMonth(-1));
$("#cal-next").addEventListener("click", () => shiftMonth(1));
$("#cal-today").addEventListener("click", () => {
  state.cal.ym = todayISO().slice(0, 7);
  renderCalendar();
  renderCalDetail(state.cal.selected);
});
$("#cal-grid").addEventListener("click", (e) => {
  const cell = e.target.closest(".cal-cell[data-date]");
  if (!cell || cell.classList.contains("dim")) return;
  state.cal.selected = cell.dataset.date;
  renderCalendar();
  renderCalDetail(cell.dataset.date);
});

/* ---------------- 订阅列表 ---------------- */
async function reloadSubs() {
  const q = state.search ? `&search=${encodeURIComponent(state.search)}` : "";
  const pay = state.payDim || "all";
  const st = state.statusDim || "all";
  state.subs = await api(`/api/subscriptions?filter=${pay}&status=${st}${q}`);
  renderSubs();
  updateChipsOverflow();
}

function renderSubs() {
  const base = state.settings.base_currency;
  let subs = state.subs;
  renderFxSummary();   // v1.6.7：外币月均汇总条（数据源 stats，口径与统计卡一致）
  if (state.sort === "asc" || state.sort === "desc") {
    const val = (s) => (s.amount_converted ?? s.amount ?? 0);   // 按折算后金额比较，跨币种才有意义
    subs = [...subs].sort((a, b) => state.sort === "asc" ? val(a) - val(b) : val(b) - val(a));
  }
  // 桌面表格
  $("#subs-tbody").innerHTML = subs.length ? subs.map((s) => `
    <tr class="${s.active ? "" : "row-paused"}">
      <td><div class="sub-name">${avatarHTML(s, "avatar sub-table-logo")}
        <div><div class="n">${esc(s.name)}${s.active ? "" : ` <span class="paused-tag">已暂停</span>`}</div>
        ${s.category ? `<div class="cat-tag">${esc(catLabel(s.category))}</div>` : ""}</div></div></td>
      <td class="ta-r amount-cell">${subAmtHTML(s)}
        ${s.currency !== base && s.amount_converted != null
          ? `<small class="fx-badge" style="font-size:12px">≈ ${fmtMoney(s.amount_converted, base)}</small>` : ""}</td>
      <td>${CYCLE_LABEL[s.cycle]}</td>
      <td>${s.active
        ? `<span class="due-badge ${dueClass(s.days_until)}">${fmtDate(s.next_billing_date)} · ${dueLabel(s.days_until)}</span>`
        : `<span class="due-badge paused">已暂停</span>`}</td>
      <td><span class="pay-tag pay-${s.payment_method}">${s.payment_method === "auto" ? "自动" : "手动"}</span>${(s.share_count || 0) >= 2 && s.share_mode !== "paid" ? ` <span class="car-badge">拼车 ${s.share_count} 人</span>` : s.share_mode === "paid" ? ` <span class="car-badge">拼车</span>` : ""}</td>
      <td class="muted">${esc(catLabel(s.category))}</td>
      <td class="ta-r"><div class="row-actions">
        <button class="icon-btn" data-act="edit" data-id="${s.id}" title="编辑"><svg viewBox="0 0 24 24"><path d="m16.5 3.5 4 4L8 20l-5 1 1-5Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg></button>
        ${s.active
          ? `<button class="icon-btn" data-act="pause" data-id="${s.id}" title="暂停（不进统计与提醒）"><svg viewBox="0 0 24 24"><path d="M8 5v14M16 5v14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg></button>`
          : `<button class="icon-btn" data-act="resume" data-id="${s.id}" title="恢复"><svg viewBox="0 0 24 24"><path d="M7 4.5v15l13-7.5Z" fill="currentColor"/></svg></button>`}
        <button class="icon-btn" data-act="del" data-id="${s.id}" title="删除"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      </div></td>
    </tr>`).join("")
    : `<tr><td colspan="7"><div class="pending-empty">${t("noSubs")}</div></td></tr>`;
/* v1.6.20 回血口径：卡片金额区——拼车（均分或实付）显示实际口径，有回收显示净额，其余显示标价 */
function subAmtHTML(s, compact) {
  // compact（手机卡片）：小字省略「实付/份额」口径前缀（meta 行拼车徽章已表达），给名称行让位
  const mode = s.share_mode;
  const hasCar = mode === "paid" || mode === "split";
  const hasRebate = (s.rebate_total || 0) > 0 && s.monthly_cost_net != null && s.monthly_cost_net < s.amount;
  if (hasCar) {
    const saved = Math.round((s.amount - s.share_base) * 100) / 100;
    const tag = compact ? "" : (mode === "paid" ? "实付 · " : "份额 · ");
    if (saved > 0) {
      const f = compact ? fmtMoneyShort : fmtMoney;
      return `${fmtMoney(s.share_base, s.currency)}<span class="amt-sub">${tag}标价 ${f(s.amount, s.currency)} · 省 ${f(saved, s.currency)}</span>`;
    }
    return `${fmtMoney(s.share_base, s.currency)}<span class="amt-sub">${compact ? "拼车" : (mode === "paid" ? "实付" : "份额")}</span>`;
  }
  if (hasRebate) {
    const f = compact ? fmtMoneyShort : fmtMoney;
    return `${fmtMoney(Math.round((s.amount - s.rebate_total) * 100) / 100, s.currency)}<span class="amt-sub">${compact ? "" : "净 · "}标价 ${f(s.amount, s.currency)} · 回收 ${f(s.rebate_total, s.currency)}</span>`;
  }
  return `${fmtMoney(s.amount, s.currency)}`;
}

  // 手机卡片（左滑露出编辑/暂停/删除，卡片本体纯展示；手势判定见 initSwipe）
  $("#subs-cards").innerHTML = subs.length ? subs.map((s) => `
    <div class="swipe-wrap">
      <div class="swipe-actions">
        <button class="swipe-btn edit" data-act="edit" data-id="${s.id}"><svg viewBox="0 0 24 24"><path d="m16.5 3.5 4 4L8 20l-5 1 1-5Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg><span>编辑</span></button>
        ${s.active
          ? `<button class="swipe-btn pause" data-act="pause" data-id="${s.id}"><svg viewBox="0 0 24 24"><path d="M8 5v14M16 5v14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg><span>暂停</span></button>`
          : `<button class="swipe-btn pause" data-act="resume" data-id="${s.id}"><svg viewBox="0 0 24 24"><path d="M7 4.5v15l13-7.5Z" fill="currentColor"/></svg><span>恢复</span></button>`}
        <button class="swipe-btn del" data-act="del" data-id="${s.id}"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>删除</span></button>
      </div>
      <div class="sub-card ${s.active ? "" : "row-paused"}">
        ${avatarHTML(s)}
        <div class="mid">
          <div class="n">${esc(s.name)}</div>
          <div class="meta">
            <span class="pay-tag pay-${s.payment_method}">${s.payment_method === "auto" ? "自动" : "手动"}</span>
            <span>${CYCLE_LABEL[s.cycle]}</span>
            ${s.category ? `<span>${esc(catLabel(s.category))}</span>` : ""}
            ${s.currency !== base && s.amount_converted != null ? `<span class="fx-badge">≈ ${fmtMoney(s.amount_converted, base)}/期</span>` : ""}
            ${s.active ? "" : `<span class="paused-tag">已暂停</span>`}
          </div>
          ${s.share_mode === "paid"
            ? `<div class="badge-row"><span class="car-badge-lg">拼车 · 实付 ${fmtMoneyShort(s.share_base, s.currency)}</span></div>`
            : s.share_mode === "split"
              ? `<div class="badge-row"><span class="car-badge-lg">拼车 · ${s.share_count} 人均分</span></div>` : ""}
        </div>
        <div class="right">
          <div class="amt">${subAmtHTML(s, true)}</div>
          ${s.active
            ? `<div class="due-row"><span class="due-badge ${dueClass(s.days_until)}">${dueLabel(s.days_until)}</span><span class="muted small">${fmtDate(s.next_billing_date)}</span></div>`
            : `<div class="due-row"><span class="due-badge paused">已暂停</span></div>`}
        </div>
      </div>
    </div>`).join("")
    : `<div class="panel"><div class="pending-empty">${t("noSubs")}</div></div>`;
}

// ---- 外币订阅月均汇总条（v1.6.7） ----
// 数据源 stats.fx_summary：全量活跃订阅、monthly_cost 求和。与概览「月均支出」同一口径，两处数字可对账
function renderFxSummary() {
  const box = $("#fx-summary"), bar = $("#fx-bar"), detail = $("#fx-detail");
  const base = state.settings.base_currency;
  const fx = state.stats && state.stats.fx_summary;
  if (!fx || (!fx.count && !fx.missing_count)) {   // 无外币订阅：整条隐藏，不占地方
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");
  $(".fx-count").textContent = fx.count;
  $(".fx-total").textContent = `≈ ${fmtMoney(fx.total_monthly, base)}/月`;
  const up = state.settings.rates_updated_at || "";
  $(".fx-date").textContent = up ? `按汇率快照 ${up.slice(5, 10)}` : "按当前汇率";
  const open = localStorage.getItem("subdeck-fx-open") === "1";
  bar.dataset.open = open ? "1" : "0";
  detail.classList.toggle("hidden", !open);
  const note = fx.missing_count
    ? `<div class="fx-note">另有 ${fx.missing_count} 笔外币订阅（${fx.missing_currencies.map((c) => esc(c)).join("、")}）因暂无汇率未计入，可在「设置 → 手动汇率」补录后纳入。</div>`
    : "";
  const rows = fx.items.map((i) => `
    <div class="fx-item">
      <span class="fx-name">${esc(i.name)}<span class="fx-sub">${CYCLE_LABEL[i.cycle] || i.cycle} ${fmtMoney(i.amount, i.currency)}</span></span>
      <span class="fx-amount">≈ ${fmtMoney(i.monthly_cost, base)}/月</span>
    </div>`).join("");
  detail.innerHTML =
    note + rows +
    `<div class="fx-item fx-total-row"><span class="fx-name">月均合计</span><span class="fx-amount">≈ ${fmtMoney(fx.total_monthly, base)}/月</span></div>`;
}
$("#fx-bar").addEventListener("click", () => {
  const open = localStorage.getItem("subdeck-fx-open") !== "1";
  localStorage.setItem("subdeck-fx-open", open ? "1" : "0");
  renderFxSummary();
});

// 列表操作（事件委托，表格/卡片共用）
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-act]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const sub = state.subs.find((s) => s.id === id);
  if (!sub) return;
  if (btn.dataset.act === "edit") openModal(sub);
  if (btn.dataset.act === "pause" || btn.dataset.act === "resume") {
    const active = btn.dataset.act === "resume" ? 1 : 0;
    try {
      await api(`/api/subscriptions/${id}`, { method: "PUT", body: { active } });
      toast(active
        ? `已恢复「${sub.name}」`
        : `已暂停「${sub.name}」，不进统计与提醒，随时可恢复`);
      await refreshData(); renderAll();
    } catch (err) { toast(err.message || "操作失败"); }
    return;
  }
  if (btn.dataset.act === "del" && confirm(t("confirmDel", sub.name))) {
    await api(`/api/subscriptions/${id}`, { method: "DELETE" });
    toast(t("deleted"));
    await refreshData(); renderAll();
  }
});

// ---- 手机卡片左滑操作（iOS 列表同款交互） ----
// 卡片 touch-action: pan-y 让浏览器接管垂直滚动，横向位移由这里接管：
// 首次位移判方向，水平明显才跟进；松手超过半程吸附露出，否则回弹。
const SWIPE_W = 228; // 胶囊面板 216px（72×3）+ 右侧留缝 6px×2，与 CSS 保持一致
function closeSwipe(except) {
  document.querySelectorAll(".swipe-wrap.open").forEach((w) => {
    if (w !== except) w.classList.remove("open");
  });
}
(function initSwipe() {
  let sx = 0, sy = 0, dx = 0, wrapEl = null, cardEl = null, horizontal = null, startOpen = false, active = false;
  document.addEventListener("touchstart", (e) => {
    const w = e.target.closest(".swipe-wrap");
    if (!w) return;
    wrapEl = w; cardEl = w.querySelector(".sub-card");
    sx = e.touches[0].clientX; sy = e.touches[0].clientY;
    dx = 0; horizontal = null; active = true;
    startOpen = w.classList.contains("open");
    cardEl.style.transition = "none";
  }, { passive: true });
  document.addEventListener("touchmove", (e) => {
    if (!active || !wrapEl) return;
    dx = e.touches[0].clientX - sx;
    const dy = e.touches[0].clientY - sy;
    if (horizontal === null) {
      if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return; // 未过起步阈值，等方向明确
      horizontal = Math.abs(dx) > Math.abs(dy);
      if (horizontal) { closeSwipe(wrapEl); wrapEl.classList.add("dragging"); } // 滑新的卡片时收起旧的
    }
    if (!horizontal) return; // 纵向手势交还浏览器滚动
    if (e.cancelable) e.preventDefault();
    const base = startOpen ? -SWIPE_W : 0;
    const x = Math.min(0, Math.max(-SWIPE_W, base + dx));
    cardEl.style.transform = `translateX(${x}px)`;
  }, { passive: false });
  document.addEventListener("touchend", () => {
    if (!active || !wrapEl) return;
    active = false;
    cardEl.style.transition = "";
    wrapEl.classList.remove("dragging");
    if (horizontal === null) return; // 纯点击，不产生位移
    const base = startOpen ? -SWIPE_W : 0;
    wrapEl.classList.toggle("open", base + dx < -SWIPE_W / 2);
    cardEl.style.transform = "";
    horizontal = null;
  });
  // 点其它区域收回（capture 阶段，先于按钮委托执行）
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".swipe-wrap")) closeSwipe();
  }, true);
})();

$("#search-input").addEventListener("input", (e) => {
  state.search = e.target.value; reloadSubs();
});
/* v1.6.14 筛选升级：三按钮 chips：全部（一键清空）+ 付款方式/订阅状态（循环切换，含无筛选档） */
const PAY_CYCLE = [null, "manual", "auto"];          // 循环含无筛选档：裸名→手动→自动→裸名
const STATUS_CYCLE = [null, "active", "paused"];     // 裸名→活跃→已暂停→裸名
const PAY_LABEL = { manual: "手动", auto: "自动" };
const STATUS_LABEL = { active: "活跃", paused: "已暂停" };

function nextCycle(cur, cycle) {
  return cycle[(cycle.indexOf(cur) + 1) % cycle.length];   // null→第1档→…→绕回 null
}

function renderFilterChips() {
  const all = $("#chip-all"), pay = $("#chip-pay"), status = $("#chip-status");
  const cleared = !state.payDim && !state.statusDim;
  all.classList.toggle("active", cleared);   // 有任意筛选生效时「全部」退高亮变灰（仍可点击重置）
  if (state.payDim) {
    pay.classList.add("armed");
    pay.innerHTML = `<span class="dim">付款方式：</span>${PAY_LABEL[state.payDim]}`;
  } else { pay.classList.remove("armed"); pay.textContent = "付款方式"; }
  if (state.statusDim) {
    status.classList.add("armed");
    status.innerHTML = `<span class="dim">订阅状态：</span>${STATUS_LABEL[state.statusDim]}`;
  } else { status.classList.remove("armed"); status.textContent = "订阅状态"; }
  updateChipsOverflow();
}

/* 方案 Z 兜底：仅真实溢出时加右缘渐隐提示可横滑 */
function updateChipsOverflow() {
  requestAnimationFrame(() => {
    const el = $("#filter-chips");
    el.classList.toggle("scrollable", el.scrollWidth > el.clientWidth + 1);
  });
}
window.addEventListener("resize", updateChipsOverflow);

$("#filter-chips").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  if (chip.id === "chip-all") { state.payDim = null; state.statusDim = null; }
  else if (chip.id === "chip-pay") state.payDim = nextCycle(state.payDim, PAY_CYCLE);
  else if (chip.id === "chip-status") state.statusDim = nextCycle(state.statusDim, STATUS_CYCLE);
  renderFilterChips();
  reloadSubs();
});

/* 统计卡点击入口：活跃订阅卡→切订阅页+活跃筛选；「另有 N 个已暂停」hint→已暂停筛选 */
function jumpFiltered(statusDim) {
  state.payDim = null;
  state.statusDim = statusDim;
  renderFilterChips();
  switchView("subs");
  window.scrollTo({ top: 0, behavior: "smooth" });
  reloadSubs();
}
$("#stat-active-card").addEventListener("click", () => jumpFiltered("active"));
$("#stat-paused-hint").addEventListener("click", (e) => {
  e.stopPropagation();   // hint 在活跃卡内部，点它只切已暂停，不冒泡成活跃
  jumpFiltered("paused");
});

/* ---------------- 添加/编辑弹窗 ---------------- */
function openModal(sub = null) {
  const f = state.form = { logoFile: null, logoPreview: null, clearLogo: false,
    color: sub?.color || hashPick(sub?.name || "S") };
  fillCurrencyOptions().then(() => {   // 确保下拉已填充再赋值
    $("#f-currency").value = sub?.currency || state.settings.base_currency;
  });
  $("#f-active").checked = sub ? !!sub.active : true;   // v1.6.3 暂停/恢复
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
  // v1.6.20 回血口径：拼车人数与回收记录（回收区块仅编辑模式显示）
  $("#f-share").value = sub ? (sub.share_count || 0) : "";
  $("#f-mypaid").value = sub && sub.my_paid ? sub.my_paid : "";
  const rblock = $("#rebate-block");
  if (sub) { rblock.hidden = false; renderRebates(sub.id); $("#f-rebate-date").value = new Date().toISOString().slice(0, 10); }
  else { rblock.hidden = true; $("#rebate-list").innerHTML = ""; }
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

/* 排序按钮：默认 → 金额 ↑ → 金额 ↓ 循环（按折算后金额） */
const SORT_LABEL = { "": "默认排序", asc: "金额 ↑", desc: "金额 ↓" };
$("#btn-sort").addEventListener("click", () => {
  const order = ["", "asc", "desc"];
  state.sort = order[(order.indexOf(state.sort) + 1) % order.length];
  $("#btn-sort").textContent = SORT_LABEL[state.sort];
  renderSubs();
});
$("#btn-cancel").addEventListener("click", () => $("#modal-mask").classList.add("hidden"));

/* ---------------- 回收记录（v1.6.20 回血口径） ---------------- */
/* 金额展示复用 fmtMoney（符号前缀格式，44 行定义）。回收按订阅币种记账。 */
const rebateCurrency = (subId) => (state.subs || []).find((x) => x.id === subId)?.currency || "CNY";

async function renderRebates(subId) {
  const list = $("#rebate-list");
  try {
    const d = await api(`/api/subscriptions/${subId}/rebates`);
    const cur = rebateCurrency(subId);
    list.innerHTML = d.rebates.length
      ? d.rebates.map((r) => `
        <div class="rebate-row">
          <span class="rebate-date">${fmtDate(r.date)}</span>
          <span class="rebate-note" title="${esc(r.note)}">${esc(r.note || "回收")}</span>
          <span class="rebate-amt">-${fmtMoney(r.amount, cur)}</span>
          <button type="button" class="icon-btn" data-rebate-del="${r.id}" title="删除"><svg viewBox="0 0 24 24" width="14" height="14"><path d="M5 7h14M9 7V5h6v2m-7 0 1 13h6l1-13" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg></button>
        </div>`).join("") + `<div class="rebate-row rebate-total"><span>合计回收</span><b>${fmtMoney(d.total, cur)}</b></div>`
      : `<div class="muted small">暂无回收记录</div>`;
  } catch { list.innerHTML = `<div class="muted small">回收记录加载失败</div>`; }
}

$("#rebate-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-rebate-del]");
  if (!btn) return;
  const subId = parseInt($("#f-id").value, 10);
  try {
    await api(`/api/subscriptions/${subId}/rebates/${btn.dataset.rebateDel}`, { method: "DELETE" });
    toast("已删除");
    renderRebates(subId);
  } catch (err) { if (err.message !== "unauthorized") toast("删除失败：" + err.message); }
});

$("#btn-add-rebate").addEventListener("click", async () => {
  const subId = parseInt($("#f-id").value, 10);
  const date = $("#f-rebate-date").value, amount = parseFloat($("#f-rebate-amount").value);
  if (!date || !amount || amount <= 0) { toast("请填写回收日期和金额"); return; }
  try {
    await api(`/api/subscriptions/${subId}/rebates`,
      { method: "POST", body: { date, amount, note: $("#f-rebate-note").value.trim() } });
    $("#f-rebate-amount").value = ""; $("#f-rebate-note").value = "";
    toast("回收已记入");
    renderRebates(subId);
  } catch (err) { if (err.message !== "unauthorized") toast("记入失败：" + err.message); }
});
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
    currency: $("#f-currency").value.trim().toUpperCase(),
    cycle: $("#f-cycle").value,
    next_billing_date: $("#f-date").value,
    payment_method: document.querySelector('input[name="f-pay"]:checked').value,
    category: $("#f-category").value.trim(),
    url: $("#f-url").value.trim(),
    notes: $("#f-notes").value,
    color: state.form.color,
    active: $("#f-active").checked ? 1 : 0,
    share_count: Math.max(0, parseInt($("#f-share").value, 10) || 0),
    my_paid: Math.max(0, parseFloat($("#f-mypaid").value) || 0),
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
  // 邮箱提醒（v1.4.0）
  $("#f-notify-enabled").checked = !!state.settings.notify_enabled;
  $("#f-notify-emails").value = state.settings.notify_emails || "";
  $("#f-notify-lead").value = state.settings.notify_lead_days;
  $("#notify-lead-preview").textContent = state.settings.notify_lead_days;
  $("#f-notify-hour").value = state.settings.notify_hour;
  $("#f-smtp-host").value = state.settings.smtp_host || "";
  $("#f-smtp-port").value = state.settings.smtp_port;
  $("#f-smtp-ssl").checked = !!state.settings.smtp_ssl;
  $("#f-smtp-user").value = state.settings.smtp_user || "";
  $("#f-smtp-pass").value = state.settings.smtp_pass || "";
  $("#rates-status").textContent = state.ratesInfo.updated_at
    ? `上次更新：${state.ratesInfo.updated_at}。` : "尚未同步过汇率。";
  api("/api/ics-url").then((r) => { $("#ics-url").value = location.origin + r.url; })
    .catch(() => { $("#ics-url").value = location.origin + "/api/calendar.ics"; });
  renderAppearanceControls();
  renderLoginControls();
  renderCatChips();
  renderCategoryOptions();
  renderCustomRates();   // 手动汇率面板（v1.6.1）
}

/* ---------------- 手动汇率面板（v1.6.1） ---------------- */
async function renderCustomRates() {
  const panel = $("#panel-custom-rates");
  if (!panel) return;
  let d;
  try { d = await api("/api/rates/custom"); } catch { return; }
  const hasMissing = d.missing.length > 0;
  const hasCustom = Object.keys(d.custom).length > 0;
  const superseded = new Set(d.superseded || []);
  // 三层显隐：无事=整块隐藏；有待折算或已设手动汇率才露面
  panel.style.display = (hasMissing || hasCustom) ? "" : "none";

  const missBox = $("#custom-rates-missing"), missList = $("#custom-rates-missing-list");
  missBox.style.display = hasMissing ? "" : "none";
  if (hasMissing) {
    $("#custom-rates-missing-title").textContent =
      `以下 ${d.missing.length} 个币种暂未计入统计（无汇率）`;
    missList.innerHTML = d.missing.map((c) => `
      <div class="cr-row" data-cur="${c}" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span style="font-weight:500;min-width:52px;">${c}</span>
        <span class="muted small">1 ${c} =</span>
        <input type="number" class="cr-rate" min="0" step="any" inputmode="decimal"
               style="width:110px;text-align:right;" placeholder="0.00">
        <span class="muted small">${d.base_currency}</span>
        <button class="btn small" data-action="cr-set" data-cur="${c}">折算</button>
      </div>`).join("");
  }

  const actBox = $("#custom-rates-active"), actList = $("#custom-rates-active-list");
  actBox.style.display = hasCustom ? "" : "none";
  if (hasCustom) {
    actList.innerHTML = Object.entries(d.custom).map(([c, v]) => {
      const taken = superseded.has(c);
      const badge = taken
        ? `<span class="cr-badge cr-badge-auto">自动汇率已接管</span>`
        : `<span class="cr-badge cr-badge-manual">手动 · 不自动更新</span>`;
      return `
      <div class="cr-row" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span style="font-weight:500;min-width:0;">1 ${c} = ${v} ${d.base_currency}</span>
        ${badge}
        <button class="btn small ghost" data-action="cr-del" data-cur="${c}">移除</button>
      </div>`;
    }).join("");
  }
}

$("#panel-custom-rates").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const cur = btn.dataset.cur;
  try {
    if (btn.dataset.action === "cr-set") {
      const row = btn.closest(".cr-row");
      const v = parseFloat(row.querySelector(".cr-rate").value);
      if (!(v > 0)) { toast("请输入大于 0 的汇率"); return; }
      const d = await api("/api/rates/custom", { method: "POST", body: { currency: cur, rate: v } });
      toast(`已设置 1 ${cur} = ${d.custom[cur]} ${d.base_currency}`);
    } else if (btn.dataset.action === "cr-del") {
      await api(`/api/rates/custom/${cur}`, { method: "DELETE" });
      toast(`已移除 ${cur} 的手动汇率`);
    }
    await refreshData();      // 统计金额实时更新
    renderCustomRates();      // 面板刷新（含空态隐藏）
  } catch (err) { toast(err.message || "操作失败"); }
});

/* ---------------- 登录页设置面板（v1.5.0） ---------------- */
function renderLoginControls() {
  const s = state.settings;
  $("#f-login-title").value = s.login_title || "";
  $("#f-login-welcome").value = s.login_welcome || "";
  $("#login-mask").value = s.login_bg_mask;
  $("#login-mask-value").textContent = `${s.login_bg_mask}%`;
  const isUpload = s.login_bg && !s.login_bg.startsWith("preset:") && s.login_bg !== "none";
  document.querySelectorAll("#login-bg-picker .bg-card").forEach((b) => {
    const v = b.dataset.bg || "";
    b.classList.toggle("on",
      isUpload ? false : v === (s.login_bg || ""));   // 自定义上传后由 upload-line 呈现选中态
  });
  $("#login-bg-upload-line").classList.toggle("hidden", !isUpload);
  if (isUpload) $("#login-bg-upload-name").textContent = `✓ 已上传：${s.login_bg}`;
  const pv = $("#login-icon-preview");
  if (s.login_icon) pv.innerHTML = `<img src="/api/brand/login-icon?v=${encodeURIComponent(s.login_icon)}" alt="">`;
  else if (s.brand_icon) pv.innerHTML = `<img src="/api/brand/icon" alt="">`;
  else pv.textContent = (s.login_title || s.app_name || "S").trim().charAt(0).toUpperCase() || "S";
}

/* 背景卡即改即存（与外观预设一致） */
$("#login-bg-picker").addEventListener("click", (e) => {
  const b = e.target.closest("button.bg-card");
  if (!b) return;
  saveAppearance({ login_bg: b.dataset.bg || "" }, "登录页背景已更新，退出登录即可查看");
});

/* 遮罩滑条：拖动实时预览，松手落库 */
$("#login-mask").addEventListener("input", () => {
  $("#login-mask-value").textContent = `${$("#login-mask").value}%`;
  $("#login-view").style.setProperty("--login-mask-a", String($("#login-mask").value / 100));
});
$("#login-mask").addEventListener("change", () => {
  saveAppearance({ login_bg_mask: Number($("#login-mask").value) }, "遮罩已保存");
});

/* 自定义登录页背景上传 / 删除 */
$("#login-bg-file").addEventListener("change", async () => {
  const f = $("#login-bg-file").files[0];
  if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  try {
    const r = await api("/api/brand/login-background", { method: "POST", body: fd });
    state.settings.login_bg = r.login_bg;   // 上传接口已写入设置，前端只同步状态
    applyAppearance(); renderLoginControls();
    toast("登录页背景已更新，退出登录即可查看");
  } catch (err) { if (err.message !== "unauthorized") toast("上传失败：" + err.message); }
  $("#login-bg-file").value = "";
});
$("#btn-login-bg-clear").addEventListener("click", async () => {
  try {
    await api("/api/brand/login-background", { method: "DELETE" });
    state.settings.login_bg = "";
    applyAppearance(); renderLoginControls();
    toast("已删除自定义背景，恢复主题渐变");
  } catch (err) { if (err.message !== "unauthorized") toast("删除失败：" + err.message); }
});

/* 登录页标题 / 欢迎语保存 */
$("#btn-save-login").addEventListener("click", async () => {
  try {
    state.settings = await api("/api/settings", { method: "PUT", body: {
      login_title: $("#f-login-title").value,
      login_welcome: $("#f-login-welcome").value,
    }});
    applyAppearance(); renderLoginControls();
    toast("登录页设置已保存，退出登录即可查看");
  } catch (err) { if (err.message !== "unauthorized") toast("保存失败：" + err.message); }
});

/* 登录页图标上传 / 删除（回落：品牌图标 → 标题首字母） */
$("#login-icon-file").addEventListener("change", async () => {
  const f = $("#login-icon-file").files[0];
  if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  try {
    const r = await api("/api/brand/login-icon", { method: "POST", body: fd });
    state.settings.login_icon = r.login_icon;
    applyAppearance(); renderLoginControls();
    toast("登录页图标已更新，退出登录即可查看");
  } catch (err) { if (err.message !== "unauthorized") toast("上传失败：" + err.message); }
  $("#login-icon-file").value = "";
});
$("#btn-login-icon-clear").addEventListener("click", async () => {
  try {
    await api("/api/brand/login-icon", { method: "DELETE" });
    state.settings.login_icon = "";
    applyAppearance(); renderLoginControls();
    toast("已删除登录页图标，恢复跟随品牌图标 / 首字母");
  } catch (err) { if (err.message !== "unauthorized") toast("删除失败：" + err.message); }
});

/* ---------------- 分类管理（v1.5.0） ---------------- */
const BUILT_IN_CATS = Object.entries(CAT_LABEL);   // [key, label]

function renderCatChips() {
  const box = $("#cat-chips");
  const custom = state.settings?.custom_categories || [];
  box.innerHTML =
    BUILT_IN_CATS.map(([k, label]) => `<span class="chip" title="内置分类">${label}</span>`).join("") +
    custom.map((c) =>
      `<span class="chip custom">${esc(c)}<button type="button" class="chip-del" data-cat="${esc(c)}" title="删除分类">✕</button></span>`
    ).join("");
}

function renderCategoryOptions() {
  const dl = $("#category-list");
  if (!dl) return;
  const custom = state.settings?.custom_categories || [];
  dl.innerHTML =
    BUILT_IN_CATS.map(([k, label]) => `<option value="${k}">${label}</option>`).join("") +
    custom.map((c) => `<option value="${esc(c)}"></option>`).join("");
}

async function saveCustomCats(cats, msg) {
  try {
    state.settings = await api("/api/settings", { method: "PUT", body: { custom_categories: cats } });
    renderCatChips(); renderCategoryOptions();
    if (msg) toast(msg);
  } catch (err) { if (err.message !== "unauthorized") toast("保存失败：" + err.message); }
}

async function addCustomCat() {
  const name = $("#f-new-cat").value.trim();
  if (!name) return;
  const custom = state.settings?.custom_categories || [];
  const dupBuiltIn = BUILT_IN_CATS.some(([k, label]) => k === name || label === name);
  if (dupBuiltIn || custom.includes(name)) { toast("分类已存在"); return; }
  if (custom.length >= 20) { toast("自定义分类最多 20 个"); return; }
  await saveCustomCats([...custom, name], `已添加分类「${name}」`);
  $("#f-new-cat").value = "";
}

$("#btn-add-cat").addEventListener("click", addCustomCat);
$("#f-new-cat").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addCustomCat(); } });
$("#cat-chips").addEventListener("click", (e) => {
  const del = e.target.closest(".chip-del");
  if (!del) return;
  const cat = del.dataset.cat;
  const custom = (state.settings?.custom_categories || []).filter((c) => c !== cat);
  saveCustomCats(custom, `已删除分类「${cat}」，已有订阅不受影响`);
})

/* 外观面板控件赋值（服务端值 → 控件） */
function renderAppearanceControls() {
  const s = state.settings;
  $("#set-app-name").value = s.app_name;
  $("#theme-color-input").value = s.theme_color || "";
  document.querySelectorAll('input[name="set-skin"]').forEach((r) => r.checked = r.value === (s.skin || "glass"));
  document.querySelectorAll("#chart-seg .seg-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.chart === (s.chart_style || "bars")));
  $("#bg-mask").value = s.bg_mask;
  $("#bg-mask-value").textContent = `${s.bg_mask}%`;
  document.querySelectorAll("#bg-presets .preset-swatch").forEach((b) =>
    b.classList.toggle("active", b.dataset.preset === (s.bg_image || "")));
  const bgPrev = $("#bg-preview");
  if (s.bg_image) {
    const url = s.bg_image.startsWith("preset:")
      ? `/assets/bg/${s.bg_image.slice(7)}.jpg`
      : "/api/brand/background";
    bgPrev.style.backgroundImage = `url("${url}")`;
    bgPrev.textContent = "";
  } else { bgPrev.style.backgroundImage = ""; bgPrev.textContent = "未设置背景图"; }
  renderThemeSwatches();
}

function renderThemeSwatches() {
  const cur = state.settings.theme_color || "";
  /* v1.6.15 双色预览：左上=浅色模式色，右下=深色模式色（与 applyAccentColor 的 L+8/上限78 提亮规则一致） */
  const grad = (c) => {
    const [h, s, l] = hexToHsl(c);
    return `linear-gradient(135deg, ${c} 50%, hsl(${h | 0} ${s | 0}% ${Math.min(l + 8, 78).toFixed(1)}%) 50%)`;
  };
  $("#theme-swatches").innerHTML =
    `<button type="button" class="theme-swatch default ${!cur ? "active" : ""}" data-color="" title="默认蓝"></button>` +
    THEME_PRESETS.map((c) =>
      `<button type="button" class="theme-swatch ${c === cur ? "active" : ""}" data-color="${c}" style="background:${grad(c)}" title="${c}"></button>`
    ).join("");
}

/* 外观即改即存：改一项立刻持久化 + 应用，多端下一次打开自动一致 */
async function saveAppearance(patch, msg) {
  try {
    state.settings = await api("/api/settings", { method: "PUT", body: patch });
    applyAppearance();
    if ("chart_style" in patch) {
      document.querySelectorAll("#chart-seg .seg-btn").forEach((b) =>
        b.classList.toggle("active", b.dataset.chart === (state.settings.chart_style || "bars")));
      renderCategoryChart();   // v1.6.12 修复：切换图表样式后立即重绘（此前仅刷新页面才生效）
    }
    if ("theme_color" in patch) renderThemeSwatches();
    if ("bg_image" in patch) renderAppearanceControls();   // v1.6.19 修复：切预设背景后立即刷新选中外环（同 v1.6.12 图表切换教训）
    if (msg) toast(msg);
  } catch (err) { if (err.message !== "unauthorized") toast("保存失败：" + err.message); }
}

$("#theme-swatches").addEventListener("click", (e) => {
  const sw = e.target.closest(".theme-swatch");
  if (sw) saveAppearance({ theme_color: sw.dataset.color }, t("themeSaved"));
});
$("#theme-color-input").addEventListener("change", (e) => {
  const v = e.target.value.trim();
  if (v && !/^#[0-9a-fA-F]{6}$/.test(v)) { toast(t("colorInvalid")); return; }
  saveAppearance({ theme_color: v }, t("themeSaved"));
});
$("#btn-theme-reset").addEventListener("click", () => saveAppearance({ theme_color: "" }, t("themeSaved")));
$("#skin-row").addEventListener("change", (e) => {
  if (e.target.name === "set-skin") saveAppearance({ skin: e.target.value }, t("skinSaved"));
});
$("#chart-seg").addEventListener("click", (e) => {
  const btn = e.target.closest(".seg-btn");
  if (btn) saveAppearance({ chart_style: btn.dataset.chart }, t("chartSaved"));
});
$("#set-app-name").addEventListener("change", (e) => {
  const v = e.target.value.trim();
  if (!v || v.length > 12) { toast(t("nameInvalid")); return; }
  saveAppearance({ app_name: v }, t("nameSaved"));
});
$("#btn-name-reset").addEventListener("click", () => saveAppearance({ app_name: "SubDeck" }, t("nameSaved")));
$("#bg-mask").addEventListener("input", (e) => {
  $("#bg-mask-value").textContent = `${e.target.value}%`;   // 实时预览，不落库
  $("#bg-layer").style.setProperty("--bg-mask-a", e.target.value / 100);
});
$("#bg-mask").addEventListener("change", (e) => saveAppearance({ bg_mask: Number(e.target.value) }));
$("#bg-presets").addEventListener("click", (e) => {
  const b = e.target.closest(".preset-swatch");
  if (!b) return;
  if (b.dataset.preset) {          // 预设：点选即用（覆盖上传背景）
    saveAppearance({ bg_image: b.dataset.preset }, t("bgPresetSaved"));
  } else {                          // 无背景：走 DELETE 清理上传文件并置空
    api("/api/brand/background", { method: "DELETE" }).then(() => {
      state.settings.bg_image = "";
      applyAppearance(); renderAppearanceControls();
      toast(t("bgCleared"));
    }).catch((err) => { if (err.message !== "unauthorized") toast("操作失败：" + err.message); });
  }
});
$("#btn-bg-clear").addEventListener("click", async () => {
  try {
    await api("/api/brand/background", { method: "DELETE" });
    state.settings.bg_image = "";
    applyAppearance(); renderAppearanceControls();
    toast(t("bgCleared"));
  } catch (err) { if (err.message !== "unauthorized") toast("操作失败：" + err.message); }
});
$("#btn-icon-clear").addEventListener("click", async () => {
  try {
    await api("/api/brand/icon", { method: "DELETE" });
    state.settings.brand_icon = "";
    applyAppearance();
    toast(t("iconCleared"));
  } catch (err) { if (err.message !== "unauthorized") toast("操作失败：" + err.message); }
});

/* 大图自动压缩：长边 ≤1920、JPEG 0.85，手机拍的照片也能直接传 */
function compressImage(file, maxEdge = 1920, quality = 0.85) {
  return new Promise((res, rej) => {
    const url = URL.createObjectURL(file);
    const im = new Image();
    im.onload = () => {
      URL.revokeObjectURL(url);
      const scale = Math.min(1, maxEdge / Math.max(im.naturalWidth, im.naturalHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(im.naturalWidth * scale);
      canvas.height = Math.round(im.naturalHeight * scale);
      canvas.getContext("2d").drawImage(im, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => blob ? res(new File([blob], "bg.jpg", { type: "image/jpeg" })) : rej(new Error("compress")),
        "image/jpeg", quality);
    };
    im.onerror = rej;
    im.src = url;
  });
}

$("#set-bg-file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) { toast(t("logoInvalid")); return; }
  if (file.size > 4 * 1024 * 1024) { toast(t("bgTooBig")); return; }
  try {
    const fd = new FormData();
    fd.append("file", await compressImage(file));
    const r = await api("/api/brand/background", { method: "POST", body: fd });
    state.settings.bg_image = r.bg_image;
    applyAppearance(); renderAppearanceControls();
    toast(t("bgUploaded"));
  } catch (err) { if (err.message !== "unauthorized") toast(t("uploadFail") + err.message); }
});
$("#set-icon-file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) { toast(t("logoInvalid")); return; }
  if (file.size > 2 * 1024 * 1024) { toast(t("logoTooBig")); return; }
  try {
    const fd = new FormData();
    fd.append("file", file);   // 图标保持原图（清晰度优先），大小由后端兜底
    const r = await api("/api/brand/icon", { method: "POST", body: fd });
    state.settings.brand_icon = r.brand_icon;
    applyAppearance();
    toast(t("iconUploaded"));
  } catch (err) { if (err.message !== "unauthorized") toast(t("uploadFail") + err.message); }
});

$("#btn-save-settings").addEventListener("click", async () => {
  try {
    const oldBase = state.settings.base_currency;
    state.settings = await api("/api/settings", { method: "PUT", body: {
      base_currency: $("#set-base-currency").value,
      remind_days: Number($("#set-remind-days").value),
    }});
    toast(t("settingsSaved"));
    if (state.settings.base_currency !== oldBase) {
      toast(`基准币种已切换为 ${state.settings.base_currency}，手动汇率已清空（如有请重新填写）`);
    }
    await refreshData(); renderAll();
  } catch (err) { if (err.message !== "unauthorized") toast("保存失败：" + err.message); }
});

/* ---------------- 邮箱提醒（v1.4.0） ---------------- */
$("#btn-save-notify").addEventListener("click", async () => {
  try {
    state.settings = await api("/api/settings", { method: "PUT", body: {
      notify_enabled: $("#f-notify-enabled").checked,
      notify_emails: $("#f-notify-emails").value,
      notify_lead_days: Number($("#f-notify-lead").value),
      notify_hour: Number($("#f-notify-hour").value),
      smtp_host: $("#f-smtp-host").value,
      smtp_port: Number($("#f-smtp-port").value),
      smtp_ssl: $("#f-smtp-ssl").checked,
      smtp_user: $("#f-smtp-user").value,
      smtp_pass: $("#f-smtp-pass").value,
    }});
    renderSettings();   // 回填服务端规范化后的值
    toast(state.settings.notify_enabled ? "提醒设置已保存，将按计划自动发送" : "已保存（当前未启用）");
  } catch (err) { if (err.message !== "unauthorized") toast("保存失败：" + err.message); }
});

$("#btn-test-notify").addEventListener("click", async () => {
  const r = $("#notify-test-result");
  r.classList.remove("hidden");
  r.textContent = "正在发送测试邮件…";
  try {
    const res = await api("/api/notify/test", { method: "POST", body: {
      notify_emails: $("#f-notify-emails").value,
      smtp_host: $("#f-smtp-host").value,
      smtp_port: Number($("#f-smtp-port").value),
      smtp_ssl: $("#f-smtp-ssl").checked,
      smtp_user: $("#f-smtp-user").value,
      smtp_pass: $("#f-smtp-pass").value,
    }});
    r.textContent = "✓ " + res.info;
  } catch (err) {
    if (err.message !== "unauthorized") r.textContent = "✗ " + err.message;
  }
});

$("#f-notify-lead").addEventListener("input", () => {
  $("#notify-lead-preview").textContent = $("#f-notify-lead").value || 3;
});

$("#ics-url").addEventListener("click", () => $("#ics-url").select());   // 点击全选整条 URL，防止只复制到尾部 token

$("#btn-copy-ics").addEventListener("click", async () => {
  const url = $("#ics-url").value;
  try { await navigator.clipboard.writeText(url); toast(t("copied")); }
  catch {
    const ta = document.createElement("textarea");
    ta.value = url; document.body.appendChild(ta); ta.select();
    document.execCommand("copy"); ta.remove(); toast(t("copied"));
  }
});

// 重置日历订阅链接（v1.6.19）：二次确认，旧链接立即作废
$("#btn-reset-ics").addEventListener("click", () => $("#ics-reset-mask").classList.remove("hidden"));
$("#btn-ics-reset-cancel").addEventListener("click", () => $("#ics-reset-mask").classList.add("hidden"));
$("#ics-reset-mask").addEventListener("click", (e) => {
  if (e.target === e.currentTarget) $("#ics-reset-mask").classList.add("hidden");
});
$("#btn-ics-reset-go").addEventListener("click", async () => {
  try {
    const r = await api("/api/ics-token/reset", { method: "POST" });
    $("#ics-url").value = location.origin + r.url;
    $("#ics-reset-mask").classList.add("hidden");
    toast("已重置，请用新链接重新订阅日历");
  } catch {
    toast("重置失败，请重试");
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

/* ---------- 数据备份：导出 / 导入 / 回滚（v1.6.11） ---------- */
(function () {
  const mask = document.getElementById("export-mask");
  const btnExport = document.getElementById("btn-export");
  if (!btnExport || !mask) return;
  const btnRollback = document.getElementById("btn-rollback");
  const note = document.getElementById("backup-note");

  // 回滚按钮显隐：有存档才显示
  api("/api/import-status").then((r) => {
    if (r.has_rollback) btnRollback.classList.remove("hidden");
  }).catch(() => {});

  /* 导出：弹选项 → 下载 → 按是否含敏感给出对应提醒 */
  btnExport.addEventListener("click", () => mask.classList.remove("hidden"));
  document.getElementById("btn-export-cancel").addEventListener("click", () => mask.classList.add("hidden"));
  mask.addEventListener("click", (e) => { if (e.target === mask) mask.classList.add("hidden"); });
  document.getElementById("btn-export-go").addEventListener("click", async () => {
    const sensitive = document.getElementById("export-sensitive").checked ? 1 : 0;
    mask.classList.add("hidden");
    try {
      const resp = await fetch(`/api/export?sensitive=${sensitive}`, { credentials: "same-origin" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const blob = await resp.blob();
      const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `subdeck-backup-${stamp}.zip`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast(sensitive
        ? "导出成功：文件含授权码等隐私敏感信息，请妥善保管"
        : "导出成功：已剔除敏感信息");
    } catch { toast("导出失败，请重试"); }
  });

  /* 导入：选文件 → 确认覆盖 → 上传 → 全量刷新 */
  const fileInput = document.getElementById("import-file");
  document.getElementById("btn-import").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    fileInput.value = "";
    if (!file) return;
    if (!confirm("导入将覆盖当前全部订阅与设置（图片以备份包为准）。\n导入前会自动留档，可一键回滚到导入前。\n\n确定导入 " + file.name + " ？")) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch("/api/import", { method: "POST", body: fd, credentials: "same-origin" });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "HTTP " + r.status);
      toast(j.sensitive
        ? "导入成功（备份包含敏感信息）"
        : "导入成功（备份包不含敏感信息，相关设置保留本地现状）");
      await refreshData(); renderAll();
      btnRollback.classList.remove("hidden");
      note.textContent = "上次导入：" + (j.exported_at || "").slice(0, 10) + " 的备份包 · 订阅 " + j.subscriptions + " 条 · 图片 " + j.assets + " 张";
    } catch (e) { toast("导入失败：" + e.message); }
  });

  /* 回滚：恢复到最近一次导入前 */
  btnRollback.addEventListener("click", async () => {
    if (!confirm("回滚将恢复到最近一次导入前的状态（回滚后存档作废）。确定？")) return;
    try {
      const r = await fetch("/api/import/rollback", { method: "POST", credentials: "same-origin" });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || "HTTP " + r.status);
      toast("已回滚到导入前");
      await refreshData(); renderAll();
      btnRollback.classList.add("hidden");
      note.textContent = "";
    } catch (e) { toast("回滚失败：" + e.message); }
  });
})();

/* ---------- 设置页左导航：点击平滑滚动 + 滚动高亮联动（v1.6.9，仅 ≥1024 显示） ---------- */
(function () {
  const nav = document.getElementById("settings-nav");
  if (!nav) return;
  // 点击：拦截默认跳转，平滑滚动 + 不污染浏览器历史
  nav.addEventListener("click", (e) => {
    const a = e.target.closest("a[href^='#']");
    if (!a) return;
    const target = document.getElementById(a.getAttribute("href").slice(1));
    if (!target) return;
    e.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    history.replaceState(null, "", a.getAttribute("href"));
  });
  // scrollspy：以视口 15% 高度线为参考，压在哪张卡片上就高亮哪项（rAF 节流，确定性取位无竞态）
  const links = [...nav.querySelectorAll("a")];
  const targets = links
    .map((a) => ({ a, el: document.getElementById(a.getAttribute("href").slice(1)) }))
    .filter((x) => x.el);
  let ticking = false;
  function spy() {
    ticking = false;
    let cur = null;
    // 已滚动到页面底部：强制高亮最后一项（否则末尾卡片永远到不了参考线）
    const doc = document.documentElement;
    if (scrollY + innerHeight >= doc.scrollHeight - 4 && targets.length) {
      cur = targets[targets.length - 1].a;
    } else {
      const line = window.innerHeight * 0.15;
      for (const { a, el } of targets) {
        if (el.style.display === "none") continue;
        if (el.getBoundingClientRect().top <= line) cur = a;
      }
    }
    links.forEach((a) => a.classList.toggle("on", a === cur));
  }
  window.addEventListener("scroll", () => {
    if (!ticking) { ticking = true; requestAnimationFrame(spy); }
  }, { passive: true });
  spy();
  // 「手动汇率」面板按需显示/隐藏时，导航项同步显隐
  const mr = document.getElementById("panel-custom-rates");
  const mrLink = targets.find((x) => x.el.id === "panel-custom-rates")?.a;
  if (mr && mrLink) {
    const sync = () => { mrLink.style.display = mr.style.display === "none" ? "none" : ""; };
    sync();
    new MutationObserver(sync).observe(mr, { attributes: true, attributeFilter: ["style"] });
  }
})();
