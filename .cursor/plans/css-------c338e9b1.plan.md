<!-- c338e9b1-4bdf-409d-9a1c-bb08ec3905e6 2cbc6519-bda3-4c6a-8f7c-5a659d8ff00e -->
# LLM API调用异步优化计划

## 目标

将同步阻塞的LLM API调用改为异步非阻塞调用：
- **并发能力**: 提升 **10倍**
- **响应性**: Worker不再阻塞，可同时处理多个请求
- **用户体验**: 多人同时聊天不会互相等待
- **吞吐量**: 从串行处理 → 并行处理

## 当前问题

### 问题1：同步调用阻塞Worker

```python
# fastnpc/llm/openrouter.py (当前代码)
def get_openrouter_completion(messages, model):
    """同步调用 - 阻塞整个Worker ❌"""
    completion = client.chat.completions.create(...)
    return completion.choices[0].message.content
```

**影响**：
- 每个LLM请求：2-10秒
- Worker被阻塞：无法处理其他请求
- 10个用户同时聊天：需要排队等待 20-100秒

### 问题2：多处使用同步调用

**调用位置**：
- `chat_routes.py`: 聊天对话（最频繁）
- `group_routes.py`: 群聊对话
- `character_routes.py`: 角色生成（20-60秒）

**当前流程**：
```
用户A发消息 → LLM调用(5秒) → Worker阻塞 → 其他用户等待
用户B发消息 → 等待A完成 → LLM调用(5秒) → Worker阻塞
用户C发消息 → 等待B完成 → LLM调用(5秒) → ...
```

## 解决方案

### 方案：AsyncOpenAI + FastAPI异步路由

**技术栈**：
- ✅ `openai.AsyncOpenAI`: 官方异步客户端
- ✅ `async/await`: Python原生异步语法
- ✅ FastAPI异步路由: 非阻塞处理
- ✅ `asyncio`: 并发管理

**优势**：
- 官方支持，稳定可靠
- 与FastAPI完美集成
- 最小代码改动
- 向后兼容（可选保留同步版本）

## 实施步骤

### 1. 创建异步LLM客户端

**更新文件**: `fastnpc/llm/openrouter.py`

**改动**：
- 添加 `_async_client()` 函数
- 创建 `async def get_openrouter_completion_async()`
- 创建 `async def get_openrouter_structured_json_async()`
- 创建 `async def stream_openrouter_text_async()`

**保持向后兼容**：
- 保留原有同步函数（向后兼容）
- 新增异步版本函数（新功能）

### 2. 更新聊天路由为异步

**更新文件**: `fastnpc/api/routes/chat_routes.py`

**关键改动**：
- 路由函数改为 `async def`
- 调用改为 `await get_openrouter_completion_async()`
- 流式响应改为异步生成器

**示例**：
```python
# 优化前
@router.post('/chat/send')
def send_message(...):
    reply = get_openrouter_completion(prompt_msgs)  # 阻塞5秒
    return reply

# 优化后
@router.post('/chat/send')
async def send_message(...):
    reply = await get_openrouter_completion_async(prompt_msgs)  # 非阻塞
    return reply
```

### 3. 更新群聊路由为异步

**更新文件**: `fastnpc/api/routes/group_routes.py`

**改动**：
- 群聊消息发送 → 异步
- 智能主持人选择 → 异步
- 多个LLM调用 → 并行处理（`asyncio.gather`）

### 4. 更新角色生成为异步

**更新文件**: `fastnpc/api/routes/character_routes.py`

**改动**：
- 角色信息生成（8个类别）→ 并行生成
- 使用 `asyncio.gather()` 同时调用多个LLM
- 时间从 20-60秒 → 3-8秒（并行）

**性能提升**：
```python
# 优化前：串行执行
结果1 = LLM调用1()  # 5秒
结果2 = LLM调用2()  # 5秒
结果3 = LLM调用3()  # 5秒
# 总计：15秒

# 优化后：并行执行
结果1, 结果2, 结果3 = await asyncio.gather(
    LLM调用1(),  # 并行
    LLM调用2(),  # 并行
    LLM调用3(),  # 并行
)
# 总计：5秒（只需最慢的那个时间）
```

### 5. 更新数据库操作为异步兼容

**说明**：
- FastAPI异步路由中调用同步数据库操作是安全的
- psycopg2连接池是线程安全的
- 可选：后续迁移到 `asyncpg`（更高性能，但改动大）

**当前策略**：
- 保持数据库操作同步（已有连接池优化）
- 只优化LLM调用为异步（最大瓶颈）

### 6. 处理内存压缩的异步

**更新函数**: `_check_and_compress_memories()`

**改动**：
- 改为 `async def`
- 内部LLM调用改为异步
- 在后台任务中调用（不阻塞主流程）

### 7. 测试验证

- 单用户聊天测试
- 10用户并发聊天测试
- 角色生成性能测试
- 流式响应测试

## 技术细节

### 异步客户端创建

```python
from openai import AsyncOpenAI

def _async_client() -> Optional[AsyncOpenAI]:
    api_key = OPENROUTER_API_KEY
    if not api_key:
        return None
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
```

### 异步函数示例

```python
async def get_openrouter_completion_async(
    messages: List[Dict[str, str]],
    model: str = "z-ai/glm-4-32b",
) -> str:
    """异步LLM调用 - 不阻塞Worker"""
    client = _async_client()
    if client is None:
        return "错误: API KEY未设置"
    
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"调用API错误: {e}"
```

### 异步流式响应

```python
async def stream_openrouter_text_async(
    messages: List[Dict[str, str]],
    model: str = "z-ai/glm-4-32b",
):
    """异步生成器：逐块产出文本"""
    client = _async_client()
    if client is None:
        yield "错误: API KEY未设置"
        return
    
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
    except Exception as e:
        yield f"错误: {e}"
```

### FastAPI异步路由

```python
@router.post('/chat/send')
async def send_message(
    char_name: str,
    content: str,
    session: dict = Depends(get_current_user)
):
    """异步路由 - 不阻塞Worker"""
    # ... 准备prompt ...
    
    # 异步调用LLM（非阻塞）
    reply = await get_openrouter_completion_async(prompt_msgs)
    
    # 数据库操作（同步，但很快）
    add_message(user_id, char_id, 'assistant', reply)
    
    return {"message": reply}
```

### 并行LLM调用

```python
# 同时生成多个类别的角色信息
results = await asyncio.gather(
    get_structured_async(prompt1, schema1),  # 基础信息
    get_structured_async(prompt2, schema2),  # 外貌特征
    get_structured_async(prompt3, schema3),  # 性格特点
    # ... 更多类别 ...
)
```

## 性能提升预期

### 单用户体验

| 操作 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 发送消息 | 2-10秒 | 2-10秒 | 无变化（本身耗时） |
| **等待响应** | 阻塞其他请求 | **不阻塞** | ✅ |

### 多用户并发

| 场景 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| **10人同时聊天** | 排队等待<br>总时间：50-100秒 | 并行处理<br>总时间：5-10秒 | **10倍** 🚀 |
| **角色生成** | 串行8次LLM<br>20-60秒 | 并行8次LLM<br>3-8秒 | **5-8倍** ⚡ |
| **Worker利用率** | 10-20% | 80-90% | **4-8倍** 📈 |

### 系统吞吐量

```
优化前：
- Worker阻塞时间：80-90%
- 可并发用户：2-3人
- QPS：0.1-0.5（极低）

优化后：
- Worker阻塞时间：<10%
- 可并发用户：20-50人
- QPS：5-10（提升10-50倍）
```

## 向后兼容

### 保留同步函数

```python
# 同步版本（保留，向后兼容）
def get_openrouter_completion(...):
    """同步调用（老代码使用）"""
    pass

# 异步版本（新增）
async def get_openrouter_completion_async(...):
    """异步调用（新路由使用）"""
    pass
```

### 渐进式迁移

1. **阶段1**：创建异步函数（不影响现有代码）
2. **阶段2**：更新聊天路由为异步（核心功能）
3. **阶段3**：更新群聊和角色生成为异步
4. **阶段4**（可选）：移除同步函数

## 注意事项

### 1. 数据库操作

FastAPI异步路由中可以调用同步数据库操作：
```python
async def async_route():
    # ✅ 可以直接调用同步数据库函数
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT ...")
    _return_conn(conn)
```

**原因**：
- psycopg2是线程安全的
- 数据库操作很快（<10ms）
- 不会阻塞事件循环

### 2. 内存管理

会话内存（sessions）访问需要加锁：
```python
# ✅ 正确
with sessions_lock:
    msgs = sessions[key]["messages"]

# ❌ 错误（异步中可能竞态）
msgs = sessions[key]["messages"]
await llm_call()
sessions[key]["messages"].append(...)
```

### 3. 错误处理

异步函数的异常处理：
```python
try:
    result = await llm_call_async()
except Exception as e:
    # 捕获异步异常
    return {"error": str(e)}
```

### 4. 超时控制

添加超时机制（避免无限等待）：
```python
import asyncio

try:
    result = await asyncio.wait_for(
        llm_call_async(),
        timeout=30.0  # 30秒超时
    )
except asyncio.TimeoutError:
    return {"error": "LLM调用超时"}
```

## 风险控制

### 潜在风险

1. **并发过高导致API限流**: OpenRouter可能有速率限制
2. **内存占用增加**: 多个并发请求占用内存
3. **错误传播**: 一个异步任务出错可能影响其他

### 缓解措施

1. **添加并发限制**:
```python
# 使用信号量限制并发数
semaphore = asyncio.Semaphore(10)  # 最多10个并发

async def limited_llm_call():
    async with semaphore:
        return await llm_call_async()
```

2. **错误隔离**: 每个请求独立处理，互不影响

3. **监控告警**: 记录LLM调用延迟和失败率

## 验收标准

- ✅ 所有异步函数正常工作
- ✅ 10人并发聊天：所有人同时获得响应
- ✅ 角色生成时间：<10秒
- ✅ Worker CPU利用率：>60%
- ✅ 无死锁、无内存泄漏
- ✅ 流式响应正常工作

## 后续优化（可选）

### 1. 数据库异步化

使用 `asyncpg` 替代 `psycopg2`：
- 更高性能
- 完全非阻塞
- 改动较大（需要重写所有数据库函数）

### 2. 缓存层

添加Redis缓存：
- 缓存角色信息（减少数据库查询）
- 缓存LLM响应（相似问题）

### 3. 任务队列

使用Celery或RQ：
- 角色生成放入后台队列
- 内存压缩放入后台队列
- WebSocket通知前端

## 总结

这个优化将带来**10倍并发能力提升**：

✅ **核心改进**：
1. LLM调用从同步 → 异步
2. Worker从阻塞 → 非阻塞
3. 用户从排队 → 并行

✅ **预期效果**：
- 10人同时聊天：从100秒 → 10秒
- 角色生成：从60秒 → 8秒
- 系统吞吐量：提升10-50倍

✅ **风险可控**：
- 向后兼容
- 渐进式迁移
- 错误隔离


### To-dos

- [ ] 创建异步LLM客户端 - AsyncOpenAI
- [ ] 添加 get_openrouter_completion_async() 函数
- [ ] 添加 get_openrouter_structured_json_async() 函数
- [ ] 添加 stream_openrouter_text_async() 生成器
- [ ] 更新聊天路由为异步 - chat_routes.py
- [ ] 更新群聊路由为异步 - group_routes.py
- [ ] 更新角色生成为异步并行 - character_routes.py
- [ ] 添加并发限制 - asyncio.Semaphore
- [ ] 测试验证 - 10人并发聊天、角色生成性能