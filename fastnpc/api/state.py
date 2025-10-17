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
from fastnpc.api.auth import update_character_structured, save_character_full_data


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
        raw_data, raw_path = pipeline_collect(role, source, choice_index=choice_index, filter_text=filter_text, chosen_href=chosen_href)
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

        # 保存到数据库并清理临时文件
        temp_files_to_cleanup = [raw_path]  # 临时文件稍后清理
        try:
            if user_id:
                # 将爬取的原始数据转换为JSON字符串（百科全文）
                baike_content = json.dumps(raw_data, ensure_ascii=False, indent=2)
                
                # 读取结构化数据并保存到数据库
                if os.path.exists(structured_path):
                    try:
                        with open(structured_path, 'r', encoding='utf-8') as sf:
                            prof = json.load(sf)
                        temp_files_to_cleanup.append(structured_path)
                        
                        # 保存到数据库
                        print(f"[INFO] 开始保存角色 {role} 到数据库...")
                        print(f"[DEBUG] 百科内容长度: {len(baike_content)} 字符")
                        print(f"[DEBUG] 章节数: {len(raw_data.get('sections', []))}")
                        save_character_full_data(
                            user_id=int(user_id),
                            name=role,
                            structured_data=prof,
                            baike_content=baike_content
                        )
                        print(f"[INFO] 角色 {role} 保存到数据库成功！")
                        
                        # 清理临时文件
                        for temp_file in temp_files_to_cleanup:
                            try:
                                if os.path.exists(temp_file):
                                    os.remove(temp_file)
                                    print(f"[INFO] 已删除临时文件: {temp_file}")
                            except Exception as e:
                                print(f"[WARNING] 删除临时文件失败 {temp_file}: {e}")
                        
                        # 清理可能的中间产物文件（facts, bullets, summary, md）
                        try:
                            base_dir = os.path.dirname(raw_path)
                            base_name = os.path.basename(raw_path)
                            name_wo_ext = os.path.splitext(base_name)[0]
                            derived = name_wo_ext.replace('zhwiki_', '').replace('baike_', '')
                            
                            optional_files = [
                                os.path.join(base_dir, f"facts_{derived}.json"),
                                os.path.join(base_dir, f"bullets_{derived}.txt"),
                                os.path.join(base_dir, f"summary_{derived}.txt"),
                                os.path.join(base_dir, f"md_{derived}.md"),
                            ]
                            for opt_file in optional_files:
                                if os.path.exists(opt_file):
                                    try:
                                        os.remove(opt_file)
                                        print(f"[INFO] 已删除中间文件: {opt_file}")
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                            
                    except Exception as e:
                        import traceback
                        print(f"[ERROR] 保存角色数据到数据库失败: {e}")
                        print(f"[ERROR] 详细错误: {traceback.format_exc()}")
                        raise  # 抛出异常
        except Exception as e:
            print(f"[ERROR] 角色创建失败: {e}")
            raise

        _set_task(task_id, status="done", progress=100, message="已完成")
    except Exception as e:
        _set_task(task_id, status="error", message=f"发生错误: {e}")

