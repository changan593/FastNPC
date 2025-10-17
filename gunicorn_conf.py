# -*- coding: utf-8 -*-
"""
Gunicorn 配置文件（生产环境推荐）

针对2核2G服务器优化：
- 2个worker进程（充分利用2核CPU）
- 每个worker使用异步模式（UvicornWorker）
- 合理的超时和连接限制
"""
import multiprocessing
import os

# 服务器绑定
bind = "0.0.0.0:8000"

# Worker配置（2核CPU优化）
workers = 2  # 2个worker，每核1个
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000  # 每个worker最多1000个并发连接

# 超时配置
timeout = 300  # 请求超时时间（5分钟，考虑到LLM调用可能较慢）
graceful_timeout = 30  # 优雅关闭超时
keepalive = 5  # Keep-Alive超时

# 进程命名
proc_name = "fastnpc"

# 日志配置
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程PID文件
pidfile = "logs/gunicorn.pid"

# Daemon模式（后台运行）
daemon = False  # 设为True可后台运行

# 预加载应用（节省内存，但不支持热重载）
preload_app = False  # 设为True可以节省内存，但重启较慢

# 重启前的最大请求数（防止内存泄漏）
max_requests = 10000
max_requests_jitter = 1000  # 随机抖动，避免所有worker同时重启

# SSL配置（如果需要HTTPS）
# keyfile = "/path/to/ssl.key"
# certfile = "/path/to/ssl.crt"

# 回调函数
def on_starting(server):
    """服务器启动时调用"""
    print("FastNPC服务器启动中...")
    print(f"  绑定地址: {bind}")
    print(f"  Worker数量: {workers}")
    print(f"  Worker类型: {worker_class}")
    print(f"  优化配置: 2核2G服务器")

def on_reload(server):
    """重载配置时调用"""
    print("FastNPC服务器配置已重载")

def worker_int(worker):
    """Worker被中断时调用"""
    worker.log.info("Worker收到中断信号，正在停止...")

def worker_abort(worker):
    """Worker异常终止时调用"""
    worker.log.info("Worker异常终止")

def pre_fork(server, worker):
    """Fork新worker前调用"""
    pass

def post_fork(server, worker):
    """Fork新worker后调用"""
    server.log.info(f"Worker {worker.pid} 已启动")

def pre_exec(server):
    """执行新二进制文件前调用"""
    server.log.info("Fork新的master进程")

def when_ready(server):
    """服务器准备就绪时调用"""
    server.log.info("FastNPC服务器已就绪，开始接受请求")

def worker_exit(server, worker):
    """Worker退出时调用"""
    server.log.info(f"Worker {worker.pid} 已退出")

