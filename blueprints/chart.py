# -*- coding: utf-8 -*-
"""
可视化图表蓝图
对应文档：
  - 可视化分析模块：Pyecharts 柱状图/折线图/词云图
  - 前端页面：可视化图表页面（分区块展示，图表渲染与自适应）
权限说明：图表面向普通浏览用户开放，无需登录即可查看
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from services.charts import ChartService, sanitize_order_field

chart_bp = Blueprint('chart', __name__)


@chart_bp.route('/charts')
def charts_page():
    """
    可视化图表页面
    分区块展示：柱状图、折线图、词云图
    Pyecharts 生成图表后通过 render_embed() 输出 HTML 片段嵌入页面

    安全说明：
    - order_by 为外部输入，先经白名单校验再使用，非法值回退默认字段
    - 图表生成过程整体包裹异常处理：数据库或渲染出错时返回友好提示，
      而不是把栈帧、局部变量与源码通过调试页暴露给未登录的游客
    """
    # 获取用户选择的排序维度，并立即做白名单校验（默认点赞数）
    order_by = sanitize_order_field(request.args.get('order_by', 'like_count'))

    try:
        # 柱状图：Top10 热度排行
        bar_chart = ChartService.get_top10_bar(order_by=order_by)

        # 折线图：近30天趋势
        line_chart = ChartService.get_trend_line(days=30)

        # 词云图：标题高频词
        wordcloud = ChartService.get_wordcloud(source='title')

        # 评论词云（如有评论数据）
        comment_wc = ChartService.get_wordcloud(source='comment')
    except Exception:
        # 不向前端输出任何异常细节，仅在服务端日志留痕
        import logging
        logging.getLogger(__name__).exception("图表生成失败")
        flash('图表数据加载失败，请稍后重试或检查数据库连接', 'danger')
        return redirect(url_for('dashboard.index'))

    return render_template(
        'charts.html',
        bar_html=bar_chart.render_embed(),
        line_html=line_chart.render_embed(),
        wordcloud_html=wordcloud.render_embed(),
        comment_wc_html=comment_wc.render_embed(),
        # 回传校验后的值，保证页面高亮状态与实际查询一致
        order_by=order_by,
        # 注入 Pyecharts 所需的 JS 依赖
        bar_js=bar_chart.load_javascript(),
        line_js=line_chart.load_javascript(),
        wc_js=wordcloud.load_javascript(),
    )