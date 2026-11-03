# -*- coding: utf-8 -*-
"""
认证蓝图 - 登录/登出
对应文档：Web后台管理模块 → 管理员账号登录鉴权
登录成功后写入 Session（含角色），用于区分普通用户与管理员

安全说明：
- 密码仅接受哈希校验，不再兼容数据库中的明文存储
- 连续登录失败达到阈值后锁定一段时间，抵御暴力破解
- 历史格式哈希在用户成功登录后自动升级为当前 PBKDF2 格式
"""

import time
from threading import Lock

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.database import Database
from utils.helpers import verify_password, hash_password, needs_rehash
from config import LOGIN_CONFIG

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

# 固定开销的哑哈希：账号不存在时对它做一次校验，使响应时间与
# 「账号存在」路径接近，减少用户名枚举的计时差异。
# 必须是常量（模块加载时生成一次），不能在请求里现算 hash_password()，
# 否则账号不存在的请求反而更慢，造成反向泄露。
_DUMMY_HASH = hash_password('timing-equalization-dummy-value')

# ===== 登录失败计数（进程内存储）=====
# 结构：{ 标识: {'count': 失败次数, 'locked_until': 解锁时间戳} }
# 说明：单进程开发服务器下有效；若后续改用多进程 WSGI 部署，
#       应改为 Redis 等共享存储，否则各进程独立计数会削弱限制效果。
_LOGIN_ATTEMPTS = {}
_ATTEMPTS_LOCK = Lock()


def _attempt_keys() -> list:
    """
    返回本次请求需要校验与计数的限流标识（双维度）：
      1. 「用户名 + IP」—— 防止针对某一账号的定向爆破
      2. 「纯 IP」      —— 防止攻击者通过不断更换用户名绕过第 1 层
    两个维度都需通过检查，任一被锁定即拒绝登录。
    """
    username = (request.form.get('username') or '').strip().lower()
    ip = request.remote_addr or 'unknown'
    return [f"{username}|{ip}", f"ip|{ip}"]


def _is_locked(key: str) -> tuple:
    """
    检查是否处于锁定期，返回 (是否锁定, 剩余秒数)

    注意：locked_until 为 0 表示「正在累计失败次数但尚未触发锁定」，
    这类记录必须保留，否则计数器永远无法达到阈值。
    只有 locked_until > 0 且已过期时，才清除记录并重新开始计数。
    """
    with _ATTEMPTS_LOCK:
        rec = _LOGIN_ATTEMPTS.get(key)
        if not rec:
            return False, 0
        locked_until = rec.get('locked_until', 0)
        if not locked_until:
            # 尚未触发锁定，保留失败计数
            return False, 0
        now = time.time()
        if now < locked_until:
            return True, int(locked_until - now)
        # 锁定期已过，清除记录并重新开始计数
        _LOGIN_ATTEMPTS.pop(key, None)
        return False, 0


def _record_failure(key: str) -> None:
    """记录一次登录失败，达到阈值则触发锁定"""
    max_attempts = LOGIN_CONFIG['MAX_FAILED_ATTEMPTS']
    lockout = LOGIN_CONFIG['LOCKOUT_SECONDS']
    with _ATTEMPTS_LOCK:
        rec = _LOGIN_ATTEMPTS.get(key)
        if not rec:
            rec = {'count': 0, 'locked_until': 0}
            _LOGIN_ATTEMPTS[key] = rec
        rec['count'] += 1
        rec['last_seen'] = time.time()
        if rec['count'] >= max_attempts:
            rec['locked_until'] = time.time() + lockout
            rec['count'] = 0   # 锁定后重新计数


def _record_failure_multi(keys: list) -> None:
    """对多个限流维度同时记录一次失败（一次加锁，保证原子性）"""
    max_attempts = LOGIN_CONFIG['MAX_FAILED_ATTEMPTS']
    lockout = LOGIN_CONFIG['LOCKOUT_SECONDS']
    now = time.time()
    with _ATTEMPTS_LOCK:
        for key in keys:
            rec = _LOGIN_ATTEMPTS.get(key)
            if not rec:
                rec = {'count': 0, 'locked_until': 0}
                _LOGIN_ATTEMPTS[key] = rec
            rec['count'] += 1
            rec['last_seen'] = now
            if rec['count'] >= max_attempts:
                rec['locked_until'] = now + lockout
                rec['count'] = 0


def _clear_failures(key: str) -> None:
    """登录成功后清除该标识的失败计数（仅清除本人，不影响其他标识）"""
    with _ATTEMPTS_LOCK:
        _LOGIN_ATTEMPTS.pop(key, None)


def _cleanup_stale() -> None:
    """
    清理长时间无活动的计数记录，防止内存无限增长。

    仅依据 last_seen 判断陈旧记录，不使用 locked_until，
    否则会把「正在累计但尚未锁定」的记录一并清除，
    导致任何一次成功登录都能顺带清空他人的爆破计数（绕过防护）。
    """
    threshold = time.time() - max(LOGIN_CONFIG['LOCKOUT_SECONDS'], 60) * 4
    with _ATTEMPTS_LOCK:
        stale = [k for k, v in _LOGIN_ATTEMPTS.items()
                 if v.get('last_seen', 0) < threshold]
        for k in stale:
            _LOGIN_ATTEMPTS.pop(k, None)


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

        # ===== 暴力破解防护（双维度：用户名+IP、纯IP）=====
        keys = _attempt_keys()
        for k in keys:
            locked, remain = _is_locked(k)
            if locked:
                flash(f'登录失败次数过多，请在 {remain} 秒后重试', 'danger')
                return render_template('login.html'), 429

        # 查询数据库校验账号
        user = Database.execute_one(
            "SELECT * FROM admin_user WHERE username = %s",
            (username,)
        )

        # ===== 密码校验 =====
        # 仅接受哈希校验。不再保留「数据库中存明文也能登录」的兜底分支，
        # 因为该分支会让明文密码成为有效凭据，且无法察觉密码未加密。
        password_ok = bool(user) and verify_password(password, user['password'])

        # 账号不存在时，对一个预先生成的固定哈希做一次等价开销的校验，
        # 使响应时间与「账号存在」的路径接近，减少用户名枚举的计时差异。
        # 注意：这里必须复用常量哈希，绝不能调用 hash_password()——
        # 后者含 20 万次迭代，会让「账号不存在」反而明显更慢，造成反向泄露。
        if not user:
            verify_password(password, _DUMMY_HASH)

        if user and password_ok:
            # 历史格式哈希自动升级为 PBKDF2（用户无感知）
            if needs_rehash(user['password']):
                Database.execute_update(
                    "UPDATE admin_user SET password = %s WHERE id = %s",
                    (hash_password(password), user['id'])
                )
                print(f"[安全] 账号 {username} 的密码哈希已升级为 PBKDF2 格式")

            for k in keys:
                _clear_failures(k)
            _cleanup_stale()

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

        _record_failure_multi(keys)
        # 统一提示，不区分「账号不存在」与「密码错误」，避免用户名枚举
        flash('用户名或密码错误', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """登出：清除Session"""
    session.clear()
    return redirect(url_for('auth.login'))