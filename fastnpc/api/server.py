# -*- coding: utf-8 -*-
"""
FastNPC API 服务器主入口
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from fastnpc.config import CHAR_DIR, TEMPLATES_DIR, STATIC_DIR, FRONTEND_ORIGINS
from fastnpc.api.auth import init_db

# 导入所有路由模块
from fastnpc.api.routes.auth_routes import router as auth_router
from fastnpc.api.routes.user_routes import router as user_router
from fastnpc.api.routes.admin_routes import router as admin_router
from fastnpc.api.routes.character_routes import router as character_router
from fastnpc.api.routes.chat_routes import router as chat_router
from fastnpc.api.routes.datasource_routes import router as datasource_router
from fastnpc.api.routes.task_routes import router as task_router
from fastnpc.api.routes.template_routes import router as template_router
from fastnpc.api.routes.group_routes import router as group_router
from fastnpc.api.routes.feedback_routes import router as feedback_router


# CHAR_DIR不再使用，所有数据存储在PostgreSQL数据库中
CHAR_DIR_STR = CHAR_DIR.as_posix()


# 创建 FastAPI 应用实例
app = FastAPI(title="FastNPC")

# CORS 中间件配置
# CORS 注意：使用 Cookie 时不能使用通配 "*"；支持逗号分隔多个来源
_ALLOWED_ORIGINS = FRONTEND_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件挂载
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR.as_posix()),
    name="static",
)

# 反馈附件目录
FEEDBACK_DIR = CHAR_DIR.parent / "Feedbacks"
os.makedirs(FEEDBACK_DIR.as_posix(), exist_ok=True)
app.mount(
    "/feedbacks",
    StaticFiles(directory=FEEDBACK_DIR.as_posix()),
    name="feedbacks",
)

# 初始化数据库
try:
    init_db()
except Exception:
    pass

# 注册所有路由
app.include_router(template_router)  # 首页等模板路由
app.include_router(auth_router)      # 认证路由
app.include_router(user_router)      # 用户设置路由
app.include_router(admin_router)     # 管理员路由
app.include_router(character_router) # 角色管理路由
app.include_router(chat_router)      # 聊天路由
app.include_router(datasource_router) # 数据源路由
app.include_router(task_router)      # 任务路由
app.include_router(group_router)     # 群聊路由
app.include_router(feedback_router)  # 反馈路由


def create_app() -> FastAPI:
    """应用工厂函数"""
    return app
