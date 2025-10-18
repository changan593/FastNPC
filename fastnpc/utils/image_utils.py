# -*- coding: utf-8 -*-
"""
图片处理工具模块
提供头像下载、裁剪、保存功能
"""
from __future__ import annotations

import os
import requests
import hashlib
from io import BytesIO
from typing import Optional, Tuple
from pathlib import Path

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def download_and_crop_avatar(
    image_url: str,
    save_dir: str,
    filename: str,
    size: Tuple[int, int] = (256, 256),
    timeout: int = 10
) -> Optional[str]:
    """下载图片并裁剪成正方形头像
    
    Args:
        image_url: 图片URL
        save_dir: 保存目录
        filename: 文件名（不含扩展名）
        size: 目标尺寸（宽，高）
        timeout: 下载超时时间（秒）
    
    Returns:
        保存的文件路径（相对于save_dir），失败返回None
    """
    if not _HAS_PIL:
        print("[WARN] Pillow未安装，无法处理图片")
        return None
    
    if not image_url:
        return None
    
    try:
        # 下载图片
        print(f"[INFO] 下载头像: {image_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://baike.baidu.com/'
        }
        response = requests.get(image_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # 加载图片
        img = Image.open(BytesIO(response.content))
        
        # 转换为RGB（处理PNG透明通道）
        if img.mode in ('RGBA', 'LA', 'P'):
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 裁剪成正方形（中心裁剪）
        width, height = img.size
        min_side = min(width, height)
        
        # 计算裁剪区域（中心）
        left = (width - min_side) // 2
        top = (height - min_side) // 2
        right = left + min_side
        bottom = top + min_side
        
        img_square = img.crop((left, top, right, bottom))
        
        # 调整大小
        img_resized = img_square.resize(size, Image.Resampling.LANCZOS)
        
        # 确保保存目录存在
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存为JPEG（体积更小）
        save_path = os.path.join(save_dir, f"{filename}.jpg")
        img_resized.save(save_path, 'JPEG', quality=85, optimize=True)
        
        print(f"[INFO] 头像已保存: {save_path}")
        return f"{filename}.jpg"
    
    except Exception as e:
        print(f"[ERROR] 下载或处理头像失败: {e}")
        return None


async def process_uploaded_avatar(
    file,
    filename_prefix: str,
    size: Tuple[int, int] = (256, 256),
    quality: int = 85
) -> str:
    """处理上传的头像文件
    
    Args:
        file: FastAPI UploadFile对象
        filename_prefix: 文件名前缀
        size: 目标尺寸（宽，高）
        quality: JPEG质量（1-100）
    
    Returns:
        头像URL路径（如 /avatars/user_1_avatar_abc123.jpg）
    """
    if not _HAS_PIL:
        raise RuntimeError("Pillow未安装，无法处理图片")
    
    from fastnpc.config import BASE_DIR
    
    # 读取文件内容
    content = await file.read()
    
    # 加载图片
    img = Image.open(BytesIO(content))
    
    # 转换为RGB（处理PNG透明通道）
    if img.mode in ('RGBA', 'LA', 'P'):
        # 创建白色背景
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 裁剪成正方形（中心裁剪）
    width, height = img.size
    min_side = min(width, height)
    
    # 计算裁剪区域（中心）
    left = (width - min_side) // 2
    top = (height - min_side) // 2
    right = left + min_side
    bottom = top + min_side
    
    img_square = img.crop((left, top, right, bottom))
    
    # 调整大小
    img_resized = img_square.resize(size, Image.Resampling.LANCZOS)
    
    # 生成唯一文件名（使用内容哈希）
    buffer = BytesIO()
    img_resized.save(buffer, 'JPEG', quality=quality, optimize=True)
    image_bytes = buffer.getvalue()
    file_hash = hashlib.md5(image_bytes).hexdigest()[:8]
    
    # 保存文件
    avatar_dir = BASE_DIR / "Avatars"
    os.makedirs(avatar_dir, exist_ok=True)
    
    final_filename = f"{filename_prefix}_{file_hash}.jpg"
    save_path = avatar_dir / final_filename
    
    with open(save_path, 'wb') as f:
        f.write(image_bytes)
    
    print(f"[INFO] 头像已保存: {save_path}")
    return f"/avatars/{final_filename}"


def extract_baike_avatar_url(html_content: str) -> Optional[str]:
    """从百度百科HTML中提取头像图片URL
    
    根据用户提供的选择器：
    #side > div.abstractAlbum_jhNeu > img
    
    Args:
        html_content: HTML内容
    
    Returns:
        图片URL，未找到返回None
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试多种选择器（从特定到通用）
        selectors = [
            # 用户提供的选择器
            '#side > div.abstractAlbum_jhNeu > img',
            'div.abstractAlbum_jhNeu > img',
            'div.abstractAlbum_jhNeu img',
            # 备用选择器
            'div.summary-pic img',
            'div.lemma-summary img',
            'div.album-wrapper img',
            'div.abstract-album img',
            # 兜底
            '#side img',
        ]
        
        for selector in selectors:
            img = soup.select_one(selector)
            if img:
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if src:
                    # 处理相对URL
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://baike.baidu.com' + src
                    
                    # 过滤掉太小的图片（可能是图标）
                    if 'icon' not in src.lower() and 'logo' not in src.lower():
                        print(f"[INFO] 找到头像URL (使用选择器 {selector}): {src}")
                        return src
        
        print("[WARN] 未找到角色头像图片")
        return None
    
    except Exception as e:
        print(f"[ERROR] 提取头像URL失败: {e}")
        return None

