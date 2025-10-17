-- FastNPC 数据库外键约束修复脚本 (PostgreSQL)
-- ⚠️ 执行前请备份数据库！
-- 备份命令: pg_dump -U fastnpc -d fastnpc > backup_$(date +%Y%m%d_%H%M%S).sql

BEGIN;

-- ==========================================
-- 步骤1: 检查并清理孤儿数据
-- ==========================================

DO $$ 
DECLARE
    orphan_count INT;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '开始清理孤儿数据...';
    RAISE NOTICE '========================================';
    
    -- 清理孤儿角色
    SELECT COUNT(*) INTO orphan_count FROM characters WHERE user_id NOT IN (SELECT id FROM users);
    IF orphan_count > 0 THEN
        DELETE FROM characters WHERE user_id NOT IN (SELECT id FROM users);
        RAISE NOTICE '✓ 清理了 % 个孤儿角色', orphan_count;
    ELSE
        RAISE NOTICE '✓ 没有孤儿角色';
    END IF;
    
    -- 清理孤儿消息（引用不存在的用户）
    SELECT COUNT(*) INTO orphan_count FROM messages WHERE user_id NOT IN (SELECT id FROM users);
    IF orphan_count > 0 THEN
        DELETE FROM messages WHERE user_id NOT IN (SELECT id FROM users);
        RAISE NOTICE '✓ 清理了 % 个孤儿消息（用户）', orphan_count;
    ELSE
        RAISE NOTICE '✓ 没有孤儿消息（用户）';
    END IF;
    
    -- 清理孤儿消息（引用不存在的角色）
    SELECT COUNT(*) INTO orphan_count FROM messages WHERE character_id NOT IN (SELECT id FROM characters);
    IF orphan_count > 0 THEN
        DELETE FROM messages WHERE character_id NOT IN (SELECT id FROM characters);
        RAISE NOTICE '✓ 清理了 % 个孤儿消息（角色）', orphan_count;
    ELSE
        RAISE NOTICE '✓ 没有孤儿消息（角色）';
    END IF;
    
    -- 清理孤儿设置
    SELECT COUNT(*) INTO orphan_count FROM user_settings WHERE user_id NOT IN (SELECT id FROM users);
    IF orphan_count > 0 THEN
        DELETE FROM user_settings WHERE user_id NOT IN (SELECT id FROM users);
        RAISE NOTICE '✓ 清理了 % 个孤儿设置', orphan_count;
    ELSE
        RAISE NOTICE '✓ 没有孤儿设置';
    END IF;
    
    -- 清理孤儿群聊
    SELECT COUNT(*) INTO orphan_count FROM group_chats WHERE user_id NOT IN (SELECT id FROM users);
    IF orphan_count > 0 THEN
        DELETE FROM group_chats WHERE user_id NOT IN (SELECT id FROM users);
        RAISE NOTICE '✓ 清理了 % 个孤儿群聊', orphan_count;
    ELSE
        RAISE NOTICE '✓ 没有孤儿群聊';
    END IF;
    
    -- 清理孤儿群聊成员
    SELECT COUNT(*) INTO orphan_count FROM group_members WHERE group_id NOT IN (SELECT id FROM group_chats);
    IF orphan_count > 0 THEN
        DELETE FROM group_members WHERE group_id NOT IN (SELECT id FROM group_chats);
        RAISE NOTICE '✓ 清理了 % 个孤儿群聊成员', orphan_count;
    ELSE
        RAISE NOTICE '✓ 没有孤儿群聊成员';
    END IF;
    
    -- 清理孤儿群聊消息
    SELECT COUNT(*) INTO orphan_count FROM group_messages WHERE group_id NOT IN (SELECT id FROM group_chats);
    IF orphan_count > 0 THEN
        DELETE FROM group_messages WHERE group_id NOT IN (SELECT id FROM group_chats);
        RAISE NOTICE '✓ 清理了 % 个孤儿群聊消息', orphan_count;
    ELSE
        RAISE NOTICE '✓ 没有孤儿群聊消息';
    END IF;
    
    -- 清理孤儿反馈
    SELECT COUNT(*) INTO orphan_count FROM feedbacks WHERE user_id NOT IN (SELECT id FROM users);
    IF orphan_count > 0 THEN
        DELETE FROM feedbacks WHERE user_id NOT IN (SELECT id FROM users);
        RAISE NOTICE '✓ 清理了 % 个孤儿反馈', orphan_count;
    ELSE
        RAISE NOTICE '✓ 没有孤儿反馈';
    END IF;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE '孤儿数据清理完成！';
    RAISE NOTICE '========================================';
END $$;

-- ==========================================
-- 步骤2: 添加外键约束
-- ==========================================

DO $$ 
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '开始添加外键约束...';
    RAISE NOTICE '========================================';
END $$;

-- 1. characters 表
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'characters_user_id_fkey'
    ) THEN
        ALTER TABLE characters 
        ADD CONSTRAINT characters_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        RAISE NOTICE '✓ characters.user_id → users.id (ON DELETE CASCADE)';
    ELSE
        RAISE NOTICE '⊙ characters.user_id 约束已存在';
    END IF;
END $$;

-- 2. messages 表 (user_id)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'messages_user_id_fkey'
    ) THEN
        ALTER TABLE messages 
        ADD CONSTRAINT messages_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        RAISE NOTICE '✓ messages.user_id → users.id (ON DELETE CASCADE)';
    ELSE
        RAISE NOTICE '⊙ messages.user_id 约束已存在';
    END IF;
END $$;

-- 3. messages 表 (character_id)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'messages_character_id_fkey'
    ) THEN
        ALTER TABLE messages 
        ADD CONSTRAINT messages_character_id_fkey 
        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE;
        RAISE NOTICE '✓ messages.character_id → characters.id (ON DELETE CASCADE)';
    ELSE
        RAISE NOTICE '⊙ messages.character_id 约束已存在';
    END IF;
END $$;

-- 4. user_settings 表
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'user_settings_user_id_fkey'
    ) THEN
        ALTER TABLE user_settings 
        ADD CONSTRAINT user_settings_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        RAISE NOTICE '✓ user_settings.user_id → users.id (ON DELETE CASCADE)';
    ELSE
        RAISE NOTICE '⊙ user_settings.user_id 约束已存在';
    END IF;
END $$;

-- 5. group_chats 表
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'group_chats_user_id_fkey'
    ) THEN
        ALTER TABLE group_chats 
        ADD CONSTRAINT group_chats_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        RAISE NOTICE '✓ group_chats.user_id → users.id (ON DELETE CASCADE)';
    ELSE
        RAISE NOTICE '⊙ group_chats.user_id 约束已存在';
    END IF;
END $$;

-- 6. group_members 表
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'group_members_group_id_fkey'
    ) THEN
        ALTER TABLE group_members 
        ADD CONSTRAINT group_members_group_id_fkey 
        FOREIGN KEY (group_id) REFERENCES group_chats(id) ON DELETE CASCADE;
        RAISE NOTICE '✓ group_members.group_id → group_chats.id (ON DELETE CASCADE)';
    ELSE
        RAISE NOTICE '⊙ group_members.group_id 约束已存在';
    END IF;
END $$;

-- 7. group_messages 表
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'group_messages_group_id_fkey'
    ) THEN
        ALTER TABLE group_messages 
        ADD CONSTRAINT group_messages_group_id_fkey 
        FOREIGN KEY (group_id) REFERENCES group_chats(id) ON DELETE CASCADE;
        RAISE NOTICE '✓ group_messages.group_id → group_chats.id (ON DELETE CASCADE)';
    ELSE
        RAISE NOTICE '⊙ group_messages.group_id 约束已存在';
    END IF;
END $$;

-- 8. feedbacks 表 (修复当前报错的关键！)
DO $$ 
BEGIN
    -- 先尝试删除旧的约束（如果存在但没有CASCADE）
    ALTER TABLE feedbacks DROP CONSTRAINT IF EXISTS feedbacks_user_id_fkey;
    
    -- 添加新的约束（带CASCADE）
    ALTER TABLE feedbacks 
    ADD CONSTRAINT feedbacks_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    
    RAISE NOTICE '✓ feedbacks.user_id → users.id (ON DELETE CASCADE) [重新创建]';
END $$;

-- ==========================================
-- 步骤3: 验证外键约束
-- ==========================================

DO $$ 
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '验证外键约束...';
    RAISE NOTICE '========================================';
END $$;

-- 输出所有外键约束的详细信息
DO $$
DECLARE
    constraint_info RECORD;
BEGIN
    FOR constraint_info IN
        SELECT 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints AS rc
            ON rc.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name IN ('characters', 'messages', 'user_settings', 'group_chats', 'group_members', 'group_messages', 'feedbacks')
        ORDER BY tc.table_name, kcu.column_name
    LOOP
        RAISE NOTICE '% ⊙ %.% → %.% [DELETE: %]', 
            CASE 
                WHEN constraint_info.delete_rule = 'CASCADE' THEN '✓'
                ELSE '✗'
            END,
            constraint_info.table_name,
            constraint_info.column_name,
            constraint_info.foreign_table_name,
            constraint_info.foreign_column_name,
            constraint_info.delete_rule;
    END LOOP;
END $$;

COMMIT;

-- ==========================================
-- 完成
-- ==========================================

DO $$ 
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ 外键约束修复完成！';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE '现在可以安全地删除用户，所有相关数据会自动级联删除：';
    RAISE NOTICE '  • 删除用户 → 自动删除角色、消息、设置、群聊、反馈';
    RAISE NOTICE '  • 删除角色 → 自动删除消息、所有角色详细信息';
    RAISE NOTICE '  • 删除群聊 → 自动删除群聊成员、群聊消息';
    RAISE NOTICE '';
END $$;

