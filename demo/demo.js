/* SubDeck 只读演示页 · 拦截层
 *
 * 在主脚本（app.js）加载前替换 window.fetch：
 *   - 读取请求：返回本页内置的虚构示例数据（见 demo-data.js），不发任何网络请求；
 *   - 写入请求：一律拒绝并弹出演示提示，页面数据保持不变；
 *   - 本页为纯静态站点，没有后端与数据库，修改操作在源头即不存在。
 * 另附少量演示标识：页头「演示」徽标、进入提示、关于弹窗里的说明。
 */
(function () {
  "use strict";

  const BLOCK_MSG = "演示模式：数据只读，修改未保存";
  const BLOCK_SPECIAL = new Set(["/api/export"]);   // 读取类特例：备份导出返回压缩包，演示页不提供

  function json(obj, status) {
    return new Response(JSON.stringify(obj), {
      status: status || 200,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }

  function demoHint() {
    // 主脚本的通用报错提示会先弹出，这里晚几秒补上只读原因，保证访客最终看到的是解释
    setTimeout(() => {
      if (typeof window.toast === "function") window.toast(BLOCK_MSG);
    }, 2600);
  }

  const realFetch = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || "";
    const qpos = url.indexOf("?");
    const path = qpos === -1 ? url : url.slice(0, qpos);
    const query = new URLSearchParams(qpos === -1 ? "" : url.slice(qpos + 1));
    let method = "GET";
    if (input && typeof input === "object" && input.method) method = input.method;
    if (init && init.method) method = init.method;
    method = String(method).toUpperCase();

    if (path.indexOf("/api/") !== 0) {
      return realFetch ? realFetch(input, init)
        : Promise.reject(new TypeError("演示页禁止外部请求"));
    }
    if (method !== "GET" || BLOCK_SPECIAL.has(path)) {
      demoHint();
      return Promise.resolve(json({ detail: BLOCK_MSG }, 403));
    }
    const served = window.SubDeckDemoData && window.SubDeckDemoData.route(path, query);
    if (served === undefined) {
      return Promise.resolve(json({ detail: "演示页未提供该接口" }, 404));
    }
    return Promise.resolve(json(served));
  };

  // 个别写入操作主脚本没有 try/catch（如删除订阅），拦截产生的拒绝会以
  // “Uncaught (in promise)”形式污染控制台。这里只压掉演示拦截这一种消息，
  // 其余异常照常暴露，冒烟检查不受影响。
  window.addEventListener("unhandledrejection", (e) => {
    if (e.reason && e.reason.message === BLOCK_MSG) e.preventDefault();
  });

  /* ---------- 演示标识（DOM 在本脚本执行时已就绪） ---------- */

  const style = document.createElement("style");
  style.textContent = [
    "#demo-badge{display:inline-block;margin-left:8px;padding:2px 9px;border-radius:999px;",
    "font-size:11px;font-weight:600;letter-spacing:.06em;vertical-align:middle;",
    "color:var(--accent,#4f6ef7);",
    "background:color-mix(in srgb,var(--accent,#4f6ef7) 12%,transparent);",
    "border:1px solid color-mix(in srgb,var(--accent,#4f6ef7) 32%,transparent);}",
    "#sett-calendar,.settings-side a[href=\"#sett-calendar\"]{display:none!important}",
  ].join("");
  document.head.appendChild(style);

  const brand = document.querySelector(".topbar-brand");
  if (brand) {
    const badge = document.createElement("span");
    badge.id = "demo-badge";
    badge.textContent = "演示";
    badge.title = "只读演示页：数据为虚构示例，无法修改";
    brand.appendChild(badge);
  }

  // 关于弹窗里「未启用密码保护」的提示不适用于演示页，替换为演示说明
  const authNote = document.getElementById("auth-note");
  const DEMO_NOTE = "当前是只读演示页：以下数据均为虚构示例，修改操作已停用；"
    + "正式部署时所有数据保存在你自己的设备上。";
  if (authNote) {
    const obs = new MutationObserver(() => {
      if (authNote.textContent && authNote.textContent.indexOf(DEMO_NOTE) === -1) {
        authNote.textContent = DEMO_NOTE;
      }
    });
    obs.observe(authNote, { childList: true, characterData: true, subtree: true });
    setTimeout(() => obs.disconnect(), 8000);   // 启动完成即停，不长驻
  }

  // 进入提示（toast 为 app.js 内的全局函数，主脚本加载后即可用）
  window.addEventListener("load", () => {
    setTimeout(() => {
      if (typeof window.toast === "function") {
        window.toast("演示模式 · 数据为虚构示例，可随意浏览，修改操作已停用", 3600);
      }
    }, 500);
  });
})();
