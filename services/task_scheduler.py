# -*- coding: utf-8 -*-
"""
定时任务调度模块
使用 APScheduler 实现周期性自动采集
对应文档：采集模块 → 定时任务（APScheduler）实现周期性自动采集
"""

from apscheduler.schedulers.background import BackgroundScheduler
from models.database import Database


class TaskScheduler:
    """采集任务调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self._started = False

    def start(self):
        """启动调度器（应用启动时调用一次）"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            print("[调度器] APScheduler 已启动")

            # 加载数据库中状态为"运行"的任务
            self._load_running_tasks()

    def _load_running_tasks(self):
        """从数据库加载所有运行中的任务"""
        tasks = Database.execute_query(
            "SELECT * FROM crawl_task WHERE status = '运行'"
        )
        if tasks:
            for task in tasks:
                self.add_job(task)
            print(f"[调度器] 已加载 {len(tasks)} 个运行中的任务")

    def _parse_cron_rule(self, cron_rule: str) -> dict:
        """
        将 cron 表达式解析为 APScheduler 参数
        格式：分 时 日 月 周  （5段式）
        示例：'0 */2 * * *' → 每2小时执行一次
        """
        parts = cron_rule.strip().split()
        if len(parts) != 5:
            return {'minute': '0', 'hour': '*/2'}  # 默认每2小时

        result = {}
        if parts[0] != '*':
            result['minute'] = parts[0]
        if parts[1] != '*':
            result['hour'] = parts[1]
        if parts[2] != '*':
            result['day'] = parts[2]
        if parts[3] != '*':
            result['month'] = parts[3]
        if parts[4] != '*':
            result['day_of_week'] = parts[4]

        return result if result else {'minute': '0', 'hour': '*/2'}

    def _execute_task(self, task_id: int, target_url: str, task_name: str):
        """
        执行单次采集任务
        采集完成后更新 last_run 时间
        """
        print(f"[调度器] 开始执行任务: {task_name} (ID={task_id})")
        try:
            count = 0
            # 平台判断：当前已实现抖音热榜爬虫，其他平台记录日志跳过
            if 'douyin.com' in target_url:
                from services.douyin_crawler import DouyinCrawler
                crawler = DouyinCrawler(headless=False, interactive=False)
                try:
                    count = crawler.crawl_and_save(target_url)
                finally:
                    crawler.close()
            else:
                print(f"[调度器] 任务 [{task_name}] 目标平台暂不支持采集: {target_url}")

            # 更新上次执行时间
            Database.execute_update(
                "UPDATE crawl_task SET last_run = NOW() WHERE id = %s",
                (task_id,)
            )
            print(f"[调度器] 任务 [{task_name}] 完成，采集 {count} 条")
        except Exception as e:
            print(f"[调度器] 任务 [{task_name}] 执行失败: {e}")

    def add_job(self, task: dict):
        """注册定时任务到调度器"""
        job_id = f"crawl_task_{task['id']}"

        # 如果任务已存在，先移除
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # 解析 cron 规则
        cron_params = self._parse_cron_rule(task['cron_rule'])

        # 添加定时任务
        self.scheduler.add_job(
            func=self._execute_task,
            trigger='cron',
            id=job_id,
            args=[task['id'], task['target_url'], task['task_name']],
            **cron_params
        )
        print(f"[调度器] 任务已注册: {task['task_name']}, cron={task['cron_rule']}")

    def remove_job(self, task_id: int):
        """从调度器中移除任务"""
        job_id = f"crawl_task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            print(f"[调度器] 任务已移除: ID={task_id}")

    def shutdown(self):
        """关闭调度器"""
        if self._started:
            self.scheduler.shutdown()
            self._started = False
            print("[调度器] APScheduler 已关闭")
