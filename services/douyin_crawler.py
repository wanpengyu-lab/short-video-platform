# -*- coding: utf-8 -*-
"""
抖音热榜数据采集模块（Selenium 实现）

功能：
- 突破抖音登录墙与 JS 动态渲染
- 采集热榜列表页：标题、封面、播放量、作者、发布时间
- 逐个点开视频详情，补齐点赞数、评论数、收藏数
- 自动加载并采集视频评论（受平台懒加载限制，尽力而为）

两种运行模式：
- 交互模式（interactive=True）：命令行运行，Cookie 失效时弹出浏览器等待扫码
- 非交互模式（interactive=False）：Web 定时任务调用，Cookie 失效直接返回 0，
  不会阻塞等待，避免网页端卡死

使用前提：
1. 安装 Chrome 浏览器
2. 下载与 Chrome 主版本号一致的 ChromeDriver，放到项目根目录
   （国内镜像：https://registry.npmmirror.com/binary.html?path=chrome-for-testing/）
3. 首次运行需命令行执行一次并扫码登录，Cookie 保存后自动复用
"""

import os
import time
import json
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from utils.helpers import format_count
from config import CRAWL_CONFIG

# Cookie 保存路径（登录后保存，下次免登录）
COOKIE_FILE = os.path.join(os.path.dirname(__file__), '..', 'douyin_cookies.pkl')


class DouyinCrawler:
    """抖音热榜 Selenium 采集器"""

    def __init__(self, headless=False, interactive=True):
        """
        初始化 Selenium WebDriver
        参数:
            headless: 是否无头模式（默认 False，登录阶段建议保持有头）
            interactive: 是否交互模式（默认 True；Web 定时任务传 False）
        """
        options = Options()
        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--user-agent={CRAWL_CONFIG["USER_AGENT_POOL"][0]}')
        options.add_argument('--window-size=1920,1080')

        # 显式指定 ChromeDriver 路径。
        # 说明：不能用 './chromedriver.exe' 这种相对路径——它依赖「从项目根目录启动」，
        # 换个目录运行就会找不到文件。这里基于本模块位置推导项目根目录。
        # 若根目录下不存在驱动文件，则回退交给 Selenium Manager 自动匹配下载
        # （selenium >= 4.6 内置，跨平台通用）。
        _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        _driver_name = 'chromedriver.exe' if os.name == 'nt' else 'chromedriver'
        _driver_path = os.path.join(_project_root, _driver_name)
        if os.path.exists(_driver_path):
            service = Service(executable_path=_driver_path)
        else:
            print(f'[爬虫] 未找到 {_driver_path}，回退使用 Selenium Manager 自动管理驱动')
            service = Service()
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(10)
        self.interactive = interactive

    # ==================== 登录管理 ====================

    def login_if_needed(self) -> bool:
        """
        检查登录状态：
        1. 有有效 Cookie → 自动登录
        2. 无 Cookie / Cookie 过期：
           交互模式 → 弹浏览器等待扫码
           非交互模式 → 直接返回 False（不阻塞）
        """
        self.driver.get('https://www.douyin.com/')

        # 尝试加载已保存的 Cookie
        if os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 10:
            print('[爬虫] 检测到已保存的登录Cookie，正在加载...')
            try:
                with open(COOKIE_FILE, 'rb') as f:
                    cookies = pickle.load(f)
            except Exception:
                print('[爬虫] Cookie文件损坏，跳过加载')
                cookies = []

            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    continue

            # 刷新页面，检查登录状态
            self.driver.refresh()
            time.sleep(3)
            if self._check_login_status():
                print('[爬虫] Cookie有效，已自动登录')
                return True
            else:
                print('[爬虫] Cookie已过期，需要重新登录')

        # 非交互模式：不等待扫码，直接返回失败
        if not self.interactive:
            print('[爬虫] 非交互模式：未检测到有效登录态，本次采集跳过')
            print('[提示] 请先在命令行执行 python -m services.douyin_crawler 完成一次扫码登录')
            return False

        # 交互模式：等待用户扫码
        print('=' * 50)
        print('  浏览器已打开抖音，请手动扫码登录')
        print('  登录成功后，回到命令行按回车继续...')
        print('=' * 50)
        input('登录完成后按回车继续...')

        # 保存 Cookie 供下次复用
        try:
            with open(COOKIE_FILE, 'wb') as f:
                pickle.dump(self.driver.get_cookies(), f)
            print('[爬虫] 登录Cookie已保存，下次自动登录')
        except Exception as e:
            print(f'[爬虫] Cookie保存失败: {e}')

        return True

    def _check_login_status(self) -> bool:
        """检查是否已登录（通过检测用户头像元素）"""
        try:
            self.driver.find_element(By.CSS_SELECTOR, '[class*="avatar"]')
            return True
        except Exception:
            return False

    # ==================== 评论采集（尽力而为） ====================

    def _auto_load_comments(self) -> list:
        """
        自动加载评论区：
        1. 真实鼠标滚轮触发懒加载
        2. 尝试点击"评论"标签
        3. 轮询等待评论区容器出现
        4. 提取评论数据
        抖音评论区为懒加载，渲染时序不稳定，采集不到时返回空列表
        """
        try:
            time.sleep(2)

            # 用 JS 滚动右侧所有可滚动容器，触发评论加载
            for scroll_step in [500, 1000, 1500]:
                self.driver.execute_script('''
                var allEls = document.querySelectorAll('div');
                for (var i = 0; i < allEls.length; i++) {
                    var el = allEls[i];
                    var r = el.getBoundingClientRect();
                    if (r.x > 800 && r.width > 200 && r.height > 300 && el.scrollHeight > el.clientHeight) {
                        el.scrollTop = ''' + str(scroll_step) + ''';
                    }
                }
                ''')
                time.sleep(1)

            # 尝试点击"评论"文字（右侧区域）
            self.driver.execute_script('''
            var allEls = document.querySelectorAll('span, div, a, li, button, p');
            for (var i = 0; i < allEls.length; i++) {
                var el = allEls[i];
                var t = (el.innerText || '').trim();
                var r = el.getBoundingClientRect();
                if (t === '评论' && r.x > 1000 && r.width > 0 && r.height > 0) {
                    el.click();
                    return true;
                }
            }
            return false;
            ''')
            time.sleep(3)

            # 提取评论
            comments = self.driver.execute_script('''
            var container = document.querySelector('[class*="comment-mainContent"]');
            if (!container) return [];
            var items = container.children;
            var results = [];
            for (var i = 0; i < items.length; i++) {
                try {
                    var item = items[i];
                    var text = item.innerText || '';
                    var lines = text.split('\\n').map(function(l) { return l.trim(); })
                                          .filter(function(l) { return l.length > 0; });
                    var userName = '';
                    var content = '';
                    var likeCount = 0;

                    for (var j = 0; j < lines.length; j++) {
                        var line = lines[j];
                        if (line.indexOf('分享') >= 0 || line.indexOf('回复') >= 0) continue;
                        if (line.indexOf('·') >= 0) continue;
                        if (/^\\d+$/.test(line) && j > 0) {
                            likeCount = parseInt(line);
                            continue;
                        }
                        if (!userName && j === 0) { userName = line; continue; }
                        if (userName && !content && line.indexOf('分享') < 0 && line.indexOf('回复') < 0) {
                            content = line;
                        }
                    }
                    if (content && content.length > 1) {
                        results.push({userName: userName, content: content, likeCount: likeCount});
                    }
                } catch(e) { continue; }
            }
            return results;
            ''')
            return comments
        except Exception as e:
            print(f'[爬虫] 评论采集异常: {e}')
            return []

    # ==================== 列表页数据采集 ====================

    def fetch_hot_list(self) -> list:
        """
        采集抖音热榜数据：
        第1步：列表页提取 标题/封面/播放量/作者/发布时间
        第2步：逐个点开详情页，补齐 点赞数/评论数/收藏数
        第3步：尝试采集评论区数据
        """
        print('[爬虫] 正在访问抖音热榜页面...')
        self.driver.get('https://www.douyin.com/hot')
        time.sleep(8)

        # ===== 第1步：从列表页 DOM 提取基本信息 =====
        video_list = self.driver.execute_script('''
        var cards = document.querySelectorAll('[class*="otherVideoCard"]');
        var results = [];
        for (var i = 0; i < cards.length; i++) {
            var card = cards[i];
            var text = card.innerText || '';
            var lines = text.split('\\n').map(function(l) { return l.trim(); })
                              .filter(function(l) { return l.length > 0; });

            var playCount = 0;
            var title = '';
            var author = '';
            var date = '';
            var cover = '';

            var img = card.querySelector('img');
            if (img) { cover = img.src || img.getAttribute('data-src') || ''; }

            for (var j = 0; j < lines.length; j++) {
                var line = lines[j];
                // 跳过时长行（如 02:42）
                if (/^\\d{1,2}:\\d{2}$/.test(line)) continue;
                // 播放量行（纯数字或带万）
                if (/^\\d+(\\.\\d+)?万?$/.test(line) && playCount === 0) {
                    if (line.indexOf('万') >= 0) {
                        playCount = Math.floor(parseFloat(line) * 10000);
                    } else {
                        playCount = parseInt(line);
                    }
                    continue;
                }
                // 作者行（@开头）
                if (line.indexOf('@') === 0) { author = line.substring(1); continue; }
                // 日期行（·开头）
                if (line.indexOf('·') === 0 || line.indexOf('Â·') === 0) {
                    date = line.replace(/^[·Â·\\s]+/, '').trim();
                    continue;
                }
                // 标题行
                if (playCount > 0 && !title) { title = line; }
                else if (playCount > 0 && title && author === '' && line.indexOf('@') !== 0) {
                    title = title + ' ' + line;
                }
            }

            if (title) {
                results.push({
                    title: title,
                    cover_url: cover,
                    play_count: playCount,
                    like_count: 0,
                    comment_count: 0,
                    collect_count: 0,
                    author_nickname: author,
                    publish_time: date
                });
            }
        }
        return results;
        ''')

        print(f'[爬虫] 列表页采集到 {len(video_list)} 条视频')

        # ===== 第2步：逐个点击卡片，采集详情页数据 =====
        print('[爬虫] 开始逐个采集详情页数据（点赞/评论/收藏）...')

        for idx, video in enumerate(video_list):
            try:
                # 重新获取卡片列表（页面元素可能已刷新）
                cards = self.driver.find_elements(By.CSS_SELECTOR, '[class*="otherVideoCard"]')
                if idx >= len(cards):
                    break

                # 点击卡片打开详情模态框
                self.driver.execute_script("arguments[0].click();", cards[idx])
                time.sleep(3)

                # 从模态框交互区读取4个数字（播放量/点赞/评论/收藏）
                detail_data = self.driver.execute_script('''
                var container = document.querySelector('[class*="D0ZulesG"]');
                if (!container) return null;
                var children = container.children;
                var numbers = [];
                for (var i = 0; i < children.length; i++) {
                    var t = (children[i].innerText || '').trim();
                    numbers.push(t);
                }
                return numbers;
                ''')

                if detail_data and len(detail_data) >= 4:
                    video['like_count'] = format_count(detail_data[1])
                    video['comment_count'] = format_count(detail_data[2])
                    video['collect_count'] = format_count(detail_data[3])

                # 尝试采集评论（尽力而为，失败不影响主数据）
                comments = self._auto_load_comments()
                video['comments'] = comments

                print(
                    f'  [{idx}] {video["title"][:18]}... | '
                    f'赞:{video["like_count"]} 评:{video["comment_count"]} 藏:{video["collect_count"]}'
                    f' | 采评{len(comments)}条'
                )

                # 关闭模态框
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)

            except Exception as e:
                print(f'  [{idx}] 详情页采集失败: {e}')
                try:
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(1)
                except Exception:
                    pass

        print(f'[爬虫] 采集完成，共 {len(video_list)} 条')
        return video_list

    # ==================== 完整流程：采集 + 入库 ====================

    def crawl_and_save(self, url: str = 'https://www.douyin.com/hot') -> int:
        """
        完整采集流程：登录检查 → 抓取列表 → 详情补齐 → 清洗入库 → 评论入库
        返回成功入库的视频条数
        """
        # 第1步：登录检查（非交互模式下 Cookie 失效会直接返回 False）
        if not self.login_if_needed():
            return 0

        # 第2步：采集热榜数据
        raw_data = self.fetch_hot_list()
        if not raw_data:
            print('[爬虫] 未采集到数据，请检查登录状态或页面结构')
            return 0

        # 第3步：清洗并入库视频数据
        from services.cleaner import DataCleaner
        cleaner = DataCleaner()
        saved_count = cleaner.clean_and_save(raw_data)

        # 第4步：评论入库
        try:
            from models.database import Database
            comment_count = 0
            for v in raw_data:
                comments = v.get('comments', [])
                if not comments:
                    continue
                video_row = Database.execute_one(
                    "SELECT id FROM video_info WHERE title = %s", (v['title'][:300],)
                )
                if not video_row:
                    continue
                video_id = video_row['id']
                for c in comments:
                    try:
                        content = c.get('content', '')[:500]
                        if not content:
                            continue
                        existing = Database.execute_one(
                            "SELECT id FROM video_comment WHERE video_id = %s AND content = %s",
                            (video_id, content)
                        )
                        if existing:
                            continue
                        Database.execute_insert(
                            "INSERT INTO video_comment (video_id, content, like_count, user_name) "
                            "VALUES (%s, %s, %s, %s)",
                            (video_id, content, c.get('likeCount', 0), c.get('userName', '')[:100])
                        )
                        comment_count += 1
                    except Exception as e:
                        print(f'[评论] 单条插入失败: {e}')
            print(f'[评论] 共入库 {comment_count} 条评论')
        except Exception as e:
            print(f'[评论] 入库流程异常: {e}')

        return saved_count

    def close(self):
        """关闭浏览器"""
        try:
            if self.driver:
                self.driver.quit()
                print('[爬虫] 浏览器已关闭')
        except Exception:
            pass


# ==================== 命令行直接运行（交互模式） ====================

if __name__ == '__main__':
    crawler = DouyinCrawler(headless=False, interactive=True)
    try:
        count = crawler.crawl_and_save()
        print(f'\n采集完成！共入库 {count} 条数据')
    except Exception as e:
        print(f'[错误] {e}')
    input('>>> 按回车关闭浏览器...')
    crawler.close()