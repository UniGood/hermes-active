# 2026-06-23 念头日志显示问题修复 + Hindsight 存储列升级

## 背景

排查时发现念头日志/心跳日志展示有 4 个独立 bug，且发现 `details.hindsight_stored` 这个埋藏在 JSON 里的 bool 字段应当提升为数据库列方便前端展示。

## 根因（4 个 bug）

### Bug 1：念头 #1040 详情显示"已发送"但 type=memory

**位置**：`frontend/src/views/ActiveConsciousness.vue` `getThoughtResultTitle`

```js
function getThoughtResultTitle(details) {
  if (details.message_sending && typeof details.message_sending.success === 'boolean') {
    return details.message_sending.success ? '已发送消息' : '发送失败'
  }
  if (details.decision === 'auto_send') return '已发送消息'  // ← 这里兜底，type=memory 误判
  ...
}
```

`type=memory` 念头根本不发送（没有 message_sending 字段），但 decision 仍是 "auto_send"（代码先判 type=memory 处理后**沿用** decision）→ 兜底分支把它当成"已发送"。

### Bug 2：心跳日志表格"发送消息"列全空

**位置**：`ActiveConsciousness.vue` `heartbeatColumns` L2079

```js
{ title: '发送消息', key: 'message_sent', width: 80, render(row) {
  const sent = row.details_parsed?.message_sending?.success
  ...
}}
```

`active_heartbeat_logs` 表有专属 `message_sent` 列字段（后端 SQL 已 SELECT，最准确值），前端却去读 `details_parsed.message_sending.success`（多数心跳此字段不存在）→ 全空。

### Bug 3：念头表格"决策"显示英文

**位置**：`ActiveConsciousness.vue` `DECISION_TYPE_CN` 字典

```js
const DECISION_TYPE_CN = {
  auto_send: '立即发送（auto_send）', delay_send: '延迟发送（delay_send）',
  skip: '跳过（skip）', memory: '存为记忆（memory）', pending: '待定（pending）'
}
```

后端 `decision_type` 新增了 `enhanced`、`gap_send`、`idle_send`、`long_idle_send` 等值，前端字典没同步更新 → 英文回退。

### Bug 4：念头"来源"显示 NULL

**位置**：`backend/services/active_consciousness_service.py` `reevaluate_delayed_thoughts`

```python
ActiveConsciousnessService.write_thought_log(
    heartbeat_id=None,
    thought_type=thought.thought_type,
    ...
    # ← 缺 recall_source 和 recall_count
)
```

延迟队列重评估升级时写入念头日志**漏传** recall_source / recall_count → 数据库字段为 NULL（432 条受影响）。

## 附加需求：Hindsight 存储列升级

**当前状态**：
- `details.hindsight_stored` 埋在 details JSON 字符串里
- 前端要解析 JSON 才能看到
- 数据库查询/索引/统计都不友好

**升级**：提升为数据库列 `hindsight_stored BOOLEAN DEFAULT 0`

## 修复方案

### 改动 1：念头详情"是否发送"用 type 作首要依据

**位置**：`ActiveConsciousness.vue` `getThoughtResultTitle` / `getSendResultLabel`

```js
function getThoughtResultTitle(details) {
  // 优先：依据 type 判断是否真的发送（type=memory/silence/time 不会发送）
  if (['memory', 'silence', 'time'].includes(details.type)) {
    return getThoughtResultTitleByType(details)
  }
  // 否则：看 message_sending.success（真实发送结果）
  if (details.message_sending && typeof details.message_sending.success === 'boolean') {
    return details.message_sending.success ? '已发送消息' : '发送失败'
  }
  // 兜底：依 decision（auto_send/gap_send 等才是发送类）
  if (details.decision === 'auto_send' || details.decision === 'gap_send'
      || details.decision === 'idle_send' || details.decision === 'long_idle_send') {
    return '已发送消息'
  }
  if (details.decision === 'memory') return '存为记忆'
  if (details.decision === 'delay_send') return '等待发送'
  if (details.decision === 'skip') return '跳过'
  if (details.decision === 'enhanced') return '增强念头'
  return '未知状态'
}
```

### 改动 2：心跳表格用 row.message_sent

**位置**：`ActiveConsciousness.vue` `heartbeatColumns` L2079

```js
{ title: '发送消息', key: 'message_sent', width: 80, render(row) {
  // 直接读后端表字段（最准确）
  if (row.message_sent === true || row.message_sent === 1) {
    return h(NTag, { type: 'success', size: 'small' }, { default: () => '✅ 已发送' })
  }
  if (row.message_sent === false || row.message_sent === 0) {
    return h(NTag, { type: 'error', size: 'small' }, { default: () => '❌ 未发送' })
  }
  return '-'
} },
```

删除 `details_parsed.message_sending.success` 兜底。

### 改动 3：DECISION_TYPE_CN 字典补全

**位置**：`ActiveConsciousness.vue` `DECISION_TYPE_CN`

```js
const DECISION_TYPE_CN = {
  auto_send: '立即发送（auto_send）',
  delay_send: '延迟发送（delay_send）',
  skip: '跳过（skip）',
  memory: '存为记忆（memory）',
  pending: '待定（pending）',
  enhanced: '增强念头（enhanced）',
  gap_send: '间隔发送（gap_send）',
  idle_send: '空闲发送（idle_send）',
  long_idle_send: '长时空闲发送（long_idle_send）',
}
```

### 改动 4：reevaluate_delayed_thoughts 补 recall_source / recall_count

**位置**：`active_consciousness_service.py` `reevaluate_delayed_thoughts` write_thought_log 调用

```python
ActiveConsciousnessService.write_thought_log(
    heartbeat_id=None,
    thought_type=thought.thought_type,
    content=thought.content,
    intensity=intensity,
    decision="delay_send",
    reason=f"延迟队列升级: old_score={thought.score:.3f}, new_score={new_score:.3f}",
    score=new_score,
    recall_source="delay_queue",       # ← 新增：标记来自延迟队列重评估
    recall_count=0,                   # ← 新增：重评估不再单独召回
    chat_heat=status.get("chat_heat", {}).get("heat", 0),
    emotional_intensity=intensity,
    details=json.dumps({
        "source": "delay_queue",
        "original_score": thought.score,
        "new_score": new_score,
        "retry_count": thought.retry_count,
        "hindsight_stored": False,     # ← 重评估路径默认不存 Hindsight（实际写也未必成功）
    }, ensure_ascii=False)
)
```

### 改动 5：数据库列 `hindsight_stored` 升级

#### 5.1 数据迁移

由于 `active.db` 是 SQLAlchemy 创建的，开发/部署时需要：
- 模型加 `hindsight_stored = Column(Boolean, default=False)`
- 启动时调用 `Base.metadata.create_all` —— 但 SQLAlchemy **不会自动给现有表加列**
- 需要手动迁移：

```python
# services/migrate.py
def ensure_hindsight_stored_column():
    """添加 hindsight_stored 列（如果不存在）"""
    with active_engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(active_thought_logs)"))]
        if "hindsight_stored" not in cols:
            conn.execute(text("ALTER TABLE active_thought_logs ADD COLUMN hindsight_stored BOOLEAN DEFAULT 0"))
            conn.commit()
            logger.info("已添加 hindsight_stored 列到 active_thought_logs")
```

启动 main.py 时调用一次。

#### 5.2 模型加字段

`backend/models/active_consciousness.py`:

```python
class ActiveThoughtLog(Base):
    __tablename__ = "active_thought_logs"
    ...
    hindsight_stored = Column(Boolean, default=False)
```

#### 5.3 write_thought_log 函数加参数

```python
def write_thought_log(
    heartbeat_id, thought_type, content, intensity,
    decision, reason=None, score=None,
    recall_count=None, recall_source=None,
    chat_heat=None, emotional_intensity=None,
    hindsight_stored: bool = False,    # ← 新增参数
    details=None
) -> int:
    ...
    result = conn.execute(text("""
        INSERT INTO active_thought_logs
        (heartbeat_id, type, content, intensity, decision, reason, score,
         recall_count, recall_source, chat_heat, emotional_intensity,
         hindsight_stored, details)            # ← 加列
        VALUES (...)
    """), {
        ...
        "hindsight_stored": hindsight_stored,
        ...
    })
```

#### 5.4 3 处调用方传入实际值

```python
# L1628 memory 路径
stored = await retain_thought_to_hindsight(thought, merged_state, thought_type, score)
all_details["hindsight_stored"] = stored
ActiveConsciousnessService.write_thought_log(
    ...
    hindsight_stored=stored,   # ← 传入
)

# L1713 auto_send 成功路径
stored = await retain_thought_to_hindsight(thought, merged_state, thought_type, score)
all_details["hindsight_stored"] = stored
ActiveConsciousnessService.write_thought_log(
    ...
    hindsight_stored=stored,   # ← 传入
)

# L2642 test 路径
ActiveConsciousnessService.write_thought_log(
    ...
    hindsight_stored=False,    # ← 测试接口默认 False
)
```

#### 5.5 reevaluate_delayed_thoughts 补 False（属于改动 4 的一部分）

```python
ActiveConsciousnessService.write_thought_log(
    ...
    hindsight_stored=False,    # ← 重评估路径不存 Hindsight
)
```

### 改动 6：前端 thoughts 列表增加"存储 Hindsight"列

**位置**：`ActiveConsciousness.vue` `thoughtColumns`

```js
{ title: '存储 Hindsight', key: 'hindsight_stored', width: 100, render(row) {
  if (row.hindsight_stored === true || row.hindsight_stored === 1) {
    return h(NTag, { type: 'success', size: 'small' }, { default: () => '✅ 已存' })
  }
  if (row.hindsight_stored === false || row.hindsight_stored === 0) {
    return h(NTag, { type: 'default', size: 'small' }, { default: () => '未存' })
  }
  return '-'  # 历史 NULL 数据
} },
```

`get_thoughts` 后端接口 SELECT 已包含此列（直接读 row.hindsight_stored）。

## 测试

### 单元验证

1. **数据库迁移**：启动后端，确认 `PRAGMA table_info(active_thought_logs)` 含 `hindsight_stored` 列
2. **列写入**：手动调一次心跳，确认新念头 `hindsight_stored=False`（Hindsight 未开）
3. **前端回显**：打开 ActiveConsciousness 念头列表，"存储 Hindsight"列显示"未存"

### 集成验证

1. 触发心跳生成 memory 念头 → `hindsight_stored=False`（保留 details.hindsight_stored 兜底）
2. 触发心跳生成 auto_send 念头 → `hindsight_stored=False`
3. 触发心跳生成 delay_send 念头 + 升级 → `hindsight_stored=False`、`recall_source="delay_queue"`、`recall_count=0`
4. 念头 #1040 详情 → 标签显示"存为记忆"（不是"已发送消息"）
5. 心跳日志表格 → "发送消息"列显示真实状态（✅/❌）
6. 念头日志"决策"列 → enhanced 显示中文标签
7. 念头日志"来源"列 → 不再 NULL（delay_send 升级路径填了 recall_source="delay_queue"）

## 影响范围

| 改动 | 文件 | 影响 |
|------|------|------|
| 1 | frontend ActiveConsciousness.vue | 念头详情判定逻辑 |
| 2 | frontend ActiveConsciousness.vue | 心跳表格列字段来源 |
| 3 | frontend ActiveConsciousness.vue | DECISION_TYPE_CN 字典 |
| 4 | backend active_consciousness_service.py | reevaluate_delayed_thoughts write_thought_log 调用 |
| 5.1 | backend services/migrate.py (新) | 数据库迁移 |
| 5.2 | backend models/active_consciousness.py | 模型字段 |
| 5.3-5.5 | backend active_consciousness_service.py | write_thought_log + 调用方 |
| 6 | frontend ActiveConsciousness.vue | 念头表格新列 |

## 风险

1. **历史数据迁移**：旧数据 `hindsight_stored=NULL`，前端显示 `-`（不会报错）
2. **迁移失败**：SQLite ALTER TABLE 添加列通常不失败，但 `PRAGMA table_info` 检查 + try/except 包裹
3. **并发**：单进程启动时迁移，重复启动也安全（PRAGMA 检查 + 跳过）
4. **Hindsight 未开启**：所有新念头 `hindsight_stored=False`，开启后会自动存为 True

## 不在范围内

- heartbeat_logs 也加 hindsight_stored 列（心跳不存 Hindsight，无需）
- 历史数据回填 hindsight_stored（不可能回填，缺失就是缺失）
- 后端加 CHECK 约束限制 recall_source 合法值（待后续单独 issue）

## 验收标准

- [ ] 后端语法检查通过
- [ ] 前端 build 成功
- [ ] 数据库迁移成功（PRAGMA 看到新列）
- [ ] 新念头写入有 hindsight_stored 字段（值=0 因 Hindsight 未开）
- [ ] 心跳表格"发送消息"列根据 row.message_sent 显示
- [ ] 念头 #1040 详情显示"存为记忆"
- [ ] 念头日志"决策"列 enhanced 显示中文
- [ ] delay_send 升级路径念头 recall_source="delay_queue"
- [ ] 念头日志新列"存储 Hindsight"显示正常