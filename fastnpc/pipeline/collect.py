# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional

from fastnpc.datasources.zhwiki import get_full as zhwiki_get_full
from fastnpc.datasources.baike import get_full as baike_get_full
from fastnpc.config import CHAR_DIR
from fastnpc.utils.roles import normalize_role_name


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
            choice_index: Optional[int] = None, filter_text: Optional[str] = None, chosen_href: Optional[str] = None) -> str:
    """根据数据源抓取并写入 Characters 目录，返回写入文件路径。"""
    os.makedirs(DEFAULT_CHAR_DIR, exist_ok=True)
    role = normalize_role_name(role)
    # UI 可能为避免重名在尾部追加时间戳；抓取时使用去后缀的关键词以命中真实词条
    query_keyword = _strip_trailing_numeric_suffix(role)

    if source == 'zhwiki':
        data = zhwiki_get_full(query_keyword, retries=retries, min_sections=min_sections, min_chars=min_chars,
                               choice_index=choice_index, filter_text=filter_text)
        out_path = os.path.join(DEFAULT_CHAR_DIR, f"zhwiki_{role}.json")
    elif source == 'baike':
        # 若前端已选择具体链接，可直接按链接抓取（通过 filter_text/choice_index 兜底）
        data = baike_get_full(query_keyword, retries=retries, min_sections=min_sections, min_chars=min_chars,
                              choice_index=choice_index, filter_text=filter_text, chosen_url=chosen_href)
        out_path = os.path.join(DEFAULT_CHAR_DIR, f"baike_{role}.json")
    else:
        raise ValueError('不支持的数据源')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_path


