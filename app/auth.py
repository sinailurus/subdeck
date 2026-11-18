# -*- coding: utf-8 -*-
"""简单密码登录 + HMAC 签名 Cookie。

设计取舍：
- 单用户场景（自部署），无用户表、无注册，只有环境变量里的一把密码；
- 密码为空 => 鉴权关闭（纯内网可用）；
- 签名密钥持久化在数据目录，重启后登录态不失效。
"""
import hashlib
import hmac
import os
import time

from .db import DATA_DIR

COOKIE_NAME = "subdeck_token"
SESSION_DAYS = 30
SECRET_FILE = os.path.join(DATA_DIR, "secret.key")

AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "").strip()


def auth_enabled() -> bool:
    return bool(AUTH_PASSWORD)


def _secret() -> bytes:
    """读取（或首次生成）签名密钥。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "rb") as f:
            data = f.read().strip()
            if data:
                return data
    data = os.urandom(32).hex().encode()
    with open(SECRET_FILE, "wb") as f:
        f.write(data)
    os.chmod(SECRET_FILE, 0o600)
    return data


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_token() -> str:
    """生成 {过期时间戳.签名} 格式的会话令牌。"""
    exp = int(time.time()) + SESSION_DAYS * 86400
    payload = str(exp)
    return f"{payload}.{_sign(payload)}"


def verify_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    payload, sig = token.rsplit(".", 1)
    if not payload.isdigit():
        return False
    if not hmac.compare_digest(sig, _sign(payload)):
        return False
    return int(payload) > int(time.time())


def check_password(password: str) -> bool:
    """常数时间比较，避免时序侧信道。"""
    return hmac.compare_digest(
        password.encode(), (AUTH_PASSWORD or "").encode()
    )
