#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv


def _compute_base_dir() -> Path:
    # 优先环境变量，其次根据源码位置推断（项目根目录）
    env_root = os.environ.get("FASTNPC_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()
    # fastnpc/config.py -> parents[1] 为项目根目录
    return Path(__file__).resolve().parents[1]


# 路径与 .env
BASE_DIR: Path = _compute_base_dir()
ENV_PATH: Path = BASE_DIR / ".env"
if ENV_PATH.exists():
    # 不覆盖已存在的进程环境变量
    load_dotenv(ENV_PATH.as_posix(), override=False)


# 关键环境变量
FASTNPC_SECRET: str | None = os.environ.get("FASTNPC_SECRET")
if not FASTNPC_SECRET:
    raise RuntimeError(
        "FASTNPC_SECRET 未设置。请在环境变量或 .env 中设置一个强随机字符串。"
    )

OPENROUTER_API_KEY: str | None = os.environ.get("OPENROUTER_API_KEY")
FASTNPC_ADMIN_USER: str | None = os.environ.get("FASTNPC_ADMIN_USER")
try:
    MAX_CONCURRENCY: int = max(1, int(os.environ.get("FASTNPC_MAX_CONCURRENCY", "4")))
except Exception:
    MAX_CONCURRENCY = 4

# CORS 前端地址，支持逗号分隔多个来源
_frontend_origins = os.environ.get("FASTNPC_FRONTEND_ORIGIN", "http://localhost:5173").strip()
FRONTEND_ORIGINS: List[str] = [o.strip() for o in _frontend_origins.split(",") if o.strip()]

# PostgreSQL 配置
USE_POSTGRESQL: bool = os.environ.get("USE_POSTGRESQL", "true").lower() in ("true", "1", "yes")
POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT: int = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB: str = os.environ.get("POSTGRES_DB", "fastnpc")
POSTGRES_USER: str = os.environ.get("POSTGRES_USER", "fastnpc")
POSTGRES_PASSWORD: str | None = os.environ.get("POSTGRES_PASSWORD")

# 数据库连接池配置
DB_POOL_MIN_CONN: int = int(os.environ.get("DB_POOL_MIN_CONN", "10"))
DB_POOL_MAX_CONN: int = int(os.environ.get("DB_POOL_MAX_CONN", "50"))

# Redis 缓存配置
REDIS_HOST: str = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB: int = int(os.environ.get("REDIS_DB", "0"))
REDIS_PASSWORD: str | None = os.environ.get("REDIS_PASSWORD")

# 提示词管理配置
USE_DB_PROMPTS: bool = os.environ.get("USE_DB_PROMPTS", "true").lower() in ("true", "1", "yes")


# 重要目录/文件路径
CHAR_DIR: Path = BASE_DIR / "Characters"
TEMPLATES_DIR: Path = BASE_DIR / "fastnpc" / "web" / "templates"
STATIC_DIR: Path = BASE_DIR / "fastnpc" / "web" / "static"
DB_PATH: Path = BASE_DIR / "fastnpc.db"


