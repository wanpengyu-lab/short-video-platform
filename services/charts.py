# -*- coding: utf-8 -*-
"""
可视化分析模块
使用 Pyecharts 生成柱状图、折线图、词云图
"""

import jieba
from collections import Counter
from pyecharts import options as opts
from pyecharts.charts import Bar, Line, WordCloud
from models.database import Database


class ChartService:
    """图表生成服务"""

    # ========== 柱状图：Top10 热度指标排行 ==========
    @staticmethod
    def get_top10_bar(order_by: str = 'like_count') -> Bar:
        """
        生成Top10视频热度柱状图
        参数：order_by - 排序字段（like_count / play_count / comment_count）
        """
        # 从数据库查询Top10数据
        sql = f"""
            SELECT v.title, v.{order_by} as count_value, a.nickname
            FROM video_info v
            LEFT JOIN author_info a ON v.author_id = a.id
            ORDER BY v.{order_by} DESC
            LIMIT 10
        """
        results = Database.execute_query(sql)

        # 提取标题和数值
        titles = [r['title'][:15] + '...' if len(r['title']) > 15 else r['title'] for r in results]
        values = [r['count_value'] for r in results]

        # 字段中文映射
        field_names = {
            'like_count': '点赞数',
            'play_count': '播放量',
            'comment_count': '评论数',
            'collect_count': '收藏数'
        }
        field_name = field_names.get(order_by, '热度')

        # 生成柱状图
        bar = (
            Bar(init_opts=opts.InitOpts(width="100%", height="420px"))
            .add_xaxis(titles)
            .add_yaxis(field_name, values, label_opts=opts.LabelOpts(position="top"))
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f"短视频 {field_name} Top10 排行"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
                yaxis_opts=opts.AxisOpts(name=field_name),
                toolbox_opts=opts.ToolboxOpts(is_show=True),
            )
            .set_colors(["#5470c6"])
        )
        return bar

    # ========== 折线图：热度趋势 ==========
    @staticmethod
    def get_trend_line(days: int = 30) -> Line:
        """
        生成近N天发布量/播放量趋势折线图
        """
        sql = """
            SELECT DATE(publish_time) as date,
                   COUNT(*) as video_count,
                   SUM(play_count) as total_plays
            FROM video_info
            WHERE publish_time >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(publish_time)
            ORDER BY date ASC
        """
        results = Database.execute_query(sql, (days,))

        dates = [str(r['date']) for r in results]
        counts = [r['video_count'] for r in results]
        plays = [int(r['total_plays'] or 0) for r in results]

        line = (
            Line(init_opts=opts.InitOpts(width="100%", height="420px"))
            .add_xaxis(dates)
            .add_yaxis(
                "发布数量",
                counts,
                linestyle_opts=opts.LineStyleOpts(width=2),
                label_opts=opts.LabelOpts(is_show=False),
            )
            .add_yaxis(
                "总播放量",
                plays,
                yaxis_index=1,
                linestyle_opts=opts.LineStyleOpts(width=2),
                label_opts=opts.LabelOpts(is_show=False),
            )
            .extend_axis(
                yaxis=opts.AxisOpts(
                    name="播放量",
                    position="right",
                    axistick_opts=opts.AxisTickOpts(is_show=True),
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f"近{days}天短视频趋势"),
                yaxis_opts=opts.AxisOpts(name="发布数量"),
                xaxis_opts=opts.AxisOpts(type_="category"),
                toolbox_opts=opts.ToolboxOpts(is_show=True),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
            )
        )
        return line

    # ========== 词云图：标题/评论高频关键词 ==========
    @staticmethod
    def get_wordcloud(source: str = 'title') -> WordCloud:
        """
        生成词云图
        参数：source - 'title'（标题词云）或 'comment'（评论词云）
        """
        if source == 'comment':
            sql = "SELECT content FROM video_comment WHERE content IS NOT NULL AND content != ''"
            results = Database.execute_query(sql)
            texts = [r['content'] for r in results]
            title = "评论高频词云"
        else:
            sql = "SELECT title FROM video_info WHERE title IS NOT NULL AND title != ''"
            results = Database.execute_query(sql)
            texts = [r['title'] for r in results]
            title = "视频标题高频词云"

        # 使用 jieba 分词
        all_words = []
        # 停用词表（可根据需要扩展）
        stop_words = {'的', '了', '是', '在', '和', '与', '这', '那', '有', '我', '你',
                      '他', '她', '它', '们', '也', '就', '都', '不', '为', '被', '把',
                      '一个', '什么', '怎么', '如何', '可以', '还是', '但是', '因为', '所以'}

        for text in texts:
            words = jieba.lcut(text)
            for word in words:
                word = word.strip()
                if len(word) >= 2 and word not in stop_words:
                    all_words.append(word)

        # 统计词频，取Top100
        word_counts = Counter(all_words).most_common(100)

        wc = (
            WordCloud(init_opts=opts.InitOpts(width="100%", height="420px"))
            .add(
                series_name=title,
                data_pair=word_counts,
                word_size_range=[12, 60],
                shape="circle",
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title),
                tooltip_opts=opts.TooltipOpts(is_show=True),
            )
        )
        return wc
