# -*- coding: utf-8 -*-
"""
工具函数模块：提供各种辅助功能
"""
from __future__ import annotations

import os
import json
import uuid
import fcntl
from typing import Any, Dict, List, Optional, Tuple
from fastapi import Request, HTTPException

from fastnpc.config import CHAR_DIR
from fastnpc.utils.roles import normalize_role_name
from fastnpc.api.auth import verify_cookie, list_users, get_or_create_character, update_character_structured
from fastnpc.pipeline.structure import build_system_prompt
from fastnpc.api.state import sessions, sessions_lock


CHAR_DIR_STR = CHAR_DIR.as_posix()


def _require_user(request: Request) -> Optional[Dict[str, Any]]:
    """验证用户身份"""
    token = request.cookies.get('fastnpc_auth', '')
    if not token:
        return None
    data = verify_cookie(token)
    return data


def _require_admin(request: Request) -> Optional[Dict[str, Any]]:
    """验证管理员权限"""
    data = _require_user(request)
    if not data:
        return None
    # 读取 DB 校验 is_admin
    try:
        users = list_users()
        for u in users:
            if int(u['id']) == int(data.get('uid')):
                return data if int(u.get('is_admin', 0)) == 1 else None
    except Exception:
        pass
    return None


def _structured_path_for_role(role: str, user_id: Optional[int] = None) -> str:
    """获取角色结构化文件的路径"""
    # 兼容 Test/test_structure.run 的命名：
    # - zhwiki 输入 -> structured_<role>.json（去掉前缀）
    # - baike 输入  -> structured_baike_<role>.json（未去掉）
    base = CHAR_DIR_STR if not user_id else os.path.join(CHAR_DIR_STR, str(user_id))
    candidates = [
        os.path.join(base, f"structured_{role}.json"),
        os.path.join(base, f"structured_baike_{role}.json"),
        os.path.join(base, f"structured_zhwiki_{role}.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # 默认回落
    return candidates[0]


def _list_structured_files(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """列出用户的所有结构化角色文件"""
    items: List[Dict[str, Any]] = []
    try:
        base = CHAR_DIR_STR if not user_id else os.path.join(CHAR_DIR_STR, str(user_id))
        os.makedirs(base, exist_ok=True)
        for name in os.listdir(base):
            if not name.startswith("structured_") or not name.endswith(".json"):
                continue
            path = os.path.join(base, name)
            try:
                stat = os.stat(path)
                # role 名推断
                role = name[len("structured_"):-5]
                for prefix in ("baike_", "zhwiki_"):
                    if role.startswith(prefix):
                        role = role[len(prefix):]
                # 读取简介预览（尽量短，优先结构化中的简介/摘要/summary）
                preview = ""
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        prof = json.load(f)
                    # 优先结构化字段
                    cand_keys = [
                        ("基础身份信息", ["人物简介", "简介", "人物摘要", "摘要", "自我描述", "简介概述"]),
                        ("角色信息", ["简介", "摘要"]),
                    ]
                    for top, subkeys in cand_keys:
                        v = prof.get(top) if isinstance(prof, dict) else None
                        if isinstance(v, dict):
                            for sk in subkeys:
                                txt = v.get(sk)
                                if isinstance(txt, str) and txt.strip():
                                    preview = txt.strip()
                                    break
                        if preview:
                            break
                    if not preview and isinstance(prof, dict):
                        # 兼容原始数据保留的 summary
                        s = prof.get("summary")
                        if isinstance(s, str) and s.strip():
                            preview = s.strip()
                    # 再次兜底：遍历顶层字符串字段
                    if not preview and isinstance(prof, dict):
                        for k, v in prof.items():
                            if isinstance(v, str) and v.strip():
                                preview = v.strip()
                                break
                    # 规范长度
                    if preview:
                        preview = preview.replace("\n", " ")
                        if len(preview) > 140:
                            preview = preview[:140] + "…"
                except Exception:
                    preview = ""
                items.append({
                    "role": role,
                    "path": path,
                    "updated_at": int(stat.st_mtime),
                    "preview": preview,
                })
            except Exception:
                continue
    except Exception:
        pass
    items.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return items


def _update_long_term_memory(role: str, uid: int, mem_context_text: str) -> Optional[str]:
    """将 Mem0 检索得到的上下文写入结构化文件的 "知识与能力.长期记忆"，并返回最新的 system 提示。"""
    try:
        role = normalize_role_name(role)
        path = _structured_path_for_role(role, user_id=uid)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            prof = json.load(f)
        know = prof.get("知识与能力")
        if not isinstance(know, dict):
            know = {}
        # 读取既有长期记忆
        existing = know.get("长期记忆")
        existing_list: List[str]
        if isinstance(existing, list):
            existing_list = [str(x).strip() for x in existing if str(x).strip()]
        elif isinstance(existing, str):
            # 按行切分，兼容以 "- " 开头的项目
            existing_list = []
            for line in existing.splitlines():
                line = str(line).strip()
                if not line:
                    continue
                if line.startswith("- "):
                    line = line[2:].strip()
                existing_list.append(line)
        else:
            existing_list = []
        # 新增项
        new_items: List[str] = []
        for line in str(mem_context_text or "").splitlines():
            line = str(line).strip()
            if not line:
                continue
            if line.startswith("- "):
                line = line[2:].strip()
            new_items.append(line)
        # 合并去重（保持顺序，限制长度）
        merged: List[str] = []
        for x in [*existing_list, *new_items]:
            if x and x not in merged:
                merged.append(x)
        if len(merged) > 400:
            merged = merged[-400:]
        know["长期记忆"] = merged
        prof["知识与能力"] = know
        with open(path, "w", encoding="utf-8") as f:
            json.dump(prof, f, ensure_ascii=False, indent=2)
        try:
            update_character_structured(int(uid), role, json.dumps(prof, ensure_ascii=False))
        except Exception:
            pass
        # 返回最新 system 提示
        return build_system_prompt(prof)
    except Exception:
        return None


def _truncate_structured_profile_text(profile: Dict[str, Any], limit_chars: int) -> Dict[str, Any]:
    """将结构化 JSON（不含长期记忆）随机丢弃一些键，直到字符串化后长度小于限制。"""
    import json as _json
    if limit_chars <= 0:
        return profile
    # 复制并去掉长期记忆
    from copy import deepcopy
    prof = deepcopy(profile)
    try:
        know = prof.get("知识与能力")
        if isinstance(know, dict) and "长期记忆" in know:
            know.pop("长期记忆", None)
    except Exception:
        pass
    s = _json.dumps(prof, ensure_ascii=False)
    if len(s) <= limit_chars:
        return prof
    # 可删分区（按顶层键随机移除）
    import random
    keys = [k for k in prof.keys() if k in [
        "基础身份信息", "个性与行为设定", "背景故事", "知识与能力", "对话与交互规范", "任务/功能性信息", "环境与世界观", "系统与控制参数"
    ]]
    random.shuffle(keys)
    for k in keys:
        try:
            prof.pop(k, None)
        except Exception:
            pass
        s = _json.dumps(prof, ensure_ascii=False)
        if len(s) <= limit_chars:
            break
    return prof


def _truncate_messages(messages: List[Dict[str, str]], limit_chars: int) -> List[Dict[str, str]]:
    """裁剪消息历史，保持在字符限制内"""
    if limit_chars <= 0:
        return messages
    import json as _json
    from collections import deque
    dq = deque(messages)
    while dq:
        s = _json.dumps(list(dq), ensure_ascii=False)
        if len(s) <= limit_chars:
            break
        # 丢弃最早的一条（保留 system/角色提示在会话外单独传入）
        left = dq[0]
        # 避免误删 system，如最左是 system 则跳过该条，删下一条
        if isinstance(left, dict) and left.get("role") == "system" and len(dq) >= 2:
            dq.popleft()
        dq.popleft()
    return list(dq)


def _truncate_long_term_memory(items: List[str], limit_chars: int) -> List[str]:
    """裁剪长期记忆，保持在字符限制内"""
    if limit_chars <= 0:
        return items
    import json as _json
    import random
    arr = list(items)
    # 根据索引越小（越早）被删概率越高的策略进行加权随机删减
    while arr:
        s = _json.dumps(arr, ensure_ascii=False)
        if len(s) <= limit_chars:
            break
        n = len(arr)
        # 权重：w_i = (n - i) 的反比，越早越大权重
        weights = [float(n - i) for i in range(n)]
        # 但我们想"越早越大概率被删"，因此选择 i=0 更容易选中
        # 转为概率
        total = sum(weights)
        probs = [w / total for w in weights]
        # 随机选择一个索引删除
        r = random.random()
        acc = 0.0
        idx = 0
        for i, p in enumerate(probs):
            acc += p
            if r <= acc:
                idx = i
                break
        arr.pop(idx)
    return arr


def _estimate_text_len(text: str) -> int:
    """估算文本长度"""
    return len(text or "")


def _ensure_chat_session_for_role(role: str, user_id: Optional[int] = None) -> str:
    """确保指定角色的聊天会话存在，返回 session_id"""
    with sessions_lock:
        for sid, sess in sessions.items():
            if sess.get("role") == role and sess.get("user_id") == user_id:
                return sid
    # 新建
    role = normalize_role_name(role)
    path = _structured_path_for_role(role, user_id=user_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="结构化文件不存在")
    with open(path, "r", encoding="utf-8") as f:
        profile = json.load(f)
    system_prompt = build_system_prompt(profile)
    sid = uuid.uuid4().hex
    with sessions_lock:
        sessions[sid] = {"messages": [{"role": "system", "content": system_prompt}], "role": role, "user_id": user_id}
    return sid


# ============= 记忆管理函数 =============

def _read_memories_from_profile(role: str, user_id: int) -> Tuple[List[str], List[str]]:
    """从结构化文件读取短期记忆和长期记忆
    
    Returns:
        (short_term_memories, long_term_memories)
    """
    try:
        role = normalize_role_name(role)
        path = _structured_path_for_role(role, user_id=user_id)
        if not os.path.exists(path):
            return [], []
        
        with open(path, 'r', encoding='utf-8') as f:
            prof = json.load(f)
        
        # 读取短期记忆
        stm = prof.get("短期记忆", [])
        if isinstance(stm, list):
            short_memories = [str(x).strip() for x in stm if str(x).strip()]
        else:
            short_memories = []
        
        # 读取长期记忆
        ltm = prof.get("长期记忆", [])
        if isinstance(ltm, list):
            long_memories = [str(x).strip() for x in ltm if str(x).strip()]
        else:
            long_memories = []
        
        return short_memories, long_memories
    except Exception as e:
        print(f"[ERROR] 读取记忆失败: {e}")
        return [], []


def _write_memories_to_profile(
    role: str,
    user_id: int,
    short_memories: Optional[List[str]] = None,
    long_memories: Optional[List[str]] = None
) -> None:
    """写入记忆到结构化文件顶层的"短期记忆"和"长期记忆"字段
    
    使用文件锁避免并发问题
    """
    try:
        role = normalize_role_name(role)
        path = _structured_path_for_role(role, user_id=user_id)
        if not os.path.exists(path):
            print(f"[ERROR] 结构化文件不存在: {path}")
            return
        
        # 使用文件锁
        with open(path, 'r+', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # 排他锁
            try:
                prof = json.load(f)
                
                # 确保记忆字段存在（兼容旧文件）
                if "短期记忆" not in prof:
                    prof["短期记忆"] = []
                if "长期记忆" not in prof:
                    prof["长期记忆"] = []
                
                # 更新短期记忆
                if short_memories is not None:
                    prof["短期记忆"] = short_memories
                
                # 更新长期记忆
                if long_memories is not None:
                    prof["长期记忆"] = long_memories
                
                # 写回文件
                f.seek(0)
                f.truncate()
                json.dump(prof, f, ensure_ascii=False, indent=2)
                
                # 同步到数据库
                try:
                    update_character_structured(user_id, role, json.dumps(prof, ensure_ascii=False))
                except Exception:
                    pass
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # 释放锁
    except Exception as e:
        print(f"[ERROR] 写入记忆失败: {e}")


def _append_short_term_memory(role: str, user_id: int, new_memories: List[str]) -> None:
    """追加短期记忆（按时间顺序）"""
    try:
        stm, ltm = _read_memories_from_profile(role, user_id)
        # 追加新记忆到末尾
        stm.extend(new_memories)
        _write_memories_to_profile(role, user_id, short_memories=stm)
    except Exception as e:
        print(f"[ERROR] 追加短期记忆失败: {e}")


def _append_long_term_memory(role: str, user_id: int, new_memories: List[str]) -> None:
    """追加长期记忆（按时间顺序）"""
    try:
        stm, ltm = _read_memories_from_profile(role, user_id)
        # 追加新记忆到末尾
        ltm.extend(new_memories)
        _write_memories_to_profile(role, user_id, long_memories=ltm)
    except Exception as e:
        print(f"[ERROR] 追加长期记忆失败: {e}")


def _get_role_summary(role: str, user_id: int) -> str:
    """从结构化文件提取角色简介（用于长期记忆整合）"""
    try:
        role = normalize_role_name(role)
        path = _structured_path_for_role(role, user_id=user_id)
        if not os.path.exists(path):
            return "角色简介缺失"
        
        with open(path, 'r', encoding='utf-8') as f:
            prof = json.load(f)
        
        # 优先从基础身份信息获取
        base_info = prof.get("基础身份信息", {})
        if isinstance(base_info, dict):
            summary = base_info.get("人物简介") or base_info.get("简介") or base_info.get("自我描述")
            if summary:
                return str(summary).strip()
        
        # 兜底：从顶层获取
        summary = prof.get("简介") or prof.get("summary") or prof.get("人物摘要")
        if summary:
            return str(summary).strip()
        
        return f"{role} 的角色画像"
    except Exception:
        return "角色简介缺失"

