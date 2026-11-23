# -*- coding: utf-8 -*-
"""SQLite 数据层：建表、连接、迁移。全部使用标准库，无第三方 ORM。"""
import os
import sqlite3
from contextlib import contextmanager

# 数据目录：容器内默认 /data（volume 挂载点），本地调试回退到 ./data
DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
LOGO_DIR = os.path.join(DATA_DIR, "logos")
BG_DIR = os.path.join(DATA_DIR, "bg")   # 品牌资产：外观背景图 / 应用图标（多端共享）

SCHEMA_VERSION = 2


def init_db() -> None:
    """初始化数据库与目录结构（幂等，可重复执行）。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGO_DIR, exist_ok=True)
    os.makedirs(BG_DIR, exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                name              TEXT    NOT NULL,
                amount            REAL    NOT NULL DEFAULT 0,
                currency          TEXT    NOT NULL DEFAULT 'CNY',
                cycle             TEXT    NOT NULL DEFAULT 'monthly',
                next_billing_date TEXT    NOT NULL,
                payment_method    TEXT    NOT NULL DEFAULT 'auto',
                category          TEXT    NOT NULL DEFAULT '',
                notes             TEXT    NOT NULL DEFAULT '',
                logo_file         TEXT    NOT NULL DEFAULT '',
                color             TEXT    NOT NULL DEFAULT '',
                url               TEXT    NOT NULL DEFAULT '',
                active            INTEGER NOT NULL DEFAULT 1,
                created_at        TEXT    NOT NULL,
                updated_at        TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rebates (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                sub_id     INTEGER NOT NULL,
                date       TEXT    NOT NULL,
                amount     REAL    NOT NULL,
                note       TEXT    NOT NULL DEFAULT '',
                created_at TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_subs_next_date
                ON subscriptions(next_billing_date);

            CREATE INDEX IF NOT EXISTS idx_rebates_sub
                ON rebates(sub_id);
            """
        )
        # v1.6.20 回血口径：老库补列（幂等）
        cols = {r[1] for r in conn.execute("PRAGMA table_info(subscriptions)")}
        if "share_count" not in cols:
            conn.execute(
                "ALTER TABLE subscriptions ADD COLUMN share_count INTEGER NOT NULL DEFAULT 0"
            )
        # 默认设置
        conn.executemany(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            [
                ("base_currency", "CNY"),
                ("remind_days", "7"),
                ("rates", "{}"),
                ("rates_updated_at", ""),
                # ---- v1.2.0 外观与品牌（多端同步，存后端） ----
                ("app_name", "SubDeck"),      # 应用名称，≤12 字
                ("theme_color", ""),          # 主题色 #RRGGBB，空 = 内置默认
                ("skin", "glass"),            # 皮肤：solid(实色) / glass(点缀玻璃) / glassplus(重度玻璃)
                ("bg_image", ""),             # 外观背景图文件名，空 = 关闭
                ("bg_mask", "35"),            # 背景图遮罩浓度 0-85（%）
                ("chart_style", "bars"),      # 分类占比图：bars / donut / pie
                ("brand_icon", ""),           # 品牌图标文件名，空 = 默认渐变 S
            ],
        )


@contextmanager
def db():
    """按请求开启连接；WAL 模式提升并发读性能。"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, "subdeck.db"), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
