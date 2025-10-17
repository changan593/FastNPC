#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis缓存测试脚本
测试缓存的读写、TTL、模式删除等功能
"""
import time
import sys
from fastnpc.api.cache import get_redis_cache


def test_redis_connection():
    """测试1: Redis连接"""
    print("=" * 60)
    print("测试1: Redis连接")
    print("=" * 60)
    
    cache = get_redis_cache()
    is_connected = cache.ping()
    
    if is_connected:
        print("✅ Redis连接成功")
    else:
        print("❌ Redis连接失败")
        print("\n请确保：")
        print("  1. Redis服务已启动: sudo systemctl start redis-server")
        print("  2. Redis监听127.0.0.1:6379")
        sys.exit(1)


def test_basic_operations():
    """测试2: 基本操作"""
    print("\n" + "=" * 60)
    print("测试2: 基本缓存操作")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # SET
    print("\n1. 测试 SET...")
    cache.set("test_key", {"name": "测试", "value": 123})
    print("✅ SET 成功")
    
    # GET
    print("\n2. 测试 GET...")
    result = cache.get("test_key")
    assert result == {"name": "测试", "value": 123}
    print(f"✅ GET 成功: {result}")
    
    # EXISTS
    print("\n3. 测试 EXISTS...")
    exists = cache.exists("test_key")
    assert exists == True
    print(f"✅ EXISTS 成功: {exists}")
    
    # DELETE
    print("\n4. 测试 DELETE...")
    cache.delete("test_key")
    result = cache.get("test_key")
    assert result is None
    print("✅ DELETE 成功")


def test_ttl():
    """测试3: TTL过期"""
    print("\n" + "=" * 60)
    print("测试3: TTL自动过期")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # 设置2秒TTL
    print("\n设置缓存（TTL=2秒）...")
    cache.set("ttl_test", "这个会过期", ttl=2)
    
    print("立即读取...")
    result = cache.get("ttl_test")
    assert result == "这个会过期"
    print(f"✅ 读取成功: {result}")
    
    print("\n等待3秒...")
    time.sleep(3)
    
    print("再次读取...")
    result = cache.get("ttl_test")
    assert result is None
    print("✅ 缓存已过期")


def test_pattern_delete():
    """测试4: 模式删除"""
    print("\n" + "=" * 60)
    print("测试4: 模式删除")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # 创建多个key
    print("\n创建多个用户设置缓存...")
    cache.set("user_settings:1", {"user": 1})
    cache.set("user_settings:2", {"user": 2})
    cache.set("user_settings:3", {"user": 3})
    cache.set("other_key", {"other": True})
    print("✅ 创建成功")
    
    # 删除user_settings:*
    print("\n删除 user_settings:* 模式...")
    count = cache.delete_pattern("user_settings:*")
    print(f"✅ 删除了 {count} 个key")
    
    # 验证
    assert cache.get("user_settings:1") is None
    assert cache.get("user_settings:2") is None
    assert cache.get("user_settings:3") is None
    assert cache.get("other_key") == {"other": True}
    print("✅ 验证成功：只删除了匹配的key")
    
    # 清理
    cache.delete("other_key")


def test_performance():
    """测试5: 性能对比"""
    print("\n" + "=" * 60)
    print("测试5: 性能对比（Redis vs 模拟数据库）")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # 模拟数据库查询（延迟50ms）
    def simulate_db_query():
        time.sleep(0.05)
        return {"user": 1, "settings": "data"}
    
    # 第一次查询（数据库 + 写入缓存）
    print("\n第一次查询（模拟数据库 + 写入缓存）...")
    start = time.time()
    result1 = simulate_db_query()
    cache.set("perf_test", result1)
    db_time = time.time() - start
    print(f"耗时: {db_time*1000:.2f}ms")
    
    # 第二次查询（从Redis缓存读取）
    print("\n第二次查询（从Redis缓存读取）...")
    start = time.time()
    result2 = cache.get("perf_test")
    cache_time = time.time() - start
    print(f"耗时: {cache_time*1000:.2f}ms")
    
    assert result1 == result2
    
    speedup = db_time / cache_time if cache_time > 0 else 0
    print(f"\n✅ 性能提升: {speedup:.1f}x")
    print(f"   数据库查询: {db_time*1000:.2f}ms")
    print(f"   Redis缓存: {cache_time*1000:.2f}ms")
    
    # 清理
    cache.delete("perf_test")


def test_cache_stats():
    """测试6: 缓存统计"""
    print("\n" + "=" * 60)
    print("测试6: 缓存统计")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # 重置统计
    cache.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
    
    # 执行一些操作
    cache.set("stat_test", "value")  # +1 set
    cache.get("stat_test")           # +1 hit
    cache.get("stat_test")           # +1 hit
    cache.get("nonexistent")         # +1 miss
    cache.delete("stat_test")        # +1 delete
    
    stats = cache.get_stats()
    print(f"\n统计数据:")
    print(f"  命中: {stats['hits']}")
    print(f"  未命中: {stats['misses']}")
    print(f"  写入: {stats['sets']}")
    print(f"  删除: {stats['deletes']}")
    print(f"  命中率: {stats['hit_rate']}")
    
    assert stats['hits'] == 2
    assert stats['misses'] == 1
    assert stats['sets'] == 1
    assert stats['deletes'] == 1
    print("\n✅ 统计功能正常")


def test_multi_worker_consistency():
    """测试7: 多Worker一致性"""
    print("\n" + "=" * 60)
    print("测试7: 多Worker一致性（模拟）")
    print("=" * 60)
    
    cache = get_redis_cache()
    
    # Worker1写入
    print("\nWorker1: 写入用户设置...")
    cache.set("user_settings:999", {"theme": "dark"})
    print("✅ Worker1写入成功")
    
    # Worker2读取（模拟另一个进程）
    print("\nWorker2: 读取用户设置...")
    result = cache.get("user_settings:999")
    assert result == {"theme": "dark"}
    print(f"✅ Worker2读取成功: {result}")
    
    # Worker1更新并清除缓存
    print("\nWorker1: 更新用户设置并清除缓存...")
    cache.delete("user_settings:999")
    cache.set("user_settings:999", {"theme": "light"})
    print("✅ Worker1更新成功")
    
    # Worker2读取新数据
    print("\nWorker2: 读取更新后的数据...")
    result = cache.get("user_settings:999")
    assert result == {"theme": "light"}
    print(f"✅ Worker2读取到最新数据: {result}")
    
    print("\n✅ 多Worker缓存一致性正常")
    
    # 清理
    cache.delete("user_settings:999")


def main():
    """运行所有测试"""
    print("\n")
    print("🚀 Redis缓存测试开始")
    print("=" * 60)
    
    try:
        test_redis_connection()
        test_basic_operations()
        test_ttl()
        test_pattern_delete()
        test_performance()
        test_cache_stats()
        test_multi_worker_consistency()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n缓存优化已成功实施！")
        print("\n下一步：")
        print("  1. 启动应用: ./start_prod.sh")
        print("  2. 查看缓存统计: http://localhost:8000/admin/cache/stats")
        print("  3. 测试缓存性能")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

