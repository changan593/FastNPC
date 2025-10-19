# -*- coding: utf-8 -*-
"""
数据库连接池监控工具

实时监控连接池状态，帮助诊断"连接池耗尽"问题。
"""
import sys
import os
from pathlib import Path
import time
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from fastnpc.api.auth.db_pool import get_pool_status, get_pg_connection_pool
from fastnpc.config import USE_POSTGRESQL


def print_header():
    print("=" * 80)
    print(" " * 20 + "数据库连接池监控工具")
    print("=" * 80)
    print()


def print_status():
    """打印连接池状态"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = get_pool_status()
    
    print(f"[{now}] 连接池状态:")
    print(f"  数据库类型: {status.get('database')}")
    print(f"  连接池启用: {status.get('pool_enabled')}")
    
    if USE_POSTGRESQL:
        print(f"  连接池已创建: {status.get('pool_created')}")
        if status.get('pool_created'):
            print(f"  最小连接数: {status.get('min_connections')}")
            print(f"  最大连接数: {status.get('max_connections')}")
            
            # 尝试获取更详细的信息
            try:
                pool = get_pg_connection_pool()
                # psycopg2.pool 没有直接的API获取当前连接数
                # 但我们可以尝试获取连接来测试可用性
                try:
                    conn = pool.getconn(timeout=0.1)  # 非阻塞获取
                    pool.putconn(conn)
                    print(f"  状态: ✅ 可用 (成功获取测试连接)")
                except Exception as e:
                    print(f"  状态: ⚠️  可能已满 ({type(e).__name__})")
            except Exception as e:
                print(f"  错误: {e}")
    
    print()


def monitor_loop(interval=5):
    """循环监控"""
    print_header()
    print(f"监控间隔: {interval}秒")
    print(f"按 Ctrl+C 停止监控")
    print()
    
    try:
        while True:
            print_status()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n监控已停止")


def test_connection_acquisition(count=10):
    """测试连接获取（压力测试）"""
    print_header()
    print(f"测试连接获取（{count}次）")
    print()
    
    if not USE_POSTGRESQL:
        print("SQLite 不使用连接池，跳过测试")
        return
    
    from fastnpc.api.auth.db_pool import get_connection_from_pool, return_connection_to_pool
    
    connections = []
    success = 0
    failed = 0
    
    # 获取连接
    print(f"尝试获取 {count} 个连接...")
    for i in range(count):
        try:
            start = time.time()
            conn = get_connection_from_pool()
            duration = (time.time() - start) * 1000
            connections.append(conn)
            success += 1
            print(f"  [{i+1}/{count}] ✅ 成功 (耗时: {duration:.1f}ms)")
        except Exception as e:
            failed += 1
            print(f"  [{i+1}/{count}] ❌ 失败: {e}")
    
    print()
    print(f"获取结果: 成功 {success}, 失败 {failed}")
    print()
    
    # 归还连接
    if connections:
        print(f"归还 {len(connections)} 个连接...")
        for i, conn in enumerate(connections):
            try:
                return_connection_to_pool(conn)
                print(f"  [{i+1}/{len(connections)}] ✅ 已归还")
            except Exception as e:
                print(f"  [{i+1}/{len(connections)}] ❌ 归还失败: {e}")
    
    print()
    print("测试完成")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库连接池监控工具')
    parser.add_argument('--mode', choices=['monitor', 'test', 'status'], default='status',
                        help='运行模式: monitor(持续监控), test(压力测试), status(显示状态)')
    parser.add_argument('--interval', type=int, default=5,
                        help='监控间隔（秒），默认5秒')
    parser.add_argument('--count', type=int, default=10,
                        help='测试连接数量，默认10')
    
    args = parser.parse_args()
    
    if args.mode == 'monitor':
        monitor_loop(args.interval)
    elif args.mode == 'test':
        test_connection_acquisition(args.count)
    else:  # status
        print_header()
        print_status()


if __name__ == '__main__':
    main()

