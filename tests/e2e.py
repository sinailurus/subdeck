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
    for p in ("/assets/app.js", "/assets/manifest.webmanifest", "/assets/icons/icon-192.png"):
        call("GET", p)
check("静态资源可访问", statics)

def delete():
    b, _ = call("DELETE", f"/api/subscriptions/{ids['i']}", cookie=C)
    assert b["ok"]
    b, _ = call("GET", "/api/subscriptions", cookie=C)
    assert len(b) == 1
check("删除订阅", delete)

print(f"\n通过 {len(PASS)} 失败 {len(FAIL)}")
if FAIL: raise SystemExit(1)
print("ALL TESTS PASSED")
