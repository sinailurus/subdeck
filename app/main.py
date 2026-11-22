# -*- coding: utf-8 -*-
"""SubDeck 自部署订阅管理（FastAPI 后端入口）。"""
import datetime
import hmac
import io
import json
import os
import re
import secrets
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import zipfile

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import auth, billing, rates
from .currencies import CURRENCIES, CYCLES, PAYMENT_METHODS
from .db import BG_DIR, LOGO_DIR, db, get_setting, init_db, set_setting
from .ical import generate_ics
from . import mailer

APP_VERSION = "1.6.18"
if getattr(sys, "frozen", False):
    # PyInstaller 打包（Windows exe，v1.6.0）：静态资源解包在 sys._MEIPASS/static
    STATIC_DIR = os.path.join(sys._MEIPASS, "static")
else:
    STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

LOGO_RE = re.compile(r"^sub_\d+_\d+\.(png|jpg|webp)$")
BRAND_RE = re.compile(r"^(bg|icon|loginicon|loginbg)_\d+\.(png|jpg|webp)$")
LOGO_MAGIC = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    # webp: RIFF....WEBP
}
LOGO_MAX_BYTES = 2 * 1024 * 1024  # 2MB
ALLOWED_CYCLES = set(CYCLES.keys())
ALLOWED_PAY = set(PAYMENT_METHODS.keys())
# 自绘头像可用的颜色（与前端保持一致）
PALETTE = ["#ef5350", "#ab63f6", "#5c9dff", "#26a69a", "#66bb6a",
           "#ffa726", "#ff7043", "#ec407a", "#8d6e63", "#78909c"]

app = FastAPI(title="SubDeck", version=APP_VERSION, docs_url=None, redoc_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """基础安全响应头：防 MIME 嗅探 / 点击劫持 / 引用泄露；CSP 收紧到同源。

    说明：
    - img-src 含 data:（PWA/占位图）；style-src 需 unsafe-inline（JS 动态样式与内联样式表）；
    - 前端无内联 script，script-src 'self' 即可；API 全同源，connect-src 'self'；
    - ICS 文本 / manifest / 静态资源同样受保护。
    """
    resp = await call_next(request)
    h = resp.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    h.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
        "form-action 'self'",
    )
    return resp


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ---------------------------------------------------------------- 鉴权工具

def _logged_in(request: Request) -> bool:
    return auth.auth_enabled() and auth.verify_token(request.cookies.get(auth.COOKIE_NAME))


def require_auth(request: Request) -> None:
    if auth.auth_enabled() and not auth.verify_token(request.cookies.get(auth.COOKIE_NAME)):
        raise HTTPException(status_code=401, detail="unauthorized")


def _session_cookie(response: Response) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_token(),
        max_age=auth.SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
    )


# ---------------------------------------------------------------- 基础接口

@app.get("/api/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/api/me")
def me(request: Request):
    return {
        "version": APP_VERSION,
        "auth_required": auth.auth_enabled(),
        "logged_in": _logged_in(request) or not auth.auth_enabled(),
    }


# ---------------------------------------------------------------- 登录限速（防暴力破解）
# 进程内计数：连续失败 ≥5 次锁定 15 分钟；成功登录清零。重启即重置（单用户自部署够用）。
_LOGIN_FAILS: dict[str, tuple[int, float]] = {}   # ip -> (连续失败次数, 锁定截止时间戳)
LOGIN_MAX_FAILS = 5
LOGIN_LOCK_SECONDS = 900


def _client_ip(request: Request) -> str:
    """真实客户端 IP：CF 隧道场景取 CF-Connecting-IP（由 CDN 覆盖写入，不可伪造）；
    直连场景取 socket 对端地址。刻意不信任可任意伪造的 X-Forwarded-For。"""
    return request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else "unknown")


@app.post("/api/login")
def login(request: Request, body: dict):
    if not auth.auth_enabled():
        return {"ok": True, "msg": "未启用密码保护"}
    ip = _client_ip(request)
    now = time.time()
    fails, lock_until = _LOGIN_FAILS.get(ip, (0, 0.0))
    if now < lock_until:
        remain = int((lock_until - now) // 60) + 1
        raise HTTPException(status_code=429, detail=f"密码错误次数过多，请约 {remain} 分钟后再试")
    if not isinstance(body.get("password"), str) or not auth.check_password(body["password"]):
        fails += 1
        if fails >= LOGIN_MAX_FAILS:
            _LOGIN_FAILS[ip] = (0, now + LOGIN_LOCK_SECONDS)
            raise HTTPException(status_code=429, detail="密码错误次数过多，已锁定 15 分钟")
        _LOGIN_FAILS[ip] = (fails, 0.0)
        raise HTTPException(status_code=401, detail="密码错误")
    _LOGIN_FAILS.pop(ip, None)
    resp = JSONResponse({"ok": True})
    _session_cookie(resp)
    return resp


@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE_NAME)
    return resp


# ---------------------------------------------------------------- 设置与汇率

def _settings_payload(conn: sqlite3.Connection) -> dict:
    return {
        "base_currency": get_setting(conn, "base_currency", "CNY"),
        "remind_days": int(get_setting(conn, "remind_days", "7") or 7),
        # ---- v1.2.0 外观与品牌 ----
        "app_name": get_setting(conn, "app_name", "SubDeck") or "SubDeck",
        "theme_color": get_setting(conn, "theme_color", ""),
        "skin": get_setting(conn, "skin", "glass") or "glass",
        "bg_image": get_setting(conn, "bg_image", ""),
        "bg_mask": int(get_setting(conn, "bg_mask", "35") or 35),
        "chart_style": get_setting(conn, "chart_style", "bars") or "bars",
        "brand_icon": get_setting(conn, "brand_icon", ""),
        # ---- v1.5.0 登录页自定义 + 分类管理 ----
        "login_title": get_setting(conn, "login_title", ""),
        "login_welcome": get_setting(conn, "login_welcome", ""),
        "login_bg": get_setting(conn, "login_bg", ""),
        "login_bg_mask": int(get_setting(conn, "login_bg_mask", "45") or 45),
        "login_icon": get_setting(conn, "login_icon", ""),
        "custom_categories": _load_custom_categories(conn),
        # ---- v1.4.0 邮箱提醒 ----
        "notify_enabled": get_setting(conn, "notify_enabled", "0") == "1",
        "notify_emails": get_setting(conn, "notify_emails", ""),
        "notify_lead_days": int(get_setting(conn, "notify_lead_days", "3") or 3),
        "notify_hour": int(get_setting(conn, "notify_hour", "8") or 8),
        # v1.6.7 外币汇总条：汇率快照日期（自动拉取时间；手动汇率不更新此值）
        "rates_updated_at": get_setting(conn, "rates_updated_at", ""),
        "smtp_host": get_setting(conn, "smtp_host", ""),
        "smtp_port": int(get_setting(conn, "smtp_port", "465") or 465),
        "smtp_ssl": get_setting(conn, "smtp_ssl", "1") == "1",
        "smtp_user": get_setting(conn, "smtp_user", ""),
        "smtp_pass": get_setting(conn, "smtp_pass", ""),
    }


ALLOWED_SKINS = {"solid", "glass", "glassplus"}
ALLOWED_CHARTS = {"bars", "donut", "pie"}
# 登录页背景："" 主题渐变（默认）/ "none" 无背景 / preset:xxx 内置 / 上传文件名
ALLOWED_LOGIN_BG_EMPTY = {"", "none"}
LOGIN_ICON_MAX_BYTES = 2 * 1024 * 1024   # 登录页图标 2MB
CUSTOM_CATEGORIES_MAX = 20               # 自定义分类上限
CUSTOM_CATEGORY_MAX_LEN = 12             # 单个分类字数上限


def _load_custom_categories(conn: sqlite3.Connection) -> list[str]:
    """custom_categories 存 JSON 数组；坏数据静默回落空列表。"""
    raw = get_setting(conn, "custom_categories", "[]")
    try:
        data = json.loads(raw or "[]")
        return [str(x) for x in data if isinstance(x, str)][:CUSTOM_CATEGORIES_MAX]
    except Exception:
        return []

COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
# 内置预设背景：与 static/bg/*.jpg 一一对应（新增预设 = 加图 + 白名单加一行）
ALLOWED_BG_PRESETS = {"aurora", "candy", "sunset"}


def _valid_bg_image(value: str) -> bool:
    """bg_image 合法值：空 / 上传文件名（仅上传接口写入）/ preset:xxx 预设。"""
    if not value:
        return True
    return value.startswith("preset:") and value.split(":", 1)[1] in ALLOWED_BG_PRESETS


@app.get("/api/currencies")
def currencies_list():
    """币种清单（公开无害：ISO 代码列表）。"""
    return {"currencies": CURRENCIES}


@app.get("/api/settings")
def get_settings(request: Request):
    require_auth(request)
    with db() as conn:
        return _settings_payload(conn)


@app.put("/api/settings")
@app.post("/api/settings")   # v1.6.4：兼容 POST 动词（此前 405，部分客户端脚本按 POST 习惯调用）
def put_settings(request: Request, body: dict):
    require_auth(request)
    with db() as conn:
        if "base_currency" in body:
            if body["base_currency"] not in CURRENCIES:
                raise HTTPException(status_code=400, detail="不支持的币种")
            old_base = get_setting(conn, "base_currency", "CNY")
            set_setting(conn, "base_currency", body["base_currency"])
            if body["base_currency"] != old_base:
                # 基准币变了：手动汇率（相对旧基准）全部失效，清空防糊涂账
                set_setting(conn, "custom_rates", "{}")
                # 修存量问题：此前改基准币后 rates 缓存仍按旧基准折算，统计全错。
                # 现在变更时立即按新基准重拉；拉失败则清空缓存（前端会显示汇率未同步）。
                ok, info, _ = rates.fetch_and_cache(conn, body["base_currency"])
                if not ok:
                    set_setting(conn, "rates", "{}")
                    set_setting(conn, "rates_updated_at", "")
        if "remind_days" in body:
            days = int(body["remind_days"])
            if not 0 <= days <= 90:
                raise HTTPException(status_code=400, detail="提醒天数需在 0-90 之间")
            set_setting(conn, "remind_days", str(days))
        # ---- v1.2.0 外观与品牌 ----
        if "app_name" in body:
            name = str(body["app_name"] or "").strip()
            if not name or len(name) > 12:
                raise HTTPException(status_code=400, detail="应用名称需为 1-12 个字")
            set_setting(conn, "app_name", name)
        if "theme_color" in body:
            color = str(body["theme_color"] or "").strip()
            if color and not COLOR_RE.match(color):
                raise HTTPException(status_code=400, detail="主题色格式应为 #RRGGBB")
            set_setting(conn, "theme_color", color)
        if "skin" in body:
            if body["skin"] not in ALLOWED_SKINS:
                raise HTTPException(status_code=400, detail="不支持的界面风格")
            set_setting(conn, "skin", body["skin"])
        if "bg_mask" in body:
            mask = int(body["bg_mask"])
            if not 0 <= mask <= 85:
                raise HTTPException(status_code=400, detail="遮罩浓度需在 0-85 之间")
            set_setting(conn, "bg_mask", str(mask))
        if "bg_image" in body:
            v = str(body["bg_image"] or "")
            if not _valid_bg_image(v):
                raise HTTPException(status_code=400, detail="未知预设背景")
            set_setting(conn, "bg_image", v)
        if "chart_style" in body:
            if body["chart_style"] not in ALLOWED_CHARTS:
                raise HTTPException(status_code=400, detail="不支持的图表类型")
            set_setting(conn, "chart_style", body["chart_style"])
        # ---- v1.5.0 登录页自定义 ----
        if "login_title" in body:
            v = str(body["login_title"] or "").strip()
            if len(v) > 24:
                raise HTTPException(status_code=400, detail="登录页标题不能超过 24 个字")
            set_setting(conn, "login_title", v)
        if "login_welcome" in body:
            v = str(body["login_welcome"] or "").strip()
            if len(v) > 40:
                raise HTTPException(status_code=400, detail="欢迎语不能超过 40 个字")
            set_setting(conn, "login_welcome", v)
        if "login_bg" in body:
            v = str(body["login_bg"] or "")
            is_preset = v.startswith("preset:") and v.split(":", 1)[1] in ALLOWED_BG_PRESETS
            if v not in ALLOWED_LOGIN_BG_EMPTY and not is_preset and not BRAND_RE.match(v):
                raise HTTPException(status_code=400, detail="非法的登录页背景值")
            set_setting(conn, "login_bg", v)
        if "login_bg_mask" in body:
            mask = int(body["login_bg_mask"])
            if not 0 <= mask <= 80:
                raise HTTPException(status_code=400, detail="遮罩浓度需在 0-80 之间")
            set_setting(conn, "login_bg_mask", str(mask))
        # ---- v1.5.0 分类管理 ----
        if "custom_categories" in body:
            raw = body["custom_categories"]
            if not isinstance(raw, list):
                raise HTTPException(status_code=400, detail="分类列表格式错误")
            cats, seen = [], set()
            for item in raw:
                name = str(item or "").strip()
                if not name:
                    continue
                if len(name) > CUSTOM_CATEGORY_MAX_LEN:
                    raise HTTPException(status_code=400, detail=f"分类「{name}」超过 {CUSTOM_CATEGORY_MAX_LEN} 个字")
                if name in seen:
                    continue
                seen.add(name)
                cats.append(name)
            if len(cats) > CUSTOM_CATEGORIES_MAX:
                raise HTTPException(status_code=400, detail=f"自定义分类最多 {CUSTOM_CATEGORIES_MAX} 个")
            set_setting(conn, "custom_categories", json.dumps(cats, ensure_ascii=False))
        # ---- v1.4.0 邮箱提醒 ----
        if "notify_enabled" in body:
            set_setting(conn, "notify_enabled", "1" if body["notify_enabled"] else "0")
        if "notify_emails" in body:
            emails = ",".join(x.strip() for x in
                              str(body["notify_emails"]).replace("；", ",").replace("，", ",")
                              .replace(";", ",").replace(" ", ",").split(",")
                              if x.strip())
            if len(emails) > 400 or (emails and any(("@" not in e or len(e) > 100) for e in emails.split(","))):
                raise HTTPException(status_code=400, detail="收件邮箱格式有误")
            set_setting(conn, "notify_emails", emails)
        if "notify_lead_days" in body:
            n = int(body["notify_lead_days"])
            if not 1 <= n <= 30:
                raise HTTPException(status_code=400, detail="提前天数需在 1-30 之间")
            set_setting(conn, "notify_lead_days", str(n))
        if "notify_hour" in body:
            n = int(body["notify_hour"])
            if not 0 <= n <= 23:
                raise HTTPException(status_code=400, detail="发送时间需在 0-23 点之间")
            set_setting(conn, "notify_hour", str(n))
        if "smtp_host" in body:
            set_setting(conn, "smtp_host", str(body["smtp_host"]).strip()[:80])
        if "smtp_port" in body:
            n = int(body["smtp_port"])
            if not 1 <= n <= 65535:
                raise HTTPException(status_code=400, detail="端口不合法")
            set_setting(conn, "smtp_port", str(n))
        if "smtp_ssl" in body:
            set_setting(conn, "smtp_ssl", "1" if body["smtp_ssl"] else "0")
        if "smtp_user" in body:
            set_setting(conn, "smtp_user", str(body["smtp_user"]).strip()[:100])
        if "smtp_pass" in body:
            set_setting(conn, "smtp_pass", str(body["smtp_pass"])[:100])
        return _settings_payload(conn)


@app.post("/api/notify/test")
def notify_test(request: Request, body: dict):
    """用请求体携带的 SMTP 配置立即发送一封测试邮件（无需先保存）。

    应用名从服务端设置读取，保证测试邮件与正式提醒邮件的品牌一致。
    """
    require_auth(request)
    with db() as conn:
        app_name = get_setting(conn, "app_name", "SubDeck") or "SubDeck"
    emails = str(body.get("notify_emails") or "").strip()
    if "@" not in emails or not body.get("smtp_host"):
        raise HTTPException(status_code=400, detail="请先填写 SMTP 服务器与收件邮箱")
    cfg = {
        "app_name": app_name,
        "smtp_host": str(body.get("smtp_host") or "").strip(),
        "smtp_port": int(body.get("smtp_port") or 465),
        "smtp_ssl": bool(body.get("smtp_ssl", True)),
        "smtp_user": str(body.get("smtp_user") or "").strip(),
        "smtp_pass": str(body.get("smtp_pass") or ""),
        "emails": emails,
    }
    html = mailer.build_html(app_name, [], 0)
    html = html.replace("共有 <strong>0</strong> 笔订阅到期", "邮件通道正常，配置成功")
    try:
        mailer.send_mail(cfg, f"{app_name} · 测试邮件", html)
        return {"ok": True, "info": "已发送，请查收收件箱（注意垃圾邮件文件夹）"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"发送失败：{e}")


@app.on_event("startup")
def start_notify_scheduler():
    """后台线程：每日到点扫描到期订阅并发送提醒邮件（v1.4.0）。"""
    threading.Thread(target=mailer.scheduler_loop, args=(db, get_setting, set_setting),
                     daemon=True, name="notify-scheduler").start()


@app.get("/api/rates")
def get_rates(request: Request):
    require_auth(request)
    with db() as conn:
        r, updated = rates.get_rates(conn)
        return {"base_currency": get_setting(conn, "base_currency", "CNY"),
                "rates": r, "updated_at": updated}


@app.post("/api/rates/refresh")
def refresh_rates(request: Request):
    require_auth(request)
    with db() as conn:
        base = get_setting(conn, "base_currency", "CNY")
        ok, info, data = rates.fetch_and_cache(conn, base)
        return {"ok": ok, "info": info, "rates": data}


# ---------------------------------------------------------------- 手动汇率 API（v1.6.1）

@app.get("/api/rates/custom")
def get_custom_rates(request: Request):
    """手动汇率面板数据：当前生效的手动汇率 + 订阅中缺汇率的币种列表。"""
    require_auth(request)
    with db() as conn:
        return _custom_payload(conn)


@app.post("/api/rates/custom")
def set_custom_rate(request: Request, body: dict):
    """录入/更新一个手动汇率。body: {"currency": "USDT", "rate": 7.24}
    rate 语义：1 单位该币种 = rate 基准币。"""
    require_auth(request)
    cur = str(body.get("currency") or "").strip().upper()
    if not _CURRENCY_RE.match(cur):
        raise HTTPException(status_code=400, detail="币种格式有误（2-8 位大写字母/数字）")
    try:
        rate = float(body.get("rate"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="汇率必须是大于 0 的数字")
    if not 0 < rate <= 1e12:
        raise HTTPException(status_code=400, detail="汇率需大于 0")
    with db() as conn:
        base = get_setting(conn, "base_currency", "CNY")
        if cur == base:
            raise HTTPException(status_code=400, detail=f"{cur} 是基准币种，无需手动汇率")
        r, _ = rates.get_rates(conn)
        if cur in r:
            raise HTTPException(status_code=400, detail=f"{cur} 已有自动汇率，无需手动设置")
        custom = _load_custom_rates(conn)
        custom[cur] = round(rate, 6)
        set_setting(conn, "custom_rates", json.dumps(custom, ensure_ascii=False))
        return _custom_payload(conn)


@app.delete("/api/rates/custom/{currency}")
def delete_custom_rate(request: Request, currency: str):
    require_auth(request)
    cur = currency.strip().upper()
    with db() as conn:
        custom = _load_custom_rates(conn)
        if cur not in custom:
            raise HTTPException(status_code=404, detail="未找到该手动汇率")
        del custom[cur]
        set_setting(conn, "custom_rates", json.dumps(custom, ensure_ascii=False))
        return _custom_payload(conn)


def _custom_payload(conn: sqlite3.Connection) -> dict:
    """set/delete 后返回与 GET 一致的面板数据。"""
    base = get_setting(conn, "base_currency", "CNY")
    r, updated = rates.get_rates(conn)
    custom = _load_custom_rates(conn)
    cur_in_use = {row["currency"] for row in conn.execute(
        "SELECT DISTINCT currency FROM subscriptions WHERE active=1")}
    missing = sorted(c for c in cur_in_use
                     if c != base and c not in r and c not in custom)
    superseded = sorted(c for c in custom if c in r)
    return {"base_currency": base, "custom": custom, "missing": missing,
            "superseded": superseded, "rates_updated_at": updated}


# ---------------------------------------------------------------- 订阅 CRUD

def _validate(body: dict, partial: bool = False) -> dict:
    """字段校验。partial=True 时只校验传入的字段。"""
    out = {}
    if not partial or "name" in body:
        name = str(body.get("name") or "").strip()
        if not name or len(name) > 100:
            raise HTTPException(status_code=400, detail="名称不能为空且不超过 100 字")
        out["name"] = name
    if not partial or "amount" in body:
        try:
            amount = round(float(body.get("amount")), 2)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="金额格式不正确")
        if amount < 0:
            raise HTTPException(status_code=400, detail="金额不能为负")
        out["amount"] = amount
    if not partial or "currency" in body:
        cur = str(body.get("currency") or "CNY").upper()
        if not _CURRENCY_RE.match(cur):
            # v1.6.1 起币种放开：ECB 30 种之外的小众币/加密币也可记录。
            # 无自动汇率时统计标「未计入」，可用设置页手动汇率补值。
            raise HTTPException(status_code=400, detail=f"币种格式有误（2-8 位大写字母/数字）：{cur}")
        out["currency"] = cur
    if not partial or "cycle" in body:
        cycle = str(body.get("cycle") or "monthly")
        if cycle not in ALLOWED_CYCLES:
            raise HTTPException(status_code=400, detail="不支持的周期")
        out["cycle"] = cycle
    if not partial or "next_billing_date" in body:
        try:
            out["next_billing_date"] = datetime.date.fromisoformat(
                str(body.get("next_billing_date"))).isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="扣费日期格式不正确")
    if not partial or "payment_method" in body:
        pay = str(body.get("payment_method") or "auto")
        if pay not in ALLOWED_PAY:
            raise HTTPException(status_code=400, detail="不支持的付款方式")
        out["payment_method"] = pay
    for key, max_len in (("category", 30), ("notes", 500), ("url", 300), ("color", 9)):
        if not partial or key in body:
            out[key] = str(body.get(key) or "")[:max_len]
    if not partial or "active" in body:
        out["active"] = 1 if body.get("active", 1) else 0
    return out


# ---------------------------------------------------------------- 手动汇率（v1.6.1）
# 背景：订阅币种已放开（ECB 30 种之外的小众币/加密币也可记录），
# 这些币种没有自动汇率 → 「未计入统计」。手动汇率给用户一个补值的出口。
# 存储语义：custom_rates[币种] = 1 单位该币种 = x 基准币（用户输入原样）。
# 折算语义：rates[y] = 1 单位基准币 = y 该币（取倒数换算）。
# 优先级：ECB 自动汇率 > 手动汇率（自动源恢复后手动值被接管，不删除，界面标注）。
# 规则：rates 里已有的币种禁止手动录入（防手动值顶掉自动准确数据）。

_CURRENCY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")   # 2-8 位大写字母/数字，放开后用于订阅与手动汇率


def _load_custom_rates(conn: sqlite3.Connection) -> dict:
    """custom_rates 存 JSON 对象；坏数据静默回落空字典，绝不让脏设置弄死统计。"""
    raw = get_setting(conn, "custom_rates", "{}")
    try:
        data = json.loads(raw or "{}")
        return {str(k).upper(): float(v) for k, v in data.items() if isinstance(v, (int, float)) and v > 0}
    except Exception:
        return {}


def _with_rates(conn: sqlite3.Connection, sub: dict) -> dict:
    """补上折算金额与月度成本（自动汇率 + 手动汇率合并）。"""
    r, _ = rates.get_rates(conn)
    custom = _load_custom_rates(conn)
    base = get_setting(conn, "base_currency", "CNY")
    merged = {**r}
    for cur, per_unit in custom.items():
        if cur not in merged:            # 自动汇率优先：rates 已有则手动值不生效（保持待接管状态）
            merged[cur] = 1.0 / per_unit  # 用户语义 1 币=x 基准 → 折算语义 1 基准=1/x 币
    sub["amount_converted"] = billing.convert(sub["amount"], sub["currency"], base, merged)
    sub["monthly_cost"] = (
        None if sub["amount_converted"] is None
        else round(sub["amount_converted"] * billing.monthly_factor(sub["cycle"]), 2)
    )
    sub["logo_url"] = f"/api/logo/{sub['logo_file']}" if sub.get("logo_file") else ""
    return sub


@app.get("/api/subscriptions")
def list_subs(request: Request, filter: str = "all", search: str = "", status: str = "all"):
    require_auth(request)
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM subscriptions ORDER BY next_billing_date ASC").fetchall()
        subs = [billing.ensure_rolled(conn, row) for row in rows]
        conn.commit()
        if filter in ALLOWED_PAY:
            subs = [s for s in subs if s["payment_method"] == filter]
        if status == "active":       # v1.6.14 订阅状态维度（与付款方式正交，可组合）
            subs = [s for s in subs if s["active"]]
        elif status == "paused":
            subs = [s for s in subs if not s["active"]]
        if search.strip():
            q = search.strip().lower()
            subs = [s for s in subs if q in s["name"].lower()
                    or q in (s["category"] or "").lower()]
        return [_with_rates(conn, s) for s in subs]


@app.post("/api/subscriptions")
def create_sub(request: Request, body: dict):
    require_auth(request)
    data = _validate(body)
    if not data.get("color"):
        import random
        data["color"] = PALETTE[random.randrange(len(PALETTE))]
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO subscriptions
               (name, amount, currency, cycle, next_billing_date, payment_method,
                category, notes, color, url, active, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["name"], data["amount"], data["currency"], data["cycle"],
             data["next_billing_date"], data["payment_method"], data["category"],
             data["notes"], data["color"], data["url"], data["active"], now, now))
        row = conn.execute("SELECT * FROM subscriptions WHERE id=?",
                           (cur.lastrowid,)).fetchone()
        return _with_rates(conn, billing.ensure_rolled(conn, row))


@app.put("/api/subscriptions/{sub_id}")
@app.patch("/api/subscriptions/{sub_id}")   # v1.6.4：REST 惯例 PATCH 别名，与 PUT 等价（partial 更新）
def update_sub(request: Request, sub_id: int, body: dict):
    require_auth(request)
    data = _validate(body, partial=True)
    with db() as conn:
        if not conn.execute("SELECT id FROM subscriptions WHERE id=?", (sub_id,)).fetchone():
            raise HTTPException(status_code=404, detail="订阅不存在")
        sets = ", ".join(f"{k}=?" for k in data)
        conn.execute(
            f"UPDATE subscriptions SET {sets}, updated_at=? WHERE id=?",
            (*data.values(), datetime.datetime.now().isoformat(timespec="seconds"), sub_id))
        row = conn.execute("SELECT * FROM subscriptions WHERE id=?", (sub_id,)).fetchone()
        return _with_rates(conn, billing.ensure_rolled(conn, row))


@app.delete("/api/subscriptions/{sub_id}")
def delete_sub(request: Request, sub_id: int):
    require_auth(request)
    with db() as conn:
        row = conn.execute("SELECT logo_file FROM subscriptions WHERE id=?", (sub_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订阅不存在")
        conn.execute("DELETE FROM subscriptions WHERE id=?", (sub_id,))
        if row["logo_file"]:
            path = os.path.join(LOGO_DIR, row["logo_file"])
            if os.path.isfile(path):
                os.remove(path)
    return {"ok": True}


# ---------------------------------------------------------------- Logo 上传

def _sniff_image(head: bytes) -> str | None:
    """魔数嗅探真实图片类型（拒绝伪装文件）。"""
    if head.startswith(LOGO_MAGIC["png"]):
        return "png"
    if head.startswith(LOGO_MAGIC["jpg"]):
        return "jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


@app.post("/api/subscriptions/{sub_id}/logo")
def upload_logo(request: Request, sub_id: int, file: UploadFile = File(...)):
    require_auth(request)
    data = file.file.read(LOGO_MAX_BYTES + 1)
    if len(data) > LOGO_MAX_BYTES:
        raise HTTPException(status_code=400, detail="图片不能超过 2MB")
    ext = _sniff_image(data[:16])
    if not ext:
        raise HTTPException(status_code=400, detail="仅支持 PNG / JPG / WebP 图片")
    with db() as conn:
        if not conn.execute("SELECT id FROM subscriptions WHERE id=?", (sub_id,)).fetchone():
            raise HTTPException(status_code=404, detail="订阅不存在")
        ts = int(datetime.datetime.now().timestamp())
        filename = f"sub_{sub_id}_{ts}.{ext}"
        path = os.path.join(LOGO_DIR, filename)
        with open(path, "wb") as f:
            f.write(data)
        old = conn.execute("SELECT logo_file FROM subscriptions WHERE id=?",
                           (sub_id,)).fetchone()["logo_file"]
        conn.execute("UPDATE subscriptions SET logo_file=?, updated_at=? WHERE id=?",
                     (filename, datetime.datetime.now().isoformat(timespec="seconds"), sub_id))
        if old:
            old_path = os.path.join(LOGO_DIR, old)
            if os.path.isfile(old_path):
                os.remove(old_path)
        return {"ok": True, "logo_url": f"/api/logo/{filename}"}


@app.delete("/api/subscriptions/{sub_id}/logo")
def clear_logo(request: Request, sub_id: int):
    """清除上传的 logo，恢复字母头像。"""
    require_auth(request)
    with db() as conn:
        row = conn.execute("SELECT logo_file FROM subscriptions WHERE id=?", (sub_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订阅不存在")
        conn.execute("UPDATE subscriptions SET logo_file=?, updated_at=? WHERE id=?",
                     (None, datetime.datetime.now().isoformat(timespec="seconds"), sub_id))
        if row["logo_file"]:
            path = os.path.join(LOGO_DIR, row["logo_file"])
            if os.path.isfile(path):
                os.remove(path)
    return {"ok": True}


@app.get("/api/logo/{filename}")
def get_logo(request: Request, filename: str):
    require_auth(request)
    if not LOGO_RE.match(filename):
        raise HTTPException(status_code=400, detail="非法文件名")
    path = os.path.join(LOGO_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文件不存在")
    media = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}[filename.rsplit(".", 1)[1]]
    return FileResponse(path, media_type=media,
                        headers={"Cache-Control": "private, max-age=86400"})


# ---------------------------------------------------------------- 品牌资产（外观背景图 / 应用图标）

BRAND_MAX_BYTES = 4 * 1024 * 1024  # 4MB


def _save_brand_file(file: UploadFile, prefix: str, max_bytes: int) -> str:
    """通用品牌文件保存：魔数嗅探 + 大小限制，返回文件名。"""
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"图片不能超过 {max_bytes // (1024 * 1024)}MB")
    ext = _sniff_image(data[:16])
    if not ext:
        raise HTTPException(status_code=400, detail="仅支持 PNG / JPG / WebP 图片")
    ts = int(datetime.datetime.now().timestamp())
    filename = f"{prefix}_{ts}.{ext}"
    with open(os.path.join(BG_DIR, filename), "wb") as f:
        f.write(data)
    return filename


def _read_brand_setting(conn: sqlite3.Connection, key: str,
                        new_filename: str | None = None) -> None:
    """更新品牌文件设置并清理旧文件。"""
    old = get_setting(conn, key, "")
    set_setting(conn, key, new_filename or "")
    if old:
        old_path = os.path.join(BG_DIR, old)
        if os.path.isfile(old_path):
            os.remove(old_path)


@app.post("/api/brand/background")
def upload_background(request: Request, file: UploadFile = File(...)):
    require_auth(request)
    filename = _save_brand_file(file, "bg", BRAND_MAX_BYTES)
    with db() as conn:
        _read_brand_setting(conn, "bg_image", filename)
        return {"ok": True, "bg_image": filename}


@app.delete("/api/brand/background")
def clear_background(request: Request):
    require_auth(request)
    with db() as conn:
        _read_brand_setting(conn, "bg_image", None)
    return {"ok": True}


@app.get("/api/brand/background")
def get_background(request: Request):
    require_auth(request)
    with db() as conn:
        filename = get_setting(conn, "bg_image", "")
    if not filename:
        raise HTTPException(status_code=404, detail="未设置背景图")
    return _brand_file_response(filename)


@app.post("/api/brand/icon")
def upload_icon(request: Request, file: UploadFile = File(...)):
    require_auth(request)
    filename = _save_brand_file(file, "icon", 2 * 1024 * 1024)
    with db() as conn:
        _read_brand_setting(conn, "brand_icon", filename)
        return {"ok": True, "brand_icon": filename}


@app.delete("/api/brand/icon")
def clear_icon(request: Request):
    require_auth(request)
    with db() as conn:
        _read_brand_setting(conn, "brand_icon", None)
    return {"ok": True}


@app.get("/api/brand/icon")
def get_icon(request: Request):
    """品牌图标（favicon / 主屏图标共用；未设置时 404，前端回落静态默认图标）。"""
    require_auth(request)
    with db() as conn:
        filename = get_setting(conn, "brand_icon", "")
    if not filename:
        raise HTTPException(status_code=404, detail="未设置自定义图标")
    return _brand_file_response(filename)


def _brand_file_response(filename: str) -> FileResponse:
    if not BRAND_RE.match(filename):
        raise HTTPException(status_code=400, detail="非法文件名")
    path = os.path.join(BG_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文件不存在")
    media = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}[filename.rsplit(".", 1)[1]]
    return FileResponse(path, media_type=media,
                        headers={"Cache-Control": "private, max-age=3600"})


# ---------------------------------------------------------------- 登录页自定义（v1.5.0）
# 上传/修改需登录；读取公开（登录页在认证前就要渲染装饰配置）。
# 公开面仅暴露装饰性内容（标题/欢迎语/背景/图标），订阅等业务数据照旧锁在登录后。

@app.get("/api/brand/login-page")
def login_page_public():
    """登录页装饰配置（公开无害：不包含任何邮箱、密码、订阅数据）。"""
    with db() as conn:
        icon_file = get_setting(conn, "login_icon", "") or get_setting(conn, "brand_icon", "")
        return {
            "app_name": get_setting(conn, "app_name", "SubDeck") or "SubDeck",
            "login_title": get_setting(conn, "login_title", ""),
            "login_welcome": get_setting(conn, "login_welcome", ""),
            "login_bg": get_setting(conn, "login_bg", ""),
            "login_bg_mask": int(get_setting(conn, "login_bg_mask", "45") or 45),
            "theme_color": get_setting(conn, "theme_color", ""),
            "icon_ver": icon_file,   # 文件名带时间戳，作为缓存破坏参数
        }


@app.post("/api/brand/login-icon")
def upload_login_icon(request: Request, file: UploadFile = File(...)):
    require_auth(request)
    filename = _save_brand_file(file, "loginicon", LOGIN_ICON_MAX_BYTES)
    with db() as conn:
        _read_brand_setting(conn, "login_icon", filename)
        return {"ok": True, "login_icon": filename}


@app.delete("/api/brand/login-icon")
def clear_login_icon(request: Request):
    require_auth(request)
    with db() as conn:
        _read_brand_setting(conn, "login_icon", None)
    return {"ok": True}


@app.get("/api/brand/login-icon")
def get_login_icon(request: Request):
    """登录页图标（公开）：登录页自定义 → 品牌图标回落 → 404（前端回落首字母）。"""
    with db() as conn:
        filename = get_setting(conn, "login_icon", "") or get_setting(conn, "brand_icon", "")
    if not filename:
        raise HTTPException(status_code=404, detail="未设置登录页图标")
    return _brand_file_response(filename)


@app.post("/api/brand/login-background")
def upload_login_background(request: Request, file: UploadFile = File(...)):
    require_auth(request)
    filename = _save_brand_file(file, "loginbg", BRAND_MAX_BYTES)
    with db() as conn:
        _read_brand_setting(conn, "login_bg", filename)
        return {"ok": True, "login_bg": filename}


@app.delete("/api/brand/login-background")
def clear_login_background(request: Request):
    """删除自定义登录页背景，回落主题渐变。"""
    require_auth(request)
    with db() as conn:
        _read_brand_setting(conn, "login_bg", None)
        set_setting(conn, "login_bg", "")
    return {"ok": True}


@app.get("/api/brand/login-background")
def get_login_background(request: Request):
    """登录页自定义背景图（公开；预设/渐变模式 404，前端走静态资源或 CSS 渐变）。"""
    with db() as conn:
        filename = get_setting(conn, "login_bg", "")
    if not filename or filename.startswith("preset:") or filename == "none":
        raise HTTPException(status_code=404, detail="未设置自定义登录页背景")
    return _brand_file_response(filename)


# ---------------------------------------------------------------- 扣费日历（月历视图数据源）

@app.get("/api/billing-calendar")
def billing_calendar(request: Request, months: int = 12):
    """未来 N 个月的扣费日程：按周期从 next_billing_date 向前推算（单一事实源）。

    返回 entries 按日期升序；weekly 按周推、月/季/半年/年按日历月推（月末收缩与
    ensure_rolled 同语义），前端月历直接消费，不重复实现推算逻辑。
    """
    require_auth(request)
    months = max(1, min(months, 24))
    today = billing.TODAY
    end = billing.add_months(today, months)
    with db() as conn:
        rows = conn.execute(
            "SELECT id,name,amount,currency,cycle,next_billing_date,category,logo_file "
            "FROM subscriptions WHERE active=1").fetchall()
        subs = [billing.ensure_rolled(conn, r) for r in rows]
    entries = []
    for s in subs:
        d = datetime.date.fromisoformat(s["next_billing_date"])
        while d <= end:
            if d >= today:
                entries.append({
                    "date": d.isoformat(), "id": s["id"], "name": s["name"],
                    "amount": s["amount"], "currency": s["currency"],
                    "cycle": s["cycle"], "category": s["category"],
                    "logo_url": f"/api/logo/{s['logo_file']}" if s["logo_file"] else "",
                })
            d = billing.add_cycle(d, s["cycle"])
    entries.sort(key=lambda e: e["date"])
    return {"entries": entries, "months": months}


# ---------------------------------------------------------------- 统计

@app.get("/api/stats")
def stats(request: Request):
    require_auth(request)
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE active=1 ORDER BY next_billing_date ASC").fetchall()
        subs = [_with_rates(conn, billing.ensure_rolled(conn, r)) for r in rows]
        conn.commit()
        base = get_setting(conn, "base_currency", "CNY")
        remind_days = int(get_setting(conn, "remind_days", "7") or 7)

        monthly_total, missing_rate = 0.0, []
        by_category: dict[str, float] = {}
        pending, upcoming = [], []
        for s in subs:
            if s["monthly_cost"] is None:
                missing_rate.append(s["currency"])
                continue
            monthly_total += s["monthly_cost"]
            cat = s["category"] or "other"
            by_category[cat] = round(by_category.get(cat, 0.0) + s["monthly_cost"], 2)
            if s["days_until"] <= remind_days:
                pending.append(s)
            if s["days_until"] <= 30:
                upcoming.append(s)
        categories = sorted(
            [{"category": k, "monthly": v} for k, v in by_category.items()],
            key=lambda x: -x["monthly"])
        # v1.6.7 外币订阅月均汇总条：与 monthly_total 同口径（全量活跃、monthly_cost 求和）
        fx_items = [{"id": s["id"], "name": s["name"], "cycle": s["cycle"],
                     "amount": s["amount"], "currency": s["currency"],
                     "monthly_cost": s["monthly_cost"]}
                    for s in subs
                    if s["currency"] != base and s["monthly_cost"] is not None]
        fx_missing = [s for s in subs
                      if s["currency"] != base and s["monthly_cost"] is None]
        fx_total = round(sum(i["monthly_cost"] for i in fx_items), 2)
        return {
            "base_currency": base,
            "monthly_total": round(monthly_total, 2),
            "yearly_total": round(monthly_total * 12, 2),
            "active_count": len(subs),
            "pending_count": len(pending),
            "missing_rate_currencies": sorted(set(missing_rate)),
            "by_category": categories,
            "pending": pending,
            "upcoming": upcoming,
            "fx_summary": {
                "count": len(fx_items),
                "total_monthly": fx_total,
                "missing_count": len(fx_missing),
                "missing_currencies": sorted({s["currency"] for s in fx_missing}),
                "items": fx_items,
            },
        }


# ---------------------------------------------------------------- 日历订阅

def _valid_ics_token(token: str) -> bool:
    """校验持久化日历令牌（v1.5.1）：settings.ics_token 长期有效，供手机日历订阅。"""
    if not token:
        return False
    with db() as conn:
        expected = get_setting(conn, "ics_token", "")
    return bool(expected) and hmac.compare_digest(token, expected)


@app.get("/api/ics-url")
def ics_url(request: Request):
    """返回带访问令牌的日历订阅链接（仅登录用户可获取）。

    v1.5.1 起令牌持久化：首次生成后固定不变（settings.ics_token），
    手机日历 App 订阅一次长期有效，不再 30 天过期。
    需要作废旧链接时清空该设置即可自动重新生成。
    v1.6.5：改为路径式 token（/api/calendar/{token}.ics）。部分日历客户端
    （如小米日历）对 URL query 参数支持不佳，路径式兼容性更好。
    """
    require_auth(request)
    with db() as conn:
        token = get_setting(conn, "ics_token", "")
        if not token:
            token = secrets.token_urlsafe(24)
            set_setting(conn, "ics_token", token)
    return {"url": f"/api/calendar/{token}.ics"}


def _calendar_ics_impl(request: Request, token: str):
    # 日历 App 不支持 Cookie，需用链接内 token；浏览器内访问走 Cookie。
    # v1.5.1：持久化 ics_token（长期有效）与旧版 HMAC 会话 token 双轨兼容
    if auth.auth_enabled() and not (
        _valid_ics_token(token)
        or auth.verify_token(token)
        or auth.verify_token(request.cookies.get(auth.COOKIE_NAME))
    ):
        raise HTTPException(status_code=401, detail="unauthorized")
    with db() as conn:
        rows = conn.execute(
            "SELECT id,name,amount,currency,cycle,next_billing_date,notes "
            "FROM subscriptions WHERE active=1").fetchall()
        subs = [billing.ensure_rolled(conn, r) for r in rows]
        base = get_setting(conn, "base_currency", "CNY")
        calname = f"{get_setting(conn, 'app_name', 'SubDeck') or 'SubDeck'} 订阅账单"
    ics = generate_ics(subs, base, calname=calname)
    # v1.6.6：声明标准文件名（路径式 URL 的 token 长文件名不利于日历 App 识别），
    # attachment 对订阅式客户端无影响（只影响浏览器下载命名）
    return PlainTextResponse(
        ics, media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="subdeck.ics"'})


@app.get("/api/calendar.ics", response_class=PlainTextResponse)
def calendar_ics(request: Request, token: str = ""):
    # 旧版 query 式订阅链接（v1.5.1–1.6.4），保留兼容已订阅用户
    return _calendar_ics_impl(request, token)


@app.get("/api/calendar/{token_ics}", response_class=PlainTextResponse)
def calendar_ics_path(request: Request, token_ics: str):
    # v1.6.5 路径式订阅链接：token 以 {token}.ics 形式出现在路径中
    if not token_ics.endswith(".ics"):
        raise HTTPException(status_code=404, detail="not found")
    return _calendar_ics_impl(request, token_ics[:-4])


# ---------------------------------------------------------- 数据备份 / 导入 / 回滚（v1.6.11）

@app.get("/api/export")
def export_backup(request: Request, sensitive: int = 0):
    """导出备份包 zip。sensitive=1 时保留 SMTP 授权码等敏感设置（默认剔除）。

    无论是否含敏感信息，导出完成提示"妥善保管"由前端负责；
    secret.key（会话密钥）永不进包。
    """
    require_auth(request)
    from . import backup
    data = backup.export_bytes(sensitive=bool(sensitive))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    filename = f"subdeck-backup-{stamp}.zip"
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/import-status")
def import_status(request: Request):
    """回滚可用性查询（前端据此显隐"回滚上次导入"按钮）。"""
    require_auth(request)
    from . import backup
    return {"has_rollback": backup.has_rollback()}


@app.post("/api/import")
async def import_backup(request: Request):
    """覆盖式导入备份包 zip；导入前自动留档，可一键回滚到导入前。"""
    require_auth(request)
    from . import backup
    try:
        form = await request.form()
        upload = form.get("file")
        if upload is None or isinstance(upload, str):
            raise ValueError("缺少上传文件（字段名 file）")
        data = await upload.read()
        if not data:
            raise ValueError("上传文件为空")
        return backup.import_zip_bytes(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/import/rollback")
def rollback_import(request: Request):
    """一键回滚到最近一次导入前的状态（回滚后存档作废）。"""
    require_auth(request)
    from . import backup
    try:
        return backup.rollback()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------- 静态资源

@app.get("/manifest.webmanifest")
def web_manifest():
    """动态 PWA 清单：应用名称 / 自定义图标 / 主题色即时生效（主屏图标名需重新添加快捷方式）。"""
    with db() as conn:
        name = get_setting(conn, "app_name", "SubDeck") or "SubDeck"
        icon = get_setting(conn, "brand_icon", "")
        theme = get_setting(conn, "theme_color", "") or "#4f6ef7"
    if icon:
        icons = [{"src": "/api/brand/icon", "sizes": "any", "type": "image/png"}]
    else:
        icons = [
            {"src": "/assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ]
    return JSONResponse({
        "name": name, "short_name": name,
        "description": "自部署订阅管理",
        "start_url": "/", "display": "standalone",
        "background_color": "#f4f6fb", "theme_color": theme,
        "icons": icons,
    })


app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/")
def index():
    # v1.6.13 修复：静态资源版本戳自动跟随 APP_VERSION（此前 ?v= 写死在 HTML 里，
    # 发版只改 app.js 时 URL 不变，浏览器命中旧缓存导致更新"不生效"）
    html = (os.path.join(STATIC_DIR, "index.html"))
    with open(html, encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r"\?v=[\w.]+", f"?v={APP_VERSION}", content)
    return HTMLResponse(content, headers={"Cache-Control": "no-cache"})
