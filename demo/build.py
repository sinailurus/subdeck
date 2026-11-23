#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SubDeck 只读演示页构建脚本（纯静态，标准库实现）。

用法：
    python demo/build.py              # 产物输出到 demo/dist/
    DEMO_VERSION=v1.6.20 python demo/build.py

做什么：
  1. 拷贝 static/ 到 demo/dist/（index.html / app.js / app.css / icons / bg / 隐私政策）；
  2. 根相对路径改写：GitHub Pages 项目页部署在 /subdeck/ 子路径下，
     源码里的 "/assets/..." 需要改成 "./..."，否则样式、图标、背景图会 404；
  3. 注入演示层：demo-data.js（虚构数据）与 demo.js（fetch 拦截）在 app.js 之前加载；
  4. 去掉动态 PWA manifest（后端接口，静态页没有对应物，避免访客把演示页装成应用）；
  5. 版本号：优先 DEMO_VERSION 环境变量（CI 里传 tag），否则读 app/main.py 的 APP_VERSION。
"""
import os
import re
import shutil
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
ASSETS = pathlib.Path(__file__).resolve().parent / "assets" / "logo"
DIST = pathlib.Path(__file__).resolve().parent / "dist"

# demo-data.js / demo.js 以纯字符串注入的版本占位
VERSION_SCRIPT = '<script>window.SUBDECK_DEMO_VERSION = "{version}";</script>'
DEMO_TAGS = VERSION_SCRIPT + '<script src="./demo-data.js"></script><script src="./demo.js"></script>\n'


def read_app_version() -> str:
    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', src)
    return m.group(1) if m else "demo"


def resolve_version() -> str:
    ver = os.environ.get("DEMO_VERSION", "").strip()
    if ver.startswith("v"):
        ver = ver[1:]
    if not re.match(r"^\d", ver):          # 分支名（如 main）不算版本，回落仓库版本
        ver = read_app_version()
    return ver


def copy_static() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)
    shutil.copytree(ASSETS, DIST / "logo")   # 虚构订阅 logo → ./logo/xxx.png
    demo_dir = pathlib.Path(__file__).resolve().parent
    shutil.copy2(demo_dir / "demo-data.js", DIST / "demo-data.js")
    shutil.copy2(demo_dir / "demo.js", DIST / "demo.js")


def rewrite_index(version: str) -> None:
    p = DIST / "index.html"
    html = p.read_text(encoding="utf-8")
    # 1) 去掉动态 manifest 链接（后端接口，静态页不提供）
    html = re.sub(r'\s*<link rel="manifest"[^>]*>', "", html)
    # 2) 根相对路径 → 子路径可用的相对路径（双引号与单引号两种写法都要处理）
    html = html.replace('"/assets/', '"./').replace("'/assets/", "'./")
    # 3) 静态资源版本戳跟随演示版本（与后端 index() 的行为一致）
    html = re.sub(r"\?v=[\w.\-]+", f"?v={version}", html)
    # 4) 在 app.js 之前注入演示层（demo-data 先于 demo）
    html = re.sub(
        r'(\s*)(<script src="\./app\.js\?v=[^"]+"></script>)',
        r"\1" + DEMO_TAGS.replace("\\", "\\\\") + r"\2",
        html,
        count=1,
    )
    p.write_text(html, encoding="utf-8")


def rewrite_css() -> None:
    p = DIST / "app.css"
    css = p.read_text(encoding="utf-8")
    css = css.replace('"/assets/', '"./').replace("'/assets/", "'./")
    p.write_text(css, encoding="utf-8")


def rewrite_js() -> None:
    p = DIST / "app.js"
    js = p.read_text(encoding="utf-8")
    js = js.replace('"/assets/', '"./').replace("`/assets/", "`./")
    p.write_text(js, encoding="utf-8")


def main() -> int:
    version = resolve_version()
    if not STATIC.exists():
        print(f"[build] 找不到前端目录：{STATIC}", file=sys.stderr)
        return 1
    copy_static()
    rewrite_index(version)
    rewrite_css()
    rewrite_js()

    # 构建结果快速自检：注入必须恰好发生一次
    html = (DIST / "index.html").read_text(encoding="utf-8")
    if html.count("demo-data.js") != 1 or html.count("demo.js") != 1:
        print("[build] 演示层注入异常，中止", file=sys.stderr)
        return 1
    if "/assets/" in html:
        print("[build] index.html 仍残留根相对路径，中止", file=sys.stderr)
        return 1
    n_logos = len(list((DIST / "logo").glob("*.png")))
    print(f"[build] 完成：demo/dist/（版本 {version}，logo {n_logos} 张）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
