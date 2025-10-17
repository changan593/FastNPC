# -*- coding: utf-8 -*-
"""
FastNPC 结构化处理模块

将原始数据（baike/zhwiki）转换为结构化的角色画像
"""
from __future__ import annotations

# 导出公共 API，保持原有导入方式兼容
from .core import run, run_async
from .prompts import build_system_prompt

__all__ = ['run', 'run_async', 'build_system_prompt']

