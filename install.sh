#!/usr/bin/env bash
# SubDeck 云服务器一键安装脚本
#
# 适用环境：任意 x86_64 云主机 / VPS（Ubuntu 22.04/24.04 或 Debian 12），
# 包括但不限于腾讯云轻量、阿里云轻量、华为云、海外 VPS。在服务器网页终端或 SSH 里执行：
#
#   curl -fsSL https://cdn.jsdelivr.net/gh/sinailurus/subdeck@main/install.sh | bash
#
# 可选参数（通过 bash -s -- 传入）：
#   --port 8300          宿主机端口（默认 8300）
#   --password xxxxx     访问密码（默认自动生成 16 位随机密码）
#   --dir /opt/subdeck   安装目录（默认 /opt/subdeck，数据也在其中）
#
# 脚本会：安装 Docker（如缺失）→ 写入 .env 与 docker-compose.yml → 拉取镜像并启动。
# 访问密码不设弱默认值：不指定就随机生成，不允许留空（公网无密码 = 任何人可读写数据）。
set -euo pipefail

PORT="8300"
PASSWORD=""
DIR="/opt/subdeck"
IMAGE_CN="ghcr.nju.edu.cn/sinailurus/subdeck:latest"
IMAGE_INTL="ghcr.io/sinailurus/subdeck:latest"

PW_SET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --password) PASSWORD="$2"; PW_SET=1; shift 2 ;;
    --dir) DIR="$2"; shift 2 ;;
    *) echo "未知参数：$1"; exit 1 ;;
  esac
done

# ---------- 环境检查 ----------
if [ "$(id -u)" -ne 0 ]; then
  echo "错误：请用 root 运行（各家云控制台的网页终端一般默认 root，否则先 sudo -i）。"
  exit 1
fi

case "$PORT" in
  ''|*[!0-9]*) echo "错误：端口必须是数字"; exit 1 ;;
esac
if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  echo "错误：端口范围 1-65535"; exit 1
fi
if [ "$PORT" -eq 22 ]; then
  echo "错误：22 是 SSH 端口，不能占用"; exit 1
fi

# 部分精简系统镜像可能缺 curl / ss，先补齐
if ! command -v curl >/dev/null 2>&1; then
  apt-get update -y && apt-get install -y curl
fi
command -v ss >/dev/null 2>&1 || apt-get install -y iproute2

if command -v ss >/dev/null 2>&1 \
  && [ -n "$(ss -tln 2>/dev/null | awk '{print $4}' | grep -E ":${PORT}$" | head -n1)" ]; then
  echo "错误：端口 ${PORT} 已被占用，请换一个（--port 其他数字）"; exit 1
fi

if [ -z "$PASSWORD" ]; then
  PASSWORD=$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 16 || true)
  if [ "${#PASSWORD}" -lt 16 ]; then
    PASSWORD=$(openssl rand -hex 12 2>/dev/null || head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')
  fi
fi

# ---------- 安装 Docker（如缺失）----------
if ! command -v docker >/dev/null 2>&1; then
  echo "==> 未检测到 Docker，开始安装（Ubuntu/Debian 走 apt，约 1-3 分钟）..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y docker.io || curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

COMPOSE="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  if docker-compose version >/dev/null 2>&1; then
    COMPOSE="docker-compose"
  else
    echo "==> 缺少 Docker Compose 插件，尝试安装..."
    apt-get install -y docker-compose-v2 || apt-get install -y docker-compose-plugin
    COMPOSE="docker compose"
  fi
fi

# ---------- 写入配置 ----------
mkdir -p "$DIR"
cd "$DIR"

# 已装过则保留旧密码，避免重装时把密码换掉导致用户找不到登录口
if [ -f .env ] && [ "$PW_SET" -eq 0 ]; then
  OLD_PW=$(grep -E '^AUTH_PASSWORD=' .env | cut -d= -f2- || true)
  if [ -n "$OLD_PW" ]; then
    PASSWORD="$OLD_PW"
    echo "==> 检测到已有配置，沿用原访问密码。"
  fi
fi

cat > .env <<EOF
AUTH_PASSWORD=${PASSWORD}
TZ=Asia/Shanghai
SUBDECK_PORT=${PORT}
SUBDECK_DATA=./data
SUBDECK_IMAGE=${IMAGE_CN}
EOF
chmod 600 .env

cat > docker-compose.yml <<'EOF'
# SubDeck 云服务器部署（由 install.sh 生成）
# 数据在 ./data 目录；升级：docker compose pull && docker compose up -d
services:
  subdeck:
    image: ${SUBDECK_IMAGE:-ghcr.nju.edu.cn/sinailurus/subdeck:latest}
    container_name: subdeck
    restart: unless-stopped
    user: "0:0"            # 修权限必需，勿删（服务进程自动降权运行）
    ports:
      - "${SUBDECK_PORT:-8300}:8000"
    environment:
      - TZ=${TZ:-Asia/Shanghai}
      - AUTH_PASSWORD=${AUTH_PASSWORD:?请在 .env 中设置 AUTH_PASSWORD}
      - DATA_DIR=/data
    volumes:
      - ${SUBDECK_DATA:-./data}:/data
EOF

# ---------- 拉镜像并启动 ----------
echo "==> 拉取镜像（国内走南大中转，失败自动切官方源）..."
if ! docker pull "$IMAGE_CN"; then
  echo "==> 南大中转拉取失败，改用官方源 ghcr.io ..."
  sed -i "s|^SUBDECK_IMAGE=.*|SUBDECK_IMAGE=${IMAGE_INTL}|" .env
fi

$COMPOSE up -d

# ---------- 健康检查 ----------
echo "==> 等待服务就绪..."
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    OK=1; break
  fi
  sleep 2
done

SERVER_IP=$(curl -fsS --max-time 5 https://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}')

echo
echo "=============================================="
if [ "${OK:-0}" = "1" ]; then
  echo "SubDeck 安装完成！"
else
  echo "服务已启动但健康检查未通过，请运行 docker logs subdeck 查看原因"
fi
echo
echo "访问地址：http://${SERVER_IP}:${PORT}"
echo "访问密码：${PASSWORD}"
echo "（密码保存在 ${DIR}/.env，请立即抄到密码管理器里，此页不会再次完整显示）"
echo
echo "重要：现在就去控制台放行端口（防火墙/安全组），否则外网访问不了！"
echo "  示范（腾讯云轻量）：控制台 → 轻量应用服务器 → 防火墙 → 添加规则"
echo "  其他云大同小异：阿里云轻量「防火墙」、ECS/华为云「安全组」、海外 VPS 看其防火墙面板"
echo "  规则内容：协议 TCP，端口 ${PORT}，来源 0.0.0.0/0"
echo
echo "----------------------------------------------"
echo "安全须知（部署者必读，详见仓库 docs/云服务器一键部署.md）："
echo "  1. 访问走 HTTP 明文：密码和数据在公网未加密传输，介意请自行配域名+HTTPS"
echo "     （大陆服务器绑域名需 ICP 备案；用 IP:端口 访问不需要备案）"
echo "  2. 密码是唯一防线：无二次验证，泄露即数据泄露，勿用弱密码"
echo "  3. 数据在 ${DIR}/data：退订/重装服务器前先备份并自行清空该目录"
echo "  4. 定期升级与备份：docker compose pull && docker compose up -d；备份 data/ 目录"
echo "=============================================="
