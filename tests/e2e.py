# -*- coding: utf-8 -*-
"""SubDeck 端到端验证。"""
import datetime, json, os, struct, urllib.request, urllib.error, zlib

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
        code, ct, payload, sc = e.code, e.headers.get("Content-Type",""), e.read(), ""
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
    holder["ics_url"] = b["url"]
    ics, _ = call("GET", b["url"])
    ics = ics.decode()
    assert "BEGIN:VCALENDAR" in ics and "Netflix" in ics
check("iCal带token订阅", ics)

def billing_cal():
    b, _ = call("GET", "/api/billing-calendar?months=12", cookie=C)
    es = b["entries"]
    assert b["months"] == 12 and es, b
    dates = [e["date"] for e in es]
    assert dates == sorted(dates), "entries 应按日期升序"
    today = datetime.date.today().isoformat()
    assert all(d >= today for d in dates), "应只包含今天及以后"
    assert len(dates) >= 10, f"月付订阅 12 个月应推算 ≥10 次，实际 {len(dates)}"
    # 越界参数收敛
    b, _ = call("GET", "/api/billing-calendar?months=999", cookie=C)
    assert b["months"] == 24
    b, _ = call("GET", "/api/billing-calendar", expect=401)
check("扣费日历推算", billing_cal)

def notify_settings():
    # 合法配置读写
    b, _ = call("PUT", "/api/settings", {"notify_enabled": True, "notify_emails": "a@qq.com，b@163.com",
                "notify_lead_days": 5, "notify_hour": 9, "smtp_host": "smtp.qq.com",
                "smtp_port": 465, "smtp_ssl": True, "smtp_user": "a@qq.com", "smtp_pass": "authcode"}, cookie=C)
    assert b["notify_enabled"] is True and b["notify_lead_days"] == 5 and b["notify_hour"] == 9
    assert b["notify_emails"] == "a@qq.com,b@163.com", "中文分号应规范化为逗号"
    assert b["smtp_port"] == 465 and b["smtp_user"] == "a@qq.com"
    # 越界拒绝
    for payload, code in [({"notify_lead_days": 0}, 400), ({"notify_lead_days": 31}, 400),
                          ({"notify_hour": 24}, 400), ({"smtp_port": 0}, 400),
                          ({"notify_emails": "no-at-sign"}, 400)]:
        call("PUT", "/api/settings", payload, cookie=C, expect=code)
    # 测试邮件：缺配置 400；假 SMTP 地址 502（不真发）
    call("POST", "/api/notify/test", {"notify_emails": "a@qq.com"}, cookie=C, expect=400)
    call("POST", "/api/notify/test", {"notify_emails": "a@qq.com", "smtp_host": "127.0.0.1",
         "smtp_port": 59999, "smtp_ssl": False}, cookie=C, expect=502)
    # 关闭开关还原
    call("PUT", "/api/settings", {"notify_enabled": False}, cookie=C)
check("邮箱提醒设置+测试端点", notify_settings)

def ics_calname():
    call("PUT", "/api/settings", {"app_name": "订阅管家"}, cookie=C)
    ics, _ = call("GET", holder["ics_url"])
    ics = ics.decode()
    assert "X-WR-CALNAME:订阅管家 订阅账单" in ics, "iCal 日历名应跟随应用名称"
    call("PUT", "/api/settings", {"app_name": "SubDeck"}, cookie=C)
check("iCal日历名跟随应用名", ics_calname)

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

def preset_bg():
    b, _ = call("PUT", "/api/settings", {"bg_image": "preset:aurora"}, cookie=C)
    assert b["bg_image"] == "preset:aurora", b
    b, _ = call("PUT", "/api/settings", {"bg_image": "preset:candy"}, cookie=C)
    assert b["bg_image"] == "preset:candy", b
    # 未知预设 400
    call("PUT", "/api/settings", {"bg_image": "preset:nope"}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"bg_image": "preset:"}, cookie=C, expect=400)
    # 预设静态图随镜像可访问
    call("GET", "/assets/bg/aurora.jpg")
    call("GET", "/assets/bg/candy.jpg")
    call("GET", "/assets/bg/sunset.jpg")
    # 预设与上传互斥：再上传应覆盖 preset 值
    png = tiny_png(); bd = "----bd3"
    part = (f"--{bd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"bg.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png + b"\r\n" + f"--{bd}--\r\n".encode()
    b, _ = call("POST", "/api/brand/background", raw=part,
                headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, cookie=C)
    assert b["bg_image"].startswith("bg_"), b
    call("DELETE", "/api/brand/background", cookie=C)
    b, _ = call("GET", "/api/settings", cookie=C)
    assert not b["bg_image"], b
check("预设背景切换+校验+互斥", preset_bg)

# ---- v1.5.0 登录页自定义 + 分类管理 ----
def login_page_custom():
    # 公开端点：未登录可读，且只含装饰字段、不含任何敏感数据
    body, _ = call("GET", "/api/brand/login-page")
    for k in ("app_name", "login_title", "login_welcome", "login_bg", "login_bg_mask", "theme_color", "icon_ver"):
        assert k in body, k
    for bad in ("notify_emails", "smtp_pass", "subscriptions", "smtp_host"):
        assert bad not in body, bad
    # 配置写入与校验
    b, _ = call("PUT", "/api/settings", {"login_title": "家庭订阅中心", "login_welcome": "统一管理全家订阅，请登录继续",
                "login_bg": "preset:sunset", "login_bg_mask": 55}, cookie=C)
    assert b["login_title"] == "家庭订阅中心" and b["login_bg"] == "preset:sunset" and b["login_bg_mask"] == 55, b
    call("PUT", "/api/settings", {"login_title": "x" * 25}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"login_welcome": "x" * 41}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"login_bg_mask": 81}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"login_bg": "preset:nope"}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"login_bg": "../../etc/passwd"}, cookie=C, expect=400)
    body, _ = call("GET", "/api/brand/login-page")
    assert body["login_title"] == "家庭订阅中心" and body["login_bg"] == "preset:sunset", body
    # 登录页图标：上传 → 公开读 → 删除回落
    call("GET", "/api/brand/login-icon", expect=404)   # 此前用例已清理 brand_icon，无图标可回落
    png = tiny_png(); bd = "----bdL"
    part = (f"--{bd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"icon.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + png + b"\r\n" + f"--{bd}--\r\n".encode()
    call("POST", "/api/brand/login-icon", raw=part,
         headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, cookie=C)
    body, _ = call("GET", "/api/brand/login-icon")
    assert body[:4] == b"\x89PNG"
    body, _ = call("GET", "/api/brand/login-page")
    assert body["icon_ver"].startswith("loginicon_"), body
    # 自定义登录页背景：上传 → 公开读 → preset 覆盖后 404（走静态资源）→ 删除回落渐变
    bd2 = "----bdL2"
    part2 = (f"--{bd2}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"bg.png\"\r\n"
             f"Content-Type: image/png\r\n\r\n").encode() + png + b"\r\n" + f"--{bd2}--\r\n".encode()
    b, _ = call("POST", "/api/brand/login-background", raw=part2,
                headers={"Content-Type": f"multipart/form-data; boundary={bd2}"}, cookie=C)
    assert b["login_bg"].startswith("loginbg_"), b
    call("GET", "/api/brand/login-background")
    call("PUT", "/api/settings", {"login_bg": "preset:aurora"}, cookie=C)
    call("GET", "/api/brand/login-background", expect=404)
    # 未登录上传 401
    call("POST", "/api/brand/login-icon", raw=part,
         headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, expect=401)
    call("DELETE", "/api/brand/login-background", cookie=C)
    call("DELETE", "/api/brand/login-icon", cookie=C)
    b, _ = call("GET", "/api/settings", cookie=C)
    assert not b["login_icon"] and b["login_bg"] == "", b
    call("PUT", "/api/settings", {"login_title": "", "login_welcome": "", "login_bg_mask": 45}, cookie=C)
check("登录页自定义+公开端点", login_page_custom)

def custom_categories():
    b, _ = call("PUT", "/api/settings", {"custom_categories": ["健身", "AI 工具"]}, cookie=C)
    assert b["custom_categories"] == ["健身", "AI 工具"], b
    # trim / 去空 / 去重
    b, _ = call("PUT", "/api/settings", {"custom_categories": [" 健身 ", "", "AI 工具"]}, cookie=C)
    assert b["custom_categories"] == ["健身", "AI 工具"], b
    # 越界拒绝
    call("PUT", "/api/settings", {"custom_categories": ["x" * 13]}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"custom_categories": [str(i) for i in range(21)]}, cookie=C, expect=400)
    call("PUT", "/api/settings", {"custom_categories": "bad"}, cookie=C, expect=400)
    # 删除自定义分类不影响已有订阅
    call("PUT", "/api/settings", {"custom_categories": []}, cookie=C)
    b, _ = call("GET", "/api/subscriptions", cookie=C)
    assert any(s["category"] == "video" for s in b), b
check("分类管理增删校验", custom_categories)

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

# ---- v1.5.0 安全加固 ----
def security_headers():
    req = urllib.request.Request(BASE + "/api/health")
    with urllib.request.urlopen(req, timeout=15) as r:
        h = {k.lower(): v for k, v in r.headers.items()}
    for k, want in (("x-content-type-options", "nosniff"), ("x-frame-options", "DENY"),
                    ("referrer-policy", "strict-origin-when-cross-origin")):
        assert h.get(k) == want, (k, h.get(k))
    csp = h.get("content-security-policy", "")
    for frag in ("default-src 'self'", "script-src 'self'", "frame-ancestors 'none'"):
        assert frag in csp, csp
check("安全响应头齐全", security_headers)

def login_throttle():
    """连续失败 5 次 → 429 锁定；锁定期内正确密码也 429；已登录会话不受影响。
    放在最后执行：会锁死 127.0.0.1 的登录 15 分钟（进程内计数）。"""
    for i in range(4):
        call("POST", "/api/login", {"password": "wrong"}, expect=401)
    body, _ = call("POST", "/api/login", {"password": "wrong"}, expect=429)
    assert "锁定" in body.get("detail", "") or "分钟" in body.get("detail", ""), body
    # 锁定期内：正确密码也被拒（429），但已持有的会话 cookie 照常可用
    call("POST", "/api/login", {"password": os.environ.get("SUBDECK_PW", "test123")}, expect=429)
    b, _ = call("GET", "/api/subscriptions", cookie=C)
    assert isinstance(b, list), b
check("登录限速防暴力破解", login_throttle)

print(f"\n通过 {len(PASS)} 失败 {len(FAIL)}")
if FAIL: raise SystemExit(1)
print("ALL TESTS PASSED")
