# -*- coding: utf-8 -*-
"""
FastNPC 结构化处理模块 - 兼容入口

为了保持向后兼容性，这个文件重新导出所有公共接口。
实际实现已经拆分到 structure/ 子模块中。

拆分后的模块结构：
- structure/core.py         - 主流程
- structure/prompts.py      - Prompt 模板和 LLM 调用
- structure/processors.py   - 文本处理和格式转换
- structure/io_utils.py     - 文件 I/O
- structure/cli.py          - 命令行接口
"""
from __future__ import annotations

# 从新模块导入所有公共接口，保持完全兼容
from .structure import run, build_system_prompt
from .structure.cli import main

__all__ = ['run', 'build_system_prompt', 'main']

# 如果直接运行此文件，调用 CLI
if __name__ == "__main__":
    main()
