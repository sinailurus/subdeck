# SubDeck · 订阅管理

中文 ｜ [English](README.en.md)

一个自部署的订阅管理工具：记录你的各种会员 / 订阅 / 定期账单，自动滚动扣费日，到期提醒，多币种实时汇率折算，按周 / 月 / 年统计花费。

> **AIGC 声明**：本项目在开发过程中使用了 AI 辅助，版权与最终决定权归仓库所有者。
>
> **文档**：[用户协议（TERMS.md）](TERMS.md) ｜ [隐私政策](static/privacy-policy.html)（应用内部署后可通过 `http://NAS_IP:8300/assets/privacy-policy.html` 访问）

## 功能特性

- 📋 **订阅管理**：名称、金额、币种、周期（每周 / 每月 / 每季度 / 每半年 / 每年）、付款方式（自动扣费 / 手动付款）、分类、备注
- 🔄 **账单日自动滚动**：过期的扣费日自动按周期滚到下一次扣费日
- ⏰ **待付款区**：临近扣费的订阅自动进入待付款区并高亮（天数可配置）
- 💱 **多币种 + 实时汇率**：内置 30 种常用币种，汇率自动同步（基于欧洲央行参考汇率），所有金额可折算为你习惯的基准币种
- 📊 **支出统计**：月均 / 年度支出、分类占比（条形 / 环形 / 饼图切换）、未来 30 天扣费时间线
- 🎨 **外观系统**：主题色自定义、三档界面风格（实色 / 点缀玻璃 / 重度玻璃）、自定义背景图 + 遮罩浓度、应用名称与图标自定义，全部多端同步
- 🖼️ **Logo**：内置字母头像（自动配色），也支持上传自定义图片（PNG / JPG / WebP，≤2MB）
- 📅 **日历订阅**：一键生成 iCal 链接，账单日直接进手机自带日历 App
- 📧 **邮箱到期提醒**：配置一次 SMTP，临近扣费自动发信提醒（可自定义提醒提前量）
- 💾 **数据备份**：网页一键导出 / 导入全量备份（含回滚留档），换设备迁移不用碰命令行
- 🌓 **深色模式**：跟随系统，也可手动切换
- 📱 **响应式适配**：桌面端表格 + 顶栏导航，手机/平板卡片 + 底部导航，支持"添加到主屏幕"（PWA）
- 🔒 **可选密码保护**：一行环境变量开启；HMAC 签名 Cookie + 登录限速防暴力破解；纯内网使用可不开启
- 🐳 **单容器部署**：SQLite 存储，无外部依赖，数据备份 = 拷贝一个目录

## 快速开始

### 绿联 UGOS Pro 用户：应用包（.upk）

到 [Releases](https://github.com/sinailurus/subdeck/releases) 下载对应架构的 `.upk`（绝大多数 x86 绿联机型选 `amd64`，ARM 机型选 `arm64`）→ 应用中心手动安装 → 按向导设置访问密码与数据文件夹即可，无需碰 Docker。

> ⚠️ **该应用包暂未在绿联应用商店上架**，属开发者自装包，未经官方审核。仅适合已完成设备授权（应用中心 → 设置 → 应用开发设置）、愿意自行承担使用风险的用户试用；安装前建议了解应用内「数据备份」功能并做好数据保护。上架进展请关注本仓库 Releases。

### 方式一：Windows / macOS 一键部署包（没有 NAS / 不会 Docker）

到 [Releases](https://github.com/sinailurus/subdeck/releases) 页面下载最新版压缩包 → 解压 → 双击运行（Windows 为 `SubDeck.exe`；macOS 为 `SubDeck`，首次打开需在「系统设置 → 隐私与安全性」放行）→ 浏览器自动打开即可使用。数据目录、访问密码、端口在压缩包内的 `subdeck.ini` 里改（有中文注释），详见包内说明文件。macOS 请按芯片选择 apple-silicon（M 系列）或 intel 包。

### 云服务器一键脚本（任何 x86 云主机：腾讯云轻量 / 阿里云 / 华为云 / 海外 VPS）

买一台最便宜的轻量云服务器（新用户常有 ¥50~100/年套餐），在网页终端粘贴一条命令装完即用，服务器 24 小时在线、日历订阅和提醒不受家里断电影响：

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/sinailurus/subdeck@main/install.sh | bash
```

完整步骤、各云控制台菜单对照与**部署前必读的安全隐私须知（明文传输 / 密码防线 / 数据留存 / 免责说明）**见 [docs/云服务器一键部署.md](docs/云服务器一键部署.md)（操作流程以腾讯云轻量为示范，其他云仅菜单名不同）。

### 方式二：使用预构建镜像（NAS / Docker 用户，推荐）

直接使用 CI 发布好的官方镜像，无需本地构建。把 `docker-compose.yml` 里的 `image:` 一行换成：

```yaml
image: ghcr.io/sinailurus/subdeck:latest
```

国内拉 GHCR 失败或很慢时，换南大代理地址（内容与官方镜像完全一致，新版本发布约 10 分钟内同步）：

```yaml
image: ghcr.nju.edu.cn/sinailurus/subdeck:latest
```

生产环境建议固定版本号（如 `ghcr.nju.edu.cn/sinailurus/subdeck:1.6.18`），避免 `latest` 自动更新带来的意外变化。端口、密码、数据目录等其余配置与「方式三」一致；绿联 UGOS 用户也可用 [compose.ugreen.yml](compose.ugreen.yml)，把其中 `image:` 换成上面的地址即可（更推荐直接用上方的 .upk 应用包）。

### 方式三：本地构建

```bash
git clone https://github.com/sinailurus/subdeck.git
cd subdeck
cp .env.example .env        # 修改 AUTH_PASSWORD
docker compose up -d        # 默认使用 8300 端口
```

访问 `http://NAS_IP:8300`。

> **NAS 权限提示（绿联 / 群晖等必读）**：请保持 compose 中的 `user: "0:0"`。Docker 自建部署时，程序入口脚本会先用 root 自动修复 `/data` 目录属主（解决 bind-mount 权限不匹配），再降权为普通用户运行服务进程。绿联 UGOS Pro 应用包（.upk）内则通过 `RUN_AS_ROOT=1` 让服务进程直接以 root 运行：UGOS 向导创建的数据文件夹是「权限位 000 + ACL 白名单」模型，且会在容器重建时重刷策略，降权用户无法稳定写入（v1.6.18 真机实测确认）。若容器以非 root 启动而数据目录属主不符，会报 `PermissionError: '/data/logos'` 并反复重启。

### 绿联 UGOS（Docker「项目」部署）

> 更推荐直接安装上方的 .upk 应用包（免 Docker、装完即用）。以下方式适合想在「项目」里自己管 Compose 的用户。

1. Docker → **「项目」** → 新建项目，名称 `subdeck`
2. 「Compose 配置」整段粘贴仓库根目录的 [compose.ugreen.yml](compose.ugreen.yml)，**只改 `AUTH_PASSWORD`**
3. 部署完成后访问 `http://NAS_IP:8300`；若提示文件夹已存在，选「使用现有文件夹」

**绿联部署注意：**

- **改配置后要重新部署**：容器配置创建后即固定，编辑 Compose 保存不会自动生效，必须触发「重新部署」重建容器；验收标准是容器详情里「创建时间」已刷新
- **保留 `user: "0:0"`**：任何部署、升级、重建都不要删这一行（原因见上方 NAS 权限提示）
- **删除项目前先确认数据**：数据目录位于项目文件夹内，删除项目前先到「文件管理」确认 `data/` 及其中文件仍在

升级方式见下方「升级指南」。

### 群晖 DSM（Container Manager）

1. 打开 **File Station**，在任意共享文件夹新建 `subdeck` 目录，把项目文件上传进去
2. 打开 **Container Manager** → **项目** → **新增**
3. 项目名称填 `subdeck`，路径选择刚才的 `subdeck` 文件夹，来源选「使用已有的 docker-compose.yml」
4. 完成向导，等待构建 / 拉取完成后访问 `http://NAS_IP:8300`

> ARM 架构的群晖机型请使用预构建镜像（方式二），本地构建会很慢。

### 威联通 QTS（Container Station）

1. 把项目上传到 NAS（如 `/share/CACHEDEV1_DATA/subdeck`）
2. SSH 登录 NAS，进入目录后执行 `docker compose up -d`
3. 访问 `http://NAS_IP:8300`

### 通用 SSH 部署

```bash
cd /path/to/subdeck
cp .env.example .env && nano .env   # 设置密码与端口
docker compose up -d
docker compose logs -f              # 查看日志，Ctrl+C 退出
```

## 配置说明

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `AUTH_PASSWORD` | 空 | 访问密码；**留空 = 不启用登录**。会暴露公网（如走隧道）时务必设置 |
| `TZ` | `Asia/Shanghai` | 时区，影响"今天"的判定与账单日滚动 |
| `SUBDECK_PORT` | `8300` | 宿主机端口 |
| `SUBDECK_DATA` | `./data` | 数据目录（数据库 + 上传的 logo） |
| `PUID` / `PGID` | 空 | 可选。对齐数据目录属主（与 NAS 其他容器共享 data 目录时用），两个都填才生效 |
| `RUN_AS_ROOT` | 空 | 服务进程以 root 运行（跳过降权）。绿联 upk 包内已内置，普通 Docker 部署**无需设置**；仅 UGOS 向导创建的数据文件夹（000 权限位 + ACL 白名单模型）需要 |

## 数据备份

### 应用内备份（推荐）

设置页 →「数据备份」：

- **导出备份包**：一键下载 zip 全量备份（订阅、设置、上传的图片）。可选是否包含 SMTP 授权码等敏感信息
- **导入备份包**：覆盖式还原，导入前自动留档，可**一键回滚**到导入前状态
- 换设备迁移：旧实例导出 → 新实例导入，不用碰命令行

### 目录级备份

所有数据都在 `data/` 目录里（SQLite 数据库 + 上传的图片）：

- **备份**：停止容器后拷贝整个 `data/` 目录（或直接拷贝，SQLite WAL 模式下热拷贝也可接受）
- **恢复**：把备份的 `data/` 放回原位，重启容器
- **迁移**：`data/` 目录拷到新机器，`docker compose up -d` 即可

## 升级指南

数据（数据库 / 登录密钥 / 上传图片）全部存放在 `data/` 挂载目录里，升级只替换程序、不触碰数据，登录状态也会保留。**唯一红线：不要修改 compose 文件里 `volumes` 的映射路径**，改了路径新容器就读不到旧数据。

### Docker 部署（预构建镜像）

```bash
docker compose pull && docker compose up -d
```

本地构建方式则执行 `git pull && docker compose up -d --build`。

- v1.1.0 起已从程序层面解决 /data 权限问题：此前用 `user: "0:0"` 绕过的，建议移除该行（保留也兼容）；需与其他容器对齐属主时改用 `PUID` / `PGID`
- 绿联 UGOS 用户例外：compose 里建议保留 `user: "0:0"`，各版本 UI 对 compose 字段的解析行为不一，保留更稳妥

### 绿联 UGOS（Docker「项目」部署）

两条路径任选：

- 项目列表里的「一键更新」（镜像走南大代理时，新版本发布约 10 分钟内可检测到）
- 「项目 → 编辑」把 `image` 末尾改成新版本号（如 `:1.6.18`），保存后确认「重新部署」

验收方式一致：容器「创建时间」刷新，且网页「关于」页版本号变新。

### 绿联 UGOS（.upk 应用包）

到 Releases 下载新版本 `.upk`，在应用中心重新安装（数据文件夹选同一个即可），数据不受影响。

### 群晖 DSM

镜像仓库中拉取新版镜像，然后用新镜像重建容器，挂载目录保持不变。

## 日历订阅

设置页 → 复制「日历订阅链接」→ 在手机日历 App 中添加「订阅日历」并粘贴链接。之后每次扣费日会自动出现在手机日历里（含未来 12 个月）。

> 链接自带访问令牌，等同于密码，请勿外传。更换密码后重新生成链接即可。

## 汇率说明

- 币种覆盖：欧洲央行参考汇率所支持的 30 种货币（CNY / USD / EUR / JPY / GBP / HKD / KRW 等）
- 数据来源：[frankfurter.dev](https://frankfurter.dev)（免费、无需 API Key），原始数据来自 European Central Bank
- 主源不可达时自动切换备用源 [open.er-api.com](https://www.exchangerate-api.com)（免费、无需 API Key），无需手动干预
- 汇率缓存本地，断网时使用上次缓存，不影响基本使用
- 个别小众币种若无法折算，会明确提示"未计入统计"，不会算错账

## 安全说明

- 密码登录使用 HMAC 签名 Cookie，常数时间比较
- 上传文件仅接受 PNG / JPG / WebP（校验文件头，**拒绝 SVG** 以杜绝 XSS），单文件 ≤ 2MB
- 数据保存在本地 volume，不上传任何第三方服务（汇率 API 除外，且只发送币种代码，不包含你的任何订阅数据）

## 项目结构

```
subdeck/
├── app/            # FastAPI 后端
│   ├── main.py     # 路由与业务逻辑
│   ├── db.py       # SQLite 数据层
│   ├── auth.py     # 密码登录与签名 Cookie
│   ├── billing.py  # 账单日滚动与折算
│   ├── rates.py    # 汇率同步与缓存
│   ├── mailer.py   # 邮箱到期提醒
│   ├── backup.py   # 备份导出 / 导入 / 回滚
│   ├── ical.py     # 日历导出
│   └── currencies.py
├── static/         # 前端（原生 JS，无构建步骤）
├── run_exe.py      # Windows/macOS 一键部署包启动器
├── ugreen/         # 绿联 UGOS Pro 应用包（.upk）打包配置
├── docker-entrypoint.sh   # 入口：修数据目录权限 / 降权 / RUN_AS_ROOT 开关
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/  # 自动构建双架构镜像 / 一键部署包 / UGOS 应用包
```

## 开发与测试

```bash
pip install -r requirements.txt
AUTH_PASSWORD=test123 DATA_DIR=./data uvicorn app.main:app --port 8017
# 另开终端运行端到端测试
python3 tests/e2e.py
```

### 用户手册再生成

正式用户手册的 PDF 由脚本生成，截图素材随仓库维护（`docs/manual-shots/`，均为本地实例演示数据）：

```bash
pip install reportlab
# 依赖 Noto Serif SC 与更纱黑体，字体路径见脚本内 FONT 注册处，可按本机字体路径调整
python3 scripts/gen_user_manual.py
```

默认输出到 `docs/`，可用环境变量 `MANUAL_OUT` 指定输出目录、`MANUAL_SHOTS` 指定截图目录。

## 更新日志

完整变更记录见 [CHANGELOG.md](CHANGELOG.md)，每次发版都会更新；升级前请阅读对应版本的「升级说明」。

## 许可证

自 v1.1.0 起采用 [PolyForm Noncommercial 1.0.0](LICENSE) 授权：

- 个人学习、自部署、**非商用的二次开发与修改**：自由使用；分发时必须保留版权与许可声明（协议内置 `Required Notice` 署名链，自动指向本仓库）
- 任何商用（集成进商业产品、转售、付费托管服务等）：需**事先获得作者书面授权**
- v1.0.0 及更早版本仍按 MIT 授权（协议变更不可追溯历史版本）

© 2026 sinailurus · 源码仓库见 `Required Notice`

## 免责声明

本项目按"现状"提供，仅供个人订阅记录管理使用。扣费日与金额以各服务商实际账单为准，因依赖本工具数据导致的漏付 / 错付，作者不承担责任。
