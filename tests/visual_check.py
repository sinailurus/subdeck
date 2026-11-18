# -*- coding: utf-8 -*-
"""v1.2.0 外观系统视觉自查：A/B/C 三档皮肤 × 深浅主题共 6 状态 + 移动端抽查。

运行前提：本地服务已起（默认 8018，密码 test123）。
输出：/tmp/subdeck-shots/*.png
"""
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("SUBDECK_BASE", "http://127.0.0.1:8018")
OUT = "/tmp/subdeck-shots"
os.makedirs(OUT, exist_ok=True)

SKINS = [("solid", "A-实色"), ("glass", "B-点缀玻璃"), ("glassplus", "C-重度玻璃")]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(BASE)
    page.fill("#login-password", "test123")
    page.click("#login-form button[type=submit]")
    page.wait_for_selector("#app-view:not(.hidden)", timeout=8000)

    for skin, label in SKINS:
        for theme in ("light", "dark"):
            # 设置皮肤（后端持久化）
            page.evaluate(
                "async (skin) => { await fetch('/api/settings', {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({skin}), credentials:'same-origin'}); }",
                skin,
            )
            page.evaluate(f"document.documentElement.dataset.theme = '{theme}'")
            page.wait_for_timeout(400)
            page.screenshot(path=f"{OUT}/{skin}-{theme}-概览.png", full_page=False)
            # 切到设置页截外观面板
            page.evaluate("document.querySelector('[data-nav=settings]').click()")
            page.wait_for_timeout(300)
            page.screenshot(path=f"{OUT}/{skin}-{theme}-设置.png", full_page=False)
            page.evaluate("document.querySelector('[data-nav=dashboard]').click()")
            print(f"  截图 {label} × {theme}")

    # 移动端抽查：C 档深色 390 宽
    mpage = browser.new_page(viewport={"width": 390, "height": 844})
    mpage.goto(BASE)
    mpage.fill("#login-password", "test123")
    mpage.click("#login-form button[type=submit]")
    mpage.wait_for_selector("#app-view:not(.hidden)", timeout=8000)
    mpage.evaluate(
        "async () => { await fetch('/api/settings', {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({skin:'glassplus'}), credentials:'same-origin'}); }"
    )
    mpage.evaluate("document.documentElement.dataset.theme = 'dark'")
    mpage.wait_for_timeout(400)
    mpage.screenshot(path=f"{OUT}/mobile-glassplus-dark-概览.png", full_page=False)
    print("  截图 移动端 C 档深色")

    browser.close()
print(f"完成 → {OUT}")
