# -*- coding: utf-8 -*-
"""账单日滚动与统计计算。

核心规则：next_billing_date 永远指向"今天及以后的最近一次扣费日"。
读取时若发现日期已过期，自动按周期向前滚动（滚动写入数据库）。
"""
import calendar
import datetime
import sqlite3

from .currencies import CYCLES


def today() -> datetime.date:
    """实时获取今天。v1.6.19 修复：此前用模块级常量 TODAY = date.today()，
    容器跨天运行后冻结在启动日期，导致倒计时、账单滚动与提醒窗口全部失真。"""
    return datetime.date.today()


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
    t = today()
    while d < t:
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
    sub["days_until"] = (rolled - today()).days
    return sub


def add_months(d: datetime.date, months: int) -> datetime.date:
    """加 N 个日历月（月末自动收缩：31 号遇 2 月落月末），与 add_cycle 同语义。"""
    total = d.year * 12 + (d.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    return datetime.date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def monthly_factor(cycle: str) -> float:
    return CYCLES[cycle][2]


# v1.6.20 回血口径：回收金额按计费周期摊销的月数。weekly 无自然月数，按 1 个月近似。
CYCLE_MONTHS = {
    "weekly": 1,
    "monthly": 1,
    "quarterly": 3,
    "semiannual": 6,
    "yearly": 12,
}


def cycle_months(cycle: str) -> int:
    return CYCLE_MONTHS.get(cycle, 1)


def convert(amount: float, currency: str, base: str, rates: dict) -> float | None:
    """按缓存汇率把外币金额折算成基准币种。缺汇率时返回 None。"""
    if currency == base:
        return round(amount, 2)
    rate = rates.get(currency)
    if not rate:
        return None
    return round(amount / rate, 2)  # rates[x] = 1 单位基准币兑换 x 外币
