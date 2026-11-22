# -*- coding: utf-8 -*-
"""数据备份 / 导入 / 回滚（v1.6.11）。

导出包结构（zip）：
  manifest.json   {"schema_version": 1, "app_version", "exported_at", "sensitive": bool}
  subdeck.db      SQLite 库快照（sensitive=False 时已剔除敏感项）
  logos/...       订阅 logo 图片
  bg/...          品牌背景 / 应用图标

导入语义（覆盖式，v1.6.11 与所有者确认）：
  subscriptions  整表替换（按现库列交集读包，兼容旧版本导出包）
  settings       按 key UPSERT（包里没有的 key 保留本地现状，避免邮箱提醒等被意外清掉）
  logos / bg     清空后按包重建
导入前自动留档（仅保留最近一次）→ 支持一键回滚。
secret.key（会话密钥）永不进包。
"""
import datetime
import io
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile

from .db import BG_DIR, DATA_DIR, LOGO_DIR

SCHEMA_VERSION = 1
APP_VERSION_TAG = "1.6.11"

# 不允许出现在导出/导入之外的敏感 settings 键（导出 sensitive=False 时剔除）
SENSITIVE_KEYS = {"smtp_pass"}

ROLLBACK_DIR = os.path.join(DATA_DIR, "import-rollback")
ROLLBACK_FILE = os.path.join(ROLLBACK_DIR, "pre-import.zip")


def _snapshot_db_bytes(strip_sensitive: bool) -> bytes:
    """用 sqlite backup API 取一致性快照；strip_sensitive 时从快照剔除敏感键。"""
    src = sqlite3.connect(os.path.join(DATA_DIR, "subdeck.db"), timeout=10)
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        dst = sqlite3.connect(tmp_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
        if strip_sensitive:
            dst = sqlite3.connect(tmp_path)
            try:
                for k in SENSITIVE_KEYS:
                    dst.execute("DELETE FROM settings WHERE key=?", (k,))
                dst.commit()
            finally:
                dst.close()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        src.close()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _pack_zip(sensitive: bool, strip_sensitive: bool = False) -> bytes:
    """打包完整备份。strip_sensitive=True 时剔除敏感键（用户勾选"不含敏感信息"）。

    内部回滚快照传 (True, False)：内部档永远保全量，回滚必须完整。
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "app_version": APP_VERSION_TAG,
            "exported_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "sensitive": bool(sensitive),
        }
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr("subdeck.db", _snapshot_db_bytes(strip_sensitive=strip_sensitive))
        for root, label in ((LOGO_DIR, "logos"), (BG_DIR, "bg")):
            if not os.path.isdir(root):
                continue
            for name in sorted(os.listdir(root)):
                path = os.path.join(root, name)
                if os.path.isfile(path):
                    z.write(path, f"{label}/{name}")
    return buf.getvalue()


def export_bytes(sensitive: bool) -> bytes:
    """用户导出：sensitive=True 保留 SMTP 授权码等；False 剔除。"""
    return _pack_zip(sensitive=sensitive, strip_sensitive=not sensitive)


def has_rollback() -> bool:
    return os.path.isfile(ROLLBACK_FILE)


def _safe_extract_assets(zf: zipfile.ZipFile) -> int:
    """解包 logos/ 与 bg/ 到数据目录（清空重建，防路径穿越）。返回文件数。"""
    count = 0
    for label, target in (("logos/", LOGO_DIR), ("bg/", BG_DIR)):
        members = [
            n for n in zf.namelist()
            if n.startswith(label) and not n.endswith("/")
            and ".." not in n and not os.path.isabs(n)
        ]
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
        os.makedirs(target, exist_ok=True)
        for name in members:
            out = os.path.join(target, os.path.basename(name))
            with zf.open(name) as fsrc, open(out, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
            count += 1
    return count


def _restore_db(db_bytes: bytes) -> dict:
    """逻辑还原：订阅整表替换（列交集兼容旧包），settings 按 key UPSERT。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    try:
        with open(tmp.name, "wb") as f:
            f.write(db_bytes)
        tmp.close()
        src = sqlite3.connect(tmp.name)
        src.row_factory = sqlite3.Row
        try:
            # 结构校验：必须有两张核心表
            tables = {r[0] for r in src.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"subscriptions", "settings"} <= tables:
                raise ValueError("备份包数据库结构不符（缺少核心表）")
            src_cur = src.execute("SELECT * FROM subscriptions")
            src_cols = [d[0] for d in src_cur.description]
            src_rows = src_cur.fetchall()
            src_settings = src.execute("SELECT key, value FROM settings").fetchall()

            from .db import db
            with db() as conn:
                dst_cols = [r[1] for r in conn.execute(
                    "PRAGMA table_info(subscriptions)")]
                common = [c for c in dst_cols if c in src_cols]
                conn.execute("DELETE FROM subscriptions")
                if src_rows:
                    ph = ",".join("?" * len(common))
                    conn.executemany(
                        f"INSERT INTO subscriptions ({','.join(common)}) VALUES ({ph})",
                        [[row[c] for c in common] for row in src_rows],
                    )
                for srow in src_settings:
                    conn.execute(
                        "INSERT INTO settings(key, value) VALUES(?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (srow["key"], srow["value"]),
                    )
            return {"subscriptions": len(src_rows), "settings": len(src_settings)}
        finally:
            src.close()
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _open_backup(data: bytes):
    """校验并打开备份包，返回 (zipfile, manifest)。结构不符抛 ValueError。"""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("不是有效的 zip 文件")
    names = set(zf.namelist())
    if "manifest.json" not in names or "subdeck.db" not in names:
        raise ValueError("缺少 manifest.json 或 subdeck.db，不是 SubDeck 备份包")
    # v1.6.19：解压后大小上限，防 zip 炸弹（小压缩包解出超大文件占满磁盘/内存）
    for info in zf.infolist():
        if info.file_size > 256 * 1024 * 1024:
            raise ValueError(f"备份包含超大文件（{info.filename} 解压后超过 256MB）")
    try:
        manifest = json.loads(zf.read("manifest.json"))
    except json.JSONDecodeError:
        raise ValueError("manifest.json 解析失败")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"备份包 schema 版本不符（{manifest.get('schema_version')}）")
    return zf, manifest


def import_zip_bytes(data: bytes) -> dict:
    """覆盖式导入。导入前自动留档（覆盖旧档，只保留最近一次可回滚）。"""
    zf, manifest = _open_backup(data)
    db_bytes = zf.read("subdeck.db")
    os.makedirs(ROLLBACK_DIR, exist_ok=True)
    with open(ROLLBACK_FILE, "wb") as f:
        f.write(_pack_zip(sensitive=True, strip_sensitive=False))
    stats = _restore_db(db_bytes)
    assets = _safe_extract_assets(zf)
    return {
        "ok": True,
        "sensitive": bool(manifest.get("sensitive")),
        "exported_at": manifest.get("exported_at", ""),
        "assets": assets,
        **stats,
        "rollback_available": True,
    }


def rollback() -> dict:
    """一键回滚到最近一次导入前的状态；回滚后快照作废。"""
    if not has_rollback():
        raise ValueError("没有可回滚的导入存档")
    with open(ROLLBACK_FILE, "rb") as f:
        data = f.read()
    zf, _manifest = _open_backup(data)
    stats = _restore_db(zf.read("subdeck.db"))
    assets = _safe_extract_assets(zf)
    try:
        os.remove(ROLLBACK_FILE)
    except OSError:
        pass
    return {"ok": True, "assets": assets, **stats, "rollback_available": False}
