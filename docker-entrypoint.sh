#!/bin/sh
# SubDeck 入口脚本：先以 root 修复数据目录属主（治 NAS bind-mount 权限问题），再降权为 appuser 运行。
# 可选环境变量 PUID/PGID：与 NAS 上其他容器共享数据目录时对齐属主（两个都填才生效）。
set -e

if [ "$(id -u)" = "0" ]; then
  # UGOS Pro（绿联应用包）专用开关：upk 的数据文件夹是「权限位 000 + ACL 白名单」
  # 模型，且容器重建时 UGOS 会重刷策略，降权用户无法稳定写入（真机实测两种死法：
  # /data/logos PermissionError 与 sqlite unable to open database file）。
  # root 持 CAP_DAC_OVERRIDE，无视权限位/ACL mask/文件属主，直接运行最稳。
  if [ "$RUN_AS_ROOT" = "1" ]; then
    exec "$@"
  fi
  if [ -n "$PUID" ] && [ -n "$PGID" ]; then
    getent group "$PGID" >/dev/null 2>&1 || groupadd -g "$PGID" appdata
    usermod -o -u "$PUID" -g "$PGID" appuser
  fi
  chown -R appuser:appuser /data
  exec gosu appuser "$@"
fi

# 非 root 启动：先自检数据目录可写性。不可写时输出明确指引后退出，
# 避免应用层抛出晦涩的 PermissionError 并陷入重启循环。
if ! touch "/data/.write-test" 2>/dev/null; then
  echo "==========================================================" >&2
  echo "SubDeck 无法写入数据目录 /data，启动终止。" >&2
  echo "" >&2
  echo "常见原因：容器以非 root 用户启动，而 /data 挂载目录属主不匹配。" >&2
  echo "（例如曾以 root 运行产生的数据文件，后来改用普通用户启动）" >&2
  echo "" >&2
  echo "解决方法：在 docker-compose.yml 的 subdeck 服务下添加一行：" >&2
  echo '    user: "0:0"' >&2
  echo "然后重建容器。程序会用 root 自动修复目录属主并降权运行，数据无损。" >&2
  echo "==========================================================" >&2
  exit 1
fi
rm -f "/data/.write-test"

# 非 root 且 /data 可写（属主恰好匹配）则直接运行
exec "$@"
