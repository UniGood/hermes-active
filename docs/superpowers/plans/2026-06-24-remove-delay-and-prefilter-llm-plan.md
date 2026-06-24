# 去掉延迟发送 + LLM 调用前置预评 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 删除延迟发送功能并加入 LLM 调用前的预评分过滤，节省 token。

**架构：** 决策矩阵从 4 档（auto_send/delay_send/memory/skip）改为 3 档（auto_send/memory/skip）。心跳流程在调 LLM 前先算 pre_score，低于 memory_threshold 直接 skip 不调 LLM；高于则调 LLM 并用真实 score 决策。

**技术栈：** Python 3.12 + FastAPI + SQLite；Vue 3 + naive-ui。

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/services/active_consciousness_service.py` | 修改 | 删除 6 个 delay 函数、改决策分支、加 pre_score 函数、改默认值/校验 |
| `frontend/src/views/ActiveConsciousness.vue` | 修改 | 配置页面删除 delay_threshold 字段 |

---

## 任务 1：备份当前 active_consciousness_service.py

**文件：**
- 不修改（备份）

- [ ] **步骤 1：备份原文件**

```bash
cp ~/.hermes/hermes-active/backend/services/active_consciousness_service.py /tmp/active_consciousness_service.py.bak
ls -la /tmp/active_consciousness_service.py.bak
```

预期：文件存在

---

## 任务 2：删除 6 个 delay 相关函数

**文件：**
- 修改：`backend/services/active_consciousness_service.py`

- [ ] **步骤 1：定位 6 个 delay 函数位置**

打开文件，搜索以下函数名（每个函数前 N 行定位）：

```bash
grep -n "^def \|^async def " ~/.hermes/hermes-active/backend/services/active_consciousness_service.py | grep -i delay
```

预期找到：
- `add_to_delay_queue`（约 L2700+）
- `add_to_delay_queue_v2`
- `generate_thought_for_delay`（约 L1346+）
- `get_delayed_thoughts`（约 L2400+）
- `reevaluate_delayed_thoughts`
- `save_delayed_thoughts`

- [ ] **步骤 2：删除 6 个函数**

对每个函数：
1. 找到函数定义行（含 `def func_name(` 或 `async def func_name(`）
2. 找下一个顶层定义（`^def ` 或 `^async def ` 或 `^class `）
3. 删除之间的所有代码

**对每个函数执行如下查找+删除模式**：

```python
# 示例：删除 add_to_delay_queue
# 找到 def add_to_delay_queue( 之后所有到下一个 def/get_delayed_thoughts/... 之前的内容
# 用 read_file 看上下文，逐个删除
```

具体步骤：

**A) 删除 `generate_thought_for_delay`**

文件约 L1346-1362：
```python
async def generate_thought_for_delay(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> Optional[Dict]:
    """为延迟队列生成念头（使用 ThoughtEngine 统一入口）"""
    try:
        from services.thought_engine import ThoughtEngine
        engine = ThoughtEngine(config)
        result = await engine.generate(status)
        return result  # 返回完整结果（含 thought + llm_details + context_bundle）
    except Exception as e:
        logger.warning("延迟念头生成失败: %s", e)
        return None
```

直接删除这整个函数（含前后空行）。

**B) 删除 `add_to_delay_queue` 和 `add_to_delay_queue_v2`**

查找：
```python
def add_to_delay_queue(
def add_to_delay_queue_v2(
```

每个都是完整独立函数，连同前后空行删除。

**C) 删除 `save_delayed_thoughts`**

查找 `def save_delayed_thoughts(`，删除到下一个 `def ` 之前。

**D) 删除 `get_delayed_thoughts`**

查找 `def get_delayed_thoughts(`，删除到下一个 `def ` 之前。

**E) 删除 `reevaluate_delayed_thoughts`**

这是最大的函数（从开头到 `return stats`）。查找 `def reevaluate_delayed_thoughts(` 到下一个 `def ` 之前，删除整个函数体。

- [ ] **步骤 3：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/active_consciousness_service.py').read()); print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 4：Commit**

```bash
cd ~/.hermes/hermes-active && git add backend/services/active_consciousness_service.py
git commit -m "refactor: 删除 6 个延迟发送相关函数"
```

---

## 任务 3：删除决策矩阵的 delay_send 分支

**文件：**
- 修改：`backend/services/active_consciousness_service.py`

- [ ] **步骤 1：定位决策矩阵**

搜 `def make_decision` 或 `score > send_threshold`：

```bash
grep -n "def make_decision\|score > send_threshold\|score > delay_threshold" ~/.hermes/hermes-active/backend/services/active_consciousness_service.py
```

- [ ] **步骤 2：改 make_decision 函数**

找到以下模式：

```python
if score > send_threshold:
    return "auto_send", f"score={score:.3f} > {send_threshold} ({reason})", score
elif score > delay_threshold:
    return "delay_send", f"score={score:.3f} > {delay_threshold} ({reason})", score
elif score > memory_threshold:
    return "memory", f"score={score:.3f} > {memory_threshold} ({reason})", score
else:
    return "skip", f"score={score:.3f} <= {memory_threshold} ({reason})", score
```

改为：

```python
if score > send_threshold:
    return "auto_send", f"score={score:.3f} > {send_threshold} ({reason})", score
elif score > memory_threshold:
    return "memory", f"score={score:.3f} > {memory_threshold} ({reason})", score
else:
    return "skip", f"score={score:.3f} <= {memory_threshold} ({reason})", score
```

删除 `elif score > delay_threshold:` 那 1 行。

- [ ] **步骤 3：删除 delay_send elif 分支（在 decide_and_execute 中）**

搜 `elif decision_type == "delay_send":`：

```bash
grep -n "delay_send" ~/.hermes/hermes-active/backend/services/active_consciousness_service.py
```

找到后删除整个 `elif decision_type == "delay_send":` 块（含后面所有缩进代码），直到 `elif decision_type == "auto_send":` 或下一个 `else:` 之前。

- [ ] **步骤 4：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/active_consciousness_service.py').read()); print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 5：Commit**

```bash
cd ~/.hermes/hermes-active && git add backend/services/active_consciousness_service.py
git commit -m "refactor: 决策矩阵删 delay_send 分支（4 档变 3 档）"
```

---

## 任务 4：删除 delay_threshold 校验和默认值

**文件：**
- 修改：`backend/services/active_consciousness_service.py`

- [ ] **步骤 1：定位 delay_threshold 引用**

```bash
grep -n "delay_threshold" ~/.hermes/hermes-active/backend/services/active_consciousness_service.py
```

预期找到：
- 配置校验函数（约 L406+）
- 默认值定义（约 L130+）
- make_decision 中已删除
- status 响应（约 L795+）

- [ ] **步骤 2：删除配置校验代码**

找到类似：

```python
try:
    delay_threshold = float(decision.get("delay_threshold", 0.3))
except (ValueError, TypeError):
    errors.append("延迟阈值必须是数字")
    delay_threshold = 0.3
```

整段删除（含 try/except）。

- [ ] **步骤 3：删除校验约束**

找到类似：

```python
if not (0 <= delay_threshold <= 1):
    errors.append("延迟阈值必须在 0-1 之间")
...
if send_threshold <= delay_threshold:
    errors.append("发送阈值必须大于延迟阈值")
if delay_threshold <= memory_threshold:
    errors.append("延迟阈值必须大于记忆阈值")
```

删除这三行（约束已不再适用——只有 send 和 memory 两个阈值）。

- [ ] **步骤 4：删除默认配置响应**

找到 status 函数里：

```python
"delay_threshold": float(decision_config.get("delay_threshold", 0.15)),
```

删除这一行。

- [ ] **步骤 5：删除 _DEFAULTS 里的 delay_threshold**

搜 `decision_config_defaults` 或类似：

```bash
grep -n "delay_threshold" ~/.hermes/hermes-active/backend/services/active_consciousness_service.py
```

找到 default 值定义（如 `"active_consciousness.decision.delay_threshold": "0.15"`）整行删除。

- [ ] **步骤 6：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/active_consciousness_service.py').read()); print('OK')"
```

- [ ] **步骤 7：Commit**

```bash
cd ~/.hermes/hermes-active && git add backend/services/active_consciousness_service.py
git commit -m "refactor: 删除 delay_threshold 配置项（校验+默认值+响应）"
```

---

## 任务 5：清理数据库 delay_queue

**文件：**
- 修改：数据库 active.db

- [ ] **步骤 1：清空 delayed_thoughts 队列**

```bash
cd ~/.hermes/hermes-active/backend && python -c "
from services.active_consciousness_service import save_delayed_thoughts, get_delayed_thoughts
# 即使 get/save 函数被删也用 SQLAlchemy 直接清
from models.database import active_engine
from sqlalchemy import text
with active_engine.connect() as conn:
    result = conn.execute(text(\"UPDATE configs SET value='[]' WHERE key='active_consciousness.delayed_thoughts'\"))
    conn.commit()
    print(f'清空延迟队列，影响 {result.rowcount} 行')
"
```

预期：影响 1 行

- [ ] **步骤 2：验证清理**

```bash
cd ~/.hermes/hermes-active/backend && python -c "
from models.database import active_engine
from sqlalchemy import text
with active_engine.connect() as conn:
    r = conn.execute(text(\"SELECT value FROM configs WHERE key='active_consciousness.delayed_thoughts'\")).fetchone()
    print('queue now:', r[0])
"
```

预期：输出 `[]`

- [ ] **步骤 3：清空 delay 配置块**

```bash
cd ~/.hermes/hermes-active/backend && python -c "
from models.database import active_engine
from sqlalchemy import text
with active_engine.connect() as conn:
    result = conn.execute(text(\"DELETE FROM configs WHERE key LIKE 'active_consciousness.delay.%'\"))
    conn.commit()
    print(f'删除 delay 配置，影响 {result.rowcount} 行')
"
```

预期：影响 5-6 行（enabled/max_retry/retry_interval/minutes/max_queue_size/max_age_hours）

---

## 任务 6：新增 LLM 调用前置预评分函数

**文件：**
- 修改：`backend/services/active_consciousness_service.py`

- [ ] **步骤 1：定位决策矩阵函数**

```bash
grep -n "def make_decision\|^def determine_decision" ~/.hermes/hermes-active/backend/services/active_consciousness_service.py
```

找到决策函数（已改为 3 档）。

- [ ] **步骤 2：在决策函数前添加 pre_calculate_score**

在 `make_decision` 函数前（之前 `add_to_delay_queue` 已删的空位）添加：

```python
def pre_calculate_score(
    emotion_state: EmotionState,
    status: Dict[str, Any],
    decision_config: Dict[str, Any]
) -> float:
    """在不调 LLM 的情况下估算 score（用于过滤低分心跳，节省 token）

    算法复用 make_decision 的核心公式：
        score = intensity × time_fitness × silence_factor × frequency_limit

    Returns:
        预估 score
    """
    intensity = emotion_state.intensity()

    time_fitness, _ = get_time_fitness()

    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes < 30:
        silence_factor = 0.6
    elif silence_minutes < 60:
        silence_factor = 0.75
    elif silence_minutes < 180:
        silence_factor = 0.85
    elif silence_minutes < 360:
        silence_factor = 0.95
    else:
        silence_factor = 1.0

    hour_sent = status.get("hour_sent_count", 0)
    max_per_hour = decision_config.get("max_per_hour", 100)
    frequency_limit = 1.0 if hour_sent < max_per_hour else 0.0

    return intensity * time_fitness * silence_factor * frequency_limit
```

- [ ] **步骤 3：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/active_consciousness_service.py').read()); print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 4：Commit**

```bash
cd ~/.hermes/hermes-active && git add backend/services/active_consciousness_service.py
git commit -m "feat: 新增 pre_calculate_score 函数（LLM 前置预评分）"
```

---

## 任务 7：心跳流程接入前置预评分

**文件：**
- 修改：`backend/services/active_consciousness_service.py`

- [ ] **步骤 1：定位心跳主循环**

```bash
grep -n "async def run_heartbeat\|run_heartbeat_loop\|async def heartbeat\b" ~/.hermes/hermes-active/backend/services/active_consciousness_service.py
```

找到 `run_heartbeat` 函数或类似入口。

- [ ] **步骤 2：在调 LLM 之前插入预评分判断**

找到类似：

```python
async def run_heartbeat(...):
    ...
    # 调 LLM 生成念头
    thought = await generate_thought_for_delay(...)  # 或类似
    ...
```

改为：

```python
async def run_heartbeat(...):
    ...
    # 阶段 1：前置预评分（不调 LLM）
    decision_config = config.get("decision", {})
    pre_score = pre_calculate_score(merged_state, status, decision_config)
    memory_threshold = decision_config.get("memory_threshold", 0.05)

    if pre_score < memory_threshold:
        # 预评分太低，直接 skip，节省 LLM 调用
        all_details["decision"] = {
            "decision": "skip",
            "reason": f"pre_score={pre_score:.3f} < {memory_threshold} (过滤低分心跳)",
            "pre_score": pre_score,
            "skipped_llm_call": True
        }
        # 写心跳日志但不调 LLM
        ActiveConsciousnessService.write_heartbeat_log(
            heartbeat_id=heartbeat_id,
            duration_ms=duration_ms,
            thoughts_generated=0,
            message_sent=0,
            longing_before=...,
            longing_after=...,
            chat_heat=...,
            emotional_intensity=...,
            recall_count=...,
            details=json.dumps(all_details, ensure_ascii=False)
        )
        return

    # 阶段 2：调 LLM 生成念头（值得消耗 token）
    ...
```

**注意**：具体实现取决于 `run_heartbeat` 当前结构——可能需要根据实际逻辑调整。

- [ ] **步骤 3：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "import ast; ast.parse(open('services/active_consciousness_service.py').read()); print('OK')"
```

预期：输出 `OK`

- [ ] **步骤 4：Commit**

```bash
cd ~/.hermes/hermes-active && git add backend/services/active_consciousness_service.py
git commit -m "feat: 心跳前置预评分 < memory_threshold 直接 skip"
```

---

## 任务 8：清理前端 delay_threshold UI

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`

- [ ] **步骤 1：定位前端决策配置 UI**

```bash
grep -n "delay_threshold\|延迟阈值" ~/.hermes/hermes-active/frontend/src/views/ActiveConsciousness.vue
```

预期找到：
- 标签"延迟阈值"
- input 绑定 `delay_threshold`

- [ ] **步骤 2：删除 delay_threshold UI 块**

找到类似：

```vue
<n-form-item label="延迟阈值">
  <n-input-number v-model:value="config.decision.delay_threshold" :min="0" :max="1" :step="0.05" />
</n-form-item>
```

整段删除。

- [ ] **步骤 3：删除前端默认值**

搜 `defaultConfig` 或类似：

```javascript
delay_threshold: 0.15,  // 找到后删除这行
```

- [ ] **步骤 4：前端 build**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build 2>&1 | tail -3
```

预期：`✓ built in X.Xs`

- [ ] **步骤 5：Commit**

```bash
cd ~/.hermes/hermes-active && git add frontend/src/views/ActiveConsciousness.vue
git commit -m "refactor(ui): 决策配置删除延迟阈值字段"
```

---

## 任务 9：端到端测试

- [ ] **步骤 1：重启后端**

```bash
ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}' | xargs -r kill -9
sleep 1
fuser -k 18720/tcp 2>/dev/null
sleep 1
cd ~/.hermes/hermes-active/backend && nohup python main.py > /tmp/hermes-fix.log 2>&1 &
sleep 5
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:18720/api/auth/me
```

预期：返回 403

- [ ] **步骤 2：拉 status API 验证 delay_threshold 不再返回**

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:18720/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s http://127.0.0.1:18720/api/active-consciousness/status -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
config = d.get('config', {}).get('decision', {})
print('config keys:', sorted(config.keys()))
assert 'delay_threshold' not in config, 'delay_threshold 仍在！'
print('✓ delay_threshold 已删除')
print('memory_threshold:', config.get('memory_threshold'))
print('send_threshold:', config.get('send_threshold'))
"
```

预期：输出 `✓ delay_threshold 已删除`

- [ ] **步骤 3：等一次心跳验证 pre_score 过滤**

```bash
sleep 60
# 等心跳自动跑（约 5 分钟一次，但这里 60 秒可能没新心跳）
# 改用查心跳日志
sqlite3 ~/.hermes/hermes-active/data/active.db "SELECT id, thoughts_generated, message_sent, json_extract(details, '$.decision') FROM active_heartbeat_logs ORDER BY id DESC LIMIT 3"
```

预期：新心跳 decisions 是 auto_send / memory / skip 之一（不会看到 delay_send）

- [ ] **步骤 4：清理验证**

```bash
sqlite3 ~/.hermes/hermes-active/data/active.db "SELECT key FROM configs WHERE key LIKE '%delay%' OR key LIKE '%delay_threshold%'"
```

预期：无 delay 相关配置项

---

## 任务 10：推送所有 commit

- [ ] **步骤 1：推送**

```bash
cd ~/.hermes/hermes-active && https_proxy=http://127.0.0.1:7890 git push origin v0.2.2
```

预期：所有 commit 推送到 v0.2.2 远程分支

- [ ] **步骤 2：验证**

```bash
cd ~/.hermes/hermes-active && git log --oneline origin/v0.2.2 -10
```

预期：看到本次所有 8-9 个 commit

---

## 执行选项

计划已完成并保存到 `docs/superpowers/plans/2026-06-24-remove-delay-and-prefilter-llm-plan.md`。

**两种执行方式：**

1. **内联执行**（推荐）— 在当前会话按任务顺序执行，10 个任务规模适中
2. **子代理驱动** — 每个任务调度一个新子代理（不必要）

我将使用 **内联执行** 方式按步骤做。

---

## 自检结果

**1. 规格覆盖度**：
- ✅ 删除 6 个 delay 函数 → 任务 2
- ✅ 删除决策矩阵 delay_send → 任务 3
- ✅ 删除 delay_threshold 配置 → 任务 4
- ✅ 清理数据库 delay_queue → 任务 5
- ✅ 新增 pre_calculate_score → 任务 6
- ✅ 心跳流程接入预评分 → 任务 7
- ✅ 清理前端 UI → 任务 8
- ✅ 端到端验证 → 任务 9
- ✅ 推送 → 任务 10

**2. 占位符扫描**：
- ❌ 无"待定"、"TODO"、"补充细节"
- ❌ 无"为上述代码编写测试"（任务 9 是手动测试）

**3. 类型一致性**：
- `pre_calculate_score` 在任务 6 定义 → 任务 7 调用 ✓
- `make_decision` 仍返回 3 档 → 任务 3 改 ✓
- `write_heartbeat_log` 已存在（不在改动列表） → 任务 7 引用 ✓