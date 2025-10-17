# -*- coding: utf-8 -*-
"""
缓存管理API路由
提供缓存统计、清除等管理功能（仅管理员）
"""
from fastapi import APIRouter, Request, HTTPException
from fastnpc.api.cache import get_redis_cache
from fastnpc.api.auth import verify_cookie

router = APIRouter()


def _require_admin(request: Request):
    """验证管理员权限"""
    token = request.cookies.get('fastnpc_auth', '')
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = verify_cookie(token)
    if not session or session.get("is_admin") != 1:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    return session


@router.get("/admin/cache/stats")
def get_cache_stats(request: Request):
    """获取缓存统计（仅管理员）"""
    _require_admin(request)
    
    cache = get_redis_cache()
    stats = cache.get_stats()
    
    # 获取Redis信息
    try:
        info = cache.client.info("memory")
        redis_memory = {
            "used_memory_human": info.get("used_memory_human"),
            "used_memory_peak_human": info.get("used_memory_peak_human"),
            "maxmemory_human": info.get("maxmemory_human"),
        }
    except Exception as e:
        redis_memory = {"error": str(e)}
    
    return {
        "stats": stats,
        "redis_memory": redis_memory
    }


@router.post("/admin/cache/clear")
def clear_cache(request: Request, pattern: str = "*"):
    """清除缓存（仅管理员）
    
    Args:
        pattern: 缓存键模式，默认"*"清除所有
    """
    _require_admin(request)
    
    cache = get_redis_cache()
    
    if pattern == "*":
        cache.clear_all()
        return {"ok": True, "message": "已清除所有缓存"}
    else:
        count = cache.delete_pattern(pattern)
        return {"ok": True, "message": f"已清除 {count} 个缓存项", "count": count}


@router.get("/admin/cache/test")
def test_cache_connection(request: Request):
    """测试Redis连接（仅管理员）"""
    _require_admin(request)
    
    cache = get_redis_cache()
    is_connected = cache.ping()
    
    return {
        "connected": is_connected,
        "message": "Redis连接正常" if is_connected else "Redis连接失败"
    }

