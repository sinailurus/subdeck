# -*- coding: utf-8 -*-
"""SubDeck Windows 桌面启动器（PyInstaller 入口，v1.6.0）。

设计给「不会 Docker / 不会命令行」的用户：
双击运行 → 读配置 → 端口预检 → 起服务 → 自动打开浏览器。

配置优先级：命令行参数 > subdeck.ini > 环境变量 > 默认值
（桌面场景用户唯一看得见、改得了的是 ini 文件，故 ini 优先于 env）。

关闭本窗口或 Ctrl+C 即停止服务；数据目录与卸载规则见「使用说明.txt」。
"""
import argparse
import configparser
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

IS_FROZEN = getattr(sys, "frozen", False)

# exe 所在目录（onefile 解包发生在临时目录，用户文件必须锚定 exe 旁）
BASE_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
INI_PATH = BASE_DIR / "subdeck.ini"

DEFAULT_PORT = 8017

INI_TEMPLATE = """\
# ============================================
#  SubDeck 配置文件
#  改完保存，重新启动 SubDeck 生效
# ============================================

# 数据目录：订阅数据、上传图片都存在这里。
# 留空 = 本文件旁边的 data 文件夹。
# 想放到别处就写完整路径，例如 D:\\SubDeckData
# （换目录=搬家：把整个 data 文件夹复制过去即可，数据不会丢）
data_dir =

# 访问密码：设了之后，打开页面和手机访问都要先输这个密码。
# 留空 = 不启用（只在自己家里电脑/手机访问，可以不设）。
password =

# 端口：留空 = 8017。若被其他程序占用，会自动顺延到 8018 并在窗口提示。
port =
"""


def ensure_ini() -> Path:
    """exe 旁没有配置文件则生成中文注释模板（删除后再次启动会自动重建）。"""
    if not INI_PATH.exists():
        INI_PATH.write_text(INI_TEMPLATE, encoding="utf-8")
    return INI_PATH


def read_ini() -> dict:
    """解析 subdeck.ini，字段缺失/损坏时一律回退默认，避免配置文件问题导致启动失败。"""
    out = {"data_dir": "", "password": "", "port": ""}
    try:
        cp = configparser.ConfigParser()
        cp.read(INI_PATH, encoding="utf-8")
        # 模板无节头，configparser 归入 DEFAULT 节；兼容显式 [SubDeck] 节
        section = cp["SubDeck"] if cp.has_section("SubDeck") else cp.defaults()
        for k in out:
            out[k] = (section.get(k) or "").strip()
    except Exception:
        pass
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SubDeck 桌面启动器")
    p.add_argument("--data-dir", dest="data_dir", default="", help="数据目录（覆盖 subdeck.ini）")
    p.add_argument("--password", default="", help="访问密码（覆盖 subdeck.ini）")
    p.add_argument("--port", type=int, default=0, help="端口（覆盖 subdeck.ini）")
    return p.parse_args()


def resolve_settings(cfg: dict, args: argparse.Namespace) -> dict:
    """命令行参数 > ini > 环境变量 > 默认值。返回最终生效配置。"""
    data_dir = args.data_dir or cfg["data_dir"] or os.environ.get("DATA_DIR", "")
    password = args.password or cfg["password"] or os.environ.get("AUTH_PASSWORD", "")
    port = args.port or _to_int(cfg["port"]) or DEFAULT_PORT
    return {"data_dir": data_dir, "password": password, "port": port}


def _to_int(v: str) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def find_free_port(start: int, tries: int = 10) -> int:
    """端口被占用则顺延，最多试 10 个；全占则退回原端口交给报错提示。"""
    for p in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", p))
                return p
            except OSError:
                continue
    return start


def lan_ip() -> str:
    """取本机局域网 IP（UDP connect 只查路由不发包），失败回退 127.0.0.1。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def open_browser_when_ready(port: int) -> None:
    """轮询到服务端口可连接后再开浏览器，避免打开过早白屏。"""
    for _ in range(100):  # 最多等 20 秒
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                webbrowser.open(f"http://127.0.0.1:{port}")
                return
        except OSError:
            time.sleep(0.2)


def set_console_title(title: str) -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass


def print_banner(s: dict, port: int) -> None:
    ip = lan_ip()
    dd = s["data_dir"] or str(BASE_DIR / "data")
    print("=" * 56)
    print("  SubDeck 已启动")
    print("=" * 56)
    print(f"  本机访问      http://127.0.0.1:{port}")
    print(f"  手机/局域网   http://{ip}:{port}   （连同一个 WiFi）")
    print(f"  数据目录      {dd}")
    print(f"  访问密码      {'已启用' if s['password'] else '未启用'}")
    print("-" * 56)
    print("  关闭此窗口或按 Ctrl+C 即停止服务")
    print("=" * 56)


def main() -> None:
    ensure_ini()
    cfg = read_ini()
    args = parse_args()
    s = resolve_settings(cfg, args)

    port = find_free_port(s["port"])
    if port != s["port"]:
        print(f"[提示] 端口 {s['port']} 被占用，已自动改用 {port}")

    # 关键：db/auth 模块在 import 时读取环境变量，必须先设定再导入
    os.environ["DATA_DIR"] = s["data_dir"] or str(BASE_DIR / "data")
    os.environ["AUTH_PASSWORD"] = s["password"]

    set_console_title(f"SubDeck 运行中 - 关闭此窗口即停止服务 (端口 {port})")
    print_banner(s, port)

    threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()

    import uvicorn
    from app.main import app
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
