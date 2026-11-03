# -*- coding: utf-8 -*-
"""
数据清洗存储模块
"""

import pandas as pd
from datetime import datetime, timedelta
from models.database import Database
from utils.helpers import format_count
import re


class DataCleaner:

    def _convert_date(self, date_str):
        """将抖音日期格式转换为MySQL标准日期"""
        if not date_str:
            return None
        date_str = str(date_str).strip()
        now = datetime.now()

        # "15小时前" → 今天减15小时
        m = re.match(r'(\d+)小时前', date_str)
        if m:
            return (now - timedelta(hours=int(m.group(1)))).strftime('%Y-%m-%d %H:%M:%S')

        # "3天前" → 今天减3天
        m = re.match(r'(\d+)天前', date_str)
        if m:
            return (now - timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d %H:%M:%S')

        # "1分钟前" → 今天
        m = re.match(r'(\d+)分钟前', date_str)
        if m:
            return now.strftime('%Y-%m-%d %H:%M:%S')

        # "9月23日" → 2024-09-23
        m = re.match(r'(\d+)月(\d+)日', date_str)
        if m:
            month = int(m.group(1))
            day = int(m.group(2))
            year = now.year
            if month > now.month:
                year = year - 1
            try:
                return datetime(year, month, day).strftime('%Y-%m-%d %H:%M:%S')
            except:
                return None

        # 已经是标准格式就直接返回
        try:
            datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
            return date_str[:19]
        except:
            return None

    def clean_data(self, raw_data: list) -> pd.DataFrame:
        if not raw_data:
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)
        df = df.drop_duplicates(subset=['title'], keep='first')
        print(f"[清洗] 去重后剩余 {len(df)} 条")

        # 数值字段处理
        numeric_cols = ['play_count', 'like_count', 'comment_count', 'collect_count']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: format_count(x) if x else 0)

        # 字符串字段处理
        str_cols = ['title', 'cover_url', 'author_nickname']
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)

        # 标题截断（最多300字符）
        if 'title' in df.columns:
            df['title'] = df['title'].str[:300]

        # 日期格式转换
        if 'publish_time' in df.columns:
            df['publish_time'] = df['publish_time'].apply(self._convert_date)

        # 过滤无效数据
        df = df[df['title'].str.strip() != '']
        print(f"[清洗] 清洗完成，有效数据 {len(df)} 条")
        return df

    def save_to_database(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        saved_count = 0
        for _, row in df.iterrows():
            try:
                author_id = self._get_or_create_author(row.get('author_nickname', ''))
                existing = Database.execute_one("SELECT id FROM video_info WHERE title = %s", (row['title'],))
                if existing:
                    continue
                sql = """INSERT INTO video_info
                    (title, cover_url, play_count, like_count, comment_count, collect_count, publish_time, author_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                import math
                def safe_int(v):
                    if v is None or (isinstance(v, float) and math.isnan(v)):
                        return 0
                    try:
                        return int(v)
                    except:
                        return 0
                def safe_str(v):
                    if v is None or (isinstance(v, float) and math.isnan(v)):
                        return ''
                    return str(v)
                Database.execute_insert(sql, (
                    safe_str(row.get('title', ''))[:300],
                    safe_str(row.get('cover_url', '')),
                    safe_int(row.get('play_count', 0)),
                    safe_int(row.get('like_count', 0)),
                    safe_int(row.get('comment_count', 0)),
                    safe_int(row.get('collect_count', 0)),
                    safe_str(row.get('publish_time', '')) or None,
                    author_id
                ))
                saved_count += 1
            except Exception as e:
                print(f"[存储] 插入失败: {row.get('title', '未知')[:30]}..., 错误: {e}")
                continue
        print(f"[存储] 成功入库 {saved_count} 条新数据")
        return saved_count

    def _get_or_create_author(self, nickname):
        if not nickname:
            return None
        author = Database.execute_one("SELECT id FROM author_info WHERE nickname = %s", (nickname,))
        if author:
            return author['id']
        author_id = Database.execute_insert("INSERT INTO author_info (nickname) VALUES (%s)", (nickname,))
        return author_id

    def clean_and_save(self, raw_data):
        df = self.clean_data(raw_data)
        return self.save_to_database(df)