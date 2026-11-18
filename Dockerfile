# SubDeck 生产镜像 —— 单容器，无外部服务依赖
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    DATA_DIR=/data

# gosu 用于入口脚本降权；tzdata 用于容器内本地时区（TZ 环境变量生效）
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

# 非 root 运行；数据目录由挂载卷提供
RUN useradd --system --create-home appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /data /app

# 入口脚本：以 root 修 /data 属主（兼容 NAS bind-mount 任意 UID）后降权运行；
# 实际服务进程以 appuser 身份执行，容器默认以 root 启动仅为修权限。
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
