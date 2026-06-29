# 念头展示问题修复 + Hindsight 存储列升级 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 修复 ActiveConsciousness 页面的 4 个念头/心跳展示 bug，并把 `details.hindsight_stored` 字段升级为数据库列方便查询和前端展示。

**架构：**
- 后端：在 `active_thought_logs` 表添加 `hindsight_stored` 列，启动时迁移；`write_thought_log` 加参数，4 处调用方传入实际值
- 前端：念头详情判定用 `type` 字段、心跳表格列改读 `row.message_sent`、DECISION_TYPE_CN 字典补全、新增"存储 Hindsight"列

**技术栈：**
- 后端：Python 3.12 + SQLAlchemy + SQLite（active.db）
- 前端：Vue 3 + naive-ui

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/models/active_consciousness.py` | 修改 | ActiveThoughtLog 模型加 `hindsight_stored` 字段 |
| `backend/services/migrate.py` | 创建 | 数据库迁移（PRAGMA 检查 + ALTER TABLE 添加列） |
| `backend/services/active_consciousness_service.py` | 修改 | `write_thought_log` 加参数；4 处调用方传入；`reevaluate_delayed_thoughts` 补 recall_source/recall_count |
| `backend/main.py` | 修改 | 启动时调迁移函数 |
| `frontend/src/views/ActiveConsciousness.vue` | 修改 | 4 处逻辑修复 + 字典补全 + 新增列 |

---

## 任务 1：添加模型字段

**文件：**
- 修改：`backend/models/active_consciousness.py`

- [ ] **步骤 1：定位 ActiveThoughtLog 类**

打开 `backend/models/active_consciousness.py`，找到 `ActiveThoughtLog` 类定义。

- [ ] **步骤 2：添加字段**

在 `recall_source` 字段后添加：

```python
hindsight_stored = Column(Boolean, default=False)
```

- [ ] **步骤 3：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('models/active_consciousness.py').read()); print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 4：Commit**

```bash
git add backend/models/active_consciousness.py
git commit -m "feat(model): active_thought_logs 加 hindsight_stored 字段"
```

---

## 任务 2：创建数据库迁移函数

**文件：**
- 创建：`backend/services/migrate.py`

- [ ] **步骤 1：创建文件**

新建 `backend/services/migrate.py`：

```python
"""
数据库迁移：自动补齐 active.db 缺失的列
"""
import logging

logger = logging.getLogger("hermes.migrate")


def ensure_column(table_name: str, column_name: str, column_type: str, default_sql: str = "DEFAULT 0") -> bool:
    """确保指定表的指定列存在，不存在则 ALTER TABLE 添加。

    Args:
        table_name: 表名
        column_name: 列名
        column_type: 列类型（如 BOOLEAN / TEXT）
        default_sql: 默认值 SQL 片段

    Returns:
        True 如果添加了新列，False 如果列已存在
    """
    from sqlalchemy import text
    from models.database import active_engine

    with active_engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})"))]
        if column_name in cols:
            logger.debug("列 %s.%s 已存在，跳过迁移", table_name, column_name)
            return False
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} {default_sql}"))
        conn.commit()
        logger.info("已添加列 %s.%s (%s)", table_name, column_name, column_type)
        return True


def run_migrations() -> None:
    """运行所有迁移（启动时调用）"""
    # active_thought_logs 表：添加 hindsight_stored 列
    ensure_column("active_thought_logs", "hindsight_stored", "BOOLEAN", "DEFAULT 0")
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/migrate.py').read()); print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 3：手动运行迁移函数验证**

```bash
cd ~/.hermes/hermes-active/backend && python -c "from services.migrate import run_migrations; run_migrations()"
```

预期：日志输出"列 active_thought_logs.hindsight_stored 已存在"（因为步骤 1 模型加字段后 SQLAlchemy 还没建表，需要手动 ALTER）

如果日志说"已添加列"，说明第一次成功。

- [ ] **步骤 4：验证列已添加**

```bash
sqlite3 ~/.hermes/hermes-active/data/active.db "PRAGMA table_info(active_thought_logs)" | grep hindsight
```

预期：输出一行包含 `hindsight_stored`

- [ ] **步骤 5：再次运行验证幂等性**

```bash
cd ~/.hermes/hermes-active/backend && python -c "from services.migrate import run_migrations; run_migrations()"
```

预期：日志输出"列已存在"（无错误）

- [ ] **步骤 6：Commit**

```bash
git add backend/services/migrate.py
git commit -m "feat(migrate): 添加 active_thought_logs.hindsight_stored 迁移"
```

---

## 任务 3：main.py 启动时调迁移

**文件：**
- 修改：`backend/main.py`

- [ ] **步骤 1：定位 startup 钩子**

打开 `backend/main.py`，找到 `start_scheduler()` 或类似 startup 函数（一般在 app = FastAPI() 之后）。

- [ ] **步骤 2：添加迁移调用**

在 `start_scheduler()` 之前或 FastAPI app 启动时（`on_event("startup")` 处理器）添加：

```python
from services.migrate import run_migrations

@app.on_event("startup")
async def startup_migrations():
    """启动时运行数据库迁移"""
    run_migrations()
```

如果 main.py 已有其他 `@app.on_event("startup")` 处理器（如 lifespan），合并到现有处理器中。

- [ ] **步骤 3：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('main.py').read()); print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 4：Commit**

```bash
git add backend/main.py
git commit -m "feat(main): 启动时自动运行数据库迁移"
```

---

## 任务 4：write_thought_log 函数加参数

**文件：**
- 修改：`backend/services/active_consciousness_service.py`

- [ ] **步骤 1：定位 write_thought_log 函数**

打开文件，找到 `def write_thought_log(` 函数签名（参数列表）。

- [ ] **步骤 2：添加 hindsight_stored 参数**

修改函数签名，在 `details` 参数前添加：

```python
def write_thought_log(
    heartbeat_id: Optional[int],
    thought_type: str,
    content: str,
    intensity: float = 0.5,
    decision: str = "pending",
    reason: Optional[str] = None,
    score: Optional[float] = None,
    recall_count: Optional[int] = None,
    recall_source: Optional[str] = None,
    chat_heat: Optional[float] = None,
    emotional_intensity: Optional[float] = None,
    hindsight_stored: bool = False,    # ← 新增
    details: Optional[str] = None
) -> int:
```

- [ ] **步骤 3：修改 INSERT 语句**

在 `INSERT INTO active_thought_logs (...)` SQL 中添加 `hindsight_stored` 列；在对应 VALUES 参数 dict 中加 `"hindsight_stored": hindsight_stored`。

完整 INSERT 应包含列：
```python
INSERT INTO active_thought_logs
(heartbeat_id, type, content, intensity, decision, reason, score,
 recall_count, recall_source, chat_heat, emotional_intensity,
 hindsight_stored, details)
VALUES
(:heartbeat_id, :type, :content, :intensity, :decision, :reason, :score,
 :recall_count, :recall_source, :chat_heat, :emotional_intensity,
 :hindsight_stored, :details)
```

完整参数 dict 加：
```python
"hindsight_stored": hindsight_stored,
```

- [ ] **步骤 4：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/active_consciousness_service.py').read()); print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 5：Commit**

```bash
git add backend/services/active_consciousness_service.py
git commit -m "feat(write_thought_log): 加 hindsight_stored 参数"
```

---

## 任务 5：3 处正常路径调用方传入 hindsight_stored

**文件：**
- 修改：`backend/services/active_consciousness_service.py`

- [ ] **步骤 1：定位 memory 路径 write_thought_log 调用**

搜 `ActiveConsciousnessService.write_thought_log(` 找到 decision_type=="memory" 分支（包含 `thought_type="memory"`）的调用。

- [ ] **步骤 2：补传 hindsight_stored**

在该 write_thought_log 调用所有 kwargs 后添加一行（在 `details=json.dumps(...)` 附近）：

```python
ActiveConsciousnessService.write_thought_log(
    heartbeat_id=heartbeat_id,
    thought_type=thought_type,
    content=thought,
    intensity=intensity,
    decision=decision_type,
    reason=f"...",
    score=score,
    recall_count=recall_count,
    recall_source="hindsight",
    chat_heat=...,
    emotional_intensity=intensity,
    hindsight_stored=stored,    # ← 新增（使用 retain_thought_to_hindsight 返回值）
    details=json.dumps({"emotion_state": merged_state.to_dict(), "hindsight_tags": hindsight_tags}, ensure_ascii=False)
)
```

- [ ] **步骤 3：定位 auto_send 成功路径调用**

搜 `decision_type == "auto_send"` 分支的 `if sent:` 内部 write_thought_log 调用。

- [ ] **步骤 4：补传 hindsight_stored**

同上添加 `hindsight_stored=stored,`：

```python
if sent:
    thought = gen_details.get("message_sending", {}).get("thought", "")
    if thought:
        stored = await retain_thought_to_hindsight(thought, merged_state, thought_type, score)
        all_details["hindsight_stored"] = stored
        ...
        ActiveConsciousnessService.write_thought_log(
            ...
            hindsight_stored=stored,    # ← 新增
            details=json.dumps(...)
        )
```

- [ ] **步骤 5：定位 test 接口调用**

搜 `retain_thought_to_hindsight(` 第三个调用（在 test 接口内），找到 test 路径的 write_thought_log 调用。

- [ ] **步骤 6：补传 hindsight_stored**

```python
ActiveConsciousnessService.write_thought_log(
    ...
    hindsight_stored=False,    # ← 测试接口默认 False
    ...
)
```

- [ ] **步骤 7：验证语法 + Commit**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/active_consciousness_service.py').read()); print('OK')"
git add backend/services/active_consciousness_service.py
git commit -m "feat: 3 处正常路径 write_thought_log 调用传 hindsight_stored"
```

---

## 任务 6：reevaluate_delayed_thoughts 补全字段

**文件：**
- 修改：`backend/services/active_consciousness_service.py`

- [ ] **步骤 1：定位重评估升级路径**

搜 `success = await send_message_to_target(config, thought.content)` 在 `reevaluate_delayed_thoughts` 函数内。

- [ ] **步骤 2：补全 write_thought_log 调用**

找到 `if success:` 块内的 `ActiveConsciousnessService.write_thought_log(` 调用，改写为：

```python
ActiveConsciousnessService.write_thought_log(
    heartbeat_id=None,
    thought_type=thought.thought_type,
    content=thought.content,
    intensity=intensity,
    decision="delay_send",
    reason=f"延迟队列升级: old_score={thought.score:.3f}, new_score={new_score:.3f}",
    score=new_score,
    recall_source="delay_queue",    # ← 新增
    recall_count=0,                # ← 新增
    chat_heat=status.get("chat_heat", {}).get("heat", 0),
    emotional_intensity=intensity,
    hindsight_stored=False,         # ← 新增（重评估路径默认 False）
    details=json.dumps({
        "source": "delay_queue",
        "original_score": thought.score,
        "new_score": new_score,
        "retry_count": thought.retry_count,
        "hindsight_stored": False,
    }, ensure_ascii=False)
)
```

- [ ] **步骤 3：验证语法 + Commit**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/active_consciousness_service.py').read()); print('OK')"
git add backend/services/active_consciousness_service.py
git commit -m "fix(cron): reevaluate_delayed_thoughts 补 recall_source/recall_count/hindsight_stored"
```

---

## 任务 7：后端语法 + 端到端测试

- [ ] **步骤 1：完整后端语法检查**

```bash
cd ~/.hermes/hermes-active/backend && python -c "
import ast
for f in ['models/active_consciousness.py', 'services/active_consciousness_service.py', 'services/migrate.py', 'main.py']:
    ast.parse(open(f).read())
    print(f'  ✓ {f}')
"
```

预期：所有文件 OK

- [ ] **步骤 2：重启后端**

```bash
ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}' | xargs -r kill -9
sleep 1
fuser -k 18720/tcp 2>/dev/null
sleep 1
cd ~/.hermes/hermes-active/backend && nohup python main.py > /tmp/hermes-active-fix.log 2>&1 &
sleep 5
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:18720/api/auth/me
```

预期：返回 403

- [ ] **步骤 3：检查迁移日志**

```bash
grep -E "hindsight_stored|迁移" /tmp/hermes-active-fix.log
```

预期：日志含 "已添加列" 或 "列已存在"

- [ ] **步骤 4：手动触发一次心跳验证新字段**

```bash
curl -s -X POST http://127.0.0.1:18720/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
```

拿 token 后触发测试或等下个心跳周期。然后：

```bash
sqlite3 ~/.hermes/hermes-active/data/active.db "SELECT id, decision, recall_source, hindsight_stored FROM active_thought_logs ORDER BY id DESC LIMIT 3"
```

预期：最新记录含 hindsight_stored=0（值=0 因 Hindsight 未开）

- [ ] **步骤 5：Commit 任何后端调试**

如果有调试改动就 commit，否则跳过：

```bash
git status
# 如果有改动
git add -A
git commit -m "chore: 后端语法 + 端到端验证通过"
```

---

## 任务 8：前端 DECISION_TYPE_CN 字典补全

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`

- [ ] **步骤 1：定位 DECISION_TYPE_CN**

搜 `DECISION_TYPE_CN` 找到字典定义（约在 thinkTypeLabelCn 函数附近）。

- [ ] **步骤 2：补全字典**

修改为：

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

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "fix(ui): DECISION_TYPE_CN 字典补全 enhanced/gap_send 等"
```

---

## 任务 9：前端念头详情 getThoughtResultTitle 用 type

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`

- [ ] **步骤 1：定位 getThoughtResultTitle**

搜 `function getThoughtResultTitle`。

- [ ] **步骤 2：改写函数**

修改为：

```js
function getThoughtResultTitle(details) {
  // 优先：依据 type 判断（type=memory/silence/time 不发送）
  const type = details.type || details.thought_type
  if (['memory', 'silence', 'time'].includes(type)) {
    if (type === 'memory') return '存为记忆（memory）'
    return getThoughtResultTitleByType(type)
  }
  // 否则：看 message_sending.success（真实发送结果）
  if (details.message_sending && typeof details.message_sending.success === 'boolean') {
    return details.message_sending.success ? '已发送消息' : '发送失败'
  }
  // 兜底：依 decision
  const sendDecisions = ['auto_send', 'gap_send', 'idle_send', 'long_idle_send']
  if (sendDecisions.includes(details.decision)) return '已发送消息'
  if (details.decision === 'memory') return '存为记忆'
  if (details.decision === 'delay_send') return '等待发送'
  if (details.decision === 'skip') return '跳过'
  if (details.decision === 'enhanced') return '增强念头'
  return '未知状态'
}

function getThoughtResultTitleByType(type) {
  // 复用 thoughtTypeLabelCn 或自定义映射
  const map = {
    silence: '沉默（silence）',
    time: '时间（time）',
    env: '环境（env）',
    emotion: '情绪（emotion）',
    assoc: '联想（assoc）',
  }
  return map[type] || type
}
```

如果 `thoughtTypeLabelCn` 已存在复用它即可，不需要新增 `getThoughtResultTitleByType`。

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "fix(ui): 念头详情用 type 判断是否发送，区分 memory vs auto_send"
```

---

## 任务 10：前端心跳表格用 row.message_sent

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`

- [ ] **步骤 1：定位 heartbeatColumns 中"发送消息"列**

搜 `title: '发送消息', key: 'message_sent'` 在 heartbeatColumns 数组内（约 L2079）。

- [ ] **步骤 2：替换列定义**

```js
{ title: '发送消息', key: 'message_sent', width: 80, render(row) {
  // 直接读后端表字段（最准确，SQL 已 SELECT）
  if (row.message_sent === true || row.message_sent === 1) {
    return h(NTag, { type: 'success', size: 'small' }, { default: () => '✅ 已发送' })
  }
  if (row.message_sent === false || row.message_sent === 0) {
    return h(NTag, { type: 'error', size: 'small' }, { default: () => '❌ 未发送' })
  }
  return '-'
} },
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "fix(ui): 心跳表格'发送消息'列改读 row.message_sent"
```

---

## 任务 11：前端念头表格新增"存储 Hindsight"列

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`

- [ ] **步骤 1：定位 thoughtColumns 数组**

搜 `const thoughtColumns` 找到数组定义。

- [ ] **步骤 2：新增列**

在数组末尾添加（在 `}` 之前）：

```js
{ title: '存储 Hindsight', key: 'hindsight_stored', width: 110, render(row) {
  if (row.hindsight_stored === true || row.hindsight_stored === 1) {
    return h(NTag, { type: 'success', size: 'small' }, { default: () => '✅ 已存' })
  }
  if (row.hindsight_stored === false || row.hindsight_stored === 0) {
    return h(NTag, { type: 'default', size: 'small' }, { default: () => '未存' })
  }
  return '-'  # 历史 NULL 数据
} },
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat(ui): 念头表格新增'存储 Hindsight'列"
```

---

## 任务 12：前端 build 验证 + 推送

- [ ] **步骤 1：前端 build**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build 2>&1 | tail -5
```

预期：看到 `✓ built in X.Xs`

- [ ] **步骤 2：推送所有提交**

```bash
cd ~/.hermes/hermes-active && https_proxy=http://127.0.0.1:7890 git push origin v0.2.2
```

预期：所有 commit 推送到 v0.2.2 远程分支

---

## 执行选项

计划已完成并保存到 `docs/superpowers/plans/2026-06-23-thought-display-fixes-plan.md`。

**两种执行方式：**

1. **内联执行** — 在当前会话中按任务顺序执行（推荐：11 个任务改 5 个文件，3-4 个 commit，规模小不需要子代理）

2. **子代理驱动** — 每个任务调度一个新子代理（适合大规模任务，本次不必要）

**选哪种方式？**

我会用 **内联执行** 方式按步骤做。