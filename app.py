# -*- coding: utf-8 -*-
"""
Flask 应用主工厂
对应文档：
  - Web框架：基于 Flask 搭建
  - 代码规范：严格按照 MVC/蓝图 模式组织目录
  - 注册所有蓝图、配置Session、启动调度器
  - 启动时自动完成数据库表结构迁移与默认账号初始化
"""

import hmac
import secrets

from flask import Flask, redirect, url_for, session
from flask_session import Session
from config import FLASK_CONFIG
from utils.helpers import hash_password


def _get_csrf_token() -> str:
    """
    获取当前会话的 CSRF 令牌；不存在则生成并存入 session。
    令牌与会话绑定，随用户登录状态存在，跨请求复用。
    """
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


def create_app():
    """Flask 应用工厂函数"""
    app = Flask(__name__)

    # ===== Flask 基础配置 =====
    app.secret_key = FLASK_CONFIG['SECRET_KEY']
    # 统一应用 FLASK_CONFIG 中的所有配置项（DEBUG、SESSION_* 等），
    # 避免新增配置项时遗漏手动赋值。
    for key, value in FLASK_CONFIG.items():
        app.config[key] = value

    # 初始化 Session 扩展
    Session(app)

    # ===== 注册蓝图 =====
    # 认证蓝图（登录/登出）
    from blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)

    # 仪表盘蓝图（数据总览，游客可访问）
    from blueprints.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    # 视频列表蓝图（榜单 + 查询 + 分页，游客可访问）
    from blueprints.video import video_bp
    app.register_blueprint(video_bp)

    # 可视化图表蓝图（游客可访问）
    from blueprints.chart import chart_bp
    app.register_blueprint(chart_bp)

    # 采集任务管理蓝图（仅管理员）
    from blueprints.task import task_bp
    app.register_blueprint(task_bp)

    # ===== 根路由重定向 =====
    @app.route('/')
    def root_redirect():
        """未登录也允许访问数据总览"""
        return redirect(url_for('dashboard.index'))

    # ===== 全局模板上下文（顶栏显示当前日期 + CSRF令牌）=====
    @app.context_processor
    def inject_globals():
        from datetime import datetime
        wk = {'Monday': '星期一', 'Tuesday': '星期二', 'Wednesday': '星期三',
              'Thursday': '星期四', 'Friday': '星期五', 'Saturday': '星期六',
              'Sunday': '星期日'}
        d = datetime.now()
        return {
            'now_str': d.strftime('%Y年%m月%d日 ') + wk.get(d.strftime('%A'), ''),
            'csrf_token': _get_csrf_token(),
        }

    # ===== CSRF 防护：校验所有状态变更请求 =====
    @app.before_request
    def _protect_csrf():
        """
        对 POST / PUT / PATCH / DELETE 请求校验 CSRF 令牌，
        防止第三方站点利用用户已登录的会话伪造提交（如删除视频、启停采集任务）。

        令牌来源优先级：表单字段 csrf_token > 请求头 X-CSRFToken。
        使用 compare_digest 做定长时间比较，避免计时侧信道。
        """
        from flask import request, abort
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return
        # 只校验 HTML 表单提交；采集器等内部调用不带表单，跳过
        if request.is_json:
            return
        expected = _get_csrf_token()
        supplied = (request.form.get('csrf_token')
                    or request.headers.get('X-CSRFToken') or '')
        if not supplied or not hmac.compare_digest(supplied, expected):
            abort(400, description='CSRF 令牌校验失败，请刷新页面后重试')

    # ===== 初始化数据库结构迁移与默认账号 =====
    with app.app_context():
        _init_database()

    # ===== 启动定时任务调度器 =====
    from blueprints.task import scheduler
    scheduler.start()

    return app


def _init_database():
    """
    数据库初始化与自动迁移：
    1. 检查 admin_user 表是否存在 role 字段，不存在则自动添加
    2. 确保管理员账号存在且 role=admin（用户名/密码取自环境变量或 .env）
    3. 确保普通用户账号存在且 role=user（用户名/密码取自环境变量或 .env）
    4. 明文密码自动升级为加密存储
    """
    from config import ADMIN_USER, NORMAL_USER
    from models.database import Database

    try:
        # ===== 第1步：检查 role 字段是否存在（兼容旧表结构自动迁移）=====
        columns = Database.execute_query("SHOW COLUMNS FROM admin_user")
        col_names = [c['Field'] for c in columns] if columns else []
        if 'role' not in col_names:
            Database.execute_update(
                "ALTER TABLE admin_user ADD COLUMN role VARCHAR(20) DEFAULT 'user' COMMENT '角色'"
            )
            print("[初始化] 已自动为 admin_user 表添加 role 字段")

        # ===== 第2步：确保管理员账号存在且角色正确 =====
        _ensure_user(ADMIN_USER)

        # ===== 第3步：确保普通用户账号存在且角色正确 =====
        _ensure_user(NORMAL_USER)

        print(f"[初始化] 账号初始化完成（管理员: {ADMIN_USER['username']}，普通用户: {NORMAL_USER['username']}；密码取自 .env）")
    except Exception as e:
        print(f"[初始化] 数据库初始化失败: {e}")
        print("[提示] 请先执行 init_db.sql 创建数据库和表结构")


def _ensure_user(user_cfg: dict):
    """确保指定账号存在、角色正确、密码为加密格式"""
    from models.database import Database

    username = user_cfg['username']
    password = user_cfg['password']
    role = user_cfg['role']

    user = Database.execute_one(
        "SELECT * FROM admin_user WHERE username = %s", (username,)
    )

    if not user:
        # 账号不存在 → 创建（密码加密存储）
        encrypted_pwd = hash_password(password)
        Database.execute_insert(
            "INSERT INTO admin_user (username, password, role) VALUES (%s, %s, %s)",
            (username, encrypted_pwd, role)
        )
        print(f"[初始化] 账号已创建: {username} (角色: {role})")
    else:
        # 账号存在 → 确保角色正确
        if user.get('role') != role:
            Database.execute_update(
                "UPDATE admin_user SET role = %s WHERE username = %s",
                (role, username)
            )
            print(f"[初始化] 账号角色已更新: {username} → {role}")

        # 明文密码升级为加密格式
        if user['password'] == password:
            encrypted_pwd = hash_password(password)
            Database.execute_update(
                "UPDATE admin_user SET password = %s WHERE username = %s",
                (encrypted_pwd, username)
            )
            print(f"[初始化] 账号密码已加密更新: {username}")