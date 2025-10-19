# 连接池耗尽问题 - 快速修复指南

## 问题

创建角色时遇到"连接池耗尽"错误。

## 原因

1. **连接池太小**：默认最大20个连接，批量创建角色时不够用
2. **长时间持有连接**：角色创建需要调用LLM（10-30秒），期间占用连接
3. **并发请求过多**：50个角色批量创建会超过连接池容量

## 已实施的修复

### ✅ 增加连接池大小

**修改前**：
- 最小连接：5
- 最大连接：20

**修改后**：
- 最小连接：10
- 最大连接：50

**文件**：`fastnpc/config.py`

### ✅ 创建监控工具

**文件**：`fastnpc/scripts/monitor_pool.py`

**使用方法**：

1. **查看当前状态**
```bash
python fastnpc/scripts/monitor_pool.py --mode status
```

2. **持续监控（每5秒刷新）**
```bash
python fastnpc/scripts/monitor_pool.py --mode monitor --interval 5
```

3. **压力测试（尝试获取30个连接）**
```bash
python fastnpc/scripts/monitor_pool.py --mode test --count 30
```

## 使用建议

### 批量创建角色时

如果需要批量创建大量角色，建议：

1. **分批创建**：每次创建5-10个，等待完成后再创建下一批
2. **添加延迟**：每个角色间隔1-2秒
3. **使用脚本时添加延迟**：

```python
import time

for character in characters:
    create_character(character)
    time.sleep(2)  # 等待2秒
```

### 重启服务

修改配置后需要重启服务才能生效：

```bash
# 如果使用systemd
sudo systemctl restart fastnpc

# 如果手动运行
# 按Ctrl+C停止，然后重新启动
```

## 环境变量配置（可选）

也可以通过环境变量调整连接池大小：

```bash
# 在.env文件中添加
DB_POOL_MIN_CONN=15
DB_POOL_MAX_CONN=100

# 或者在启动命令中设置
DB_POOL_MAX_CONN=100 python -m fastnpc.api.main
```

## 监控连接池状态

在 `http://localhost:8000/docs` 可以访问新的监控API（需要管理员权限）：

- `GET /admin/db-pool-status` - 查看连接池状态

## 详细文档

完整的问题分析和长期优化方案，请查看：
- `docs/CONNECTION_POOL_ANALYSIS.md`

## 如果问题仍然出现

1. **增加连接池到更大值**
```bash
export DB_POOL_MAX_CONN=100
```

2. **检查数据库服务器**
```bash
# PostgreSQL 查看当前连接数
psql -U fastnpc -d fastnpc -c "SELECT count(*) FROM pg_stat_activity;"

# PostgreSQL 查看最大连接数限制
psql -U fastnpc -d fastnpc -c "SHOW max_connections;"
```

3. **联系支持**
提供以下信息：
- 监控工具输出
- 错误日志
- 并发请求数量

## 更新日期

2025-10-19

