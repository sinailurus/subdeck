/* SubDeck 只读演示页 · 虚构数据层
 *
 * 页面上的订阅、金额、日期均为演示示例，与任何真实账号无关。
 * 日期以「访问当天」为基准推算（即将扣费 / 日历 / 统计都随之滚动），
 * 保证演示数据始终新鲜；汇率与金额为写死的示例值。
 * 接口字段与后端 /api 返回结构对齐，由 demo.js 拦截层消费。
 */
(function () {
  "use strict";

  const VERSION = window.SUBDECK_DEMO_VERSION || "demo";

  /* ---------- 日期工具（与后端 billing 同语义） ---------- */
  const CYCLE_MONTHS = { weekly: 1, monthly: 1, quarterly: 3, semiannual: 6, yearly: 12 };
  const MONTHLY_FACTOR = { weekly: 52 / 12, monthly: 1, quarterly: 1 / 3, semiannual: 1 / 6, yearly: 1 / 12 };
  const pad2 = (n) => String(n).padStart(2, "0");
  const iso = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  const daysInMonth = (y, m0) => new Date(y, m0 + 1, 0).getDate();
  function addMonths(d, n) {
    const total = d.getFullYear() * 12 + d.getMonth() + n;
    const y = Math.floor(total / 12);
    const m = total - y * 12;
    return new Date(y, m, Math.min(d.getDate(), daysInMonth(y, m)));
  }
  function addCycle(d, cycle) {
    if (cycle === "weekly") { const w = new Date(d); w.setDate(w.getDate() + 7); return w; }
    return addMonths(d, CYCLE_MONTHS[cycle] || 1);
  }

  const TODAY = new Date();
  TODAY.setHours(0, 0, 0, 0);
  const plusDays = (n) => { const d = new Date(TODAY); d.setDate(d.getDate() + n); return d; };
  const agoISO = (n, hm) => { const d = plusDays(-n); return `${iso(d)}T${hm}`; };

  const round2 = (x) => Math.round(x * 100) / 100;

  /* ---------- 虚构静态汇率：rates[x] = 1 单位基准币 = x 单位 x 币种 ---------- */
  const BASE = "CNY";
  const RATES = { USD: 0.1408, EUR: 0.1292, JPY: 21.35, GBP: 0.1108, HKD: 1.0921 };
  const convert = (amount, cur) =>
    cur === BASE ? round2(amount) : (RATES[cur] ? round2(amount / RATES[cur]) : null);

  /* ---------- 虚构订阅清单（offset = 下次扣费距今天数） ---------- */
  const SPECS = [
    { id: 1,  name: "Netflix 标准版",        amount: 15.49, currency: "USD", cycle: "monthly",    offset: 2,   pay: "auto",   cat: "流媒体", color: "#ef5350", logo: "netflix.png",   url: "https://www.netflix.com", created: 210 },
    { id: 2,  name: "ChatGPT Plus",          amount: 20,    currency: "USD", cycle: "monthly",    offset: 4,   pay: "auto",   cat: "AI 工具", color: "#26a69a", logo: "chatgpt.png",  url: "https://chatgpt.com",     created: 160, share: 5,
      rebates: [{ ago: 12, amount: 20, note: "拼车空位短期转出" }] },
    { id: 3,  name: "爱奇艺黄金会员",        amount: 78,    currency: "CNY", cycle: "quarterly",  offset: 6,   pay: "auto",   cat: "流媒体", color: "#f59f0a", logo: "iqiyi.png",     url: "",                        created: 120,
      rebates: [{ ago: 35, amount: 25, note: "季卡立减活动" }] },
    { id: 4,  name: "网易云音乐黑胶 VIP",    amount: 15,    currency: "CNY", cycle: "monthly",    offset: 11,  pay: "auto",   cat: "音乐",   color: "#ec407a", logo: "netease.png",   url: "",                        created: 400 },
    { id: 5,  name: "iCloud+ 200GB",         amount: 21,    currency: "CNY", cycle: "monthly",    offset: 15,  pay: "auto",   cat: "云存储", color: "#5c9dff", logo: "icloud.png",    url: "https://www.icloud.com",  created: 700, share: 5 },
    { id: 6,  name: "百度网盘超级会员",      amount: 30,    currency: "CNY", cycle: "monthly",    offset: 22,  pay: "auto",   cat: "云存储", color: "#ab63f6", logo: "baidu.png",     url: "",                        created: 320 },
    { id: 7,  name: "Microsoft 365 家庭版",  amount: 498,   currency: "CNY", cycle: "yearly",     offset: 29,  pay: "auto",   cat: "办公",   color: "#ff7043", logo: "m365.png",      url: "",                        created: 560, share: 5 },
    { id: 8,  name: "Photoshop 摄影套餐",    amount: 888,   currency: "CNY", cycle: "yearly",     offset: 44,  pay: "auto",   cat: "设计",   color: "#8d6e63", logo: "photoshop.png", url: "",                        created: 240 },
    { id: 9,  name: "轻量云服务器",          amount: 288,   currency: "CNY", cycle: "yearly",     offset: 96,  pay: "manual", cat: "主机",   color: "#66bb6a", logo: "",              url: "",                        created: 430,
      note: "手动续费，已开到期提醒" },
    { id: 10, name: "Notion Plus",           amount: 10,    currency: "USD", cycle: "monthly",    offset: 40,  pay: "auto",   cat: "AI 工具", color: "#78909c", logo: "",              url: "",                        created: 200,
      note: "已暂停，免费版够用了", active: 0 },
  ];

  /* 生成订阅对象：折算 / 月均 / 拼车 / 回收字段与后端 _with_rates 同口径 */
  function buildSubs() {
    const list = SPECS.map((sp) => {
      const active = sp.active === undefined ? 1 : sp.active;
      const next = plusDays(sp.offset);
      const rebates = sp.rebates || [];
      const rebateTotal = round2(rebates.reduce((a, r) => a + r.amount, 0));
      const amountConverted = convert(sp.amount, sp.currency);
      const monthlyCost = amountConverted === null ? null : round2(amountConverted * MONTHLY_FACTOR[sp.cycle]);
      const shareCount = sp.share || 0;
      const myPaid = 0;
      let shareBase, shareMode;
      if (myPaid > 0) { shareBase = myPaid; shareMode = "paid"; }
      else if (shareCount >= 2) { shareBase = round2(sp.amount / shareCount); shareMode = "split"; }
      else { shareBase = sp.amount; shareMode = null; }
      const shareConv = convert(shareBase, sp.currency);
      const monthlyShare = shareConv === null ? null : round2(shareConv * MONTHLY_FACTOR[sp.cycle]);
      const monthlyNet = monthlyShare === null ? null
        : round2(Math.max(0, monthlyShare - rebateTotal / (CYCLE_MONTHS[sp.cycle] || 1)));
      return {
        id: sp.id, name: sp.name, amount: sp.amount, currency: sp.currency,
        cycle: sp.cycle, next_billing_date: iso(next), payment_method: sp.pay,
        category: sp.cat, notes: sp.note || "", logo_file: sp.logo ? sp.logo : "",
        color: sp.color, url: sp.url || "", active,
        created_at: agoISO(sp.created, "09:30:00"), updated_at: agoISO(Math.max(0, sp.created - 30), "21:05:00"),
        days_until: sp.offset,
        amount_converted: amountConverted, monthly_cost: monthlyCost,
        share_base: shareBase, share_mode: shareMode,
        monthly_cost_share: monthlyShare,
        rebate_total: rebateTotal, monthly_cost_net: monthlyNet,
        logo_url: sp.logo ? `./logo/${sp.logo}` : "",
      };
    });
    list.sort((a, b) => (a.next_billing_date < b.next_billing_date ? -1 : 1));
    return list;
  }

  const SUBS = buildSubs();
  const ACTIVE = SUBS.filter((s) => s.active);
  const REBATES = {};
  for (const sp of SPECS) {
    if (!sp.rebates) continue;
    REBATES[sp.id] = sp.rebates.map((r, i) => ({
      id: sp.id * 100 + i, date: iso(plusDays(-r.ago)), amount: r.amount, note: r.note,
    }));
  }

  /* ---------- 设置（演示配置，与后端 /api/settings 字段一致） ---------- */
  const SETTINGS = {
    base_currency: BASE,
    remind_days: 7,
    app_name: "SubDeck",
    theme_color: "",
    skin: "glass",
    bg_image: "",
    bg_mask: 35,
    chart_style: "bars",
    brand_icon: "",
    login_title: "",
    login_welcome: "",
    login_bg: "",
    login_bg_mask: 45,
    custom_categories: [],
    notify_enabled: false,
    notify_emails: "",
    notify_lead_days: 3,
    notify_hour: 8,
    rates_updated_at: iso(TODAY),
    smtp_host: "",
    smtp_port: 465,
    smtp_ssl: true,
    smtp_user: "",
    smtp_pass: "",
  };

  /* ---------- 统计（与后端 /api/stats 同口径） ---------- */
  function buildStats() {
    let monthlyTotal = 0, monthlyNet = 0;
    const byCategory = new Map();
    const pending = [], upcoming = [], missing = [];
    for (const s of ACTIVE) {
      if (s.monthly_cost === null) { missing.push(s.currency); continue; }
      monthlyTotal += s.monthly_cost;
      monthlyNet += (s.monthly_cost_net !== null ? s.monthly_cost_net : s.monthly_cost);
      const cat = s.category || "other";
      byCategory.set(cat, round2((byCategory.get(cat) || 0) + s.monthly_cost));
      if (s.days_until <= SETTINGS.remind_days) pending.push(s);
      if (s.days_until <= 30) upcoming.push(s);
    }
    const categories = [...byCategory.entries()]
      .map(([category, monthly]) => ({ category, monthly }))
      .sort((a, b) => b.monthly - a.monthly);
    const fxItems = ACTIVE
      .filter((s) => s.currency !== BASE && s.monthly_cost !== null)
      .map((s) => ({ id: s.id, name: s.name, cycle: s.cycle, amount: s.amount, currency: s.currency, monthly_cost: s.monthly_cost }));
    return {
      base_currency: BASE,
      monthly_total: round2(monthlyTotal),
      monthly_total_net: round2(monthlyNet),
      yearly_total: round2(monthlyTotal * 12),
      active_count: ACTIVE.length,
      pending_count: pending.length,
      missing_rate_currencies: [...new Set(missing)].sort(),
      by_category: categories,
      pending, upcoming,
      fx_summary: {
        count: fxItems.length,
        total_monthly: round2(fxItems.reduce((a, i) => a + i.monthly_cost, 0)),
        missing_count: 0,
        missing_currencies: [],
        items: fxItems,
      },
    };
  }
  const STATS = buildStats();

  /* ---------- 扣费日历（与后端 /api/billing-calendar 同口径） ---------- */
  function buildCalendar(months) {
    const n = Math.max(1, Math.min(months || 12, 24));
    const end = addMonths(TODAY, n);
    const entries = [];
    for (const s of ACTIVE) {
      let d = plusDays(s.offset);
      while (d <= end) {
        entries.push({
          date: iso(d), id: s.id, name: s.name, amount: s.amount,
          currency: s.currency, cycle: s.cycle, category: s.category,
          logo_url: s.logo_url,
        });
        d = addCycle(d, s.cycle);
      }
    }
    entries.sort((a, b) => (a.date < b.date ? -1 : 1));
    return { entries, months: n };
  }

  /* ---------- 订阅列表筛选（与后端 list_subs 同口径） ---------- */
  function listSubs(query) {
    const filter = query.get("filter") || "all";
    const status = query.get("status") || "all";
    const search = (query.get("search") || "").trim().toLowerCase();
    let subs = SUBS.slice();
    if (filter === "auto" || filter === "manual") subs = subs.filter((s) => s.payment_method === filter);
    if (status === "active") subs = subs.filter((s) => s.active);
    else if (status === "paused") subs = subs.filter((s) => !s.active);
    if (search) subs = subs.filter((s) => s.name.toLowerCase().includes(search) || (s.category || "").toLowerCase().includes(search));
    return subs;
  }

  /* ---------- 币种清单（与后端一致：ECB 覆盖范围） ---------- */
  const CURRENCIES = [
    "CNY", "USD", "EUR", "JPY", "GBP", "HKD", "TWD", "KRW", "SGD",
    "AUD", "CAD", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF",
    "BRL", "MXN", "IDR", "INR", "ILS", "PHP", "THB", "MYR", "NZD",
    "TRY", "ZAR", "ISK",
  ];

  /* ---------- 请求分发：path -> 数据；返回 undefined 表示演示页未提供 ---------- */
  function route(path, query) {
    if (path === "/api/me") {
      return { version: VERSION, auth_required: false, logged_in: true };
    }
    if (path === "/api/settings") return SETTINGS;
    if (path === "/api/rates") {
      return { base_currency: BASE, rates: RATES, updated_at: iso(TODAY) };
    }
    if (path === "/api/currencies") return { currencies: CURRENCIES };
    if (path === "/api/subscriptions") return listSubs(query);
    if (path === "/api/stats") return STATS;
    if (path === "/api/billing-calendar") return buildCalendar(parseInt(query.get("months") || "12", 10));
    if (path === "/api/rates/custom") {
      return { base_currency: BASE, custom: {}, missing: [], superseded: [], rates_updated_at: iso(TODAY) };
    }
    if (path === "/api/brand/login-page") {
      return {
        app_name: SETTINGS.app_name, login_title: "", login_welcome: "",
        login_bg: "", login_bg_mask: 45, theme_color: "", icon_ver: "",
      };
    }
    if (path === "/api/import-status") return { has_rollback: false };
    if (path === "/api/health") return { status: "ok", version: VERSION };
    const m = path.match(/^\/api\/subscriptions\/(\d+)\/rebates$/);
    if (m) {
      if (!SUBS.some((s) => String(s.id) === m[1])) return undefined;
      const list = REBATES[m[1]] || [];
      return { rebates: list, total: round2(list.reduce((a, r) => a + r.amount, 0)) };
    }
    return undefined;
  }

  window.SubDeckDemoData = { route };
})();
