# -*- coding: utf-8 -*-
"""docs/*.md 渲染为 static/docs/*.html 片段（发件教程帮助页内容源）。

用法：python3 scripts/render_smtp_docs.py
依赖：markdown（仅开发机需要，应用运行时零依赖——产物 HTML 已提交入库）。
"""
import os

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAIRS = [
    ("docs/smtp-guide.zh.md", "static/docs/smtp-guide.zh.html"),
    ("docs/smtp-guide.en.md", "static/docs/smtp-guide.en.html"),
]


def main() -> None:
    for src, dst in PAIRS:
        with open(os.path.join(ROOT, src), encoding="utf-8") as f:
            text = f.read()
        html = markdown.markdown(text, extensions=["tables", "sane_lists"])
        with open(os.path.join(ROOT, dst), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"{src} -> {dst} ({len(html)} chars)")


if __name__ == "__main__":
    main()
