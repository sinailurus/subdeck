# -*- coding: utf-8 -*-
"""v1.6.19 日历订阅链接重置——三断点弹窗排版 + 前端闭环验证。
跑法：先起服务（DATA_DIR=临时目录 AUTH_PASSWORD=test123 uvicorn app.main:app --port 8017），再 python3 scripts/verify_v1619.py
"""
import os, sys
from playwright.sync_api import sync_playwright

BASE = os.environ.get("SUBDECK_BASE", "http://127.0.0.1:8017")
PASS, FAIL = [], []

def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  OK " if cond else "  FAIL ") + name + ((" | " + extra) if extra and not cond else ""))

def open_calendar_modal(page, width, height):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(BASE + "/", wait_until="domcontentloaded")
    lp = page.locator("#login-password")
    if lp.count() and lp.is_visible():
        lp.fill("test123")
        page.locator("#login-form button[type=submit]").click()
        page.wait_for_timeout(800)
    page.locator('[data-nav="settings"]:visible').first.click()
    page.wait_for_timeout(300)
    page.locator('#sett-calendar').scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    page.locator("#btn-reset-ics").click()
    page.wait_for_timeout(300)

def modal_geometry(page):
    m = page.locator("#ics-reset-mask .modal")
    bb = m.bounding_box()
    ov = page.evaluate(
        "el => ({overflowX: el.scrollWidth > el.clientWidth, overflowY: el.scrollHeight > el.clientHeight + 2})",
        m.element_handle())
    return bb, ov

def assert_layout(name, page, width, height, expect_center):
    open_calendar_modal(page, width, height)
    bb, ov = modal_geometry(page)
    m = page.locator("#ics-reset-mask .modal")
    check(f"{name}: 弹窗可见", m.is_visible())
    if not m.is_visible() or bb is None:
        return
    check(f"{name}: 宽度={bb['width']:.0f}px", 300 <= bb["width"] <= min(400, width), f"got {bb['width']}")
    check(f"{name}: 无内部溢出", not ov["overflowX"] and not ov["overflowY"], str(ov))
    check(f"{name}: 不超视口", bb["x"] >= 0 and bb["x"] + bb["width"] <= width and bb["y"] >= 0, f"bb={bb}")
    if expect_center:
        cy = bb["y"] + bb["height"] / 2
        check(f"{name}: 桌面居中弹窗", abs(cy - height / 2) < height * 0.2, f"centerY={cy:.0f}/{height}")
    else:
        check(f"{name}: 手机贴底抽屉", bb["y"] + bb["height"] >= height - 4,
              f"bottom={bb['y']+bb['height']:.0f}/{height}")
    for bid in ["#btn-ics-reset-cancel", "#btn-ics-reset-go"]:
        btn = page.locator(bid)
        check(f"{name}: 按钮 {bid} 可见", btn.is_visible() and btn.bounding_box() is not None)
    m.screenshot(path=f"/tmp/sd-v1619-modal-{name}.png")

def assert_flow(page):
    """确认按钮闭环：调 API、输入框换新链接、弹窗关闭、toast 出现；取消路径不改动"""
    open_calendar_modal(page, 390, 844)
    old_url = page.locator("#ics-url").input_value()
    page.locator("#btn-ics-reset-go").click()
    page.wait_for_timeout(600)
    new_url = page.locator("#ics-url").input_value()
    check("闭环: 输入框换成新链接", new_url != old_url and "/api/calendar/" in new_url,
          f"old={old_url} new={new_url}")
    check("闭环: 弹窗已关闭", page.locator("#ics-reset-mask").is_hidden())
    toast = page.locator(".toast").first
    check("闭环: toast 提示出现", toast.count() and ("重新订阅" in (toast.text_content() or "")))
    page.locator("#btn-reset-ics").click(); page.wait_for_timeout(200)
    page.locator("#btn-ics-reset-cancel").click(); page.wait_for_timeout(200)
    check("取消路径: 弹窗关闭且链接不变", page.locator("#ics-reset-mask").is_hidden()
          and page.locator("#ics-url").input_value() == new_url)

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    assert_layout("手机390", page, 390, 844, expect_center=False)
    assert_layout("平板980", page, 980, 1200, expect_center=False)
    assert_layout("桌面1280", page, 1280, 800, expect_center=True)
    assert_flow(page)
    b.close()

print(f"\n通过 {len(PASS)}  失败 {len(FAIL)}")
sys.exit(1 if FAIL else 0)
