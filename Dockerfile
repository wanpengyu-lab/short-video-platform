# ============================================================
# 短视频热门数据采集与可视化平台 - Docker 镜像
# 基于 Python 3.10 + Chrome（Selenium headless 采集）
# ============================================================

FROM python:3.10-slim

# 安装 Chrome 运行时依赖 + wget（用于下载 ChromeDriver）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg2 curl unzip \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnspr4 \
    libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    xdg-utils libu2f-udev libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Google Chrome
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/chrome.deb \
    || apt-get install -yf \
    && rm /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层加速构建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 再复制项目代码
COPY . .

# Flask Session 持久化目录（挂载为 volume）
RUN mkdir -p /app/flask_session

# 暴露端口（Gunicorn 监听）
EXPOSE 5000

# 用 Gunicorn 启动，4 个 worker
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "run:app"]
