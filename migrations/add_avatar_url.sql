-- 为角色表添加头像URL字段的迁移脚本
-- 适用于PostgreSQL和SQLite

-- PostgreSQL 版本
ALTER TABLE characters ADD COLUMN IF NOT EXISTS avatar_url TEXT;

-- SQLite 版本（如果需要手动运行）
-- ALTER TABLE characters ADD COLUMN avatar_url TEXT;

-- 说明：
-- 1. 该字段用于存储角色头像的URL路径（例如：/avatars/user_1_角色名.jpg）
-- 2. 头像文件会在角色创建时自动从百度百科等来源下载并裁剪成256x256的正方形
-- 3. 前端会显示为圆角正方形
-- 4. 如果没有头像，会显示默认图标（👤）

