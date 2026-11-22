# SubDeck 用户协议 / User Agreement

**生效及更新日期 / Effective and last updated: 2026-11-20**（适用 v1.6.16 及之后版本）

## 1. 服务说明 / Service Description

SubDeck 是开源自部署的订阅管理工具，用于记录个人会员、订阅与定期账单，自动滚动扣费日、
多币种汇率折算、支出统计，并可选提供日历订阅与邮箱提醒。所有数据保存在部署者自己的
服务器或 NAS 上，SubDeck 项目方不运营任何云端服务，与任何订阅服务商不存在官方授权、
合作或隶属关系。

SubDeck is a self-hosted, open-source subscription manager for tracking memberships,
recurring bills and spending. All data stays on the deployer's own server or NAS.
The project operator runs no cloud service and is not affiliated with any subscription provider.

## 2. 使用条件 / Acceptable Use

用户应在自己拥有或获授权使用的设备与网络环境中部署和使用 SubDeck，不得利用本工具
存储违法内容或用于商业代记账等营利用途（商用授权见第 5 条）。实例暴露公网时，部署者
应设置访问密码并妥善保管服务器凭据；将实例分享给家人朋友使用时，部署者对实例数据
与访问控制负责。

Deploy and use SubDeck only on devices and networks you own or are authorized to use.
Do not store unlawful content or use it for commercial bookkeeping services (see §5).
When exposing the instance to the public internet, the deployer must set an access
password and safeguard server credentials.

## 3. 数据与备份责任 / Data and Backup Responsibility

所有业务数据保存在部署者指定的 `data/` 目录（SQLite 数据库 + 图片文件）。删除该目录
即物理删除全部数据且无法恢复。备份、迁移与保留期限完全由部署者自行决定与执行；
因未备份、误删、磁盘故障或升级操作不当造成的数据丢失，SubDeck 项目方无法恢复也不承担责任。

升级版本前请阅读对应版本的升级说明，且不要修改 compose 文件中 `volumes` 的映射路径，
否则新容器将读不到旧数据。

All data lives in the deployer-designated `data/` directory; deleting it is irreversible.
Backups, migration and retention are solely the deployer's responsibility. The SubDeck
project cannot recover data lost to missing backups, misdeletion, disk failure or
improper upgrades. Read the upgrade notes before updating, and never change the
`volumes` mapping paths in your compose file.

## 4. 第三方服务 / Third-Party Services

SubDeck 仅在以下场景与第三方发生网络交互，且不发送任何订阅内容：

- **汇率折算**（可选）：向 frankfurter.dev（主）与 open.er-api.com（备用）请求汇率，只发送币种代码；断网时使用本地缓存。
- **邮箱提醒**（可选）：凭部署者自行配置的 SMTP 信息向邮箱服务商发送提醒邮件。
- **日历订阅**（可选）：手机日历 App 凭订阅链接拉取 .ics 内容，链接与令牌等同密码，请勿外传。

SubDeck 不接入任何广告、统计或遥测 SDK。详见《隐私政策》（仓库 `static/privacy-policy.html`，
应用内可通过 `/assets/privacy-policy.html` 访问）。

SubDeck talks to third parties only for optional exchange-rate lookup (currency codes
only), optional SMTP reminders, and optional calendar subscriptions. No ads, analytics
or telemetry SDKs are included. See the Privacy Policy for details.

## 5. 开源许可与商用限制 / License and Commercial Use

自 v1.1.0 起本项目依据 [PolyForm Noncommercial 1.0.0](LICENSE) 授权：个人学习、自部署与
非商用二次开发可自由使用；任何商用（集成进商业产品、转售、付费托管服务等）需事先获得
作者书面授权。v1.0.0 及更早版本仍按 MIT 授权。使用本项目即表示接受该许可条款。

From v1.1.0 the project is licensed under PolyForm Noncommercial 1.0.0: personal,
noncommercial use and modification are free; any commercial use requires prior written
permission from the author. Versions up to v1.0.0 remain MIT-licensed.

## 6. 免责声明 / Disclaimer

在适用法律允许的最大范围内，软件按"现状"提供，不承诺适用于所有设备、网络环境或
NAS 机型。扣费日、金额与提醒均以各服务商实际账单为准；因依赖本工具数据导致的漏付、
错付或其他损失，作者不承担责任。

The software is provided "as is", to the fullest extent permitted by law, without
warranty that it will work on every device, NAS model or network environment. Billing
dates and amounts are subject to your providers' actual invoices; the author is not
liable for missed or incorrect payments based on data in this tool.

## 7. 联系方式 / Contact

源代码、许可证、隐私政策和问题反馈入口位于 GitHub 项目主页：
<https://github.com/sinailurus/subdeck>
