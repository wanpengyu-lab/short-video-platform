# -*- coding: utf-8 -*-
"""
视频列表蓝图 - 榜单列表 + 条件查询 + 分页
对应文档：
  - 条件查询模块：按关键词/时间/热度组合检索
  - 前端页面：榜单列表页面（顶部查询表单 + 数据表格 + 底部分页）
权限说明：
  - 榜单浏览/条件查询：普通浏览用户（含未登录游客）均可访问
  - 编辑/删除历史数据：仅管理员
"""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, abort
from functools import wraps
from models.database import Database
from utils.helpers import paginate

video_bp = Blueprint('video', __name__)


def admin_required(f):
    """管理员权限校验装饰器：未登录跳登录页，普通用户拒绝访问"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_login'):
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('权限不足：该操作仅限管理员使用', 'danger')
            return redirect(url_for('video.video_list'))
        return f(*args, **kwargs)
    return decorated


@video_bp.route('/videos')
def video_list():
    """
    榜单列表页面（普通用户与游客均可访问）
    支持条件查询：
      - keyword: 关键词（模糊匹配标题/作者昵称）
      - start_date / end_date: 发布时间区间
      - order_by: 热度排序字段（play_count / like_count / comment_count）
      - order_dir: 排序方向（asc / desc）
    支持分页：page 参数控制当前页
    """
    # 获取查询参数
    keyword = request.args.get('keyword', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    order_by = request.args.get('order_by', 'like_count').strip()
    order_dir = request.args.get('order_dir', 'desc').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # ===== 动态拼接SQL查询条件 =====
    where_clauses = []
    params = []

    # 关键词模糊匹配（标题 或 作者昵称）
    if keyword:
        where_clauses.append(
            "(v.title LIKE %s OR a.nickname LIKE %s)"
        )
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    # 发布时间区间
    if start_date:
        where_clauses.append("DATE(v.publish_time) >= %s")
        params.append(start_date)
    if end_date:
        where_clauses.append("DATE(v.publish_time) <= %s")
        params.append(end_date)

    # 拼接 WHERE 子句
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # 排序字段白名单校验（防SQL注入）
    valid_order_fields = ['play_count', 'like_count', 'comment_count',
                          'collect_count', 'publish_time', 'crawl_time']
    if order_by not in valid_order_fields:
        order_by = 'like_count'
    if order_dir not in ('asc', 'desc'):
        order_dir = 'desc'

    # ===== 查询总数（用于分页）=====
    count_sql = f"""
        SELECT COUNT(*) as total
        FROM video_info v
        LEFT JOIN author_info a ON v.author_id = a.id
        {where_sql}
    """
    count_result = Database.execute_one(count_sql, tuple(params) if params else None)
    total = count_result['total'] if count_result else 0

    # ===== 分页计算 =====
    page_info = paginate(total, page, per_page)

    # ===== 查询当前页数据 =====
    data_sql = f"""
        SELECT v.*, a.nickname as author_name, a.avatar_url
        FROM video_info v
        LEFT JOIN author_info a ON v.author_id = a.id
        {where_sql}
        ORDER BY v.{order_by} {order_dir}
        LIMIT %s OFFSET %s
    """
    data_params = list(params)
    data_params.extend([per_page, page_info['offset']])
    videos = Database.execute_query(data_sql, tuple(data_params))

    return render_template(
        'video_list.html',
        videos=videos or [],
        page_info=page_info,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        order_by=order_by,
        order_dir=order_dir,
    )


@video_bp.route('/videos/edit/<int:video_id>', methods=['GET', 'POST'])
@admin_required
def edit_video(video_id):
    """
    编辑视频数据（仅管理员权限）
    对应文档：历史数据管理（增删改查）→ 改
    """
    if request.method == 'POST':
        # 获取表单数据
        title = request.form.get('title', '').strip()
        play_count = request.form.get('play_count', 0, type=int)
        like_count = request.form.get('like_count', 0, type=int)
        comment_count = request.form.get('comment_count', 0, type=int)
        collect_count = request.form.get('collect_count', 0, type=int)

        # 更新数据库
        Database.execute_update("""
            UPDATE video_info
            SET title=%s, play_count=%s, like_count=%s,
                comment_count=%s, collect_count=%s
            WHERE id=%s
        """, (title, play_count, like_count, comment_count, collect_count, video_id))

        flash('数据修改成功', 'success')
        return redirect(url_for('video.video_list'))

    # GET: 查询单条数据，渲染编辑表单
    video = Database.execute_one("SELECT * FROM video_info WHERE id = %s", (video_id,))
    return render_template('video_edit.html', video=video)


@video_bp.route('/videos/delete/<int:video_id>', methods=['POST'])
@admin_required
def delete_video(video_id):
    """
    删除视频数据（仅管理员权限）
    对应文档：历史数据管理（增删改查）→ 删
    """
    Database.execute_update("DELETE FROM video_info WHERE id = %s", (video_id,))
    flash('数据已删除', 'success')
    return redirect(url_for('video.video_list'))