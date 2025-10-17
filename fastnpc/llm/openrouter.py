# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from typing import List, Dict, Any, Optional

from openai import OpenAI, AsyncOpenAI
from fastnpc.config import OPENROUTER_API_KEY


def _client() -> Optional[OpenAI]:
    """同步客户端（向后兼容）"""
    api_key = OPENROUTER_API_KEY
    if not api_key:
        return None
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def _async_client() -> Optional[AsyncOpenAI]:
    """异步客户端（新增）"""
    api_key = OPENROUTER_API_KEY
    if not api_key:
        return None
    return AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def get_openrouter_completion(
    messages: List[Dict[str, str]],
    model: str = "z-ai/glm-4-32b",
    *,
    stream: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
) -> str:
    """常规补全；支持可选 stream 与 response_format 直传。"""
    client = _client()
    if client is None:
        return "错误: 环境变量 OPENROUTER_API_KEY 未设置。"
    try:
        if stream:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                response_format=response_format,
            )
            chunks: List[str] = []
            for ev in resp:  # type: ignore
                try:
                    delta = ev.choices[0].delta.content or ""  # type: ignore
                except Exception:
                    delta = ""
                if delta:
                    chunks.append(delta)
            return "".join(chunks)
        else:
            completion = client.chat.completions.create(
                model=model, messages=messages, response_format=response_format
            )
            return completion.choices[0].message.content  # type: ignore
    except Exception as e:
        return f"调用API时发生错误: {e}"


def get_openrouter_structured_json(
    messages: List[Dict[str, str]],
    schema: Dict[str, Any],
    model: str = "z-ai/glm-4-32b",
    *,
    stream: bool = True,
    name: str = "structured_output",
) -> Any:
    """使用 Structured Outputs + Streaming，返回解析后的 JSON（失败则返回原文本）。"""
    # 依据 OpenAI/OpenRouter 的结构化输出接口形态
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            # 非强制严格，避免过严导致失败；如需严格可改 True
            "strict": False,
        },
    }
    text = get_openrouter_completion(
        messages, model=model, stream=stream, response_format=response_format
    )
    # 解析为 JSON
    try:
        return json.loads(text)
    except Exception:
        # 尝试从文本中提取首个 JSON
        try:
            start = min([i for i in [text.find("{"), text.find("[")] if i != -1])
        except Exception:
            start = -1
        if start != -1:
            candidate = text[start:]
            end = max(candidate.rfind("}"), candidate.rfind("]"))
            if end != -1:
                try:
                    return json.loads(candidate[: end + 1])
                except Exception:
                    pass
    return text


def stream_openrouter_text(
    messages: List[Dict[str, str]],
    model: str = "z-ai/glm-4-32b",
    *,
    response_format: Optional[Dict[str, Any]] = None,
):
    """生成器：逐块产出增量文本。"""
    client = _client()
    if client is None:
        yield "错误: 环境变量 OPENROUTER_API_KEY 未设置。"
        return
    try:
        resp = client.chat.completions.create(
            model=model, messages=messages, stream=True, response_format=response_format
        )
        for ev in resp:  # type: ignore
            try:
                delta = ev.choices[0].delta.content or ""  # type: ignore
            except Exception:
                delta = ""
            if delta:
                yield delta
    except Exception as e:
        yield f"调用API时发生错误: {e}"


# ========== 异步版本函数（新增） ==========


async def get_openrouter_completion_async(
    messages: List[Dict[str, str]],
    model: str = "z-ai/glm-4-32b",
    *,
    stream: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
) -> str:
    """异步常规补全；支持可选 stream 与 response_format 直传。
    
    不阻塞Worker，允许多个请求并发处理。
    """
    client = _async_client()
    if client is None:
        return "错误: 环境变量 OPENROUTER_API_KEY 未设置。"
    try:
        if stream:
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                response_format=response_format,
            )
            chunks: List[str] = []
            async for ev in resp:  # type: ignore
                try:
                    delta = ev.choices[0].delta.content or ""  # type: ignore
                except Exception:
                    delta = ""
                if delta:
                    chunks.append(delta)
            return "".join(chunks)
        else:
            completion = await client.chat.completions.create(
                model=model, messages=messages, response_format=response_format
            )
            return completion.choices[0].message.content  # type: ignore
    except Exception as e:
        return f"调用API时发生错误: {e}"


async def get_openrouter_structured_json_async(
    messages: List[Dict[str, str]],
    schema: Dict[str, Any],
    model: str = "z-ai/glm-4-32b",
    *,
    stream: bool = True,
    name: str = "structured_output",
) -> Any:
    """异步使用 Structured Outputs + Streaming，返回解析后的 JSON（失败则返回原文本）。
    
    不阻塞Worker，允许多个请求并发处理。
    """
    # 依据 OpenAI/OpenRouter 的结构化输出接口形态
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            # 非强制严格，避免过严导致失败；如需严格可改 True
            "strict": False,
        },
    }
    text = await get_openrouter_completion_async(
        messages, model=model, stream=stream, response_format=response_format
    )
    # 解析为 JSON
    try:
        return json.loads(text)
    except Exception:
        # 尝试从文本中提取首个 JSON
        try:
            start = min([i for i in [text.find("{"), text.find("[")] if i != -1])
        except Exception:
            start = -1
        if start != -1:
            candidate = text[start:]
            end = max(candidate.rfind("}"), candidate.rfind("]"))
            if end != -1:
                try:
                    return json.loads(candidate[: end + 1])
                except Exception:
                    pass
    return text


async def stream_openrouter_text_async(
    messages: List[Dict[str, str]],
    model: str = "z-ai/glm-4-32b",
    *,
    response_format: Optional[Dict[str, Any]] = None,
):
    """异步生成器：逐块产出增量文本。
    
    不阻塞Worker，允许多个请求并发处理。
    """
    client = _async_client()
    if client is None:
        yield "错误: 环境变量 OPENROUTER_API_KEY 未设置。"
        return
    try:
        resp = await client.chat.completions.create(
            model=model, messages=messages, stream=True, response_format=response_format
        )
        async for ev in resp:  # type: ignore
            try:
                delta = ev.choices[0].delta.content or ""  # type: ignore
            except Exception:
                delta = ""
            if delta:
                yield delta
    except Exception as e:
        yield f"调用API时发生错误: {e}"


