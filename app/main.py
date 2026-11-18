# -*- coding: utf-8 -*-
"""SubDeck —— 自部署订阅管理（FastAPI 后端入口）。"""
import datetime
import os
import re
import shutil
import sqlite3

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import auth, billing, rates
from .currencies import CURRENCIES, CYCLES, PAYMENT_METHODS
from .db import LOGO_DIR, db, get_setting, init_db, set_setting
from .ical import generate_ics

APP_VERSION = "1.1.1"
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

LOGO_RE = re.compile(r"^sub_\d+_\d+\.(png|jpg|webp)$")
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


@app.post("/api/login")
def login(request: Request, body: dict):
    if not auth.auth_enabled():
        return {"ok": True, "msg": "未启用密码保护"}
    if not isinstance(body.get("password"), str) or not auth.check_password(body["password"]):
        raise HTTPException(status_code=401, detail="密码错误")
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
    }


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
def put_settings(request: Request, body: dict):
    require_auth(request)
    with db() as conn:
        if "base_currency" in body:
            if body["base_currency"] not in CURRENCIES:
                raise HTTPException(status_code=400, detail="不支持的币种")
            set_setting(conn, "base_currency", body["base_currency"])
        if "remind_days" in body:
            days = int(body["remind_days"])
            if not 0 <= days <= 90:
                raise HTTPException(status_code=400, detail="提醒天数需在 0-90 之间")
            set_setting(conn, "remind_days", str(days))
        return _settings_payload(conn)


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
        if cur not in CURRENCIES:
            raise HTTPException(status_code=400, detail=f"暂不支持的币种：{cur}")
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


def _with_rates(conn: sqlite3.Connection, sub: dict) -> dict:
    """补上折算金额与月度成本（基于缓存汇率）。"""
    r, _ = rates.get_rates(conn)
    base = get_setting(conn, "base_currency", "CNY")
    sub["amount_converted"] = billing.convert(sub["amount"], sub["currency"], base, r)
    sub["monthly_cost"] = (
        None if sub["amount_converted"] is None
        else round(sub["amount_converted"] * billing.monthly_factor(sub["cycle"]), 2)
    )
    sub["logo_url"] = f"/api/logo/{sub['logo_file']}" if sub.get("logo_file") else ""
    return sub


@app.get("/api/subscriptions")
def list_subs(request: Request, filter: str = "all", search: str = ""):
    require_auth(request)
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM subscriptions ORDER BY next_billing_date ASC").fetchall()
        subs = [billing.ensure_rolled(conn, row) for row in rows]
        conn.commit()
        if filter in ALLOWED_PAY:
            subs = [s for s in subs if s["payment_method"] == filter]
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
        }


# ---------------------------------------------------------------- 日历订阅

@app.get("/api/ics-url")
def ics_url(request: Request):
    """返回带访问令牌的日历订阅链接（仅登录用户可获取）。"""
    require_auth(request)
    return {"url": f"/api/calendar.ics?token={auth.make_token()}"}


@app.get("/api/calendar.ics", response_class=PlainTextResponse)
def calendar_ics(request: Request, token: str = ""):
    # 日历 App 不支持 Cookie，需用链接内 token；浏览器内访问走 Cookie
    if auth.auth_enabled() and not (
        auth.verify_token(token) or auth.verify_token(request.cookies.get(auth.COOKIE_NAME))
    ):
        raise HTTPException(status_code=401, detail="unauthorized")
    with db() as conn:
        rows = conn.execute(
            "SELECT id,name,amount,currency,cycle,next_billing_date,notes "
            "FROM subscriptions WHERE active=1").fetchall()
        subs = [billing.ensure_rolled(conn, r) for r in rows]
        base = get_setting(conn, "base_currency", "CNY")
    ics = generate_ics(subs, base)
    return PlainTextResponse(ics, media_type="text/calendar; charset=utf-8")


# ---------------------------------------------------------------- 静态资源

app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
