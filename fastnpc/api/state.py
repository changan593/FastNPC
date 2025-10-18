# -*- coding: utf-8 -*-
"""
状态管理模块：管理任务和会话状态
"""
from __future__ import annotations

import os
import re
import shutil
import json
import threading
from typing import Any, Dict, Optional
import time

from fastnpc.config import CHAR_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.pipeline.collect import collect as pipeline_collect
from fastnpc.pipeline.structure import run as structure_run, run_async as structure_run_async
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
        self.status: str = "pending"  # pending | running | done | error | cancelled
        self.message: str = ""
        self.raw_path: str = ""
        self.structured_path: str = ""
        self.started_at: int = int(time.time())
        self.cancelled: bool = False  # 新增：取消标志


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


def _cleanup_temp_files(file_paths: List[str]) -> None:
    """清理临时文件"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                print(f"[INFO] 已删除临时文件: {path}")
            except Exception as e:
                print(f"[WARNING] 删除临时文件失败 {path}: {e}")


def _collect_and_structure(task_id: str) -> None:
    print(f"[INFO] ======== 后台任务开始执行: task_id={task_id} ========")
    t = tasks.get(task_id)
    if not t:
        print(f"[ERROR] 任务 {task_id} 不存在于tasks字典中！")
        return
    try:
        print(f"[INFO] 更新任务状态为 running, progress=5")
        _set_task(task_id, status="running", progress=5, message="准备开始…")
        print(f"[INFO] 任务状态已更新，当前进度: {tasks.get(task_id).progress if tasks.get(task_id) else 'N/A'}")

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

        # 检查取消标志
        if t.cancelled:
            print(f"[INFO] 任务 {task_id} 已被取消（准备阶段）")
            _set_task(task_id, status="cancelled", message="已取消")
            return

        # 1) 数据抓取
        print(f"[INFO] ========开始数据抓取阶段========")
        print(f"[INFO] 任务ID: {task_id}")
        print(f"[INFO] 角色名（原始）: {role}")
        _set_task(task_id, progress=10, message=f"正在从 {source} 抓取数据…")
        role = normalize_role_name(role)
        print(f"[INFO] 角色名（规范化）: {role}")
        print(f"[INFO] chosen_href参数: {chosen_href}")
        print(f"[INFO] 调用 pipeline_collect...")
        raw_data, raw_path = pipeline_collect(role, source, choice_index=choice_index, filter_text=filter_text, chosen_href=chosen_href)
        print(f"[INFO] 数据抓取完成")
        print(f"[INFO] raw_path: {raw_path}")
        print(f"[INFO] raw_data title: {raw_data.get('title', 'N/A')}")
        print(f"[INFO] raw_data keyword: {raw_data.get('keyword', 'N/A')}")
        
        # 验证 title 和 keyword 的一致性（防止浏览器缓存导致的数据污染）
        raw_title = raw_data.get('title', '')
        raw_keyword = raw_data.get('keyword', '')
        # 提取角色名的核心部分（去掉时间戳）
        import re
        core_role = re.sub(r'\d{12}$', '', role).strip()
        
        # 检查 title 或 keyword 是否包含角色名的核心部分
        title_match = core_role in raw_title if raw_title else False
        keyword_match = core_role in raw_keyword if raw_keyword else False
        
        if not title_match and not keyword_match:
            print(f"[WARNING] ⚠️  数据验证失败：爬取的内容与目标角色不匹配！")
            print(f"[WARNING] 目标角色: {core_role}")
            print(f"[WARNING] 爬取到的 title: {raw_title}")
            print(f"[WARNING] 爬取到的 keyword: {raw_keyword}")
            print(f"[WARNING] 这可能是浏览器缓存导致的，建议用户重试")
            # 不强制中断，但记录警告
        elif not title_match and keyword_match:
            print(f"[WARNING] ⚠️  title 不匹配但 keyword 匹配，可能存在浏览器缓存问题")
            print(f"[WARNING] title: {raw_title}, keyword: {raw_keyword}, 目标: {core_role}")
        
        # 检查取消标志
        if t.cancelled:
            print(f"[INFO] 任务 {task_id} 已被取消（数据抓取后）")
            _cleanup_temp_files([raw_path])
            _set_task(task_id, status="cancelled", message="已取消")
            return
        
        _set_task(task_id, progress=40, message="数据抓取完成，开始结构化…", raw_path=raw_path)

        # 2) 结构化（异步并行生成，5-8倍速度提升）
        print(f"[INFO] ========开始结构化阶段========")
        print(f"[INFO] 输入文件: {raw_path}")
        import asyncio
        try:
            # 尝试使用异步版本（并行生成8个类别）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            structured_path = loop.run_until_complete(structure_run_async(
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
            ))
            loop.close()
            print(f"[INFO] 结构化完成（异步）")
        except Exception as e:
            # 回退到同步版本
            print(f"[WARNING] 异步角色生成失败，使用同步版本: {e}")
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
            print(f"[INFO] 结构化完成（同步）")
        
        print(f"[INFO] 结构化输出文件: {structured_path}")
        
        # 检查取消标志
        if t.cancelled:
            print(f"[INFO] 任务 {task_id} 已被取消（结构化后）")
            _cleanup_temp_files([raw_path, structured_path])
            _set_task(task_id, status="cancelled", message="已取消")
            return
        
        _set_task(task_id, progress=90, message="结构化完成，收尾中…", structured_path=structured_path)

        # 保存到数据库并清理临时文件
        temp_files_to_cleanup = [raw_path]  # 临时文件稍后清理
        character_created = False  # 标记是否已创建角色
        
        # 处理头像（如果有）
        avatar_saved_path = None
        try:
            if user_id and raw_data.get('avatar_url'):
                from fastnpc.utils.image_utils import download_and_crop_avatar
                from fastnpc.config import BASE_DIR
                
                avatar_dir = BASE_DIR / "Avatars"
                avatar_filename = f"user_{user_id}_{role}"
                
                print(f"[INFO] 下载并处理头像: {raw_data['avatar_url']}")
                avatar_saved = download_and_crop_avatar(
                    image_url=raw_data['avatar_url'],
                    save_dir=avatar_dir.as_posix(),
                    filename=avatar_filename,
                    size=(256, 256),
                    timeout=15
                )
                
                if avatar_saved:
                    avatar_saved_path = f"/avatars/{avatar_saved}"
                    print(f"[INFO] 头像保存成功: {avatar_saved_path}")
                else:
                    print(f"[WARN] 头像保存失败，将使用默认头像")
        except Exception as e:
            print(f"[WARN] 处理头像失败: {e}")
            avatar_saved_path = None
        
        try:
            if user_id:
                # 将爬取的原始数据转换为JSON字符串（百科全文）
                baike_content = json.dumps(raw_data, ensure_ascii=False, indent=2)
                
                # 读取结构化数据并保存到数据库
                print(f"[INFO] ========检查结构化文件========")
                print(f"[INFO] 结构化文件路径: {structured_path}")
                print(f"[INFO] 文件是否存在: {os.path.exists(structured_path)}")
                if os.path.exists(structured_path):
                    try:
                        with open(structured_path, 'r', encoding='utf-8') as sf:
                            prof = json.load(sf)
                        print(f"[INFO] 结构化数据读取成功")
                        print(f"[INFO] 基础身份信息.姓名: {prof.get('基础身份信息', {}).get('姓名', 'N/A')}")
                        print(f"[INFO] 基础身份信息.人物简介: {prof.get('基础身份信息', {}).get('人物简介', 'N/A')[:100]}...")
                        temp_files_to_cleanup.append(structured_path)
                        
                        # 修正结构化数据中的姓名字段（移除tempfile随机后缀）
                        if '基础身份信息' in prof and '姓名' in prof['基础身份信息']:
                            original_name = prof['基础身份信息']['姓名']
                            # 移除tempfile的随机后缀（如 _2iwftoc0）
                            corrected_name = re.sub(r'_[a-z0-9]{8}', '', original_name)
                            if corrected_name != original_name:
                                print(f"[INFO] 修正姓名字段: {original_name} -> {corrected_name}")
                                prof['基础身份信息']['姓名'] = corrected_name
                                # 同时修正人物简介中的姓名
                                if '人物简介' in prof['基础身份信息']:
                                    prof['基础身份信息']['人物简介'] = prof['基础身份信息']['人物简介'].replace(original_name, corrected_name)
                        
                        # 最后检查取消标志（保存前）
                        if t.cancelled:
                            print(f"[INFO] 任务 {task_id} 已被取消（保存数据库前）")
                            _cleanup_temp_files(temp_files_to_cleanup + [structured_path])
                            _set_task(task_id, status="cancelled", message="已取消")
                            return
                        
                        # 保存到数据库
                        print(f"[INFO] 开始保存角色 {role} 到数据库...")
                        print(f"[DEBUG] 百科内容长度: {len(baike_content)} 字符")
                        print(f"[DEBUG] 章节数: {len(raw_data.get('sections', []))}")
                        save_character_full_data(
                            user_id=int(user_id),
                            name=role,
                            structured_data=prof,
                            baike_content=baike_content,
                            avatar_url=avatar_saved_path
                        )
                        character_created = True
                        print(f"[INFO] 角色 {role} 保存到数据库成功！")
                        
                        # 再次检查取消标志（保存后）
                        if t.cancelled:
                            print(f"[INFO] 任务 {task_id} 已被取消（保存数据库后），删除已创建的角色")
                            try:
                                from fastnpc.api.auth import delete_character
                                print(f"[DEBUG] 开始删除角色: user_id={user_id}, role={role}")
                                delete_character(int(user_id), role)
                                print(f"[INFO] 已成功删除取消任务创建的角色: {role}")
                                
                                # 再次清除角色列表缓存，确保删除后前端能立即看到更新
                                try:
                                    from fastnpc.api.cache import get_redis_cache
                                    cache = get_redis_cache()
                                    cache_key = f"char_list:{user_id}"
                                    cache.delete(cache_key)
                                    print(f"[INFO] 已清除角色列表缓存（取消后）: {cache_key}")
                                except Exception as cache_err:
                                    print(f"[WARNING] 清除缓存失败（取消后）: {cache_err}")
                            except Exception as del_err:
                                print(f"[ERROR] 删除角色失败: {del_err}")
                                import traceback
                                traceback.print_exc()
                            _cleanup_temp_files(temp_files_to_cleanup + [structured_path])
                            _set_task(task_id, status="cancelled", message="已取消")
                            return
                        
                        # 清除角色列表缓存，确保前端能立即看到新角色
                        try:
                            from fastnpc.api.cache import get_redis_cache
                            cache = get_redis_cache()
                            cache_key = f"char_list:{user_id}"
                            cache.delete(cache_key)
                            print(f"[INFO] 已清除角色列表缓存: {cache_key}")
                        except Exception as cache_err:
                            print(f"[WARNING] 清除缓存失败（不影响功能）: {cache_err}")
                        
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

