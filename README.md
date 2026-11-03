# 短视频热门数据采集与可视化平台

基于 Flask + MySQL + Selenium 的短视频数据采集、清洗、可视化系统。
当前已实现抖音热榜采集，架构上预留了其他平台的扩展位。

## 环境要求
- Python 3.10+
- MySQL 5.7+
- Chrome 浏览器（版本需与驱动匹配）

## 安装步骤

### 1. 克隆项目
git clone https://github.com/你的用户名/short-video-platform.git
cd short-video-platform

### 2. 安装依赖
python -m pip install -r requirements.txt

### 3. 配置环境变量
copy .env.example .env
编辑 .env，填入 MySQL 密码、SECRET_KEY、账号密码。
生成 SECRET_KEY：python -c "import secrets; print(secrets.token_hex(32))"

### 4. 初始化数据库
mysql -u root -p < init_db.sql
（自动创建 short_video 库和 5 张表）

### 5. 准备 ChromeDriver
项目不含驱动文件，需自行下载与你 Chrome 版本匹配的 chromedriver.exe
放到项目根目录。
下载：https://googlechromelabs.github.io/chrome-for-testing/

### 6. 启动
python run.py
访问 http://127.0.0.1:5000

## 首次采集需扫码登录
抖音采集需要登录态。首次运行以下命令，会弹出浏览器等待扫码：
python -m services.douyin_crawler
扫码成功后 Cookie 自动保存为 douyin_cookies.pkl，后续免登录。
该文件已被 .gitignore 排除，不会上传。

## 功能模块
- 数据总览仪表盘
- 视频榜单查询与分页
- 可视化图表（含评论词云）
- 采集任务管理（仅管理员）

## 目录结构
app.py            应用工厂
run.py            启动入口
config.py         配置（读环境变量）
blueprints/       路由蓝图（MVC 的 C）
models/           数据访问层（M）
services/         业务逻辑（爬虫/清洗/图表/调度）
utils/            工具函数
templates/        Jinja2 模板（V）
static/           CSS / JS / 图片
init_db.sql       数据库初始化脚本

## 扩展其他平台
services/crawler.py 是平台爬虫的模板骨架，
参照 services/douyin_crawler.py 实现对应平台的选择器即可。