# -*- coding: utf-8 -*-
"""
提示词系统状态检查脚本

检查提示词版本控制系统的集成状态和当前配置
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from fastnpc.config import USE_DB_PROMPTS, USE_POSTGRESQL
from fastnpc.prompt_manager import PromptManager, PromptCategory
from fastnpc.api.cache import get_redis_cache
from fastnpc.api.auth import _get_conn, _return_conn


def print_header(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def check_config():
    """检查配置状态"""
    print_header("📋 配置状态")
    
    print(f"USE_DB_PROMPTS: {USE_DB_PROMPTS}")
    print(f"USE_POSTGRESQL: {USE_POSTGRESQL}")
    
    if USE_DB_PROMPTS:
        print("\n✅ 数据库提示词已启用")
    else:
        print("\n⚠️  数据库提示词未启用，将使用硬编码版本")
        print("   要启用，请设置环境变量: USE_DB_PROMPTS=true")


def check_database_prompts():
    """检查数据库中的提示词"""
    print_header("💾 数据库提示词状态")
    
    if not USE_DB_PROMPTS:
        print("⚠️  USE_DB_PROMPTS=false，跳过数据库检查")
        return
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        # 统计提示词数量
        cur.execute("SELECT COUNT(*) FROM prompt_templates")
        total_count = cur.fetchone()[0]
        
        cur.execute(f"SELECT COUNT(*) FROM prompt_templates WHERE is_active = {placeholder}", (1,))
        active_count = cur.fetchone()[0]
        
        print(f"总提示词数: {total_count}")
        print(f"激活的提示词数: {active_count}")
        
        if total_count == 0:
            print("\n⚠️  数据库中没有提示词！")
            print("   请运行: python fastnpc/scripts/init_prompts.py")
            return
        
        # 按类别统计
        print("\n📊 按类别统计:")
        cur.execute(f"""
            SELECT category, COUNT(*) as count, 
                   SUM(CASE WHEN is_active = {placeholder} THEN 1 ELSE 0 END) as active_count
            FROM prompt_templates 
            GROUP BY category
            ORDER BY category
        """, (1,))
        
        rows = cur.fetchall()
        print(f"\n{'类别':<40} {'总数':<8} {'激活':<8}")
        print("-" * 60)
        for row in rows:
            category, count, active = row
            status = "✅" if active > 0 else "⚠️ "
            print(f"{status} {category:<38} {count:<8} {active:<8}")
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")
    finally:
        _return_conn(conn)


def check_active_prompts():
    """检查各类别的激活提示词"""
    print_header("🎯 激活的提示词详情")
    
    if not USE_DB_PROMPTS:
        print("⚠️  USE_DB_PROMPTS=false，使用硬编码版本")
        return
    
    categories = [
        ("结构化生成 - 基础身份信息", PromptCategory.STRUCTURED_GENERATION, "基础身份信息"),
        ("结构化生成 - 个性与行为设定", PromptCategory.STRUCTURED_GENERATION, "个性与行为设定"),
        ("结构化生成 - 背景故事", PromptCategory.STRUCTURED_GENERATION, "背景故事"),
        ("结构化系统消息", PromptCategory.STRUCTURED_SYSTEM_MESSAGE, None),
        ("简介生成", PromptCategory.BRIEF_GENERATION, None),
        ("单聊系统提示", PromptCategory.SINGLE_CHAT_SYSTEM, None),
        ("单聊短期记忆凝练", PromptCategory.SINGLE_CHAT_STM_COMPRESSION, None),
        ("群聊短期记忆凝练", PromptCategory.GROUP_CHAT_STM_COMPRESSION, None),
        ("长期记忆整合", PromptCategory.LTM_INTEGRATION, None),
        ("群聊中控", PromptCategory.GROUP_MODERATOR, None),
        ("群聊角色发言", PromptCategory.GROUP_CHAT_CHARACTER, None),
    ]
    
    print("\n检查核心提示词类别:\n")
    
    for name, category, sub_category in categories:
        prompt = PromptManager.get_active_prompt(category, sub_category)
        if prompt:
            version = prompt.get('version', 'Unknown')
            content_length = len(prompt.get('template_content', ''))
            print(f"✅ {name:<35} v{version:<8} ({content_length} 字符)")
        else:
            print(f"❌ {name:<35} 未找到")


def check_cache():
    """检查Redis缓存状态"""
    print_header("🗄️  Redis缓存状态")
    
    try:
        cache = get_redis_cache()
        
        # 尝试获取所有提示词缓存键
        # 注意：这里假设Redis有KEYS命令支持
        print("查找提示词缓存键...\n")
        
        # 测试几个常用的缓存键
        test_keys = [
            "prompt:active:SINGLE_CHAT_SYSTEM",
            "prompt:active:BRIEF_GENERATION",
            "prompt:active:GROUP_MODERATOR",
            "prompt:active:STRUCTURED_GENERATION:基础身份信息",
        ]
        
        cached_count = 0
        for key in test_keys:
            value = cache.get(key)
            if value is not None:
                cached_count += 1
                print(f"✅ {key}")
            else:
                print(f"⚪ {key} (未缓存)")
        
        if cached_count > 0:
            print(f"\n找到 {cached_count} 个缓存的提示词")
            print("缓存TTL: 5分钟")
        else:
            print("\n⚪ 暂无缓存（首次访问时会自动缓存）")
        
    except Exception as e:
        print(f"❌ 检查缓存失败: {e}")
        print("   请确认Redis服务是否运行")


def check_evaluators():
    """检查评估提示词"""
    print_header("⭐ 评估提示词状态")
    
    if not USE_DB_PROMPTS:
        print("⚠️  USE_DB_PROMPTS=false，跳过检查")
        return
    
    evaluator_categories = [
        ("结构化生成评估器", PromptCategory.EVALUATOR_STRUCTURED_GEN),
        ("简介生成评估器", PromptCategory.EVALUATOR_BRIEF_GEN),
        ("单聊对话评估器", PromptCategory.EVALUATOR_SINGLE_CHAT),
        ("群聊对话评估器", PromptCategory.EVALUATOR_GROUP_CHAT),
        ("短期记忆凝练评估器", PromptCategory.EVALUATOR_STM_COMPRESSION),
        ("长期记忆整合评估器", PromptCategory.EVALUATOR_LTM_INTEGRATION),
        ("群聊中控评估器", PromptCategory.EVALUATOR_GROUP_MODERATOR),
    ]
    
    print("\n检查评估器:\n")
    
    found_count = 0
    for name, category in evaluator_categories:
        prompt = PromptManager.get_active_prompt(category)
        if prompt:
            version = prompt.get('version', 'Unknown')
            print(f"✅ {name:<30} v{version}")
            found_count += 1
        else:
            print(f"❌ {name:<30} 未找到")
    
    if found_count == 0:
        print("\n⚠️  未找到评估提示词")
        print("   请运行: python fastnpc/scripts/init_evaluation_prompts.py")
    else:
        print(f"\n✅ 找到 {found_count}/{len(evaluator_categories)} 个评估器")


def test_prompt_rendering():
    """测试提示词渲染"""
    print_header("🧪 提示词渲染测试")
    
    # 测试变量替换
    template = "你好，{name}！今天天气{weather}。"
    variables = {"name": "张三", "weather": "晴朗"}
    
    rendered = PromptManager.render_prompt(template, variables)
    
    print("模板:")
    print(f"  {template}")
    print("\n变量:")
    for k, v in variables.items():
        print(f"  {k} = {v}")
    print("\n渲染结果:")
    print(f"  {rendered}")
    
    if rendered == "你好，张三！今天天气晴朗。":
        print("\n✅ 变量替换功能正常")
    else:
        print("\n❌ 变量替换功能异常")


def generate_summary():
    """生成总结报告"""
    print_header("📝 总结")
    
    if not USE_DB_PROMPTS:
        print("⚠️  数据库提示词未启用")
        print("   系统将使用硬编码的提示词")
        print("\n要启用数据库提示词，请:")
        print("   1. 设置环境变量: USE_DB_PROMPTS=true")
        print("   2. 运行初始化脚本: python fastnpc/scripts/init_prompts.py")
        print("   3. 重启服务器")
        return
    
    # 快速统计
    conn = _get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRESQL else "?"
        
        cur.execute("SELECT COUNT(*) FROM prompt_templates")
        total = cur.fetchone()[0]
        
        cur.execute(f"SELECT COUNT(*) FROM prompt_templates WHERE is_active = {placeholder}", (1,))
        active = cur.fetchone()[0]
        
        if total == 0:
            print("❌ 数据库中没有提示词")
            print("\n下一步:")
            print("   运行: python fastnpc/scripts/init_prompts.py")
        elif active == 0:
            print("⚠️  有提示词但没有激活的")
            print("\n下一步:")
            print("   在Web管理界面中激活需要的提示词版本")
        else:
            print("✅ 提示词系统运行正常")
            print(f"   数据库中共有 {total} 个提示词，{active} 个已激活")
            print("\n✨ 您可以在Web管理界面中:")
            print("   1. 查看和编辑提示词")
            print("   2. 创建新版本")
            print("   3. 激活不同版本")
            print("   4. 对比版本差异")
            print("\n💡 修改提示词后，点击'激活'按钮即可立即生效！")
    
    except Exception as e:
        print(f"❌ 生成总结失败: {e}")
    finally:
        _return_conn(conn)


def main():
    """主函数"""
    print("\n" + "🔍 FastNPC 提示词系统状态检查".center(60, "="))
    
    try:
        check_config()
        check_database_prompts()
        check_active_prompts()
        check_evaluators()
        check_cache()
        test_prompt_rendering()
        generate_summary()
        
    except Exception as e:
        print(f"\n❌ 检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("检查完成！".center(60))
    print("=" * 60 + "\n")
    
    print("📚 详细文档: docs/PROMPT_VERSIONING_STATUS.md")
    print()


if __name__ == "__main__":
    main()

