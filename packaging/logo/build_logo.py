# -*- coding: utf-8 -*-
"""SubDeck logo 生成器（v1.6.3 资产）。
设计：三张错位叠起的订阅卡片（Deck 意象）+ 前卡对勾（已管理），主题蓝底。
导出：SVG 源文件 / PNG 全尺寸 / 多尺寸 .ico（Windows 包）/ .icns（mac 包）。
"""
import struct, os
import cairosvg
from PIL import Image

OUT = "/home/z/my-project/subdeck/packaging/logo"
WEB = "/home/z/my-project/subdeck/static/icons"
os.makedirs(OUT, exist_ok=True)

BLUE = "#4f6ef7"          # App 默认主题色
BLUE_D = "#3d55e0"        # 渐变深端

# ---------- 主视觉 SVG（1024×1024，图形居中于 maskable 安全区内） ----------
SVG_FULL = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{BLUE}"/>
      <stop offset="1" stop-color="{BLUE_D}"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" rx="228" fill="url(#bg)"/>
  <g transform="rotate(-6 512 512)"><rect x="292" y="252" width="440" height="330" rx="54" fill="#ffffff" opacity="0.30"/></g>
  <g transform="rotate(-3 512 512)"><rect x="274" y="288" width="476" height="340" rx="56" fill="#ffffff" opacity="0.55"/></g>
  <rect x="256" y="332" width="512" height="382" rx="58" fill="#ffffff"/>
  <path d="M370 566 l76 76 l208 -224" fill="none" stroke="{BLUE}" stroke-width="46"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''

# ---------- favicon 简化版（≤48px：双层卡 + 加粗对勾，保证小尺寸可读） ----------
SVG_SIMPLE = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{BLUE}"/>
      <stop offset="1" stop-color="{BLUE_D}"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" rx="228" fill="url(#bg)"/>
  <g transform="rotate(-5 512 512)"><rect x="292" y="272" width="440" height="400" rx="56" fill="#ffffff" opacity="0.42"/></g>
  <rect x="248" y="316" width="528" height="424" rx="60" fill="#ffffff"/>
  <path d="M362 556 l92 92 l210 -230" fill="none" stroke="{BLUE}" stroke-width="62"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''

# ---------- 导出 ----------
# 网页/通用 PNG
for size, svg in [(1024, SVG_FULL), (512, SVG_FULL), (192, SVG_FULL), (180, SVG_FULL), (64, SVG_FULL)]:
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/logo-{size}.png", output_width=size, output_height=size)
for size in (48, 32, 16):
    cairosvg.svg2png(bytestring=SVG_SIMPLE.encode(), write_to=f"{OUT}/logo-{size}.png", output_width=size, output_height=size)

# 网页 favicon（替换 static/icons 旧图）
cairosvg.svg2png(bytestring=SVG_FULL.encode(), write_to=f"{WEB}/icon-512.png", output_width=512, output_height=512)
cairosvg.svg2png(bytestring=SVG_FULL.encode(), write_to=f"{WEB}/icon-192.png", output_width=192, output_height=192)

# maskable（Android 自适应图标：同一图形，图形本身已含安全边距）
cairosvg.svg2png(bytestring=SVG_FULL.encode(), write_to=f"{OUT}/logo-maskable-512.png", output_width=512, output_height=512)

# ---------- .ico（Windows 发行包，多尺寸单文件） ----------
ico_sizes = [16, 24, 32, 48, 64, 128, 256]
imgs = []
for s in ico_sizes:
    svg = SVG_SIMPLE if s <= 48 else SVG_FULL
    p = f"{OUT}/_ico-{s}.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=p, output_width=s, output_height=s)
    imgs.append(Image.open(p).convert("RGBA"))
imgs[-1].save("/home/z/my-project/subdeck/packaging/subdeck.ico",
              format="ICO", sizes=[(s, s) for s in ico_sizes], append_images=imgs[:-1])
for s in ico_sizes:
    os.remove(f"{OUT}/_ico-{s}.png")
print("ico OK:", os.path.getsize("/home/z/my-project/subdeck/packaging/subdeck.ico"), "bytes")

# ---------- .icns（mac 包 Dock 图标；PNG 块手工组装，无需系统工具） ----------
ICNS_MAP = [("icp4", 16), ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024)]
chunks = b""
for t, s in ICNS_MAP:
    p = f"{OUT}/_icns-{s}.png"
    cairosvg.svg2png(bytestring=SVG_FULL.encode(), write_to=p, output_width=s, output_height=s)
    data = open(p, "rb").read()
    chunks += t.encode() + struct.pack(">I", len(data) + 8) + data
    os.remove(p)
icns = b"icns" + struct.pack(">I", len(chunks) + 8) + chunks
open("/home/z/my-project/subdeck/packaging/subdeck.icns", "wb").write(icns)
print("icns OK:", os.path.getsize("/home/z/my-project/subdeck/packaging/subdeck.icns"), "bytes")

# SVG 源文件
open(f"{OUT}/logo.svg", "w", encoding="utf-8").write(SVG_FULL)
open(f"{OUT}/logo-simple.svg", "w", encoding="utf-8").write(SVG_SIMPLE)
print("SVG OK")
for f in sorted(os.listdir(OUT)):
    print(" ", f, os.path.getsize(f"{OUT}/{f}"))
