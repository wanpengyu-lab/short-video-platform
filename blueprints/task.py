# -*- coding: utf-8 -*-
"""
采集任务管理蓝图
对应文档：
  - Web后台管理模块：采集任务启停控制
  - 前端页面：采集任务管理页面（任务列表 + 启动/停止按钮 + 状态展示）
权限说明：采集任务管理仅限管理员使用，普通用户无权限访问
"""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from functools import wraps
from models.database import Database
from services.task_scheduler import TaskScheduler

task_bp = Blueprint('task', __name__)

# 全局调度器实例
scheduler = TaskScheduler()


def admin_required(f):
    """管理员权限校验装饰器：未登录跳登录页，普通用户拒绝访问"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_login'):
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('权限不足：采集任务管理仅限管理员使用', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@task_bp.route('/tasks')
@admin_required
def task_list():
    """
    采集任务管理页面
    展示所有任务列表，包含实时状态、上次执行时间
    提供"启动/停止"操作按钮
    """
    tasks = Database.execute_query(
        "SELECT * FROM crawl_task ORDER BY created_at DESC"
    )
    return render_template('task_manage.html', tasks=tasks or [])


@task_bp.route('/tasks/start/<int:task_id>', methods=['POST'])
@admin_required
def start_task(task_id):
    """
    启动采集任务
    1. 更新数据库状态为"运行"
    2. 在调度器中注册定时任务
    """
    task = Database.execute_one("SELECT * FROM crawl_task WHERE id = %s", (task_id,))
    if not task:
        flash('任务不存在', 'danger')
        return redirect(url_for('task.task_list'))

    # 更新状态
    Database.execute_update(
        "UPDATE crawl_task SET status = '运行' WHERE id = %s", (task_id,)
    )

    # 注册定时任务
    scheduler.add_job(task)
    flash(f'任务 [{task["task_name"]}] 已启动', 'success')
    return redirect(url_for('task.task_list'))


@task_bp.route('/tasks/stop/<int:task_id>', methods=['POST'])
@admin_required
def stop_task(task_id):
    """
    停止采集任务
    1. 更新数据库状态为"停止"
    2. 从调度器中移除任务
    """
    task = Database.execute_one("SELECT * FROM crawl_task WHERE id = %s", (task_id,))
    if not task:
        flash('任务不存在', 'danger')
        return redirect(url_for('task.task_list'))

    # 更新状态
    Database.execute_update(
        "UPDATE crawl_task SET status = '停止' WHERE id = %s", (task_id,)
    )

    # 移除定时任务
    scheduler.remove_job(task_id)
    flash(f'任务 [{task["task_name"]}] 已停止', 'success')
    return redirect(url_for('task.task_list'))


@task_bp.route('/tasks/add', methods=['POST'])
@admin_required
def add_task():
    """新增采集任务"""
    task_name = request.form.get('task_name', '').strip()
    target_url = request.form.get('target_url', '').strip()
    cron_rule = request.form.get('cron_rule', '0 */2 * * *').strip()

    if not task_name or not target_url:
        flash('任务名称和目标链接不能为空', 'danger')
        return redirect(url_for('task.task_list'))

    Database.execute_insert("""
        INSERT INTO crawl_task (task_name, target_url, status, cron_rule)
        VALUES (%s, %s, '停止', %s)
    """, (task_name, target_url, cron_rule))

    flash(f'任务 [{task_name}] 已创建', 'success')
    return redirect(url_for('task.task_list'))


@task_bp.route('/tasks/delete/<int:task_id>', methods=['POST'])
@admin_required
def delete_task(task_id):
    """删除采集任务"""
    # 先停止再删除
    scheduler.remove_job(task_id)
    Database.execute_update("DELETE FROM crawl_task WHERE id = %s", (task_id,))
    flash('任务已删除', 'success')
    return redirect(url_for('task.task_list'))


@task_bp.route('/tasks/run_now/<int:task_id>', methods=['POST'])
@admin_required
def run_now(task_id):
    """
    手动立即执行一次采集任务
    对应文档：管理员可控制采集任务启停
    """
    task = Database.execute_one("SELECT * FROM crawl_task WHERE id = %s", (task_id,))
    if not task:
        flash('任务不存在', 'danger')
        return redirect(url_for('task.task_list'))

    # 立即执行采集（非交互模式：Cookie 有效则采集，失效则跳过不阻塞）
    count = 0
    target_url = task['target_url']

    # 平台判断：当前已实现抖音热榜爬虫，其他平台提示暂不支持
    if 'douyin.com' in target_url:
        from services.douyin_crawler import DouyinCrawler
        crawler = DouyinCrawler(headless=False, interactive=False)
        try:
            count = crawler.crawl_and_save(target_url)
        finally:
            crawler.close()
    else:
        flash(f'暂不支持该平台采集：{target_url}', 'danger')
        return redirect(url_for('task.task_list'))

    # 更新上次执行时间
    Database.execute_update(
        "UPDATE crawl_task SET last_run = NOW() WHERE id = %s", (task_id,)
    )

    flash(f'任务 [{task["task_name"]}] 执行完成，采集 {count} 条数据', 'success')
    return redirect(url_for('task.task_list'))