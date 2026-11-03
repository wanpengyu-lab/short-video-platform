# -*- coding: utf-8 -*-
"""
项目配置文件
所有敏感信息从环境变量或 .env 文件读取，不硬编码在代码中
"""

import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env（该文件已被 .gitignore 排除，不会上传）
load_dotenv()


def _env(key, default=None):
    """读取环境变量"""
    return os.environ.get(key, default)


# ========== 数据库配置 ==========
DB_CONFIG = {
    'host': _env('DB_HOST', 'localhost'),
    'port': int(_env('DB_PORT', '3306')),
    'user': _env('DB_USER', 'root'),
    'password': _env('DB_PASSWORD', ''),      # 从环境变量读取，不再硬编码
    'database': _env('DB_NAME', 'short_video'),
    'charset': 'utf8mb4',
    'cursorclass': 'DictCursor'
}

SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    f"?charset={DB_CONFIG['charset']}"
)

# ========== Flask 配置 ==========
FLASK_CONFIG = {
    'SECRET_KEY': _env('SECRET_KEY', 'dev-only-insecure-key-change-me'),
    # 默认关闭调试模式。
    # debug=True 会让 Werkzeug 在出错时渲染交互式调试页，
    # 向访问者暴露栈帧、局部变量与源码，并可能提供代码执行控制台，
    # 因此仅在明确需要时通过 .env 打开。
    'DEBUG': _env('DEBUG', 'False').lower() in ('1', 'true', 'yes'),
    'SESSION_TYPE': 'filesystem',
    # Session Cookie 安全属性
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
}

# ========== Web 服务监听配置 ==========
# 默认只监听本机回环地址，避免服务被同局域网内的其他设备访问。
# 确需对外提供服务时，应在 .env 中显式设置 SERVER_HOST=0.0.0.0，
# 并优先使用生产级 WSGI 服务器（如 waitress / gunicorn）而非 Flask 开发服务器。
SERVER_CONFIG = {
    'host': _env('SERVER_HOST', '127.0.0.1'),
    'port': int(_env('SERVER_PORT', '5000')),
}

# ========== 登录安全配置 ==========
LOGIN_CONFIG = {
    'MAX_FAILED_ATTEMPTS': int(_env('LOGIN_MAX_ATTEMPTS', '5')),   # 允许的连续失败次数
    'LOCKOUT_SECONDS': int(_env('LOGIN_LOCKOUT_SECONDS', '300')),  # 锁定时长（秒）
}

# ========== 采集配置（非敏感，保留在代码中）==========
CRAWL_CONFIG = {
    'REQUEST_TIMEOUT': 10,
    'REQUEST_DELAY_MIN': 1,
    'REQUEST_DELAY_MAX': 3,
    'MAX_RETRIES': 3,
    'USER_AGENT_POOL': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0',
    ]
}

# ========== 默认账号 ==========
ADMIN_USER = {
    'username': _env('ADMIN_USERNAME', 'admin'),
    'password': _env('ADMIN_PASSWORD', 'change-me'),
    'role': 'admin'
}

NORMAL_USER = {
    'username': _env('NORMAL_USERNAME', 'user'),
    'password': _env('NORMAL_PASSWORD', 'change-me'),
    'role': 'user'
}