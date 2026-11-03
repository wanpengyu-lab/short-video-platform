#!/bin/bash
# ============================================================
# 短视频热门数据采集与可视化平台 - 一键部署脚本
# 适用于 Ubuntu/Debian 服务器
# 用法：bash deploy.sh
# ============================================================

set -e

echo "=========================================="
echo "  短视频平台 - Docker 部署脚本"
echo "=========================================="

# ---------- 1. 检查 Docker ----------
echo ""
echo "[1/6] 检查 Docker 环境..."

if ! command -v docker &> /dev/null; then
    echo "  Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo systemctl enable docker
    sudo systemctl start docker
    echo "  ✓ Docker 安装完成"
else
    echo "  ✓ Docker 已安装: $(docker --version)"
fi

# 确保 docker compose 命令可用（Docker 20.10+ 自带）
if ! docker compose version &> /dev/null; then
    echo "  ✗ docker compose 不可用，请升级 Docker 到 20.10+"
    exit 1
fi
echo "  ✓ Docker Compose 可用"

# ---------- 2. 检查 MySQL ----------
echo ""
echo "[2/6] 检查 MySQL..."

if mysql --version &> /dev/null; then
    echo "  ✓ MySQL 已安装: $(mysql --version)"
else
    echo "  MySQL 未在宿主机检测到（如果你的 MySQL 在其他机器上可忽略此提示）"
fi

# ---------- 3. 配置环境变量 ----------
echo ""
echo "[3/6] 检查 .env 配置..."

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
    echo "  .env 不存在，从模板创建..."
    cp .env.example .env

    # 自动生成 SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env

    echo ""
    echo "  ⚠️  .env 已创建但需要你手动编辑："
    echo "     nano $PROJECT_DIR/.env"
    echo "  必须修改的项："
    echo "     - DB_PASSWORD（你的 MySQL 密码）"
    echo "     - DB_HOST（如果 MySQL 在宿主机，改为 host.docker.internal）"
    echo "     - ADMIN_PASSWORD / NORMAL_PASSWORD"
    echo ""
    echo "  修改完成后重新运行此脚本。"
    exit 0
else
    echo "  ✓ .env 已存在"
fi

# ---------- 4. 初始化数据库 ----------
echo ""
echo "[4/6] 数据库初始化..."

# 从 .env 读取 MySQL 连接信息
DB_USER=$(grep -E '^DB_USER=' .env | cut -d= -f2)
DB_PASSWORD=$(grep -E '^DB_PASSWORD=' .env | cut -d= -f2)
DB_NAME=$(grep -E '^DB_NAME=' .env | cut -d= -f2)

# 尝试用宿主机 MySQL 初始化数据库
if [ -f init_db.sql ]; then
    echo "  正在执行 init_db.sql..."
    if mysql -u"$DB_USER" -p"$DB_PASSWORD" < init_db.sql 2>/dev/null; then
        echo "  ✓ 数据库初始化完成"
    else
        echo "  ⚠️  无法直接连接宿主机 MySQL，可能需要手动执行："
        echo "     mysql -u root -p < init_db.sql"
        echo "  或者在 .env 中确认 DB_PASSWORD 正确后重试"
    fi
fi

# ---------- 5. 构建 & 启动 ----------
echo ""
echo "[5/6] 构建 Docker 镜像并启动..."

echo "  正在构建镜像（首次约 3-5 分钟）..."
docker compose build

echo "  正在启动容器..."
docker compose up -d

echo "  ✓ 容器已启动"

# ---------- 6. 验证 ----------
echo ""
echo "[6/6] 验证部署..."

sleep 3

if docker compose ps | grep -q "running"; then
    echo "  ✓ 容器运行中"
else
    echo "  ✗ 容器未正常运行，查看日志："
    docker compose logs --tail=20
    exit 1
fi

# 获取服务器 IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=========================================="
echo "  ✓ 部署完成！"
echo ""
echo "  访问地址: http://$SERVER_IP"
echo "  本机测试: curl http://127.0.0.1"
echo ""
echo "  常用命令："
echo "    查看日志:   docker compose logs -f"
echo "    重启服务:   docker compose restart"
echo "    停止服务:   docker compose down"
echo "    更新代码:   git pull && docker compose up -d --build"
echo "=========================================="

# 提醒上传 Cookie
if [ ! -f douyin_cookies.pkl ]; then
    echo ""
    echo "  ⚠️  未检测到 douyin_cookies.pkl"
    echo "     爬虫需要登录态，请在本地扫码登录后上传："
    echo "     scp douyin_cookies.pkl user@$SERVER_IP:$PROJECT_DIR/"
fi
