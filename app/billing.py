# -*- coding: utf-8 -*-
"""账单日滚动与统计计算。

核心规则：next_billing_date 永远指向"今天及以后的最近一次扣费日"。
读取时若发现日期已过期，自动按周期向前滚动（滚动写入数据库）。
"""
import calendar
import datetime
import sqlite3

from .currencies import CYCLES

TODAY = datetime.date.today()


def add_cycle(d: datetime.date, cycle: str) -> datetime.date:
    """按周期推算下一个日期。月/季/半年/年用日历月推算，保持"几号"不变。"""
    months = {
        "weekly": None,
        "monthly": 1,
        "quarterly": 3,
        "semiannual": 6,
        "yearly": 12,
    }[cycle]
    if months is None:  # weekly
        return d + datetime.timedelta(days=7)
    month_index = d.year * 12 + (d.month - 1) + months
    year, month = divmod(month_index, 12)
    month += 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def roll_forward(d: datetime.date, cycle: str) -> datetime.date:
    """把过期日期滚动到今天或未来。"""
    while d < TODAY:
        d = add_cycle(d, cycle)
    return d


def ensure_rolled(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    """读取单条订阅：滚动账单日并计算派生字段。"""
    sub = dict(row)
    d = datetime.date.fromisoformat(sub["next_billing_date"])
    rolled = roll_forward(d, sub["cycle"])
    if rolled != d:
        conn.execute(
            "UPDATE subscriptions SET next_billing_date=?, updated_at=? WHERE id=?",
            (rolled.isoformat(), datetime.datetime.now().isoformat(timespec="seconds"), sub["id"]),
        )
        sub["next_billing_date"] = rolled.isoformat()
    sub["days_until"] = (rolled - TODAY).days
    return sub


def monthly_factor(cycle: str) -> float:
    return CYCLES[cycle][2]


def convert(amount: float, currency: str, base: str, rates: dict) -> float | None:
    """按缓存汇率把外币金额折算成基准币种。缺汇率时返回 None。"""
    if currency == base:
        return round(amount, 2)
    rate = rates.get(currency)
    if not rate:
        return None
    return round(amount / rate, 2)  # rates[x] = 1 单位基准币兑换 x 外币
