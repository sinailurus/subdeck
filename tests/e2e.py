# -*- coding: utf-8 -*-
"""SubDeck 端到端验证。"""
import json, os, struct, urllib.request, urllib.error, zlib

BASE = os.environ.get("SUBDECK_BASE", "http://127.0.0.1:8017")
PASS, FAIL = [], []

def call(method, path, data=None, cookie=None, raw=None, headers=None, expect=200):
    h = dict(headers or {})
    if cookie: h["Cookie"] = cookie
    body = raw
    if data is not None:
        body = json.dumps(data).encode(); h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, body, h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            code, ct, payload, sc = r.status, r.headers.get("Content-Type",""), r.read(), r.headers.get("Set-Cookie","")
    except urllib.error.HTTPError as e:
        code, ct, payload, sc = e.code, "", e.read(), ""
    assert code == expect, f"{method} {path} -> {code} (expect {expect}): {payload[:200]}"
    return (json.loads(payload) if "json" in ct else payload), sc

def check(name, fn):
    try:
        fn(); PASS.append(name); print(f"  OK {name}")
    except Exception as e:
        FAIL.append(name); print(f"  FAIL {name}: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()

def tiny_png():
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 13, 1, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b"")

holder, C, ids = {}, None, {}

check("未登录401", lambda: call("GET", "/api/subscriptions", expect=401))
check("错密码401", lambda: call("POST", "/api/login", {"password": "wrong"}, expect=401))

def login():
    body, sc = call("POST", "/api/login", {"password": "test123"})
    assert body.get("ok"), body
    globals()["C"] = sc.split(";")[0]
check("登录成功", login)

def cleanup():
    b, _ = call("GET", "/api/subscriptions", cookie=C)
    for row in b:
        call("DELETE", f"/api/subscriptions/{row['id']}", cookie=C)
check("清理历史数据", cleanup)

def create():
    b, _ = call("POST", "/api/subscriptions", {
        "name": "Netflix", "amount": 9.99, "currency": "USD", "cycle": "monthly",
        "next_billing_date": "2026-01-05", "payment_method": "auto",
        "category": "video", "notes": "基础套餐", "color": "#ef5350"}, cookie=C)
    ids["n"] = b["id"]; assert b["days_until"] >= 0, b
check("创建+账单日自动滚动", create)

def create2():
    b, _ = call("POST", "/api/subscriptions", {
        "name": "iCloud+", "amount": 21, "currency": "CNY", "cycle": "monthly",
        "next_billing_date": "2026-12-01", "payment_method": "manual", "category": "cloud"}, cookie=C)
    ids["i"] = b["id"]
check("创建第二个", create2)

def bad_input():
    call("POST", "/api/subscriptions", {"name": "", "amount": 1}, cookie=C, expect=400)
    call("POST", "/api/subscriptions", {"name": "X", "amount": -5, "currency": "CNY",
        "cycle": "monthly", "next_billing_date": "2026-12-01"}, cookie=C, expect=400)
check("非法输入422", bad_input)

def update():
    b, _ = call("PUT", f"/api/subscriptions/{ids['i']}", {
        "name": "iCloud+", "amount": 25, "currency": "CNY", "cycle": "yearly",
        "next_billing_date": "2026-12-01", "payment_method": "auto",
        "category": "cloud", "notes": "升级2TB"}, cookie=C)
    assert b["amount"] == 25 and b["cycle"] == "yearly", b
check("更新订阅", update)

def upload():
    png = tiny_png(); bd = "----bd"
    part = (f"--{bd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"logo.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png + b"\r\n" + f"--{bd}--\r\n".encode()
    b, _ = call("POST", f"/api/subscriptions/{ids['i']}/logo", raw=part,
                headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, cookie=C)
    assert b.get("logo_url"), b
    holder["logo"] = b["logo_url"]
check("上传PNG logo", upload)

def getlogo():
    body, _ = call("GET", holder["logo"], cookie=C)
    assert body[:4] == b"\x89PNG"
check("Cookie读取logo", getlogo)

def reject_svg():
    # 服务端按扩展名与MIME拒绝SVG，防XSS
    bd = "----bd"
    head = f"--{bd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"evil.svg\"\r\n"
    head += "Content-Type: image/svg+xml\r\n\r\n"
    part = head.encode() + b"plain-text-not-image" + f"\r\n--{bd}--\r\n".encode()
    call("POST", f"/api/subscriptions/{ids[chr(105)]}/logo", raw=part,
         headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, cookie=C, expect=400)

def rates():
    b, _ = call("POST", "/api/rates/refresh", cookie=C)
    if b.get("ok"): assert b["rates"].get("USD"), b
    else: print(f"    (沙箱访问汇率API失败: {b.get('error')} -- 不算失败)")
check("汇率刷新", rates)

def stats():
    b, _ = call("GET", "/api/stats", cookie=C)
    for k in ("base_currency","monthly_total","yearly_total","active_count","pending","by_category","missing_rate_currencies","pending_count"):
        assert k in b, k
    assert b["active_count"] == 2, b
check("统计字段完整", stats)

def listapi():
    b, _ = call("GET", "/api/subscriptions", cookie=C)
    assert isinstance(b, list) and len(b) == 2, b
    s = b[0]
    for k in ("amount_converted","monthly_cost","days_until","logo_url"):
        assert k in s, k
check("列表含折算与到期标签", listapi)

def ics():
    b, _ = call("GET", "/api/ics-url", cookie=C)
    assert b["url"].startswith("/api/calendar.ics?token="), b
    ics, _ = call("GET", b["url"])
    ics = ics.decode()
    assert "BEGIN:VCALENDAR" in ics and "Netflix" in ics
check("iCal带token订阅", ics)

def statics():
    body, _ = call("GET", "/")
    assert b"SubDeck" in body
    for p in ("/assets/app.js", "/manifest.webmanifest", "/assets/icons/icon-192.png"):
        call("GET", p)
check("静态资源可访问", statics)

# ---- v1.2.0 外观与品牌 ----
def settings_ext():
    b, _ = call("GET", "/api/settings", cookie=C)
    for k in ("app_name", "theme_color", "skin", "bg_image", "bg_mask", "chart_style", "brand_icon"):
        assert k in b, k
    assert b["skin"] in ("solid", "glass", "glassplus"), b
check("settings含外观键", settings_ext)

def put_appearance():
    b, _ = call("PUT", "/api/settings", {"skin": "glassplus", "theme_color": "#22c55e",
        "chart_style": "donut", "bg_mask": 50, "app_name": "我的订阅"}, cookie=C)
    assert b["skin"] == "glassplus" and b["theme_color"] == "#22c55e", b
    assert b["chart_style"] == "donut" and b["app_name"] == "我的订阅" and b["bg_mask"] == 50, b
    # 非法值全部 400
    call("PUT", "/api/settings", {"skin": "neon"}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"theme_color": "red"}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"chart_style": "3d"}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"app_name": "012345678901234"}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"bg_mask": 99}, cookie=C, expect=400)
    b, _ = call("PUT", "/api/settings", {"skin": "glass", "chart_style": "bars",
        "theme_color": "", "bg_mask": 35, "app_name": "SubDeck"}, cookie=C)
    assert b["skin"] == "glass", b
check("外观设置读写+校验", put_appearance)

def brand_upload():
    png = tiny_png(); bd = "----bd"
    part = (f"--{bd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"bg.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png + b"\r\n" + f"--{bd}--\r\n".encode()
    b, _ = call("POST", "/api/brand/background", raw=part,
                headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, cookie=C)
    assert b["bg_image"].startswith("bg_"), b
    body, _ = call("GET", "/api/brand/background", cookie=C)
    assert body[:4] == b"\x89PNG"
    b, _ = call("POST", "/api/brand/icon", raw=part,
                headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, cookie=C)
    assert b["brand_icon"].startswith("icon_"), b
    body, _ = call("GET", "/api/brand/icon", cookie=C)
    assert body[:4] == b"\x89PNG"
    # 非图片拒绝（防 XSS：与 logo 同策略）
    bd2 = "----bd2"
    evil = (f"--{bd2}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"x.svg\"\r\n"
            f"Content-Type: image/svg+xml\r\n\r\n").encode() + b"nope" + f"\r\n--{bd2}--\r\n".encode()
    call("POST", "/api/brand/background", raw=evil,
         headers={"Content-Type": f"multipart/form-data; boundary={bd2}"}, cookie=C, expect=400)
    call("POST", "/api/brand/icon", raw=evil,
         headers={"Content-Type": f"multipart/form-data; boundary={bd2}"}, cookie=C, expect=400)
    # 未登录 401
    call("GET", "/api/brand/background", expect=401)
    # 清理与回落
    call("DELETE", "/api/brand/background", cookie=C)
    call("DELETE", "/api/brand/icon", cookie=C)
    call("GET", "/api/brand/background", cookie=C, expect=404)
    b, _ = call("GET", "/api/settings", cookie=C)
    assert not b["bg_image"] and not b["brand_icon"], b
check("品牌背景图/图标上传清理", brand_upload)

def manifest_dyn():
    # 注意：call() 第二个返回值是 Set-Cookie 头，不是 Content-Type；JSON 校验用 isinstance
    body, _ = call("GET", "/manifest.webmanifest")
    assert isinstance(body, dict) and body["name"] == "SubDeck" and body["icons"], body
    call("PUT", "/api/settings", {"app_name": "订阅管家"}, cookie=C)
    body, _ = call("GET", "/manifest.webmanifest")
    assert body["name"] == "订阅管家", body
    call("PUT", "/api/settings", {"app_name": "SubDeck"}, cookie=C)
check("动态manifest随名称/图标联动", manifest_dyn)

def delete():
    b, _ = call("DELETE", f"/api/subscriptions/{ids['i']}", cookie=C)
    assert b["ok"]
    b, _ = call("GET", "/api/subscriptions", cookie=C)
    assert len(b) == 1
check("删除订阅", delete)

print(f"\n通过 {len(PASS)} 失败 {len(FAIL)}")
if FAIL: raise SystemExit(1)
print("ALL TESTS PASSED")
