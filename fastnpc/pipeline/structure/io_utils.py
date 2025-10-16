# -*- coding: utf-8 -*-
"""
文件 I/O 工具模块
"""
from __future__ import annotations

import json
from typing import Optional, Any


def read_text(path: str, encoding: str = "utf-8") -> str:
    """读取文本文件"""
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def try_load_json(path: str) -> Optional[Any]:
    """尝试加载 JSON 文件，失败返回 None"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

