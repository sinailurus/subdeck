# SubDeck · 订阅管理

一个自部署的订阅管理工具：记录你的各种会员 / 订阅 / 定期账单，自动滚动扣费日，到期提醒，多币种实时汇率折算，按周 / 月 / 年统计花费。

> **AIGC 声明**：本项目通过 AI 辅助（Vibe Coding）方式开发，由人类主导需求设计、功能取舍、代码审查与测试验证。

## 功能特性

- 📋 **订阅管理**：名称、金额、币种、周期（每周 / 每月 / 每季度 / 每半年 / 每年）、付款方式（自动扣费 / 手动付款）、分类、备注
- 🔄 **账单日自动滚动**：过期的扣费日自动按周期滚到下一次，永不过期
- ⏰ **待付款区**：临近扣费的订阅自动进入待付款区并高亮（天数可配置）
- 💱 **多币种 + 实时汇率**：内置 30 种常用币种，汇率自动同步（基于欧洲央行参考汇率），所有金额可折算为你习惯的基准币种
- 📊 **支出统计**：月均 / 年度支出、分类占比、即将扣费统计
- 🖼️ **Logo**：内置字母头像（自动配色），也支持上传自定义图片（PNG / JPG / WebP，≤2MB）
- 📅 **日历订阅**：一键生成 iCal 链接，账单日直接进手机自带日历 App
- 🌓 **深色模式**：跟随系统，也可手动切换
- 📱 **响应式适配**：桌面端表格 + 顶栏导航，手机/平板卡片 + 底部导航，支持"添加到主屏幕"（PWA）
- 🔒 **可选密码保护**：一行环境变量开启；纯内网使用可不开启
- 🐳 **单容器部署**：SQLite 存储，无外部依赖，数据备份 = 拷贝一个目录

## 界面预览

| 桌面端 | 手机端 |
| --- | --- |
| 表格布局 + 筛选 | 卡片布局 + 底部导航 |

## 快速开始

### 方式一：使用预构建镜像（推荐）

先发布镜像（见下方「发布你自己的镜像」），然后把 `docker-compose.yml` 里的 `image:` 改成你的镜像地址即可。

### 方式二：本地构建

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/subdeck.git
cd subdeck
cp .env.example .env        # 修改 AUTH_PASSWORD
docker compose up -d        # 默认使用 8300 端口
```

访问 `http://NAS_IP:8300`。

### 群晖 DSM（Container Manager）

1. 打开 **File Station**，在任意共享文件夹新建 `subdeck` 目录，把项目文件上传进去
2. 打开 **Container Manager** → **项目** → **新增**
3. 项目名称填 `subdeck`，路径选择刚才的 `subdeck` 文件夹，来源选「使用已有的 docker-compose.yml」
4. 完成向导，等待构建 / 拉取完成后访问 `http://NAS_IP:8300`

> ARM 架构的群晖机型请使用预构建镜像（方式一），本地构建会很慢。

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

## 数据备份

所有数据都在 `data/` 目录里（SQLite 数据库 + 上传的图片）：

- **备份**：停止容器后拷贝整个 `data/` 目录（或直接拷贝，SQLite WAL 模式下热拷贝也可接受）
- **恢复**：把备份的 `data/` 放回原位，重启容器
- **迁移**：`data/` 目录拷到新机器，`docker compose up -d`，完事

## 升级指南

已部署用户更新到新版本（数据不受影响）：

```bash
docker compose pull && docker compose up -d   # 预构建镜像方式
# 或本地构建方式：git pull && docker compose up -d --build
```

- 数据（数据库 / 登录密钥 / 上传图片）全部存放在 `data/` 挂载目录里，更新只替换容器、不触碰数据，登录状态也会保留
- **升级红线：不要修改 compose 文件里 `volumes` 的映射路径**——改了路径，新容器就读不到旧数据了
- v1.1.0 起已治本 /data 权限问题：此前用 `user: "0:0"` 绕过的，**建议移除该行**（保留也兼容）；需与其他容器对齐属主时改用 `PUID` / `PGID`
- 绿联 / 群晖图形界面：镜像仓库 → 拉取新版镜像 → 用新镜像重建容器，挂载目录保持不变

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

## 发布你自己的镜像

1. 在 GitHub 创建仓库并推送本项目
2. 仓库无需额外配置 Secrets（`GITHUB_TOKEN` 自动提供），Actions 会自动构建 `linux/amd64` + `linux/arm64` 双架构镜像并发布到 GHCR
3. 镜像地址形如 `ghcr.io/<你的用户名>/subdeck:latest`
4. 如需公开发布到 Docker Hub，可在 Actions 中追加一个 Docker Hub 的推送步骤

## 项目结构

```
subdeck/
├── app/            # FastAPI 后端
│   ├── main.py     # 路由与业务逻辑
│   ├── db.py       # SQLite 数据层
│   ├── auth.py     # 密码登录与签名 Cookie
│   ├── billing.py  # 账单日滚动与折算
│   ├── rates.py    # 汇率同步与缓存
│   ├── ical.py     # 日历导出
│   └── currencies.py
├── static/         # 前端（原生 JS，无构建步骤）
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/  # 自动构建双架构镜像
```

## 开发与测试

```bash
pip install -r requirements.txt
AUTH_PASSWORD=test123 DATA_DIR=./data uvicorn app.main:app --port 8017
# 另开终端运行端到端测试
python3 tests/e2e.py
```

## 更新日志

完整变更记录见 [CHANGELOG.md](CHANGELOG.md)，每次发版都会更新；升级前请阅读对应版本的「升级说明」。

## 许可证

自 v1.1.0 起采用 [PolyForm Noncommercial 1.0.0](LICENSE) 授权：

- 个人学习、自部署、**非商用的二次开发与修改**：自由使用；分发时必须保留版权与许可声明（协议内置 `Required Notice` 署名链，自动指向本仓库）
- 任何商用（集成进商业产品、转售、付费托管服务等）：需**事先获得作者书面授权**
- v1.0.0 及更早版本仍按 MIT 授权（协议变更不可追溯历史版本）

© 2026 COPYRIGHT_HOLDER · 源码仓库见 `Required Notice`

## 免责声明

本项目按"现状"提供，仅供个人订阅记录管理使用。扣费日与金额以各服务商实际账单为准，因依赖本工具数据导致的漏付 / 错付，作者不承担责任。
