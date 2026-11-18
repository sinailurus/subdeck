# -*- coding: utf-8 -*-
"""邮箱提醒（v1.4.0）：SMTP 发信 + 每日到期扫描调度。

零依赖：全部使用 Python 标准库（smtplib / email / threading）。
邮件 Subject / 发件人显示名 / 正文落款均跟随设置中的应用名称，
与页面、manifest、iCal 日历名的品牌联动保持一致。
"""
import datetime
import json
import smtplib
import ssl
import threading
import time
import traceback
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

from .billing import TODAY, ensure_rolled
from .db import get_setting, set_setting

SMTP_TIMEOUT = 15

# ---------------------------------------------------------------- 邮件构建

def _money(amount: float, currency: str) -> str:
    v = f"{amount:g}".rstrip("0").rstrip(".")
    return f"{v} {currency}"


def build_html(app_name: str, entries: list[dict], lead_days: int,
               rates_hint: str = "") -> str:
    """到期提醒邮件正文（内联样式，兼容各家邮箱客户端）。"""
    rows = "".join(
        f"<tr>"
        f"<td style='padding:10px 6px;border-bottom:1px solid #eef0f4;font-weight:600;color:#1f2430'>"
        f"{e['name']}</td>"
        f"<td style='padding:10px 6px;border-bottom:1px solid #eef0f4;text-align:right;"
        f"font-variant-numeric:tabular-nums'>{_money(e['amount'], e['currency'])}</td>"
        f"<td style='padding:10px 6px;border-bottom:1px solid #eef0f4;text-align:right;color:#6b7280'>"
        f"{e['date']}</td></tr>"
        for e in entries)
    total = ""
    hint = f"<p style='margin:6px 0 0;color:#9ca3af;font-size:12px'>{rates_hint}</p>" if rates_hint else ""
    return f"""<div style="max-width:560px;margin:0 auto;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">
  <h2 style="margin:24px 0 4px;font-size:19px;color:#1f2430">{app_name} · 到期提醒</h2>
  <p style="margin:0 0 16px;color:#6b7280;font-size:13.5px">未来 {lead_days} 天内共有 <strong>{len(entries)}</strong> 笔订阅到期：</p>
  <table style="width:100%;border-collapse:collapse;font-size:14px">
    <tr><th style="text-align:left;padding:6px;color:#9ca3af;font-weight:500">订阅</th>
        <th style="text-align:right;padding:6px;color:#9ca3af;font-weight:500">金额</th>
        <th style="text-align:right;padding:6px;color:#9ca3af;font-weight:500">扣费日</th></tr>
    {rows}
  </table>{hint}
  <p style="margin:20px 0 8px;color:#9ca3af;font-size:12px">此邮件由 {app_name} 自动发送（每日 {entries and entries[0].get('send_hour', 8) or 8} 点扫描，同一账单日只提醒一次）。可在「设置 → 邮箱提醒」中调整。</p>
</div>"""


def send_mail(cfg: dict, subject: str, html: str) -> None:
    """发送 HTML 邮件。cfg 需含 smtp_host/smtp_port/smtp_ssl/smtp_user/smtp_pass/emails。

    From 显示名取 cfg["app_name"]（品牌联动）；发件地址必须为 smtp_user（邮箱服务商要求）。
    失败抛异常，由调用方转为用户可读的中文提示。
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(cfg["app_name"], "utf-8")), cfg["smtp_user"]))
    msg["To"] = cfg["emails"]
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(html, "html", "utf-8"))
    to_list = [x.strip() for x in cfg["emails"].split(",") if x.strip()]
    if cfg["smtp_ssl"]:
        with smtplib.SMTP_SSL(cfg["smtp_host"], int(cfg["smtp_port"]),
                              context=ssl.create_default_context(), timeout=SMTP_TIMEOUT) as s:
            s.login(cfg["smtp_user"], cfg["smtp_pass"])
            s.sendmail(cfg["smtp_user"], to_list, msg.as_string())
    else:  # 587 STARTTLS
        with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"]), timeout=SMTP_TIMEOUT) as s:
            s.ehlo()
            s.starttls(context=ssl.create_default_context())
            s.login(cfg["smtp_user"], cfg["smtp_pass"])
            s.sendmail(cfg["smtp_user"], to_list, msg.as_string())

# ---------------------------------------------------------------- 到期扫描

def scan_entries(conn, lead_days: int) -> list[dict]:
    """未来 lead_days 天内到期、且该账单日未提醒过的活跃订阅（单一事实源推算）。

    返回 [{id, name, amount, currency, date}]；去重依据 notify_state（已提醒的
    账单日不再重复提醒，下个周期是新账单日、正常提醒）。
    """
    end = TODAY + datetime.timedelta(days=lead_days)
    state = json.loads(get_setting(conn, "notify_state", "{}") or "{}")
    rows = conn.execute(
        "SELECT id,name,amount,currency,cycle,next_billing_date FROM subscriptions "
        "WHERE active=1").fetchall()
    out = []
    for r in rows:
        sub = ensure_rolled(conn, r)
        d = datetime.date.fromisoformat(sub["next_billing_date"])
        if TODAY <= d <= end and state.get(str(sub["id"])) != d.isoformat():
            out.append({"id": sub["id"], "name": sub["name"], "amount": sub["amount"],
                        "currency": sub["currency"], "date": d.isoformat()})
    out.sort(key=lambda e: e["date"])
    return out

# ---------------------------------------------------------------- 每日调度

def _smtp_cfg(conn, app_name: str, emails: str) -> dict:
    return {
        "app_name": app_name,
        "smtp_host": get_setting(conn, "smtp_host", ""),
        "smtp_port": int(get_setting(conn, "smtp_port", "465") or 465),
        "smtp_ssl": get_setting(conn, "smtp_ssl", "1") == "1",
        "smtp_user": get_setting(conn, "smtp_user", ""),
        "smtp_pass": get_setting(conn, "smtp_pass", ""),
        "emails": emails,
    }


def scheduler_loop(db_factory, get_setting, set_setting) -> None:
    """后台线程：每分钟检查一次，到达发送时刻后当天只处理一次。

    last_notify_date 记录"今天已处理"（无论是否真的发出），避免重启后重发；
    notify_state 记录 每个订阅已提醒到的账单日（JSON），实现"同一账单日只提醒一次"。
    """
    while True:
        time.sleep(60)
        try:
            with db_factory() as conn:
                if get_setting(conn, "notify_enabled", "0") != "1":
                    continue
                emails = get_setting(conn, "notify_emails", "")
                if not get_setting(conn, "smtp_host", "") or not emails:
                    continue
                hour = int(get_setting(conn, "notify_hour", "8") or 8)
                now = datetime.datetime.now()
                if now.hour < hour:
                    continue
                today = now.date().isoformat()
                if get_setting(conn, "last_notify_date", "") == today:
                    continue
                set_setting(conn, "last_notify_date", today)   # 当天只处理一次
                lead = int(get_setting(conn, "notify_lead_days", "3") or 3)
                entries = scan_entries(conn, lead)
                if not entries:
                    continue
                app_name = get_setting(conn, "app_name", "SubDeck") or "SubDeck"
                cfg = _smtp_cfg(conn, app_name, emails)
                for e in entries:
                    e["send_hour"] = hour
                subject = f"{app_name} · 未来 {lead} 天有 {len(entries)} 笔订阅到期"
                send_mail(cfg, subject, build_html(app_name, entries, lead))
                # 发送成功后更新已提醒状态（失败则下轮到点前不再尝试，明天会重试该账单日）
                state = json.loads(get_setting(conn, "notify_state", "{}") or "{}")
                for e in entries:
                    state[str(e["id"])] = e["date"]
                set_setting(conn, "notify_state", json.dumps(state))
        except Exception:
            traceback.print_exc()   # 后台任务：打印日志继续轮询
