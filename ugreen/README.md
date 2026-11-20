# SubDeck 绿联 UGOS Pro 应用包打包配置

本目录存放 SubDeck 的绿联 UGOS Pro 应用（`.upk`）打包配置，支持 `amd64` 与 `arm64` 双架构。应用基于仓库 CI 自动构建的多架构 Docker 镜像制作，应用 ID 为 `com.sinailurus.subdeck`，当前版本 `1.6.17`（构建号 `0001`）。

## 应用信息

- 开发者 / 发布者：sinailurus
- 源码：https://github.com/sinailurus/subdeck
- 许可协议：PolyForm Noncommercial 1.0.0（https://github.com/sinailurus/subdeck/blob/main/LICENSE）
- 隐私政策：https://github.com/sinailurus/subdeck/blob/main/static/privacy-policy.html
- 问题反馈：https://github.com/sinailurus/subdeck/issues

## 安装与数据文件夹

1. 从 Release 下载符合设备架构的 UPK，在 UGOS Pro 应用中心选择手动安装。
2. 在安装配置的「数据文件夹 / Data folder」中选择有读写权限的文件夹；选择共享文件夹时，先在 UGOS Pro 应用设置中授权本应用访问该目录。订阅数据库、备份与 Logo 图片缓存都保存在此处。该选项可留空；留空使用应用内置的 `./data` 目录。
3. 建议为应用选择一个专用文件夹，不要与其他应用共用。安装向导允许随时改选文件夹。
4. 安装后浏览器输入 `http://NAS的IP:8300` 访问，使用安装时设置的「网页登录密码」登录。

## 目录说明

```
ugreen/subdeck-app/
├── project.yaml                    # 应用元数据（版本、参数、中英文介绍、协议与源码链接）
└── rootfs_common/
    ├── docker-compose.yaml         # 包内编排文件（镜像 tag 与包内 tar 一致，安装不联网）
    └── icon.png                    # 应用图标（512x512）
```

`rootfs_amd64/images/` 与 `rootfs_arm64/images/` 两个目录不入库，由 CI 工作流从 GHCR 拉取对应架构镜像并导出 `subdeck-<arch>.tar` 后生成；镜像 tar 内 tag 统一为 `ghcr.io/sinailurus/subdeck:<版本>`，与 compose 中的 `image:` 一致。镜像内随附 `LICENSE` 文件（PolyForm Noncommercial 1.0.0）。

## 构建方式

在 GitHub Actions 中手动运行 **Build UGOS Pro UPK** 工作流：工作流校验版本一致性后，分别拉取该版本的 `amd64`、`arm64` 镜像并导出为 tar，使用绿联官方 `ugcli` 校验项目并生成两个 UPK 安装包，同时生成 `SHA256SUMS-UPK`；指定匹配版本的 Release tag 时自动上传到对应 Release。

本地生成的镜像归档和 UPK 文件属于构建产物，不提交到 Git 仓库。
