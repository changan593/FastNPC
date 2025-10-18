# -*- coding: utf-8 -*-
"""
头像上传和管理路由
"""
from __future__ import annotations

import os
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse

from fastnpc.config import BASE_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.api.utils import _require_user
from fastnpc.api.auth import get_character_id
from fastnpc.utils.image_utils import download_and_crop_avatar


router = APIRouter()


@router.post('/api/characters/{role}/avatar')
async def upload_character_avatar(role: str, request: Request, file: UploadFile = File(...)):
    """上传或更新角色头像"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    role = normalize_role_name(role)
    uid = int(user['uid'])
    
    # 检查角色是否存在
    char_id = get_character_id(uid, role)
    if not char_id:
        return JSONResponse({"error": "角色不存在"}, status_code=404)
    
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith('image/'):
        return JSONResponse({"error": "只支持图片文件"}, status_code=400)
    
    try:
        # 读取上传的文件
        contents = await file.read()
        
        # 临时保存
        avatars_dir = BASE_DIR / "Avatars"
        avatars_dir.mkdir(exist_ok=True)
        
        temp_path = avatars_dir / f"temp_{uid}_{role}_{file.filename}"
        with open(temp_path, 'wb') as f:
            f.write(contents)
        
        # 使用图片处理工具裁剪和优化
        from PIL import Image
        from io import BytesIO
        
        img = Image.open(temp_path)
        
        # 转换为RGB（处理透明通道）
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 检查图片是否已经是正方形（前端裁剪好的）
        width, height = img.size
        print(f"[DEBUG] 上传图片尺寸: {width}x{height}")
        
        if width == height:
            # 已经是正方形，直接调整大小
            img_resized = img.resize((256, 256), Image.Resampling.LANCZOS)
        else:
            # 不是正方形，进行中心裁剪（适用于直接上传的情况）
            min_side = min(width, height)
            
            left = (width - min_side) // 2
            top = (height - min_side) // 2
            right = left + min_side
            bottom = top + min_side
            
            img_square = img.crop((left, top, right, bottom))
            img_resized = img_square.resize((256, 256), Image.Resampling.LANCZOS)
        
        # 保存为JPEG
        final_filename = f"user_{uid}_{role}.jpg"
        final_path = avatars_dir / final_filename
        img_resized.save(final_path, 'JPEG', quality=85, optimize=True)
        
        # 删除临时文件
        os.remove(temp_path)
        
        # 更新数据库
        from fastnpc.api.auth.char_data import save_character_full_data
        from fastnpc.api.auth import load_character_full_data
        
        # 加载现有数据
        full_data = load_character_full_data(char_id)
        if not full_data:
            return JSONResponse({"error": "加载角色数据失败"}, status_code=500)
        
        # 提取结构化数据
        structured_data = {k: v for k, v in full_data.items() if k not in ['_metadata', 'baike_content']}
        baike_content = full_data.get('baike_content')
        
        # 更新avatar_url
        avatar_url = f"/avatars/{final_filename}"
        
        save_character_full_data(
            user_id=uid,
            name=role,
            structured_data=structured_data,
            baike_content=baike_content,
            avatar_url=avatar_url
        )
        
        # 清除缓存
        try:
            from fastnpc.api.cache import get_redis_cache
            cache = get_redis_cache()
            cache.delete(f"char_profile:{uid}:{role}")
            cache.delete(f"char_list:{uid}")
            print(f"[INFO] 已清除头像更新缓存: {role}")
        except Exception as cache_err:
            print(f"[WARN] 清除缓存失败: {cache_err}")
        
        return {
            "ok": True,
            "avatar_url": avatar_url,
            "message": "头像上传成功"
        }
        
    except Exception as e:
        print(f"[ERROR] 上传头像失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 清理临时文件
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        
        return JSONResponse({"error": f"上传失败: {str(e)}"}, status_code=500)


@router.delete('/api/characters/{role}/avatar')
async def delete_character_avatar(role: str, request: Request):
    """删除角色头像"""
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    
    role = normalize_role_name(role)
    uid = int(user['uid'])
    
    # 检查角色是否存在
    char_id = get_character_id(uid, role)
    if not char_id:
        return JSONResponse({"error": "角色不存在"}, status_code=404)
    
    try:
        # 获取当前头像路径
        from fastnpc.api.auth import load_character_full_data
        full_data = load_character_full_data(char_id)
        if not full_data:
            return JSONResponse({"error": "加载角色数据失败"}, status_code=500)
        
        metadata = full_data.get('_metadata', {})
        current_avatar = metadata.get('avatar_url')
        
        # 删除文件
        if current_avatar:
            avatar_filename = current_avatar.split('/')[-1]
            avatar_path = BASE_DIR / "Avatars" / avatar_filename
            if avatar_path.exists():
                os.remove(avatar_path)
                print(f"[INFO] 已删除头像文件: {avatar_path}")
        
        # 更新数据库
        from fastnpc.api.auth.char_data import save_character_full_data
        structured_data = {k: v for k, v in full_data.items() if k not in ['_metadata', 'baike_content']}
        baike_content = full_data.get('baike_content')
        
        save_character_full_data(
            user_id=uid,
            name=role,
            structured_data=structured_data,
            baike_content=baike_content,
            avatar_url=None
        )
        
        # 清除缓存
        try:
            from fastnpc.api.cache import get_redis_cache
            cache = get_redis_cache()
            cache.delete(f"char_profile:{uid}:{role}")
            cache.delete(f"char_list:{uid}")
        except:
            pass
        
        return {"ok": True, "message": "头像已删除"}
        
    except Exception as e:
        print(f"[ERROR] 删除头像失败: {e}")
        return JSONResponse({"error": f"删除失败: {str(e)}"}, status_code=500)

