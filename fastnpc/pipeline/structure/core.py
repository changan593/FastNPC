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
from .prompts import _category_prompts, _call_category_llm, _call_category_llm_async, _generate_persona_brief


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
    
    # 并发生成九大类，受 MAX_CONCURRENCY 限制
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

    # 补充来源信息的元数据（如果LLM没有生成或信息不全）
    try:
        if "来源" not in results or not isinstance(results.get("来源"), dict):
            results["来源"] = {}
        
        source_info = results["来源"]
        
        # 提取实际的数据源信息
        page_link = ''
        if isinstance(data, dict):
            page_link = str(data.get('url') or data.get('source') or '').strip()
        
        # 只在缺失时补充链接
        if not source_info.get('链接') and page_link:
            source_info['链接'] = page_link
        
        # 补充来源信息量（原始数据大小）
        if not source_info.get('来源信息量'):
            try:
                if isinstance(source_text, str):
                    char_count = len(source_text)
                    source_info['来源信息量'] = f"约{char_count}字"
            except Exception:
                pass
        
        results["来源"] = source_info
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


# ========== 异步版本（新增）==========


async def run_async(
    input_path: str,
    output_path: Optional[str] = None,
    level: str = "detailed",
    *,
    export_facts: bool = False,
    facts_output_path: Optional[str] = None,
    export_bullets: bool = False,
    bullets_output_path: Optional[str] = None,
    strategy: str = "global",
    export_summary: bool = False,
    summary_output_path: Optional[str] = None,
    export_markdown: bool = False,
    markdown_output_path: Optional[str] = None,
) -> str:
    """
    异步主流程：从原始数据生成结构化角色画像（并行生成9个类别）
    
    性能提升：从串行20-60秒 → 并行3-8秒（5-8倍）
    """
    import asyncio
    
    raw_text = read_text(input_path)
    data = try_load_json(input_path)
    source_text = ensure_string_source(data, raw_text)
    max_chunks = 6 if level == 'concise' else 8
    
    # 人物名（用于提示一致性）
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

    # Markdown转换
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
    
    # 异步并行生成九大类（🚀 关键优化：同时调用9个LLM）
    tasks = []
    categories = []
    for cat, ptxt in prompts.items():
        tasks.append(_call_category_llm_async(cat, ptxt, markdown_text))
        categories.append(cat)
    
    try:
        # 并行执行所有LLM调用
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        results = {}
        for cat, res in zip(categories, results_list):
            if isinstance(res, Exception):
                results[cat] = {}
            elif isinstance(res, dict):
                results[cat] = res
            else:
                results[cat] = {}
    except Exception:
        # 回退到串行（理论上不会发生）
        results = {}
        for cat, ptxt in prompts.items():
            try:
                js = await _call_category_llm_async(cat, ptxt, markdown_text)
                results[cat] = js if isinstance(js, dict) else {}
            except Exception:
                results[cat] = {}

    # 简介
    brief = _generate_persona_brief(results, persona_name, choose_person="third")
    base = results.get("基础身份信息", {}) or {}
    if isinstance(base, dict) and brief:
        base["人物简介"] = brief
        results["基础身份信息"] = base

    # 补充来源信息的元数据（如果LLM没有生成或信息不全）
    try:
        if "来源" not in results or not isinstance(results.get("来源"), dict):
            results["来源"] = {}
        
        source_info = results["来源"]
        
        # 提取实际的数据源信息
        page_link = ''
        if isinstance(data, dict):
            page_link = str(data.get('url') or data.get('source') or '').strip()
        
        # 只在缺失时补充链接
        if not source_info.get('链接') and page_link:
            source_info['链接'] = page_link
        
        # 补充来源信息量（原始数据大小）
        if not source_info.get('来源信息量'):
            try:
                if isinstance(source_text, str):
                    char_count = len(source_text)
                    source_info['来源信息量'] = f"约{char_count}字"
            except Exception:
                pass
        
        results["来源"] = source_info
    except Exception:
        pass

    structured = results
    
    # 预留记忆字段（三层记忆系统）
    structured["短期记忆"] = []
    structured["长期记忆"] = []

    # 输出路径
    if not output_path:
        base_dir = os.path.dirname(input_path)
        base_name = os.path.basename(input_path)
        name_wo_ext = os.path.splitext(base_name)[0]
        derived_name = name_wo_ext.replace('zhwiki_', '').replace('baike_', '')
        output_path = os.path.join(base_dir, f"structured_{derived_name}.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    return output_path

