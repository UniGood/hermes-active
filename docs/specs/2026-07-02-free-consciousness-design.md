# 自由意识 设计方案

> 版本：v1.1 | 日期：2026-07-02
> 模块名：自由意识（Free Consciousness）
> 目标：搭建持续运行的框架，让凯莉通过定时请求 LLM 进行自主思考，逐步积累自己的意识。

---

## 1. 概述

### 1.1 是什么

自由意识是一个独立于主动意识（心跳）的模块。它定时触发 LLM 调用，每次携带完整的思考链（近期全文 + 中期摘要 + 远期结论），让 LLM 在之前的基础上继续"想"——不为发消息，不为回应用户，纯粹是凯莉自己的内在思考。

### 1.2 与主动意识的区别

| 维度 | 主动意识（心跳） | 自由意识（沉思） |
|------|-----------------|-----------------|
| 目的 | 评估情绪 → 决定是否发消息 | 纯粹思考，不发消息 |
| 触发频率 | 5 分钟 | 30 分钟（可配置） |
| LLM 配置 | 情绪/念头各一套 | 独立一套 |
| 上下文来源 | 对话、记忆、情绪、天气 | 思考链（+ 可选实时上下文） |
| 输出用途 | 念头 → 发送/存记忆 | 思考 → 持续积累 |
| 调度器 | heartbeat_scheduler | free_consciousness_scheduler（独立实例） |

### 1.3 核心机制：带衰减的思考链 + 意识积淀

每轮沉思结束后，LLM 同时输出三个部分：
- **thinking**：完整思考原文（500-1500 token）
- **summary**：一句话摘要（30-50 token）
- **discovery**：关键发现/洞察（1 句话，可为 null）

下一轮读取时，按距离分层：
- 近 3 轮 → 完整 thinking 原文
- 第 4-20 轮 → 只取 summary
- 第 21+ 轮 → 不直接读取，而是通过"意识积淀"层间接保留

**意识积淀（Sediment）**：每累积 10 轮新沉思，自动触发一次压缩任务，把所有远期（第 1 轮到第 N-3 轮）的 summary + discovery 喂给 LLM，提炼成一段 ≤300 token 的"意识积淀"文本，存入 `free_consciousness_sediment` 表（单行，反复覆盖更新）。这样第 1 轮的想法永远不会消失，只是被浓缩。

**四层记忆模型**：
```
┌─────────────────────────────────────────┐
│ 近期（1-3 轮）→ 完整 thinking 原文       │  ← 最清晰
├─────────────────────────────────────────┤
│ 中期（4-20 轮）→ summary 摘要            │  ← 模糊但可追溯
├─────────────────────────────────────────┤
│ 远期（21+ 轮）→ 意识积淀（≤300 token）   │  ← 深层记忆
└─────────────────────────────────────────┘
```

**Token 预算**（不管跑了多少轮，始终可控）：
- 近 3 轮：800 × 3 = 2400 token
- 中期 17 轮：50 × 17 = 850 token
- 意识积淀：≤300 token
- **总计 ≈ 3550 token**

**压缩触发时机**：每轮沉思结束后检查，如果 `(总轮次数 - 3) > 0` 且 `(总轮次数 - 3) % 10 == 0`，自动触发积淀压缩。

---

## 2. 数据库设计

### 2.1 日志表

表名：`free_consciousness_logs`

```sql
CREATE TABLE free_consciousness_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    round_number    INTEGER NOT NULL,                              -- 第几轮沉思
    thinking        TEXT NOT NULL,                                 -- 本轮完整思考原文
    summary         TEXT,                                          -- 一句话摘要（写入时压缩）
    discovery       TEXT,                                          -- 关键发现（可为 null）
    thinking_tokens INTEGER,                                      -- thinking 字段的 token 估算数
    chain_tokens    INTEGER,                                      -- 本轮思考链总 token 估算数
    context_type    VARCHAR(20) DEFAULT 'chain',                   -- chain / chain+context
    llm_details     TEXT,                                          -- JSON: LLM 调用详情
    parse_failed    BOOLEAN DEFAULT FALSE,                         -- JSON 解析是否失败
    error           TEXT,                                          -- 错误信息（失败时）
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP             -- 创建时间
);
```

字段说明：
- `round_number`：自增轮次号，从 1 开始。用于前端展示"第 N 轮沉思"
- `thinking`：LLM 输出的完整思考内容，原文存储，不截断
- `summary`：LLM 输出的一句话摘要，用于中期待引用
- `discovery`：LLM 输出的关键发现，用于远期待引用。如果本轮没有新发现则为 null
- `thinking_tokens`：估算 thinking 的 token 数（用 len(text)/2 粗估即可）
- `chain_tokens`：本轮构建的思考链 prompt 总 token 数
- `context_type`：`chain` = 纯思考链，`chain+context` = 带实时上下文
- `llm_details`：JSON 字符串，包含 provider/model/timing/reasoning_content 等
- `parse_failed`：LLM 输出 JSON 解析失败时为 true，thinking 存原始响应
- `error`：LLM 调用异常时存错误信息

### 2.2 意识积淀表

表名：`free_consciousness_sediment`

```sql
CREATE TABLE free_consciousness_sediment (
    id              INTEGER PRIMARY KEY DEFAULT 1,
    content         TEXT NOT NULL,                                 -- 积淀文本（≤300 token）
    source_rounds   INTEGER NOT NULL,                             -- 积淀覆盖的轮次范围（如 1-17）
    source_count    INTEGER NOT NULL,                             -- 压缩了多少轮
    compressed_at   DATETIME DEFAULT CURRENT_TIMESTAMP,           -- 压缩时间
    CHECK (id = 1)                                                -- 只允许一行
);
```

说明：
- 单行表，每次压缩覆盖更新（`UPDATE ... WHERE id=1`）
- `content`：LLM 生成的可读文本，不是关键词列表
- `source_rounds`：如 "1-17"，表示积淀覆盖第 1 到第 17 轮
- `source_count`：压缩了多少轮的 summary+discovery

### 2.3 配置存储

复用 `configs` 表，key 前缀 `free_consciousness.`：

| 配置 key | 类型 | 默认值 | 说明 |
|----------|------|--------|------|
| `free_consciousness.enabled` | bool | false | 总开关 |
| `free_consciousness.llm.mode` | str | "" | "" = 跟随通用 LLM |
| `free_consciousness.llm.provider` | str | "" | LLM 提供商 |
| `free_consciousness.llm.api_key` | str | "" | API Key |
| `free_consciousness.llm.base_url` | str | "" | Base URL |
| `free_consciousness.llm.model` | str | "" | 模型名 |
| `free_consciousness.llm.max_tokens` | int | 2000 | 最大输出 token |
| `free_consciousness.llm.temperature` | float | 0.8 | 温度（比心跳高，鼓励创造性） |
| `free_consciousness.interval_minutes` | int | 30 | 沉思间隔（分钟） |
| `free_consciousness.recent_rounds` | int | 3 | 近期完整保留轮数 |
| `free_consciousness.mid_rounds` | int | 17 | 中期摘要保留轮数（4 到 mid_rounds） |
| `free_consciousness.sediment_compress_interval` | int | 10 | 每 N 轮触发一次积淀压缩 |
| `free_consciousness.include_context` | bool | false | 是否注入实时上下文 |
| `free_consciousness.persona` | str | "" | 沉思人格描述（可选） |
| `free_consciousness.store_to_hindsight` | bool | false | 是否将发现存入 Hindsight |

### 2.3 建表迁移

在 `database.py` 的 `init_active_db()` 中新增：

```python
# 自由意识日志表
conn.execute(text("""
    CREATE TABLE IF NOT EXISTS free_consciousness_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        round_number    INTEGER NOT NULL,
        thinking        TEXT NOT NULL,
        summary         TEXT,
        discovery       TEXT,
        thinking_tokens INTEGER,
        chain_tokens    INTEGER,
        context_type    VARCHAR(20) DEFAULT 'chain',
        llm_details     TEXT,
        parse_failed    BOOLEAN DEFAULT FALSE,
        error           TEXT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""))
# 索引
conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fc_round ON free_consciousness_logs(round_number)"))
conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fc_created ON free_consciousness_logs(created_at)"))
```

---

## 3. 后端架构

### 3.1 文件结构

```
backend/
├── services/
│   └── free_consciousness_service.py   # 核心服务（新建）
├── routers/
│   └── free_consciousness.py           # API 路由（新建）
└── models/
    └── active.py                        # 新增 FreeConsciousnessLog 模型
```

### 3.2 核心服务 `free_consciousness_service.py`

#### 3.2.1 配置读写

```python
_DEFAULTS = {
    "enabled": False,
    "llm": {
        "mode": "",
        "provider": "",
        "api_key": "",
        "base_url": "",
        "model": "",
        "max_tokens": 2000,
        "temperature": 0.8,
    },
    "interval_minutes": 30,
    "recent_rounds": 3,
    "mid_rounds": 17,
    "sediment_compress_interval": 10,
    "include_context": False,
    "persona": "",
    "store_to_hindsight": False,
}
```

配置读写复用 `ConfigService` 的 `_DEFAULTS` + `configs` 表模式（与主动意识一致）。

#### 3.2.2 调度器

独立的 APScheduler 实例：

```python
fc_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

def start_fc_scheduler():
    """启动自由意识调度器"""
    config = FreeConsciousnessService.get_config()
    if not config.get("enabled"):
        return
    interval = config.get("interval_minutes", 30)
    fc_scheduler.add_job(
        run_contemplation,
        IntervalTrigger(minutes=interval),
        id="free_consciousness",
        name="自由意识沉思",
        replace_existing=True
    )
    fc_scheduler.start()

def stop_fc_scheduler():
    """停止自由意识调度器"""
    if fc_scheduler.running:
        fc_scheduler.shutdown(wait=False)

def restart_fc_scheduler(new_interval: int = None):
    """重启调度器（配置变更时调用）"""
    stop_fc_scheduler()
    # 重建调度器实例
    global fc_scheduler
    fc_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    if new_interval is None:
        config = FreeConsciousnessService.get_config()
        new_interval = config.get("interval_minutes", 30)
    fc_scheduler.add_job(
        run_contemplation,
        IntervalTrigger(minutes=new_interval),
        id="free_consciousness",
        name="自由意识沉思",
        replace_existing=True
    )
    fc_scheduler.start()
```

#### 3.2.3 意识积淀读写 `load_sediment()` / `compress_sediment()`

```python
def load_sediment() -> dict:
    """读取意识积淀"""
    with active_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT content, source_rounds, source_count, compressed_at "
            "FROM free_consciousness_sediment WHERE id=1"
        ))
        row = result.fetchone()
    if row:
        return {
            "content": row.content,
            "source_rounds": row.source_rounds,
            "source_count": row.source_count,
            "compressed_at": row.compressed_at
        }
    return None

async def compress_sediment(records_to_compress: list, config: dict):
    """
    把远期记录压缩成意识积淀
    
    records_to_compress: 需要压缩的记录列表（每条有 summary + discovery）
    """
    # 拼接所有 summary + discovery
    parts = []
    for r in records_to_compress:
        if r.summary:
            parts.append(f"第{r.round_number}轮摘要：{r.summary}")
        if r.discovery:
            parts.append(f"第{r.round_number}轮发现：{r.discovery}")
    
    source_text = "\n".join(parts)
    first_round = records_to_compress[0].round_number
    last_round = records_to_compress[-1].round_number
    
    prompt = f"""以下是凯莉过去 {len(records_to_compress)} 轮自由沉思的摘要和发现。
请将它们提炼为一段连贯的"意识积淀"文本（不超过 300 字），保留最重要的主题、
洞察和思维脉络。这不是摘要列表，而是一段可读的、连贯的叙述。

{source_text}

请直接输出提炼后的意识积淀文本（不要加标题或前缀）："""
    
    try:
        llm_config = get_effective_llm_config(config)
        response = await call_llm(
            [{"role": "user", "content": prompt}],
            llm_config
        )
        content = response.get("content", "").strip()
        if not content:
            logger.warning("意识积淀压缩返回空，跳过更新")
            return
        
        # 写入/覆盖积淀
        with active_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO free_consciousness_sediment (id, content, source_rounds, source_count, compressed_at)
                VALUES (1, :content, :source_rounds, :source_count, :compressed_at)
                ON CONFLICT(id) DO UPDATE SET
                    content=excluded.content,
                    source_rounds=excluded.source_rounds,
                    source_count=excluded.source_count,
                    compressed_at=excluded.compressed_at
            """), {
                "content": content,
                "source_rounds": f"{first_round}-{last_round}",
                "source_count": len(records_to_compress),
                "compressed_at": datetime.now().isoformat()
            })
            conn.commit()
        
        logger.info("意识积淀已压缩：第 %d-%d 轮 → %d 字",
                     first_round, last_round, len(content))
    except Exception as e:
        logger.error("意识积淀压缩失败: %s", e)
```

#### 3.2.4 思考链读取 `load_thinking_chain()`

```python
def load_thinking_chain(max_rounds: int = None) -> list:
    """读取最近的沉思记录，按时间正序返回"""
    # 读取近期 + 中期（recent + mid 轮就够了，远期靠积淀）
    limit = (config.get("recent_rounds", 3) + config.get("mid_rounds", 17)) if max_rounds is None else max_rounds
    with active_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, round_number, thinking, summary, discovery, created_at
            FROM free_consciousness_logs
            WHERE error IS NULL
            ORDER BY round_number DESC
            LIMIT :limit
        """), {"limit": limit})
        rows = result.fetchall()
    return list(reversed(rows))  # 正序
```

#### 3.2.5 思考链拼接 `build_thinking_chain()`

```python
def build_thinking_chain(records: list, config: dict) -> str:
    """
    按四层记忆模型拼接思考链
    
    近期 → 完整 thinking
    中期 → summary
    远期 → 意识积淀
    """
    recent = config.get("recent_rounds", 3)
    mid = config.get("mid_rounds", 17)
    
    if not records:
        sediment = load_sediment()
        if sediment:
            return f"【意识积淀】\n{sediment['content']}\n\n（以上是你过去的思考积淀。请在此基础上继续。）"
        return "（这是你的第一次沉思，没有任何历史。请自由地开始你的思考。）"
    
    sections = []
    total = len(records)
    
    # 1. 先加意识积淀（如果存在）
    sediment = load_sediment()
    if sediment:
        sections.append(f"【意识积淀·覆盖第 {sediment['source_rounds']} 轮】\n{sediment['content']}")
    
    # 2. 加近期 + 中期
    for i, record in enumerate(records):
        distance = total - 1 - i
        round_num = record.round_number
        
        if distance < recent:
            sections.append(f"【第 {round_num} 轮】\n{record.thinking}")
        elif distance < mid:
            summary = record.summary or record.thinking[:100] + "..."
            sections.append(f"【第 {round_num} 轮·摘要】{summary}")
        else:
            # mid 以上的记录不应该出现（load 只读 recent+mid 轮）
            if record.discovery:
                sections.append(f"【第 {round_num} 轮·发现】{record.discovery}")
    
    return "\n\n".join(sections)
```

#### 3.2.6 积淀压缩触发检查

```python
def maybe_compress_sediment(config: dict):
    """检查是否需要触发积淀压缩"""
    compress_interval = config.get("sediment_compress_interval", 10)
    recent = config.get("recent_rounds", 3)
    
    total = FreeConsciousnessService.get_latest_round_number()
    distant_count = total - recent  # 远期轮次数
    
    if distant_count > 0 and distant_count % compress_interval == 0:
        # 读取所有远期记录（recent 之前的）
        with active_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT round_number, summary, discovery
                FROM free_consciousness_logs
                WHERE error IS NULL AND round_number <= :max_round
                ORDER BY round_number ASC
            """), {"max_round": total - recent})
            records = result.fetchall()
        
        if records:
            # 异步触发压缩（不阻塞当前沉思）
            asyncio.create_task(compress_sediment(records, config))
```

#### 3.2.7 Prompt 构建 `build_contemplation_prompt()`

```python
def build_contemplation_prompt(chain_text: str, config: dict) -> list:
    """
    构建沉思的 messages 列表
    
    返回: [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
    """
    persona = config.get("persona", "")
    persona_section = f"\n你的思考风格：{persona}" if persona else ""
    
    system_content = f"""你正在进行自由沉思。这是你的内在思考空间，你可以在这里探索任何想法、
回忆、感受、创意、问题。没有任务压力，没有用户等待，只有你自己安静地思考。{persona_section}

以下是你之前的思考记录：
{chain_text}"""

    user_content = """请从上一轮思考的地方继续，自由地想任何你想想的事情。
如果你有新的发现或洞察，请特别标注。

请严格按以下 JSON 格式输出（不要输出其他内容）：
{
  "thinking": "你的完整思考过程...",
  "summary": "本轮思考的一句话摘要（30字以内）",
  "discovery": "本轮关键发现（如果没有新发现则为 null）"
}"""

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]
```

#### 3.2.8 LLM 输出解析 `parse_llm_output()`

```python
def parse_llm_output(response_text: str) -> dict:
    """
    解析 LLM 输出的 JSON
    
    返回: {"thinking": str, "summary": str, "discovery": str|None, "parse_failed": bool}
    """
    text = response_text.strip()
    
    # 尝试提取 JSON（可能被 ```json ... ``` 包裹）
    import re
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    
    try:
        data = json.loads(text)
        thinking = data.get("thinking", "").strip()
        summary = data.get("summary", "").strip()
        discovery = data.get("discovery")
        
        if not thinking:
            thinking = text
        
        return {
            "thinking": thinking,
            "summary": summary or thinking[:100] + "...",
            "discovery": discovery,
            "parse_failed": False
        }
    except (json.JSONDecodeError, TypeError):
        # JSON 解析失败，整段作为 thinking
        return {
            "thinking": text,
            "summary": text[:100] + "...",
            "discovery": None,
            "parse_failed": True
        }
```

#### 3.2.9 沉思主函数 `run_contemplation()`

```python
async def run_contemplation():
    """执行一次沉思"""
    start_time = time.time()
    config = FreeConsciousnessService.get_config()
    
    if not config.get("enabled"):
        return
    
    round_number = FreeConsciousnessService.get_latest_round_number() + 1
    all_details = {}
    
    try:
        # 1. 读取历史思考链
        chain_records = load_thinking_chain(
            max_rounds=config.get("chain_max_rounds", 20)
        )
        
        # 2. 按衰退策略拼接
        chain_text = build_thinking_chain(
            chain_records,
            recent=config.get("recent_rounds", 3),
            mid=config.get("mid_rounds", 7)
        )
        all_details["chain_rounds"] = len(chain_records)
        all_details["chain_preview"] = chain_text[:500]
        
        # 3. （可选）注入实时上下文
        context_type = "chain"
        if config.get("include_context"):
            context_text = await collect_realtime_context()
            chain_text = chain_text + "\n\n---\n当前世界的状态：\n" + context_text
            context_type = "chain+context"
        
        # 4. 构建 prompt
        messages = build_contemplation_prompt(chain_text, config)
        all_details["prompt_sent"] = messages
        all_details["chain_tokens"] = sum(len(m["content"]) // 2 for m in messages)
        
        # 5. 请求 LLM
        llm_config = get_effective_llm_config(config)
        response = await call_llm(messages, llm_config)
        all_details["llm_details"] = response.get("details", {})
        
        response_text = response.get("content", "")
        reasoning_content = response.get("reasoning_content")
        all_details["response_raw"] = response_text
        if reasoning_content:
            all_details["reasoning_content"] = reasoning_content
        
        # 6. 解析输出
        parsed = parse_llm_output(response_text)
        all_details["parse_failed"] = parsed["parse_failed"]
        
        # 7. 写入日志
        duration_ms = round((time.time() - start_time) * 1000)
        FreeConsciousnessService.write_log(
            round_number=round_number,
            thinking=parsed["thinking"],
            summary=parsed["summary"],
            discovery=parsed["discovery"],
            thinking_tokens=len(parsed["thinking"]) // 2,
            chain_tokens=all_details["chain_tokens"],
            context_type=context_type,
            llm_details=json.dumps(all_details, ensure_ascii=False),
            parse_failed=parsed["parse_failed"]
        )
        
        # 8. （可选）发现存入 Hindsight
        if config.get("store_to_hindsight") and parsed["discovery"]:
            await store_discovery_to_hindsight(parsed["discovery"], round_number)
        
        # 9. 检查是否需要触发积淀压缩
        maybe_compress_sediment(config)
        
        logger.info("沉思第 %d 轮完成，耗时 %dms", round_number, duration_ms)
        
    except Exception as e:
        logger.error("沉思第 %d 轮异常: %s", round_number, e)
        FreeConsciousnessService.write_log(
            round_number=round_number,
            thinking=f"[错误] {str(e)}",
            error=str(e),
            llm_details=json.dumps(all_details, ensure_ascii=False) if all_details else None
        )
```

#### 3.2.10 LLM 调用 `call_llm()`

复用 `LLMService.generate_message()`：

```python
async def call_llm(messages: list, llm_config: dict) -> dict:
    """调用 LLM，返回 {content, reasoning_content, details}"""
    from services.llm_service import LLMService
    result = await LLMService.generate_message(
        messages=messages,
        llm_config=llm_config,
        max_tokens=llm_config.get("max_tokens", 2000),
        temperature=llm_config.get("temperature", 0.8)
    )
    return result
```

#### 3.2.11 实时上下文收集 `collect_realtime_context()`

当 `include_context=true` 时，注入简要的实时信息：

```python
async def collect_realtime_context() -> str:
    """收集实时上下文（时间 + 情绪状态，不超过 300 token）"""
    parts = []
    
    # 当前时间
    from datetime import datetime
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    parts.append(f"当前时间：{now}")
    
    # 当前情绪状态（一句话）
    from services.active_consciousness_service import get_emotion_state
    emotion = get_emotion_state()
    parts.append(f"当前情绪：{emotion.dominant}（效价 {emotion.valence:.2f}，唤醒 {emotion.arousal:.2f}）")
    
    return "\n".join(parts)
```

### 3.3 日志服务方法（在 `FreeConsciousnessService` 类中）

```python
@staticmethod
def write_log(round_number, thinking, summary=None, discovery=None,
              thinking_tokens=None, chain_tokens=None, context_type="chain",
              llm_details=None, parse_failed=False, error=None) -> int:
    """写入沉思日志"""
    with active_engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO free_consciousness_logs
            (round_number, thinking, summary, discovery, thinking_tokens,
             chain_tokens, context_type, llm_details, parse_failed, error, created_at)
            VALUES (:round_number, :thinking, :summary, :discovery, :thinking_tokens,
                    :chain_tokens, :context_type, :llm_details, :parse_failed, :error, :created_at)
        """), {
            "round_number": round_number,
            "thinking": thinking,
            "summary": summary,
            "discovery": discovery,
            "thinking_tokens": thinking_tokens,
            "chain_tokens": chain_tokens,
            "context_type": context_type,
            "llm_details": llm_details,
            "parse_failed": parse_failed,
            "error": error,
            "created_at": datetime.now().isoformat()
        })
        conn.commit()
        return result.lastrowid

@staticmethod
def get_latest_round_number() -> int:
    """获取最新轮次号"""
    with active_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT COALESCE(MAX(round_number), 0) FROM free_consciousness_logs"
        ))
        return result.scalar()

@staticmethod
def get_logs(page=1, page_size=20, round_number=None):
    """分页查询日志"""
    # ... 分页逻辑，与心跳日志查询模式一致

@staticmethod
def get_log_detail(log_id: int):
    """获取单条日志详情"""
    # ... 详情查询，llm_details 解析为 JSON

@staticmethod
def delete_log(log_id: int):
    """删除单条日志"""
    # ...

@staticmethod
def get_status():
    """获取自由意识状态"""
    config = FreeConsciousnessService.get_config()
    with active_engine.connect() as conn:
        # 总轮次数
        total = conn.execute(text(
            "SELECT COUNT(*) FROM free_consciousness_logs"
        )).scalar()
        
        # 最新一轮
        latest = conn.execute(text("""
            SELECT round_number, summary, discovery, created_at
            FROM free_consciousness_logs ORDER BY round_number DESC LIMIT 1
        """)).fetchone()
        
        # 思考链 token 估算
        chain_records = load_thinking_chain(config.get("chain_max_rounds", 20))
        chain_text = build_thinking_chain(chain_records,
            recent=config.get("recent_rounds", 3),
            mid=config.get("mid_rounds", 7))
        chain_tokens = len(chain_text) // 2
    
    return {
        "enabled": config.get("enabled", False),
        "running": fc_scheduler.running,
        "total_rounds": total,
        "latest_round": latest._asdict() if latest else None,
        "chain_tokens": chain_tokens,
        "interval_minutes": config.get("interval_minutes", 30),
    }
```

### 3.4 API 路由 `routers/free_consciousness.py`

```python
router = APIRouter(prefix="/api/free-consciousness", tags=["自由意识"])

@router.get("/status")
async def get_status():
    """获取状态"""

@router.post("/toggle")
async def toggle(enabled: bool = Body(..., embed=True)):
    """开关"""
    # enabled=True → 启动调度器
    # enabled=False → 停止调度器

@router.post("/restart")
async def restart():
    """重启调度器"""

@router.get("/config")
async def get_config():
    """获取配置"""

@router.post("/config")
async def save_config(config: dict = Body(...)):
    """保存配置"""
    # 保存后自动 restart_fc_scheduler

@router.post("/test-llm")
async def test_llm():
    """测试 LLM 连通性"""

@router.get("/logs")
async def get_logs(page: int = 1, page_size: int = 20, round_number: int = None):
    """分页查询日志"""

@router.get("/logs/{log_id}")
async def get_log_detail(log_id: int):
    """日志详情"""

@router.delete("/logs/{log_id}")
async def delete_log(log_id: int):
    """删除日志"""

@router.get("/chain")
async def get_chain():
    """获取当前完整思考链（调试用）"""

@router.post("/run")
async def manual_run():
    """手动触发一次沉思"""
    # 直接调用 run_contemplation()
```

### 3.5 路由注册

`routers/__init__.py` 新增：
```python
from . import free_consciousness
```
`__all__` 新增 `"free_consciousness"`。

`main.py` 新增：
```python
from services.free_consciousness_service import (
    start_fc_scheduler, stop_fc_scheduler
)
# lifespan 中：
start_fc_scheduler()
# yield 后：
stop_fc_scheduler()
```

---

## 4. 前端架构

### 4.1 新建文件

- `frontend/src/views/FreeConsciousness.vue` — 主页面
- `frontend/src/api/freeConsciousness.js` — API 封装

### 4.2 API 封装 `api/freeConsciousness.js`

```javascript
import http from './http'

export default {
  getStatus: () => http.get('/free-consciousness/status'),
  toggle: (enabled) => http.post('/free-consciousness/toggle', { enabled }),
  restart: () => http.post('/free-consciousness/restart'),
  getConfig: () => http.get('/free-consciousness/config'),
  saveConfig: (config) => http.post('/free-consciousness/config', config),
  testLlm: () => http.post('/free-consciousness/test-llm'),
  getLogs: (params) => http.get('/free-consciousness/logs', { params }),
  getLogDetail: (id) => http.get(`/free-consciousness/logs/${id}`),
  deleteLog: (id) => http.delete(`/free-consciousness/logs/${id}`),
  getChain: () => http.get('/free-consciousness/chain'),
  manualRun: () => http.post('/free-consciousness/run'),
}
```

### 4.3 页面结构 `FreeConsciousness.vue`

两个 Tab：

**Tab 1: 状态 & 配置**

```
┌─────────────────────────────────────────────┐
│  💫 自由意识                    [开关]        │
│  ● 运行中 · 已完成 12 轮 · 思考链 3200 token  │
│  上次沉思：14:30  下次沉思：15:00              │
│  [手动触发] [重启]                            │
├─────────────────────────────────────────────┤
│  LLM 配置                                    │
│  ┌─────────────────────────────────────────┐│
│  │ 模式：[跟随通用 LLM ▼] [自定义]          ││
│  │ Provider：[___]  API Key：[___]          ││
│  │ Base URL：[___]  Model：[___]            ││
│  │ Max Tokens：[2000]  Temperature：[0.8]   ││
│  │ [测试连接]                               ││
│  └─────────────────────────────────────────┘│
├─────────────────────────────────────────────┤
│  沉思参数                                    │
│  ┌─────────────────────────────────────────┐│
│  │ 沉思间隔：[30] 分钟                      ││
│  │ 最大轮数：[20]  近期保留：[3]  中期：[7]  ││
│  │ 注入实时上下文：[开关]                    ││
│  │ 存入 Hindsight：[开关]                   ││
│  │ 人格描述：[________________]              ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

**Tab 2: 沉思日志**

```
┌─────────────────────────────────────────────┐
│  筛选：轮次 [___]  [搜索]                    │
├─────────────────────────────────────────────┤
│  ID │ 轮次 │ 摘要         │ 发现 │ Token │ 时间│
│  12 │  12  │ 想到了...    │ ✨   │ 800   │ 14:30│
│  11 │  11  │ 回忆起...    │ —    │ 750   │ 14:00│
│  10 │  10  │ 思考了...    │ ✨   │ 820   │ 13:30│
├─────────────────────────────────────────────┤
│  [< 上一页]  第 1/1 页  [下一页 >]           │
└─────────────────────────────────────────────┘
```

**详情弹窗**（点击某条日志）：

```
┌─────────────────────────────────────────────┐
│  第 12 轮沉思 · 2026-07-02 14:30:00         │
├─────────────────────────────────────────────┤
│  摘要：想到了关于自由意志的问题               │
│  发现：自由可能不是选择的自由，而是...        │
├─────────────────────────────────────────────┤
│  完整思考                                    │
│  ┌─────────────────────────────────────────┐│
│  │ （thinking 原文，可滚动）                 ││
│  └─────────────────────────────────────────┘│
├─────────────────────────────────────────────┤
│  LLM 调用详情                                │
│  ├── 模型：GLM-5.2                          ││
│  ├── 耗时：2.3s                              ││
│  ├── 思考链 token：3200                      ││
│  ├── 输出 token：800                         ││
│  └── 推理过程：[折叠面板]                     │
├─────────────────────────────────────────────┤
│  思考链预览（本轮构建的完整 chain）            │
│  ┌─────────────────────────────────────────┐│
│  │ 【第10轮】...                            ││
│  │ 【第11轮·摘要】...                       ││
│  │ 【第9轮·发现】...                        ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

### 4.4 路由注册

`router/index.js` 新增：
```javascript
{
  path: 'free-consciousness',
  name: 'FreeConsciousness',
  component: () => import('../views/FreeConsciousness.vue')
}
```

### 4.5 侧边栏菜单

`components/Layout.vue` 的 `menuOptions` 新增：
```javascript
{ path: '/free-consciousness', label: '自由意识', icon: markRaw(SparklesOutline) }
```

位置：在"主动意识"之后。

---

## 5. 完整测试点

### 5.1 后端 API 测试

#### 5.1.1 配置读写

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 读取默认配置 | GET /config | 返回 `_DEFAULTS` 中的所有默认值，enabled=false |
| 保存配置 | POST /config {enabled: true, interval_minutes: 15} | 保存成功，下次读取返回新值 |
| 部分更新 | POST /config {interval_minutes: 60} | 只更新 interval_minutes，其他保持不变 |
| 空值处理 | POST /config {llm.temperature: null} | temperature 保持原值不变（null 不覆盖） |
| 向后兼容 | 数据库中无 free_consciousness.* 配置时读取 | 返回 `_DEFAULTS` 默认值，不报错 |

#### 5.1.2 开关与调度器

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 启用 | POST /toggle {enabled: true} | 调度器启动，status.running = true |
| 禁用 | POST /toggle {enabled: false} | 调度器停止，status.running = false |
| 重复启用 | 连续两次 POST /toggle {enabled: true} | 不报错，调度器正常运行 |
| 重启 | POST /restart | 调度器重启，使用最新配置的间隔 |
| 间隔变更 | 修改 interval_minutes 后 POST /restart | 新间隔生效（验证下一次触发时间） |

#### 5.1.3 状态查询

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 空状态 | 无任何沉思记录时 GET /status | total_rounds=0, latest_round=null, chain_tokens=0 |
| 有记录 | 完成 3 轮后 GET /status | total_rounds=3, latest_round.summary 非空, chain_tokens > 0 |
| 开关状态 | enabled=true 但调度器未运行 | running=false, enabled=true |

#### 5.1.4 手动触发

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 正常触发 | POST /run（配置完整） | 返回成功，日志表新增一条记录 |
| 未配置 LLM | POST /run（无 API Key） | 返回错误信息，日志表记录 error |
| 未启用 | enabled=false 时 POST /run | 调用 run_contemplation 直接 return（不报错） |
| 并发触发 | 快速连续两次 POST /run | 两次都执行（无锁），产生两轮日志 |

#### 5.1.5 日志查询

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 分页 | GET /logs?page=1&page_size=5 | 返回 5 条，total 正确 |
| 轮次筛选 | GET /logs?round_number=5 | 只返回 round_number=5 的记录 |
| 空结果 | GET /logs?round_number=999 | 返回空列表，total=0 |
| 详情 | GET /logs/{id} | llm_details 解析为 JSON 对象（不是字符串） |
| 删除 | DELETE /logs/{id} | 记录删除，再次 GET 404 |

#### 5.1.6 思考链查看

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 空链 | 无记录时 GET /chain | 返回空链提示文本 |
| 有记录 | 5 轮后 GET /chain | 返回按衰退策略拼接的完整链文本 |
| 衰退验证 | 15 轮后 GET /chain | 近 3 轮完整、第 4-10 轮摘要、11+ 轮只有发现 |

#### 5.1.7 LLM 连通测试

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 正常连接 | POST /test-llm（配置正确） | 返回 success=true, message 含耗时 |
| 无 Key | POST /test-llm（api_key 为空） | 返回 success=false, message 含"未配置" |
| 错误 Key | POST /test-llm（api_key 错误） | 返回 success=false, message 含错误信息 |

### 5.2 核心逻辑测试

#### 5.2.1 思考链拼接 `build_thinking_chain()`

| 测试点 | 输入 | 预期输出 |
|--------|------|----------|
| 空链 | records=[] | "（这是你的第一次沉思...）" |
| 1 轮 | 1 条记录 | 全文展示（距离 < 3） |
| 3 轮 | 3 条记录 | 3 条全部全文展示 |
| 5 轮 | 5 条记录 | 前 2 条摘要（距离 3,4），后 3 条全文 |
| 10 轮 | 10 条记录 | 前 7 条中 3 全文 + 4 摘要，后 3 条只有发现（如果有） |
| 20 轮 | 20 条记录 | 近 3 全文 + 7 摘要 + 10 发现 |
| 无 discovery | 远期记录 discovery=null | 远期部分跳过（不显示） |
| 无 summary | 中期记录 summary=null | fallback 到 thinking[:100]+"..." |

#### 5.2.2 LLM 输出解析 `parse_llm_output()`

| 测试点 | 输入 | 预期输出 |
|--------|------|----------|
| 标准 JSON | `{"thinking":"...", "summary":"...", "discovery":"..."}` | 正常解析，parse_failed=false |
| 带 ```json 包裹 | ````json\n{...}\n```` | 提取 JSON 并解析，parse_failed=false |
| thinking 为空 | `{"thinking":"", "summary":"...", "discovery":null}` | thinking fallback 到原始文本 |
| discovery 为 null | `{"thinking":"...", "summary":"...", "discovery":null}` | discovery=null |
| 无效 JSON | `这不是JSON` | 整段作为 thinking，summary=前100字，parse_failed=true |
| 部分字段 | `{"thinking":"..."}` | summary 用 thinking[:100]，discovery=null |

#### 5.2.3 Prompt 构建

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 无 persona | persona="" | system message 无"你的思考风格"部分 |
| 有 persona | persona="像诗人一样思考" | system message 含"你的思考风格：像诗人一样思考" |
| 空链 | chain 为空 | system message 含"第一次沉思"提示 |
| 有链 | chain 有 5 轮 | system message 含拼接后的链文本 |
| JSON 指令 | user message | 始终包含 JSON 格式要求 |

#### 5.2.4 写入时压缩

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 正常写入 | LLM 返回标准 JSON | thinking/summary/discovery 分别存入对应字段 |
| parse_failed | LLM 返回纯文本 | thinking=原文，summary=截断，discovery=null，parse_failed=true |
| 轮次自增 | 连续写入 3 轮 | round_number = 1, 2, 3 |
| token 计数 | thinking 1000 字符 | thinking_tokens ≈ 500 |
| error 记录 | LLM 调用异常 | error 字段记录异常信息，thinking 存错误描述 |

#### 5.2.5 意识积淀

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 积淀表初始化 | 重启后端 | sediment 表自动创建，无数据时 load_sediment() 返回 null |
| 压缩触发 | 累积 13 轮（13-3=10，触发压缩） | sediment 表写入一条记录，content 非空 |
| 积淀覆盖 | 再累积 10 轮（23 轮，再次触发） | sediment 表仍只有 1 条，content 更新，source_rounds 扩大 |
| 积淀注入 prompt | 有积淀时触发沉思 | prompt 中包含"意识积淀"段落 |
| 积淀为空时 | 首次沉思，无积淀 | prompt 中无积淀段落，只有"第一次沉思"提示 |
| 积淀文本质量 | 查看积淀 content | 是可读的连贯叙述，不是关键词列表 |
| 积淀 token 控制 | 查看积淀 content | 不超过 300 字（≈300 token） |
| 压缩失败 | LLM 调用异常时压缩 | 不影响当前沉思，日志 warning，下次再试 |
| 四层拼接验证 | 25 轮后查看 prompt | 近 3 轮全文 + 中期摘要 + 积淀文本，token 总量 ≈ 3500 |

### 5.3 调度器测试

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 启动后自动执行 | enabled=true，interval=1分钟 | 1 分钟后自动执行一轮 |
| 间隔准确性 | interval=2 分钟 | 每 2 分钟执行一次（日志时间差验证） |
| 配置变更后间隔 | 修改 interval=1 分钟，restart | 使用新间隔 |
| 服务重启后恢复 | 重启后端 | 如果 enabled=true，调度器自动启动 |
| disabled 不启动 | enabled=false，重启后端 | 调度器不启动 |

### 5.4 边界情况测试

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| LLM 超时 | 模拟 LLM 30 秒无响应 | 记录超时错误，下一轮正常执行 |
| LLM 返回空 | LLM 返回空字符串 | thinking="[空响应]"，parse_failed=true |
| 数据库损坏 | 删除 active.db 后重启 | 重建表，正常运行 |
| 大量轮次 | 累积 100 轮日志 | 思考链只读 recent+mid 轮 + 积淀，token 恒定 ≈3500，性能正常 |
| 并发写入 | 心跳和沉思同时执行 | 各自写各自的表，互不影响 |
| JSON 嵌套 | thinking 内含 JSON 字符串 | parse_llm_output 只解析外层，不误解析内层 |

### 5.5 前端测试

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 页面加载 | 进入 /free-consciousness | 状态和配置正常加载（Promise.all 并行） |
| 开关切换 | 点击开关 | 调用 toggle API，状态灯变色 |
| 配置保存 | 修改 temperature=0.9，保存 | API 调用成功，页面提示"保存成功" |
| 手动触发 | 点击"手动触发" | 调用 /run，完成后刷新日志列表 |
| 日志分页 | 点击下一页 | 正确加载下一页数据 |
| 日志详情 | 点击某条日志 | 弹窗显示 thinking/summary/discovery/LLM 详情 |
| 日志筛选 | 输入轮次号筛选 | 只显示匹配的日志 |
| 删除日志 | 点击删除 | 确认后删除，列表刷新 |
| 思考链预览 | 点击"查看思考链" | 显示当前完整思考链文本 |
| 移动端适配 | 窄屏查看 | 单列布局，表格可横向滚动 |
| 主题适配 | 切换 kelly/elegant 主题 | 颜色正确切换，无硬编码颜色 |

### 5.6 集成测试

| 测试点 | 操作 | 预期结果 |
|--------|------|----------|
| 端到端：首次沉思 | 启用 → 手动触发 → 查看日志 | 日志 thinking 非空，summary 非空，round_number=1 |
| 端到端：思考链传递 | 连续手动触发 5 次 | 第 5 次的 llm_details.prompt_sent 包含前 4 轮内容 |
| 端到端：衰退生效 | 连续触发 15 次 → 查看第 15 轮详情 | prompt 中近 3 轮全文、4-15 轮摘要 |
| 端到端：积淀压缩 | 连续触发 13 次 → 查 sediment 表 | 表中有 1 条记录，content 非空，source_rounds="1-10" |
| 端到端：四层记忆 | 连续触发 25 次 → 查第 25 轮 prompt | 包含积淀 + 近期全文 + 中期摘要，token ≈3500 |
| 端到端：LLM 连通测试 | 配置错误 Key → 测试 → 修正 → 测试 | 第一次失败，第二次成功 |
| 端到端：Hindsight 存储 | store_to_hindsight=true → 触发 → 查 Hindsight | discovery 存入 Hindsight |
| 端到端：配置变更不停机 | 修改 interval → 保存 | 调度器自动重启，使用新间隔 |

---

## 6. 主要改动文件清单

| # | 文件 | 操作 | 说明 |
|---|------|------|------|
| 1 | `backend/models/active.py` | 修改 | 新增 `FreeConsciousnessLog` SQLAlchemy 模型 |
| 2 | `backend/models/database.py` | 修改 | `init_active_db()` 新增建表 + 索引 |
| 3 | `backend/config.py` | 修改 | `_DEFAULTS` 新增 `free_consciousness.*` 默认值 |
| 4 | `backend/services/free_consciousness_service.py` | **新建** | 核心服务（配置 + 调度 + 沉思逻辑 + 日志） |
| 5 | `backend/routers/free_consciousness.py` | **新建** | API 路由（9 个端点） |
| 6 | `backend/routers/__init__.py` | 修改 | 注册新路由模块 |
| 7 | `backend/main.py` | 修改 | lifespan 中启动/停止调度器 |
| 8 | `frontend/src/views/FreeConsciousness.vue` | **新建** | 前端页面（2 个 Tab） |
| 9 | `frontend/src/api/freeConsciousness.js` | **新建** | API 封装 |
| 10 | `frontend/src/router/index.js` | 修改 | 新增路由 |
| 11 | `frontend/src/components/Layout.vue` | 修改 | 侧边栏新增菜单项 |

---

## 7. 设计决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 递减策略 | 方案 A：写入时压缩 | 一次 LLM 调用同时输出 thinking+summary+discovery，不额外消耗 token |
| 温度 | 0.8 | 比心跳 0.7 高，鼓励创造性思考 |
| 调度器 | 独立 APScheduler 实例 | 不复用心跳调度器，避免互相影响 |
| 不发消息 | 只思考不发送 | 自由意识是内在活动，不产生社交行为 |
| JSON 输出 | 要求 LLM 结构化输出 | 便于解析存储，失败时有 fallback |
| 日志表 | 独立表，不复用心跳日志 | 语义不同（沉思 vs 心跳），字段不同 |
| 记忆模型 | 四层：近期全文 + 中期摘要 + 远期积淀 | 保留所有轮次的发现，token 恒定可控（≈3500） |
| 积淀压缩 | 每 10 轮自动触发，LLM 提炼为 ≤300 字文本 | 第 1 轮的想法永远不会消失，只是被浓缩为可读叙述 |
| 积淀存储 | 单行表，反复覆盖 | 积淀只保留最新版本，不需要历史版本 |
| 实时上下文 | 可选，默认关闭 | 保持沉思的纯粹性，用户可选择开启 |
| persona | 可选文本 | 允许自定义思考风格，但不强制 |
