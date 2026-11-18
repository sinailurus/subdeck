# -*- coding: utf-8 -*-
"""汇率：主源 frankfurter.dev（ECB 参考汇率）+ 备用源自动回退，缓存进 SQLite。

数据来源声明（将写入 README）：European Central Bank reference rates，
经由 https://frankfurter.dev 免费获取，无需 API Key；
备用源 https://open.er-api.com 亦免费无需 Key，返回格式兼容（{"rates": {...}}）。
"""
import datetime
import json
import urllib.request

from .db import get_setting, set_setting

# 主源在前；请求失败自动切换下一个源。约定：rates[x] = 1 单位 base = x 外币。
SOURCES = (
    ("ECB/frankfurter", "https://api.frankfurter.dev/v1/latest?base={base}"),
    ("ER-API", "https://open.er-api.com/v6/latest/{base}"),
)


def get_rates(conn) -> tuple[dict, str]:
    """返回 (rates 缓存, 更新时间)。rates[x] = 1 单位基准币 = x 外币。"""
    rates = json.loads(get_setting(conn, "rates", "{}") or "{}")
    updated = get_setting(conn, "rates_updated_at", "")
    return rates, updated


def _fetch_source(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "SubDeck/1.1"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    raw = data.get("rates")
    if not isinstance(raw, dict) or not raw:
        raise ValueError("响应缺少 rates 字段")
    return {k: float(v) for k, v in raw.items()}


def fetch_and_cache(conn, base: str) -> tuple[bool, str, dict]:
    """联网刷新汇率，主源失败自动回退备源。

    成功返回 (True, 更新时间, rates)；全部源失败返回 (False, 原因, 旧缓存)。
    网络失败时保留旧缓存，应用可继续使用。
    """
    old_rates, _ = get_rates(conn)
    errors = []
    for name, tpl in SOURCES:
        try:
            fetched = _fetch_source(tpl.format(base=base))
            rates = {base: 1.0}
            rates.update(fetched)
            updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            set_setting(conn, "rates", json.dumps(rates))
            set_setting(conn, "rates_updated_at", updated)
            return True, updated, rates
        except Exception as e:  # 单个源失败：记录原因，继续尝试下一个源
            errors.append(f"{name} {type(e).__name__}: {e}")
    return False, "；".join(errors), old_rates
