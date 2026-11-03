# -*- coding: utf-8 -*-
"""
可视化图表蓝图
对应文档：
  - 可视化分析模块：Pyecharts 柱状图/折线图/词云图
  - 前端页面：可视化图表页面（分区块展示，图表渲染与自适应）
权限说明：图表面向普通浏览用户开放，无需登录即可查看
"""

from flask import Blueprint, render_template, request
from services.charts import ChartService

chart_bp = Blueprint('chart', __name__)


@chart_bp.route('/charts')
def charts_page():
    """
    可视化图表页面
    分区块展示：柱状图、折线图、词云图
    Pyecharts 生成图表后通过 render_embed() 输出 HTML 片段嵌入页面
    """
    # 获取用户选择的排序维度（默认点赞数）
    order_by = request.args.get('order_by', 'like_count')

    # 柱状图：Top10 热度排行
    bar_chart = ChartService.get_top10_bar(order_by=order_by)

    # 折线图：近30天趋势
    line_chart = ChartService.get_trend_line(days=30)

    # 词云图：标题高频词
    wordcloud = ChartService.get_wordcloud(source='title')

    # 评论词云（如有评论数据）
    comment_wc = ChartService.get_wordcloud(source='comment')

    return render_template(
        'charts.html',
        bar_html=bar_chart.render_embed(),
        line_html=line_chart.render_embed(),
        wordcloud_html=wordcloud.render_embed(),
        comment_wc_html=comment_wc.render_embed(),
        order_by=order_by,
        # 注入 Pyecharts 所需的 JS 依赖
        bar_js=bar_chart.load_javascript(),
        line_js=line_chart.load_javascript(),
        wc_js=wordcloud.load_javascript(),
    )