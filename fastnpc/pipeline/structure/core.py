# -*- coding: utf-8 -*-
"""
结构化处理核心流程
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastnpc.config import MAX_CONCURRENCY
from .io_utils import read_text, try_load_json
from .processors import ensure_string_source, json_to_markdown
from .prompts import _category_prompts, _call_category_llm, _generate_persona_brief


def run(
    input_path: str,
    output_path: Optional[str] = None,
    level: str = "detailed",
    *,
    export_facts: bool = False,
    facts_output_path: Optional[str] = None,
    export_bullets: bool = False,
    bullets_output_path: Optional[str] = None,
    strategy: str = "global",  # global | mapreduce
    export_summary: bool = False,
    summary_output_path: Optional[str] = None,
    export_markdown: bool = False,
    markdown_output_path: Optional[str] = None,
) -> str:
    """
    主流程：从原始数据生成结构化角色画像
    
    Args:
        input_path: 输入文件路径
        output_path: 输出路径（可选）
        level: 详细程度（detailed/concise）
        export_facts: 是否导出事实
        facts_output_path: 事实输出路径
        export_bullets: 是否导出要点
        bullets_output_path: 要点输出路径
        strategy: 策略（global/mapreduce）
        export_summary: 是否导出摘要
        summary_output_path: 摘要输出路径
        export_markdown: 是否导出 Markdown
        markdown_output_path: Markdown 输出路径
    
    Returns:
        输出文件路径
    """
    raw_text = read_text(input_path)
    data = try_load_json(input_path)
    source_text = ensure_string_source(data, raw_text)
    max_chunks = 6 if level == 'concise' else 8
    
    # 人物名（用于提示一致性）：优先使用"用户创建时的角色名"（来自文件名）
    persona_name = "角色"
    try:
        base_name = os.path.basename(input_path)
        name_wo_ext = os.path.splitext(base_name)[0]
        if name_wo_ext.startswith('baike_'):
            persona_name = name_wo_ext[len('baike_'):]
        elif name_wo_ext.startswith('zhwiki_'):
            persona_name = name_wo_ext[len('zhwiki_'):]
        else:
            persona_name = name_wo_ext
        persona_name = str(persona_name or '角色').strip() or '角色'
        # 去掉创建时添加的时间戳后缀（YYYYMMDDHHmm）
        try:
            persona_name = re.sub(r"\d{12}$", "", persona_name).strip() or persona_name
        except Exception:
            pass
    except Exception:
        try:
            if isinstance(data, dict):
                persona_name = str(data.get('title') or data.get('keyword') or '角色').strip() or '角色'
        except Exception:
            persona_name = '角色'

    # 新实现：直接基于完整 JSON → Markdown 的事实，按八大类分别调用 LLM
    try:
        markdown_text = json_to_markdown(data if data is not None else source_text)
    except Exception:
        markdown_text = source_text
    
    if export_markdown:
        try:
            base_dir = os.path.dirname(input_path)
            base_name = os.path.basename(input_path)
            name_wo_ext = os.path.splitext(base_name)[0]
            derived_name = name_wo_ext.replace('zhwiki_', '').replace('baike_', '')
            md_out = markdown_output_path or os.path.join(base_dir, f"md_{derived_name}.md")
            with open(md_out, "w", encoding="utf-8") as f:
                f.write(markdown_text)
        except Exception:
            pass

    prompts = _category_prompts(persona_name)
    results: Dict[str, Any] = {}
    
    # 并发生成八大类，受 MAX_CONCURRENCY 限制
    max_workers = max(1, int(MAX_CONCURRENCY or 4))
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(_call_category_llm, cat, ptxt, markdown_text): cat for cat, ptxt in prompts.items()}
            for fut in as_completed(future_map):
                cat = future_map[fut]
                try:
                    js = fut.result()
                except Exception:
                    js = {}
                results[cat] = js if isinstance(js, dict) else {}
    except Exception:
        # 发生异常则回退至串行
        for cat, ptxt in prompts.items():
            js = _call_category_llm(cat, ptxt, markdown_text)
            results[cat] = js if isinstance(js, dict) else {}

    # 简介
    brief = _generate_persona_brief(results, persona_name, choose_person="third")
    base = results.get("基础身份信息", {}) or {}
    if isinstance(base, dict) and brief:
        base["人物简介"] = brief
        results["基础身份信息"] = base

    # 来源信息（唯一标识 + 链接）
    try:
        # 角色名（保留用户输入形态：来自文件名去前缀）
        base_name = os.path.basename(input_path)
        name_wo_ext = os.path.splitext(base_name)[0]
        if name_wo_ext.startswith('baike_'):
            role_input = name_wo_ext[len('baike_'):]
        elif name_wo_ext.startswith('zhwiki_'):
            role_input = name_wo_ext[len('zhwiki_'):]
        else:
            role_input = name_wo_ext
        # 用户ID（若位于 Characters/<uid>/ 路径）
        uid = None
        try:
            parts = os.path.normpath(input_path).split(os.sep)
            if 'Characters' in parts:
                idx = parts.index('Characters')
                if idx + 1 < len(parts):
                    _maybe = parts[idx + 1]
                    if _maybe.isdigit():
                        uid = _maybe
        except Exception:
            uid = None
        # 消歧选择信息：优先使用抓取后的 page title；否则 keyword
        chosen_label = ''
        page_link = ''
        if isinstance(data, dict):
            chosen_label = str(data.get('title') or data.get('keyword') or '').strip()
            page_link = str(data.get('url') or data.get('source') or '').strip()
        # 唯一标识：用户/<角色名>_<选择信息>（无 uid 时省略前缀）
        unique_id = f"{role_input}_{chosen_label}" if chosen_label else role_input
        if uid:
            unique_id = f"{uid}/{unique_id}"
        results["来源信息"] = {
            "唯一标识": unique_id,
            "链接": page_link,
        }
    except Exception:
        pass

    structured = results
    
    # 预留记忆字段（三层记忆系统）
    structured["短期记忆"] = []
    structured["长期记忆"] = []

    if not output_path:
        base_dir = os.path.dirname(input_path)
        base_name = os.path.basename(input_path)
        name_wo_ext = os.path.splitext(base_name)[0]
        output_path = os.path.join(base_dir, f"structured_{name_wo_ext.replace('zhwiki_', '').replace('baike_', '')}.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    return output_path

