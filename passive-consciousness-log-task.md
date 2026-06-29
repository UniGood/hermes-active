# 被动意识日志系统任务

## 目标

为被动意识插件添加完整的日志记录系统，每次 pre_llm_call 触发时记录详细数据到 active.db，并在前端新增日志监控 Tab。

## STRICT RULES

- 只修改下面列出的文件，不要改其他文件
- 不要修改 config.py、config.yaml、.env
- 不要运行 git 命令

## 项目路径

- hermes-active 项目：`/home/ubuntu/.hermes/hermes-active/`
- 插件目录：`~/.hermes/plugins/passive-consciousness/`
- active.db：`~/.hermes/hermes-active/data/active.db`

## 需要新建的文件

### 文件 1: `/home/ubuntu/.hermes/hermes-active/backend/models/passive_consciousness_log.py`

SQLAlchemy 模型，表名 `passive_consciousness_logs`：

```python
class PassiveConsciousnessLog(Base):
    __tablename__ = "passive_consciousness_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    session_id = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    sender_id = Column(String, nullable=True)
    
    # 状态数据
    longing_score = Column(Float, default=0.0)
    longing_label = Column(String, default="calm")
    chat_heat = Column(Float, default=0.0)
    chat_heat_label = Column(String, default="cold")
    emotional_intensity = Column(Float, default=0.0)
    emotional_label = Column(String, default="工作")
    
    # 天气
    weather_city = Column(String, nullable=True)
    weather_info = Column(String, nullable=True)  # "晴 28°C"
    
    # 记忆
    memories_count = Column(Integer, default=0)
    has_reflection = Column(Boolean, default=False)
    
    # 注入结果
    status = Column(String, default="success")  # success / skipped / error
    context_length = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    
    # 用户消息摘要
    user_message_preview = Column(String, nullable=True)  # 前100字
```

在 `init_active_db()` 中添加 `Base.metadata.create_all` 以自动建表。

## 需要修改的文件

### 文件 2: `/home/ubuntu/.hermes/plugins/passive-consciousness/__init__.py`

在 `inject_consciousness_context` 函数中，每次执行后调用日志写入。

在函数末尾（return context 之前）添加：

```python
# 写入日志
try:
    _write_log(
        session_id=session_id,
        platform=platform,
        sender_id=sender_id,
        consciousness_data=consciousness_data,
        weather_data=weather_data,
        memories=memories,
        reflection=reflection,
        context=context,
        user_message=user_message,
        status="success",
    )
except Exception as log_e:
    logger.debug("写入被动意识日志失败: %s", log_e)
```

在 skip 和 error 分支也写入日志（status="skipped" 或 status="error"）。

新增 `_write_log` 函数，用 sqlite3 直接写入 active.db 的 `passive_consciousness_logs` 表。

### 文件 3: `/home/ubuntu/.hermes/hermes-active/backend/routers/passive_consciousness.py`

新增日志查询 API：

```python
@router.get("/logs")
async def get_logs(
    limit: int = 100,
    status: str = None,
    offset: int = 0,
):
    """获取被动意识日志"""
    # 查询 passive_consciousness_logs 表
    # 支持 status 过滤（success/skipped/error）
    # 按 timestamp 倒序
    # 返回 {total, items}

@router.get("/logs/stats")
async def get_log_stats():
    """获取日志统计"""
    # 返回：
    # - 总注入次数
    # - 成功/跳过/错误次数
    # - 最近24小时注入次数
    # - 平均上下文长度
    # - 各状态分布（用于饼图）
    # - 最近7天每天注入次数（用于折线图）

@router.delete("/logs")
async def clear_logs():
    """清空日志"""
```

### 文件 4: `/home/ubuntu/.hermes/hermes-active/frontend/src/api/passive_consciousness.js`

新增日志 API 方法：

```javascript
getLogs(params) {
  return http.get('/passive-consciousness/logs', { params })
},
getLogStats() {
  return http.get('/passive-consciousness/logs/stats')
},
clearLogs() {
  return http.delete('/passive-consciousness/logs')
},
```

### 文件 5: `/home/ubuntu/.hermes/hermes-active/frontend/src/views/PassiveConsciousness.vue`

新增第五个 Tab "日志"，包含：

1. **统计卡片**（顶部）：
   - 总注入次数
   - 成功率
   - 最近24小时次数
   - 平均上下文长度

2. **过滤栏**：
   - 状态筛选（全部/成功/跳过/错误）
   - 刷新按钮
   - 清空日志按钮（带确认）

3. **日志表格**（n-data-table）：
   列：
   - 时间（timestamp）
   - 平台（platform）
   - 用户消息预览（user_message_preview，截断显示）
   - 想念（longing_label + score）
   - 热度（chat_heat_label + heat）
   - 情绪（emotional_label + intensity）
   - 天气（weather_info）
   - 记忆数（memories_count）
   - 上下文长度（context_length）
   - 状态（status，用 n-tag 颜色区分：success=green, skipped=orange, error=red）
   - 错误信息（error_message，仅错误时显示）

4. **分页**：
   - 使用 n-pagination
   - 每页50条

UI 要求：
- 表格用 n-data-table
- 状态用 n-tag 带颜色
- 统计用 n-statistic
- 加载用 n-spin

## 验证

完成后：
1. 检查 active.db 中有 `passive_consciousness_logs` 表
2. 检查后端有 3 个新日志 API
3. 检查前端有日志 Tab
4. 构建前端
