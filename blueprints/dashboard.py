# -*- coding: utf-8 -*-
"""
仪表盘蓝图 - 数据总览
对应文档：前端页面 → 数据总览仪表盘
顶部展示核心统计卡片（总视频数、总播放量等），下方展示概览性图表
说明：数据总览面向普通浏览用户开放，无需登录即可查看
"""

from flask import Blueprint, render_template
from models.database import Database

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """
    数据总览仪表盘
    查询统计数据：总视频数、总播放量、总点赞数、总作者数
    """
    # 核心统计卡片数据
    stats = {}

    # 总视频数
    result = Database.execute_one("SELECT COUNT(*) as cnt FROM video_info")
    stats['total_videos'] = result['cnt'] if result else 0

    # 总播放量
    result = Database.execute_one("SELECT SUM(play_count) as total FROM video_info")
    stats['total_plays'] = result['total'] if result and result['total'] else 0

    # 总点赞数
    result = Database.execute_one("SELECT SUM(like_count) as total FROM video_info")
    stats['total_likes'] = result['total'] if result and result['total'] else 0

    # 总评论数
    result = Database.execute_one("SELECT SUM(comment_count) as total FROM video_info")
    stats['total_comments'] = result['total'] if result and result['total'] else 0

    # 总作者数
    result = Database.execute_one("SELECT COUNT(*) as cnt FROM author_info")
    stats['total_authors'] = result['cnt'] if result else 0

    # 总收藏数
    result = Database.execute_one("SELECT SUM(collect_count) as total FROM video_info")
    stats['total_collects'] = result['total'] if result and result['total'] else 0

    # 采集任务数
    result = Database.execute_one("SELECT COUNT(*) as cnt FROM crawl_task")
    stats['total_tasks'] = result['cnt'] if result else 0

    # 运行中的任务数
    result = Database.execute_one("SELECT COUNT(*) as cnt FROM crawl_task WHERE status = '运行'")
    stats['running_tasks'] = result['cnt'] if result else 0

    return render_template('dashboard.html', stats=stats)