# -*- coding: utf-8 -*-
"""
认证蓝图 - 登录/登出
对应文档：Web后台管理模块 → 管理员账号登录鉴权
登录成功后写入 Session（含角色），用于区分普通用户与管理员
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.database import Database
from utils.helpers import verify_password

# 创建蓝图
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    登录页面
    GET  → 渲染登录表单
    POST → 校验账号密码，成功则写入Session并跳转仪表盘
    """
    # 已登录用户直接跳转
    if session.get('is_login'):
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # 表单校验
        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('login.html')

        # 查询数据库校验账号
        user = Database.execute_one(
            "SELECT * FROM admin_user WHERE username = %s",
            (username,)
        )

        # 校验密码（支持加密格式；兼容历史明文格式）
        password_ok = False
        if user:
            if verify_password(password, user['password']):
                password_ok = True
            elif user['password'] == password:
                password_ok = True

        if user and password_ok:
            # 登录成功，写入Session（含角色信息）
            session['is_login'] = True
            session['username'] = user['username']
            session['user_id'] = user['id']
            session['role'] = user.get('role', 'user')

            # 管理员跳转仪表盘并提示
            if session['role'] == 'admin':
                flash(f'欢迎回来，管理员 {user["username"]}', 'success')
            else:
                flash(f'欢迎回来，{user["username"]}（普通用户）', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('用户名或密码错误', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """登出：清除Session"""
    session.clear()
    return redirect(url_for('auth.login'))