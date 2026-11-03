-- ============================================================
-- 短视频热门数据采集与可视化平台 - 数据库初始化脚本
-- 使用方法：在 MySQL 命令行中执行 source init_db.sql
-- 说明：若此前已执行过旧版脚本，可跳过本文件，直接使用
--       app.py 启动时自动完成的表结构迁移（自动添加 role 字段）
-- ============================================================

-- 创建数据库（如不存在）
CREATE DATABASE IF NOT EXISTS short_video
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE short_video;

-- ========== 1. 作者表 ==========
DROP TABLE IF EXISTS video_comment;
DROP TABLE IF EXISTS video_info;
DROP TABLE IF EXISTS crawl_task;
DROP TABLE IF EXISTS author_info;
DROP TABLE IF EXISTS admin_user;

CREATE TABLE author_info (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nickname    VARCHAR(100) NOT NULL COMMENT '作者昵称',
    avatar_url  VARCHAR(500) DEFAULT '' COMMENT '头像链接',
    follower_count INT DEFAULT 0 COMMENT '粉丝数',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB COMMENT='作者信息表';

-- ========== 2. 作品表 ==========
CREATE TABLE video_info (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(300) NOT NULL COMMENT '视频标题',
    cover_url       VARCHAR(500) DEFAULT '' COMMENT '封面链接',
    play_count      BIGINT DEFAULT 0 COMMENT '播放量',
    like_count      BIGINT DEFAULT 0 COMMENT '点赞数',
    comment_count   BIGINT DEFAULT 0 COMMENT '评论数',
    collect_count   BIGINT DEFAULT 0 COMMENT '收藏数',
    publish_time    DATETIME DEFAULT NULL COMMENT '发布时间',
    author_id       INT DEFAULT NULL COMMENT '关联作者ID',
    crawl_time      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    FOREIGN KEY (author_id) REFERENCES author_info(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='视频作品表';

-- ========== 3. 采集任务表 ==========
CREATE TABLE crawl_task (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    task_name   VARCHAR(100) NOT NULL COMMENT '任务名称',
    target_url  VARCHAR(500) DEFAULT '' COMMENT '目标链接',
    status      VARCHAR(20) DEFAULT '停止' COMMENT '状态：运行/停止',
    cron_rule   VARCHAR(50) DEFAULT '0 */2 * * *' COMMENT '定时规则(cron表达式)',
    last_run    DATETIME DEFAULT NULL COMMENT '上次执行时间',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB COMMENT='采集任务表';

-- ========== 4. 评论表 ==========
CREATE TABLE video_comment (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    video_id    INT NOT NULL COMMENT '关联视频ID',
    content     TEXT NOT NULL COMMENT '评论内容',
    like_count  INT DEFAULT 0 COMMENT '评论点赞数',
    user_name   VARCHAR(100) DEFAULT '' COMMENT '评论者昵称',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '评论时间',
    FOREIGN KEY (video_id) REFERENCES video_info(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='视频评论表';

-- ========== 5. 管理员表（登录鉴权 + 角色区分）==========
CREATE TABLE admin_user (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password    VARCHAR(128) NOT NULL COMMENT '密码（加密存储）',
    role        VARCHAR(20) DEFAULT 'user' COMMENT '角色：admin 管理员 / user 普通用户',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB COMMENT='用户账号表';

-- 插入默认采集任务示例
INSERT INTO crawl_task (task_name, target_url, status, cron_rule) VALUES
('短视频热榜采集', 'https://www.douyin.com/hot', '停止', '0 */2 * * *'),
('短视频评论采集', 'https://www.douyin.com/comments', '停止', '0 0 */6 * * *');

-- 插入默认账号（密码为明文，首次运行由Python脚本加密替换）
-- 管理员账号：admin / admin123
-- 普通用户账号：user / user123
INSERT INTO admin_user (username, password, role) VALUES
('admin', 'admin123', 'admin'),
('user', 'user123', 'user');

SELECT '数据库初始化完成！' AS message;