# -*- coding: utf-8 -*-
"""SubDeck 正式用户手册 PDF（面向最终用户，可 GitHub 分发）。"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                PageBreak, Table, TableStyle, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

# 可移植性：默认用仓库相对路径，可用环境变量覆盖（截图在 docs/manual-shots/）
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("MANUAL_OUT", os.path.join(REPO, "docs"))
SHOTS = os.environ.get("MANUAL_SHOTS", os.path.join(REPO, "docs", "manual-shots"))
SW, SH = A4
PRIMARY = colors.HexColor("#4f6ef7")
INK = colors.HexColor("#1f2430")
MUTED = colors.HexColor("#6b7280")

pdfmetrics.registerFont(TTFont("SC", "/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf"))
pdfmetrics.registerFont(TTFont("SC-Bold", "/usr/share/fonts/truetype/chinese/SarasaMonoSC-Bold.ttf"))

S = {
    "title": ParagraphStyle("t", fontName="SC-Bold", fontSize=26, leading=40, alignment=TA_CENTER, textColor=INK),
    "subtitle": ParagraphStyle("st", fontName="SC", fontSize=14, leading=24, alignment=TA_CENTER, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName="SC-Bold", fontSize=15, leading=24, spaceBefore=16, spaceAfter=8, textColor=PRIMARY),
    "h2": ParagraphStyle("h2", fontName="SC-Bold", fontSize=12, leading=20, spaceBefore=10, spaceAfter=6, textColor=INK),
    "body": ParagraphStyle("b", fontName="SC", fontSize=10.5, leading=18, textColor=INK, spaceAfter=6, firstLineIndent=21),
    "li": ParagraphStyle("li", fontName="SC", fontSize=10.5, leading=18, textColor=INK, spaceAfter=4, leftIndent=18),
    "cap": ParagraphStyle("cap", fontName="SC", fontSize=9, leading=14, alignment=TA_CENTER, textColor=MUTED, spaceBefore=4, spaceAfter=10),
}

def img(path, width):
    with PILImage.open(path) as im:
        w, h = im.size
    return Image(path, width=width, height=width * h / w)

def figure(path, width, caption):
    return KeepTogether([img(path, width), Paragraph(caption, S["cap"])])

def header_footer(canv, doc):
    canv.saveState()
    canv.setFont("SC", 8)
    canv.setFillColor(MUTED)
    canv.drawString(50, SH - 36, "SubDeck  用户手册")
    canv.drawRightString(SW - 50, SH - 36, f"第 {doc.page} 页")
    canv.setStrokeColor(colors.HexColor("#d5d9e2"))
    canv.setLineWidth(0.5)
    canv.line(50, SH - 42, SW - 50, SH - 42)
    canv.restoreState()

E = []
# ---------------- 封面 ----------------
E += [Spacer(1, 180),
      Paragraph("SubDeck 订阅管理", S["title"]),
      Spacer(1, 10),
      Paragraph("用 户 手 册", ParagraphStyle("bt", parent=S["title"], fontSize=30, leading=48)),
      Spacer(1, 24),
      Paragraph("适用于 V1.6 及以上版本", S["subtitle"]),
      Paragraph("2026 年 11 月", S["subtitle"]),
      PageBreak()]

# ---------------- 1 软件概述 ----------------
E += [Paragraph("一、软件概述", S["h1"]),
      Paragraph("SubDeck 是一套自部署的个人订阅管理软件，用来集中管理各类会员订阅和周期性扣费的服务与账单。软件以网页应用方式运行，手机或电脑浏览器打开就能用，不用装客户端。全部数据保存在用户自有的服务器、NAS 或个人电脑中，不依赖任何第三方云服务。", S["body"]),
      Paragraph("软件的核心功能包括：订阅的创建、编辑、删除、暂停与分类管理；月均支出、年度支出等费用统计；分类占比图表分析（条形图、环形图、饼图）；未来 30 天扣费时间线提醒；扣费日历月视图展示；多币种记账与自动汇率折算；界面外观个性化（主题色、界面风格、背景图、应用名称与图标自定义）；iCal 日历订阅导出；邮箱到期提醒；数据备份与还原；以及 PWA 手机桌面安装。", S["body"]),
      Paragraph("软件支持三种部署方式：Docker 容器部署（推荐 NAS 与服务器用户）、Windows 一键部署包（双击即用）、macOS 一键部署包（Intel 与 Apple Silicon 双架构）。客户端支持 Chrome、Edge、Safari 等现代浏览器，并适配手机端界面。", S["body"])]

# ---------------- 2 安装部署 ----------------
E += [Paragraph("二、安装部署", S["h1"]),
      Paragraph("2.1 Docker 部署（NAS / 服务器用户推荐）", S["h2"]),
      Paragraph("在具备 Docker 环境的设备上，将软件的 docker-compose.yml 文件保存到任意目录并启动即可完成部署。在群晖、绿联等 NAS 设备的 Docker 管理界面中，选择「项目」或「Compose」功能，新建项目并粘贴部署文件内容后启动。启动成功后通过「http://设备IP:8300」访问软件。", S["body"]),
      Paragraph("镜像更新时，在项目管理界面执行「重新部署」或「一键更新」操作即可拉取新版本镜像并重建容器。订阅数据存储于挂载的数据目录中，升级过程数据不受影响。注意：升级应为容器重建而非仅重启；升级后可在关于页核对版本号。", S["body"]),
      Paragraph("2.2 Windows 一键部署包（普通电脑用户推荐）", S["h2"]),
      Paragraph("在软件发布页下载 Windows 版压缩包，解压后双击 SubDeck.exe 即可运行：程序自动初始化数据目录、启动服务并打开浏览器；窗口中会同时显示局域网访问地址，手机连同一 Wi-Fi 后也可访问。同目录的 subdeck.ini 文件可自定义端口、访问密码与数据目录，不修改则使用默认配置。", S["body"]),
      Paragraph("若杀毒软件弹出拦截提示，选择「允许」或将程序目录加入信任即可（程序未购买代码签名）。数据全部保存在本地数据目录中，删除程序不影响已备份的数据文件。", S["body"]),
      Paragraph("2.3 macOS 一键部署包", S["h2"]),
      Paragraph("按芯片类型选择对应压缩包（Apple Silicon 或 Intel），解压后双击运行。首次打开如提示无法验证开发者，请前往「系统设置 → 隐私与安全性」，点击「仍要打开」放行一次即可。运行方式与 Windows 版相同：自动打开浏览器并显示访问地址。", S["body"])]

# ---------------- 3 登录与密码保护 ----------------
E += [Paragraph("三、登录与密码保护", S["h1"]),
      Paragraph("软件支持可选的访问密码保护。在部署配置中设置管理密码后，打开软件需要先在登录页输入密码；登录一次后在有效期内不用重复输入。若不设置密码，软件以开放模式运行，此时建议只在可信的内网环境使用；如果开放了公网访问，务必设置密码。", S["body"]),
      Paragraph("为了防暴力破解，同一个地址连续输错多次密码后会被临时锁定，等一会儿就能重试。软件的日历订阅地址采用独立访问令牌，无需在日历客户端中配置密码；令牌可在设置页随时重置，旧链接立即失效。", S["body"]),
      figure(f"{SHOTS}/m-login.png", 240, "图 3-1  登录页（手机端界面，演示数据）")]
E += [PageBreak()]

# ---------------- 4 订阅管理 ----------------
E += [Paragraph("四、订阅管理", S["h1"]),
      Paragraph("4.1 添加订阅", S["h2"]),
      Paragraph("在「订阅」页点击「添加订阅」按钮打开表单，填写：订阅名称（必填）；扣费金额与币种（支持人民币、美元、欧元、日元、港币等任意币种代码）；扣费周期（每周、每月、每季度、每半年、每年）；首次扣费日期；付款方式（自动扣费或手动付款）；所属分类。表单支持上传自定义 Logo，自动压缩并生成圆形头像；未上传时以名称首字配合分类配色生成默认头像。", S["body"]),
      Paragraph("保存后系统按扣费周期自动推算下一次扣费日期；账单日到期后自动滚动至下一周期，月末日期自动收缩（31 日扣费的订阅在 2 月自动落到当月最后一天）。月度费用按周期折算为月均金额，用于统计与图表。", S["body"]),
      Paragraph("4.2 编辑与删除", S["h2"]),
      Paragraph("订阅卡片与表格行均提供编辑、删除按钮。编辑时可修改全部字段并更换 Logo；删除操作有确认提示，防止误删。", S["body"]),
      Paragraph("4.3 搜索、筛选与排序", S["h2"]),
      Paragraph("订阅页顶部提供搜索框，支持按名称与分类关键字模糊搜索；提供「全部 / 自动扣费 / 手动付款」快捷筛选。排序按钮支持三态循环切换：默认排序（按创建顺序）→ 金额升序 → 金额降序，排序依据为折算成基准币种后的金额，跨币种订阅可直接比较。", S["body"]),
      figure(f"{SHOTS}/m-subs.png", 240, "图 4-1  订阅列表：外币汇总条、排序按钮与暂停操作（手机端，演示数据）"),
      Paragraph("4.4 暂停与恢复", S["h2"]),
      Paragraph("对暂时不再续费但不想删除的订阅（如季卡会员、暂停使用的服务），可点击卡片或表格行上的暂停按钮：订阅整行灰显并标记「已暂停」状态。暂停期间该订阅不计入支出统计、待付款列表与扣费日历；再次点击恢复按钮后，账单日自动滚动至下一周期并重新计入统计。编辑弹窗中也可通过「订阅进行中」开关切换状态。", S["body"]),
      Paragraph("4.5 分类管理", S["h2"]),
      Paragraph("设置页提供分类管理面板，可新增、重命名、删除自定义分类，删除分类时该分类下的订阅自动转为未分类，不影响订阅数据本身。", S["body"])]
E += [PageBreak()]

# ---------------- 5 概览统计 ----------------
E += [Paragraph("五、概览统计", S["h1"]),
      Paragraph("概览页集中展示订阅费用统计：月均支出、年度支出、活跃订阅数量、即将扣费数量四个统计卡片；待付款区列出未来 30 天内的扣费计划，按时间先后排列，当天到期的订阅以醒目样式标记。订阅列表顶部设有外币月均汇总条，展开后显示全部外币订阅折算后的月均合计，个别币种暂无汇率时会明确提示缺失数量。", S["body"]),
      Paragraph("汇率机制：软件默认使用欧洲央行参考汇率并自动更新，全部外币订阅按最新汇率折算统计；概览页汇率卡片显示汇率更新时间，点击「刷新」可手动同步。设置页提供手动汇率面板，可为没有自动汇率的币种手动录入折算价（录入格式为 1 单位该币种折合多少基准币），已有自动汇率的币种以自动值优先。", S["body"]),
      Paragraph("分类月度占比图表支持条形图、环形图、饼图三种形态，在图卡右上角即时切换。图表按各分类的月均金额绘制，环形图与饼图中央显示月合计金额。", S["body"]),
      figure(f"{SHOTS}/m-dashboard.png", 240, "图 5-1  概览统计与分类占比环形图（手机端，演示数据）")]

# ---------------- 6 扣费日历 ----------------
E += [Paragraph("六、扣费日历", S["h1"]),
      Paragraph("「日历」为独立导航模块，以月视图形式展示全部订阅的续费日程。有续费安排的日期显示圆点标记与当日合计金额小字；今日以高亮色块标识；月历下方显示本月续费笔数与合计金额。", S["body"]),
      Paragraph("点击任意日期，下方明细区展开显示当日续费的订阅清单，包含头像、名称、分类标签、原币金额与折算金额。打开日历时默认选中下一个最近的续费日期。月历通过顶部箭头逐月切换，支持翻看未来 12 个月的扣费分布，「今天」按钮快速回到当月。已暂停的订阅不出现在日历中。", S["body"]),
      figure(f"{SHOTS}/m-calendar.png", 240, "图 6-1  扣费日历月视图与当日明细（手机端，演示数据）")]
E += [PageBreak()]

# ---------------- 7 外观设置 ----------------
E += [Paragraph("七、外观设置", S["h1"]),
      Paragraph("设置页提供完整的外观个性化面板，全部设置保存于服务端，手机、电脑、平板多端访问自动同步。", S["body"]),
      Paragraph("7.1 主题色", S["h2"]),
      Paragraph("提供 9 个预置主题色与任意十六进制颜色自定义输入，支持一键恢复默认。主题色应用于按钮、链接、图表配色、浏览器地址栏等界面元素，深色模式下自动亮度适配。", S["body"]),
      Paragraph("7.2 界面风格", S["h2"]),
      Paragraph("提供三档界面风格：「实色」为传统不透明卡片风格，最稳妥；「点缀玻璃」在背景加入柔和色晕，卡片保持实色；「重度玻璃」为卡片半透明毛玻璃效果，卡片会透出背景图，属实验性风格。", S["body"]),
      Paragraph("7.3 背景图", S["h2"]),
      Paragraph("内置三张渐变预设背景（极光、糖果、日落）与「无背景」快捷选项；支持上传自定义背景图，上传大图自动压缩。遮罩浓度滑杆实时调节背景上方遮罩的深浅，让前景文字在任何背景下都看得清。", S["body"]),
      Paragraph("7.4 应用名称与图标", S["h2"]),
      Paragraph("支持自定义应用名称（1-12 字）与品牌图标。名称与图标同步应用于浏览器标签页、PWA 安装名称与桌面图标。此外登录页背景、页面标题等也可自定义。", S["body"]),
      figure(f"{SHOTS}/d-settings.png", 440, "图 7-1  外观设置面板（桌面端界面，演示数据）")]
E += [PageBreak()]

# ---------------- 8 iCal 日历订阅 ----------------
E += [Paragraph("八、iCal 日历订阅", S["h1"]),
      Paragraph("软件内置 iCal（ICS）格式的日历订阅端点。在设置页复制订阅链接后，粘贴到手机或电脑系统日历（iOS 日历、Google 日历等）的「订阅日历 / 添加日历账户」功能中，即可在系统日历中同步查看每一笔续费安排，包含订阅名称、金额与备注。", S["body"]),
      Paragraph("对于不支持网络订阅的日历应用（如部分手机的系统日历），可改用文件导入：在浏览器中打开订阅链接下载 .ics 文件，再通过日历应用的「导入」功能导入，效果相同。", S["body"]),
      Paragraph("订阅链接内嵌独立访问令牌，无需配置密码；在设置页可随时重置令牌，旧链接立即失效，适合在链接泄露或更换设备时使用。", S["body"])]

# ---------------- 9 数据备份与还原 ----------------
E += [Paragraph("九、数据备份与还原", S["h1"]),
      Paragraph("设置页提供一键备份与一键还原：备份将全部订阅、外观设置与 Logo 图片打包为单个备份文件下载；还原时选择备份文件即可完整恢复数据。", S["body"]),
      Paragraph("安全细节：导出时可选是否包含敏感信息（如 SMTP 授权码等凭据）；会话密钥不会写入备份文件；导入前系统自动将当前数据完整留档，导入结果不对时可一键回滚到导入前的状态。", S["body"]),
      Paragraph("除备份文件外，全部业务数据（订阅记录、图片、设置）都存储在部署时挂载的数据目录中，定期备份该目录同样有效；更换设备时携带备份文件即可完整迁移。", S["body"])]

# ---------------- 10 PWA 安装 ----------------
E += [Paragraph("十、PWA 手机桌面安装", S["h1"]),
      Paragraph("软件符合 PWA（渐进式 Web 应用）规范。在手机浏览器中打开软件后，通过浏览器菜单的「添加到主屏幕」功能，可将软件以独立应用图标的形式安装到手机桌面；安装后全屏运行，体验接近原生应用，名称与图标跟随外观设置自动更新。", S["body"])]

# ---------------- 11 邮箱提醒 ----------------
E += [Paragraph("十一、邮箱提醒", S["h1"]),
      Paragraph("进入「设置 → 邮箱提醒」面板启用订阅到期邮件提醒。启用后，软件在每天设定时刻（0-23 点）自动检查未来 N 天（默认 3 天，可设 1-30 天）内到期的订阅，汇总成一封邮件发送；同一订阅的同一账单日只提醒一次。邮件主题与落款使用外观设置中的应用名称。", S["body"]),
      Paragraph("配置步骤：", S["body"]),
      Paragraph("1. 填写收件邮箱，多个邮箱用逗号分隔。", S["li"]),
      Paragraph("2. 设置提前提醒天数与每天发送时间。", S["li"]),
      Paragraph("3. 填写 SMTP 服务器、端口与发件信息。QQ 邮箱服务器为 smtp.qq.com，163 邮箱为 smtp.163.com，端口都用 465（SSL）。", S["li"]),
      Paragraph("4. SMTP 授权码在邮箱网页版设置中开启 SMTP 服务后获取。注意授权码不是邮箱登录密码。", S["li"]),
      Paragraph("5. 点击「发送测试邮件」验证配置，收到测试邮件后勾选启用并保存。", S["li"]),
      figure(f"{SHOTS}/mail.png", 400, "图 11-1  到期提醒邮件效果（演示数据）")]

# ---------------- 12 常见问题 ----------------
E += [Paragraph("十二、常见问题", S["h1"]),
      Paragraph("忘记访问密码：在部署配置中修改管理密码后重建容器（或重启程序）即可，订阅数据不受影响。", S["li"]),
      Paragraph("升级后界面异常：确认容器为重建而非重启（查看容器创建时间是否刷新）；仍异常时可重复执行一次更新操作。", S["li"]),
      Paragraph("某个币种没有汇率：在设置页手动汇率面板录入该币种的折算价；已有自动汇率的币种无需手动录入。", S["li"]),
      Paragraph("导入备份后数据不对：在设置页使用一键回滚，即可恢复到导入前的完整状态。", S["li"]),
      Paragraph("日历订阅导入失败：改用文件导入方式（先下载 .ics 再用日历应用导入）；确认链接完整未截断；更换令牌后需重新添加。", S["li"]),
      Paragraph("数据安全：全部数据存储在自有设备的挂载目录中，建议定期使用一键备份；公网环境使用务必设置访问密码。", S["li"])]

os.makedirs(OUT, exist_ok=True)
out_path = os.path.join(OUT, "SubDeck用户手册.pdf")
doc = SimpleDocTemplate(out_path, pagesize=A4,
                        leftMargin=50, rightMargin=50, topMargin=60, bottomMargin=50,
                        title="SubDeck 用户手册", author="SubDeck")
doc.build(E, onFirstPage=header_footer, onLaterPages=header_footer)
print("用户手册 PDF 生成完成:", out_path, os.path.getsize(out_path) // 1024, "KB")
