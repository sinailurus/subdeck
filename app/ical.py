# -*- coding: utf-8 -*-
"""iCal 日历导出：把未来 12 个月的扣费日生成 .ics，供手机日历订阅。"""
import datetime

from .billing import add_cycle

ICAL_DT_FMT = "%Y%m%d"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def generate_ics(subs: list[dict], base_currency: str, calname: str = "SubDeck 订阅账单") -> str:
    """subs 为已滚动的活跃订阅列表（已含 name/amount/currency/cycle/next_billing_date）。

    calname 跟随设置中的应用名称（v1.4.0 起），日历 App 内显示一致的品牌名。
    """
    today = datetime.date.today()
    # 未来一年窗口：复用 add_cycle 的年周期推算（月末收缩），避免 2 月 29 日
    # 直接 replace(year+1) 抛 ValueError（闰日当天生成日历会 500）
    horizon = add_cycle(today, "yearly")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SubDeck//Subscription Billing//ZH",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(calname)}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]
    for sub in subs:
        d = datetime.date.fromisoformat(sub["next_billing_date"])
        while d < horizon:
            amount = f"{sub['amount']:g}".rstrip("0").rstrip(".") or "0"
            # v1.6.6：SUMMARY 去除 emoji。部分日历客户端（如小米日历）解析
            # 4 字节 UTF-8 字符（emoji）崩溃导致导入失败；中文名（3 字节）不受影响
            summary = f"{_escape(sub['name'])} {amount} {sub['currency']}"
            lines += [
                "BEGIN:VEVENT",
                f"UID:subdeck-{sub['id']}-{d.strftime(ICAL_DT_FMT)}@subdeck.local",
                f"DTSTAMP:{today.strftime(ICAL_DT_FMT)}T000000Z",
                f"DTSTART;VALUE=DATE:{d.strftime(ICAL_DT_FMT)}",
                f"DTEND;VALUE=DATE:{(d + datetime.timedelta(days=1)).strftime(ICAL_DT_FMT)}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{_escape(sub.get('notes') or '')}",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]
            d = add_cycle(d, sub["cycle"])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
