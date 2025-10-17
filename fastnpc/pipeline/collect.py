# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import json
import tempfile
from typing import Dict, Any, Optional, Tuple

from fastnpc.datasources.zhwiki import get_full as zhwiki_get_full
from fastnpc.datasources.baike import get_full as baike_get_full
from fastnpc.datasources.baike_robust import get_full_robust as baike_get_full_robust
from fastnpc.config import CHAR_DIR
from fastnpc.utils.roles import normalize_role_name

# 配置：优先使用高鲁棒性爬虫
USE_ROBUST_CRAWLER = True


DEFAULT_CHAR_DIR = CHAR_DIR.as_posix()


def _strip_trailing_numeric_suffix(name: str) -> str:
    """去掉角色名末尾的长数字后缀（用于 UI 追加时间戳的场景）。

    规则：删除末尾连续 ≥8 位数字（常见为 YYYYMMDDhhmm）。
    对于本就包含少量数字的正常名称影响极小。
    """
    try:
        m = re.search(r"(.*?)(\d{8,})$", name)
        if m:
            base = m.group(1)
            return base if base.strip() else name
        return name
    except Exception:
        return name


def collect(role: str, source: str, *, retries: int = 5, min_sections: int = 0, min_chars: int = 500, force_amp: bool = False,
            choice_index: Optional[int] = None, filter_text: Optional[str] = None, chosen_href: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
    """根据数据源抓取百科内容，返回 (data, temp_file_path) 元组。
    
    注意：返回的临时文件仅供调试/备份，调用方应在使用后删除。
    """
    role = normalize_role_name(role)
    # UI 可能为避免重名在尾部追加时间戳；抓取时使用去后缀的关键词以命中真实词条
    query_keyword = _strip_trailing_numeric_suffix(role)

    if source == 'zhwiki':
        data = zhwiki_get_full(query_keyword, retries=retries, min_sections=min_sections, min_chars=min_chars,
                               choice_index=choice_index, filter_text=filter_text)
        prefix = f"zhwiki_{role}_"
    elif source == 'baike':
        # 使用高鲁棒性爬虫（基于Playwright）
        if USE_ROBUST_CRAWLER:
            print(f"[INFO] 使用高鲁棒性爬虫抓取: {query_keyword}")
            data = baike_get_full_robust(query_keyword, retries=retries, chosen_url=chosen_href)
        else:
            # 传统爬虫（回退方案）
            data = baike_get_full(query_keyword, retries=retries, min_sections=min_sections, min_chars=min_chars,
                                  choice_index=choice_index, filter_text=filter_text, chosen_url=chosen_href)
        prefix = f"baike_{role}_"
    else:
        raise ValueError('不支持的数据源')

    # 写入临时文件（供调试或后续处理使用）
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix=prefix, suffix='.json', delete=False) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path = f.name
    
    return data, temp_path


