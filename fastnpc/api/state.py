# -*- coding: utf-8 -*-
"""
状态管理模块：管理任务和会话状态
"""
from __future__ import annotations

import os
import shutil
import json
import threading
from typing import Any, Dict, Optional
import time

from fastnpc.config import CHAR_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.pipeline.collect import collect as pipeline_collect
from fastnpc.pipeline.structure import run as structure_run
from fastnpc.api.auth import update_character_structured


CHAR_DIR_STR = CHAR_DIR.as_posix()


class TaskState:
    def __init__(self, role: str, source: str, model: str, user_id: Optional[int] = None, detail: str = "detailed",
                 choice_index: Optional[int] = None, filter_text: Optional[str] = None, chosen_href: Optional[str] = None,
                 export_facts: bool = False, export_bullets: bool = False,
                 export_summary: bool = False, export_md: bool = False):
        self.role = role
        self.source = source
        self.model = model
        self.user_id = user_id
        self.detail = detail
        self.choice_index = choice_index
        self.filter_text = filter_text
        self.chosen_href = chosen_href
        self.export_facts = export_facts
        self.export_bullets = export_bullets
        self.export_summary = export_summary
        self.export_md = export_md
        self.progress: int = 0
        self.status: str = "pending"  # pending | running | done | error
        self.message: str = ""
        self.raw_path: str = ""
        self.structured_path: str = ""
        self.started_at: int = int(time.time())


tasks_lock = threading.Lock()
tasks: Dict[str, TaskState] = {}

sessions_lock = threading.Lock()
# 会话: session_id -> { messages: List[Dict[str,str]], role: str }
sessions: Dict[str, Dict[str, Any]] = {}


def _set_task(task_id: str, **fields: Any) -> None:
    with tasks_lock:
        t = tasks.get(task_id)
        if not t:
            return
        for k, v in fields.items():
            setattr(t, k, v)


def _collect_and_structure(task_id: str) -> None:
    t = tasks.get(task_id)
    if not t:
        return
    try:
        _set_task(task_id, status="running", progress=5, message="准备开始…")

        role = t.role.strip()
        source = t.source
        model = t.model
        user_id = t.user_id or 0
        detail = t.detail or "detailed"
        choice_index = getattr(t, 'choice_index', None)
        filter_text = getattr(t, 'filter_text', None)
        chosen_href = getattr(t, 'chosen_href', None)
        export_facts = bool(getattr(t, 'export_facts', False))
        export_bullets = bool(getattr(t, 'export_bullets', False))
        export_summary = bool(getattr(t, 'export_summary', False))
        export_md = bool(getattr(t, 'export_md', False))

        # 1) 数据抓取
        _set_task(task_id, progress=10, message=f"正在从 {source} 抓取数据…")
        role = normalize_role_name(role)
        raw_path = pipeline_collect(role, source, choice_index=choice_index, filter_text=filter_text, chosen_href=chosen_href)
        _set_task(task_id, progress=40, message="数据抓取完成，开始结构化…", raw_path=raw_path)

        # 2) 结构化
        structured_path = structure_run(
            raw_path,
            None,
            level=detail,
            export_facts=export_facts,
            facts_output_path=None,
            export_bullets=export_bullets,
            bullets_output_path=None,
            strategy="global",
            export_summary=export_summary,
            summary_output_path=None,
            export_markdown=export_md,
            markdown_output_path=None,
        )
        _set_task(task_id, progress=90, message="结构化完成，收尾中…", structured_path=structured_path)

        # 移动文件到用户私有目录
        try:
            if user_id:
                user_dir = os.path.join(CHAR_DIR_STR, str(user_id))
                os.makedirs(user_dir, exist_ok=True)
                if os.path.exists(raw_path):
                    shutil.move(raw_path, os.path.join(user_dir, os.path.basename(raw_path)))
                if os.path.exists(structured_path):
                    new_spath = os.path.join(user_dir, os.path.basename(structured_path))
                    shutil.move(structured_path, new_spath)
                    # 同步到 DB
                    try:
                        with open(new_spath, 'r', encoding='utf-8') as sf:
                            prof = json.load(sf)
                        update_character_structured(int(user_id), role, json.dumps(prof, ensure_ascii=False))
                    except Exception:
                        pass
                # 同步移动可选导出的 facts 与 bullets
                try:
                    # 与 structure.run 的默认命名保持一致
                    base_dir = os.path.dirname(raw_path)
                    base_name = os.path.basename(raw_path)
                    name_wo_ext = os.path.splitext(base_name)[0]
                    derived = name_wo_ext.replace('zhwiki_', '').replace('baike_', '')
                    facts_p = os.path.join(base_dir, f"facts_{derived}.json")
                    bullets_p = os.path.join(base_dir, f"bullets_{derived}.txt")
                    summary_p = os.path.join(base_dir, f"summary_{derived}.txt")
                    md_p = os.path.join(base_dir, f"md_{derived}.md")
                    if export_facts and os.path.exists(facts_p):
                        shutil.move(facts_p, os.path.join(user_dir, os.path.basename(facts_p)))
                    if export_bullets and os.path.exists(bullets_p):
                        shutil.move(bullets_p, os.path.join(user_dir, os.path.basename(bullets_p)))
                    if export_summary and os.path.exists(summary_p):
                        shutil.move(summary_p, os.path.join(user_dir, os.path.basename(summary_p)))
                    if export_md and os.path.exists(md_p):
                        shutil.move(md_p, os.path.join(user_dir, os.path.basename(md_p)))
                except Exception:
                    pass
        except Exception:
            pass

        _set_task(task_id, status="done", progress=100, message="已完成")
    except Exception as e:
        _set_task(task_id, status="error", message=f"发生错误: {e}")

