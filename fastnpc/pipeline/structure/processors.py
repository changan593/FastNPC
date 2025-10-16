# -*- coding: utf-8 -*-
"""
文本处理和格式转换模块
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple


def ensure_string_source(data: Any, fallback_text: str) -> str:
    """确保返回字符串源数据"""
    try:
        # 变更：若是 JSON（dict/list），整体序列化为字符串作为源文本，
        # 不再优先抽取 summary/text 等单字段，避免信息不足。
        if isinstance(data, (dict, list)):
            return json.dumps(data, ensure_ascii=False)
        if data is not None:
            return str(data)
        return fallback_text
    except Exception:
        return fallback_text


def chunk_text(text: str, max_chars: int = 12000) -> List[str]:
    """将文本按段落分块，每块不超过 max_chars 字符"""
    if not text:
        return []
    paragraphs = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if current_len + len(p) + 2 <= max_chars:
            current.append(p)
            current_len += len(p) + 2
        else:
            if current:
                chunks.append("\n\n".join(current))
            current = [p]
            current_len = len(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def parse_json_from_text(text: str) -> Optional[Any]:
    """从文本中提取并解析 JSON"""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        start_idx = min([idx for idx in [text.find("{"), text.find("[")] if idx != -1])
    except ValueError:
        start_idx = -1
    if start_idx == -1:
        return None
    candidate = text[start_idx:]
    last_brace = max(candidate.rfind("}"), candidate.rfind("]"))
    if last_brace != -1:
        candidate = candidate[: last_brace + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def json_to_markdown(data: Any) -> str:
    """将较通用的抓取 JSON（baike/zhwiki）转换成 Markdown。

    规则：
    - 若包含 title/keyword/summary/sections，优先按常见结构排版
    - 其余键以递归方式渲染为标题与项目符号，限制深度，避免过度膨胀
    """
    try:
        lines: List[str] = []

        def write_kv_table(obj: Dict[str, Any], keys: List[str]) -> None:
            kvs: List[Tuple[str, str]] = []
            for k in keys:
                v = obj.get(k)
                if isinstance(v, (str, int, float)) and str(v).strip():
                    kvs.append((k, str(v).strip()))
            if not kvs:
                return
            lines.append("")
            lines.append("| 键 | 值 |")
            lines.append("|---|---|")
            for k, v in kvs:
                v = v.replace("\n", " ")
                lines.append(f"| {k} | {v} |")
            lines.append("")

        def render_any(key: Optional[str], value: Any, depth: int = 0) -> None:
            if depth > 4:
                # 深度限制，防止过深嵌套
                try:
                    s = json.dumps(value, ensure_ascii=False)
                except Exception:
                    s = str(value)
                if s:
                    lines.append(s)
                return
            if isinstance(value, dict):
                if key:
                    lines.append(("#" * min(6, depth + 2)) + f" {key}")
                # 常见字段优先
                title = str(value.get("title") or value.get("keyword") or "").strip()
                summary = str(value.get("summary") or "").strip()
                if title and not key:
                    lines.append(f"# {title}")
                if summary:
                    lines.append("## 概述")
                    lines.append(summary)
                # sections 专用渲染
                secs = value.get("sections")
                if isinstance(secs, list) and secs:
                    for sec in secs:
                        if not isinstance(sec, dict):
                            continue
                        st = str(sec.get("title") or "").strip()
                        if st:
                            lines.append("## " + st)
                        paras = sec.get("paragraphs") or sec.get("paras") or sec.get("content")
                        if isinstance(paras, list):
                            for p in paras:
                                ps = str(p or "").strip()
                                if ps:
                                    lines.append(ps)
                        elif isinstance(paras, str):
                            ps = paras.strip()
                            if ps:
                                lines.append(ps)
                # 其余键
                for k, v in value.items():
                    if k in {"title", "keyword", "summary", "sections"}:
                        continue
                    render_any(k, v, depth + 1)
            elif isinstance(value, list):
                if key:
                    lines.append(("#" * min(6, depth + 2)) + f" {key}")
                count = 0
                for it in value:
                    count += 1
                    if isinstance(it, (str, int, float)):
                        lines.append(f"- {str(it)}")
                    elif isinstance(it, dict):
                        # 尝试单行描述，否则递归
                        title = str(it.get("title") or it.get("name") or "").strip()
                        if title:
                            lines.append(f"- {title}")
                            # 继续展开关键字段
                            sub = {k: v for k, v in it.items() if k not in {"title", "name"}}
                            if sub:
                                render_any(None, sub, depth + 1)
                        else:
                            render_any(None, it, depth + 1)
                    else:
                        render_any(None, it, depth + 1)
                    if count > 2000:
                        # 极端保护：避免异常大数组
                        break
            else:
                s = str(value or "").strip()
                if s:
                    if key:
                        lines.append(("#" * min(6, depth + 2)) + f" {key}")
                    lines.append(s)

        if isinstance(data, (dict, list)):
            render_any(None, data, 0)
        else:
            try:
                # 若已经是文本
                return str(data)
            except Exception:
                return ""
        return "\n\n".join(lines)
    except Exception:
        try:
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return str(data or "")

