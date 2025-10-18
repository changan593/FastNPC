#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试头像功能
"""

def test_image_utils():
    """测试图片处理工具"""
    from fastnpc.utils.image_utils import download_and_crop_avatar
    import os
    import tempfile
    
    print("=== 测试图片处理工具 ===")
    
    # 测试图片URL（哪吒百度百科）
    test_url = "https://bkimg.cdn.bcebos.com/pic/d439b6003af33a87e9502e63ce5c10385343b5f5"
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"临时目录: {tmpdir}")
        
        # 下载并处理
        result = download_and_crop_avatar(
            image_url=test_url,
            save_dir=tmpdir,
            filename="test_nezha",
            size=(256, 256),
            timeout=15
        )
        
        if result:
            saved_path = os.path.join(tmpdir, result)
            file_size = os.path.getsize(saved_path)
            print(f"✅ 头像保存成功: {result}")
            print(f"✅ 文件大小: {file_size / 1024:.2f} KB")
            
            # 验证文件
            from PIL import Image
            img = Image.open(saved_path)
            print(f"✅ 图片尺寸: {img.size}")
            print(f"✅ 图片格式: {img.format}")
            
            assert img.size == (256, 256), "图片尺寸不正确"
            assert img.format == "JPEG", "图片格式不正确"
            
            print("\n✅ 所有测试通过！")
        else:
            print("❌ 头像下载失败")
            return False
    
    return True


def test_baike_avatar_extraction():
    """测试百度百科头像提取"""
    from fastnpc.datasources.baike_robust import get_full_robust
    
    print("\n=== 测试百度百科头像提取 ===")
    
    # 测试关键词
    keywords = ["哪吒", "孙悟空", "李白"]
    
    for keyword in keywords:
        print(f"\n测试关键词: {keyword}")
        try:
            result = get_full_robust(keyword, retries=1, timeout_ms=15000)
            
            if result.get('avatar_url'):
                print(f"✅ 找到头像: {result['avatar_url']}")
            else:
                print(f"⚠️  未找到头像")
            
            print(f"标题: {result.get('title', 'N/A')}")
            print(f"摘要长度: {len(result.get('summary', ''))}")
            print(f"章节数: {len(result.get('sections', []))}")
            
        except Exception as e:
            print(f"❌ 抓取失败: {e}")
    
    return True


def test_database_migration():
    """测试数据库迁移"""
    from fastnpc.api.auth import _get_conn
    from fastnpc.config import USE_POSTGRESQL
    
    print("\n=== 测试数据库迁移 ===")
    
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 检查 avatar_url 字段是否存在
        if USE_POSTGRESQL:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'characters' AND column_name = 'avatar_url'
            """)
        else:
            cur.execute("PRAGMA table_info(characters)")
            columns = [row[1] for row in cur.fetchall()]
            has_avatar = 'avatar_url' in columns
            
            if has_avatar:
                print("✅ avatar_url 字段已存在")
            else:
                print("❌ avatar_url 字段不存在")
            
            conn.close()
            return has_avatar
        
        row = cur.fetchone()
        if row:
            print("✅ avatar_url 字段已存在")
            conn.close()
            return True
        else:
            print("❌ avatar_url 字段不存在")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        conn.close()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("FastNPC 头像功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 数据库迁移
    try:
        results.append(("数据库迁移", test_database_migration()))
    except Exception as e:
        print(f"数据库迁移测试异常: {e}")
        results.append(("数据库迁移", False))
    
    # 测试2: 图片处理
    try:
        results.append(("图片处理", test_image_utils()))
    except Exception as e:
        print(f"图片处理测试异常: {e}")
        results.append(("图片处理", False))
    
    # 测试3: 百度百科头像提取（可选，需要 Playwright）
    try:
        import playwright
        results.append(("头像提取", test_baike_avatar_extraction()))
    except ImportError:
        print("\n⚠️  Playwright 未安装，跳过头像提取测试")
        results.append(("头像提取", None))
    except Exception as e:
        print(f"头像提取测试异常: {e}")
        results.append(("头像提取", False))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, result in results:
        if result is True:
            status = "✅ 通过"
        elif result is False:
            status = "❌ 失败"
        else:
            status = "⚠️  跳过"
        print(f"{name:20s}: {status}")
    
    passed = sum(1 for _, r in results if r is True)
    total = len([r for r in results if r[1] is not None])
    
    print(f"\n通过: {passed}/{total}")
    
    return all(r is not False for _, r in results)


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

