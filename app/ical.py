# -*- coding: utf-8 -*-
"""iCal 日历导出：把未来 12 个月的扣费日生成 .ics，供手机日历订阅。"""
import datetime

from .billing import add_cycle

ICAL_DT_FMT = "%Y%m%d"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def generate_ics(subs: list[dict], base_currency: str) -> str:
    """subs 为已滚动的活跃订阅列表（已含 name/amount/currency/cycle/next_billing_date）。"""
    today = datetime.date.today()
    horizon = today.replace(year=today.year + 1)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SubDeck//Subscription Billing//ZH",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:SubDeck 订阅账单",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]
    for sub in subs:
        d = datetime.date.fromisoformat(sub["next_billing_date"])
        while d < horizon:
            amount = f"{sub['amount']:g}".rstrip("0").rstrip(".") or "0"
            summary = f"🔁 {_escape(sub['name'])} {amount} {sub['currency']}"
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
