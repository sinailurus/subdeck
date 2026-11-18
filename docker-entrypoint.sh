#!/bin/sh
# SubDeck 入口脚本：先以 root 修复数据目录属主（治 NAS bind-mount 权限问题），再降权为 appuser 运行。
# 可选环境变量 PUID/PGID：与 NAS 上其他容器共享数据目录时对齐属主（两个都填才生效）。
set -e

if [ "$(id -u)" = "0" ]; then
  if [ -n "$PUID" ] && [ -n "$PGID" ]; then
    getent group "$PGID" >/dev/null 2>&1 || groupadd -g "$PGID" appdata
    usermod -o -u "$PUID" -g "$PGID" appuser
  fi
  chown -R appuser:appuser /data
  exec gosu appuser "$@"
fi

# 非 root 启动（如手动指定 user:）则直接运行
exec "$@"
