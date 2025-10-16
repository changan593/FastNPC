# -*- coding: utf-8 -*-
from __future__ import annotations

import re


_ALLOWED_PATTERN = re.compile(r"[^\w\u4e00-\u9fa5\-\s]+", re.UNICODE)


def normalize_role_name(name: str, *, max_len: int = 64) -> str:
    """将角色名规范化为安全的文件名片段：
    - 允许 汉字/字母/数字/下划线/连字符/空格
    - 其它字符替换为下划线
    - 合并重复空白为单空格并去首尾
    - 限制最大长度
    - 空结果回退为 'role'
    """
    if not isinstance(name, str):
        return "role"
    s = name.strip()
    if not s:
        return "role"
    # 替换非法字符
    s = _ALLOWED_PATTERN.sub("_", s)
    # 归一空白
    s = re.sub(r"\s+", " ", s).strip()
    # 长度限制
    if len(s) > max_len:
        s = s[:max_len].rstrip()
    return s or "role"


