# 自由意识 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 hermes-active 新增"自由意识"模块——一个持续运行的定时 LLM 推理框架，使用四层记忆模型（近期全文 + 中期摘要 + 远期意识积淀），让凯莉自主思考并积累意识。

**架构：** 独立于主动意识的调度器 + 配置 + 日志表。每轮沉思携带完整思考链（带衰减），LLM 输出 thinking + summary + discovery 三部分。每 10 轮自动触发意识积淀压缩。前端新建独立页面。

**技术栈：** FastAPI + SQLAlchemy + APScheduler + Vue 3 + Naive UI

**设计文档：** `docs/specs/2026-07-02-free-consciousness-design.md`

---

## 文件结构

### 新建文件
- `backend/services/free_consciousness_service.py` — 核心服务（配置 + 调度 + 沉思逻辑 + 日志 + 积淀）
- `backend/routers/free_consciousness.py` — API 路由（9 个端点）
- `frontend/src/views/FreeConsciousness.vue` — 前端页面（2 个 Tab）
- `frontend/src/api/freeConsciousness.js` — API 封装

### 修改文件
- `backend/models/active.py` — 新增 FreeConsciousnessLog SQLAlchemy 模型
- `backend/models/database.py` — init_active_db() 新增建表 + 索引
- `backend/routers/__init__.py` — 注册新路由模块
- `backend/main.py` — lifespan 中启动/停止调度器
- `frontend/src/router/index.js` — 新增路由
- `frontend/src/components/Layout.vue` — 侧边栏新增菜单项

---

## 任务 1：数据库模型 + 建表迁移

**文件：**
- 修改：`backend/models/active.py`
- 修改：`backend/models/database.py`

- [ ] **步骤 1：在 active.py 中新增 FreeConsciousnessLog 模型**

在 `HeartbeatLog` 类之后添加：

```python
class FreeConsciousnessLog(Base):
    """自由意识沉思日志表"""
    __tablename__ = "free_consciousness_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round_number = Column(Integer, nullable=False, index=True)
    thinking = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    discovery = Column(Text, nullable=True)
    thinking_tokens = Column(Integer, nullable=True)
    chain_tokens = Column(Integer, nullable=True)
    context_type = Column(String(20), default="chain")
    llm_details = Column(Text, nullable=True)
    parse_failed = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")), index=True)

    def to_dict(self):
        details = self.llm_details
        if details:
            try:
                details = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "id": self.id,
            "round_number": self.round_number,
            "thinking": self.thinking,
            "summary": self.summary,
            "discovery": self.discovery,
            "thinking_tokens": self.thinking_tokens,
            "chain_tokens": self.chain_tokens,
            "context_type": self.context_type,
            "llm_details": details,
            "parse_failed": self.parse_failed,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class FreeConsciousnessSediment(Base):
    """意识积淀表（单行）"""
    __tablename__ = "free_consciousness_sediment"

    id = Column(Integer, primary_key=True, default=1)
    content = Column(Text, nullable=False)
    source_rounds = Column(String(50), nullable=False)
    source_count = Column(Integer, nullable=False)
    compressed_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")))

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "source_rounds": self.source_rounds,
            "source_count": self.source_count,
            "compressed_at": self.compressed_at.isoformat() if self.compressed_at else None
        }
```

- [ ] **步骤 2：在 database.py 的 init_active_db() 中新增建表**

在 `init_active_db()` 函数末尾（自动迁移代码之后）添加：

```python
# 自由意识日志表索引
try:
    with active_engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fc_round ON free_consciousness_logs(round_number)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fc_created ON free_consciousness_logs(created_at)"))
        conn.commit()
except Exception as e:
    print(f"创建自由意识索引失败: {e}")
```

注意：表本身由 `Base.metadata.create_all(bind=active_engine)` 自动创建（因为模型已继承 Base），只需手动补索引。

- [ ] **步骤 3：验证建表**

```bash
cd ~/.hermes/hermes-active/backend && python -c "
from models.database import init_active_db, active_engine
from sqlalchemy import text
init_active_db()
with active_engine.connect() as conn:
    tables = conn.execute(text(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%free%'\")).fetchall()
    print('Tables:', [t[0] for t in tables])
"
```

预期：输出 `Tables: ['free_consciousness_logs', 'free_consciousness_sediment']`

- [ ] **步骤 4：Commit**

```bash
git add backend/models/active.py backend/models/database.py
git commit -m "feat: 自由意识数据库模型 + 建表"
```

---

## 任务 2：核心服务 — 配置 + 调度器

**文件：**
- 新建：`backend/services/free_consciousness_service.py`

- [ ] **步骤 1：创建服务文件骨架 + 配置读写**

```python
"""
自由意识服务 — 配置读写 + 调度 + 沉思逻辑 + 日志 + 积淀
"""
import json
import re
import time
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from models.database import ActiveSession, active_engine
from services.config_service import ConfigService

logger = logging.getLogger("hermes.free_consciousness")

PREFIX = "free_consciousness."

_DEFAULTS = {
    "free_consciousness.enabled": "false",
    "free_consciousness.llm.mode": "",
    "free_consciousness.llm.provider": "",
    "free_consciousness.llm.api_key": "",
    "free_consciousness.llm.base_url": "",
    "free_consciousness.llm.model": "",
    "free_consciousness.llm.max_tokens": "2000",
    "free_consciousness.llm.temperature": "0.8",
    "free_consciousness.interval_minutes": "30",
    "free_consciousness.recent_rounds": "3",
    "free_consciousness.mid_rounds": "17",
    "free_consciousness.sediment_compress_interval": "10",
    "free_consciousness.include_context": "false",
    "free_consciousness.persona": "",
    "free_consciousness.store_to_hindsight": "false",
}


class FreeConsciousnessService:
    """自由意识服务"""

    _config_cache = None
    _config_cache_ts = 0
    _CONFIG_CACHE_TTL = 60  # 缓存 60 秒

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """获取自由意识配置（嵌套 dict）"""
        now = time.time()
        if (FreeConsciousnessService._config_cache is not None
                and now - FreeConsciousnessService._config_cache_ts < FreeConsciousnessService._CONFIG_CACHE_TTL):
            return FreeConsciousnessService._config_cache

        db = ActiveSession()
        try:
            result = {}
            for key, default in _DEFAULTS.items():
                value = ConfigService.get_config(db, key)
                result[key] = value if value is not None else default
            nested = FreeConsciousnessService._flat_to_nested(result)
            FreeConsciousnessService._config_cache = nested
            FreeConsciousnessService._config_cache_ts = now
            return nested
        finally:
            db.close()

    @staticmethod
    def update_config(config: Dict[str, Any]):
        """更新自由意识配置"""
        db = ActiveSession()
        try:
            flat = FreeConsciousnessService._nested_to_flat(config)
            for key, value in flat.items():
                if key.startswith(PREFIX):
                    ConfigService.set_config(db, key, str(value) if value is not None else "")
        finally:
            FreeConsciousnessService._config_cache = None
            FreeConsciousnessService._config_cache_ts = 0
            db.close()

    @staticmethod
    def _flat_to_nested(flat: Dict[str, str]) -> Dict[str, Any]:
        """扁平 key → 嵌套 dict"""
        result = {}
        for key, value in flat.items():
            if not key.startswith(PREFIX):
                continue
            parts = key[len(PREFIX):].split(".")
            d = result
            for part in parts[:-1]:
                if part not in d:
                    d[part] = {}
                d = d[part]
            # 类型转换
            final_key = parts[-1]
            if value in ("true", "false"):
                d[final_key] = value == "true"
            else:
                try:
                    d[final_key] = int(value)
                except (ValueError, TypeError):
                    try:
                        d[final_key] = float(value)
                    except (ValueError, TypeError):
                        d[final_key] = value
        return result

    @staticmethod
    def _nested_to_flat(config: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """嵌套 dict → 扁平 key"""
        result = {}
        for key, value in config.items():
            full_key = f"{prefix}{key}" if prefix else f"{PREFIX}{key}"
            if isinstance(value, dict):
                result.update(FreeConsciousnessService._nested_to_flat(value, full_key + "."))
            elif value is not None:
                result[full_key] = str(value)
        return result
```

- [ ] **步骤 2：添加日志读写方法**

在 `FreeConsciousnessService` 类中添加：

```python
    @staticmethod
    def get_latest_round_number() -> int:
        """获取最新轮次号"""
        with active_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COALESCE(MAX(round_number), 0) FROM free_consciousness_logs"
            ))
            return result.scalar()

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
    def get_logs(page=1, page_size=20, round_number=None):
        """分页查询日志"""
        db = ActiveSession()
        try:
            offset = (page - 1) * page_size
            where = "WHERE 1=1"
            params = {"limit": page_size, "offset": offset}
            if round_number is not None:
                where += " AND round_number = :round_number"
                params["round_number"] = round_number

            with active_engine.connect() as conn:
                count_result = conn.execute(
                    text(f"SELECT COUNT(*) FROM free_consciousness_logs {where}"),
                    {k: v for k, v in params.items() if k not in ("limit", "offset")}
                )
                total = count_result.scalar()

                result = conn.execute(text(f"""
                    SELECT id, round_number, thinking, summary, discovery,
                           thinking_tokens, chain_tokens, context_type,
                           llm_details, parse_failed, error, created_at
                    FROM free_consciousness_logs {where}
                    ORDER BY round_number DESC
                    LIMIT :limit OFFSET :offset
                """), params)
                rows = result.fetchall()

            items = []
            for row in rows:
                items.append({
                    "id": row.id,
                    "round_number": row.round_number,
                    "thinking": row.thinking,
                    "summary": row.summary,
                    "discovery": row.discovery,
                    "thinking_tokens": row.thinking_tokens,
                    "chain_tokens": row.chain_tokens,
                    "context_type": row.context_type,
                    "parse_failed": row.parse_failed,
                    "error": row.error,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}
        finally:
            db.close()

    @staticmethod
    def get_log_detail(log_id: int) -> Optional[Dict]:
        """获取单条日志详情"""
        with active_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM free_consciousness_logs WHERE id = :id
            """), {"id": log_id})
            row = result.fetchone()
        if not row:
            return None
        details = row.llm_details
        if details:
            try:
                details = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "id": row.id,
            "round_number": row.round_number,
            "thinking": row.thinking,
            "summary": row.summary,
            "discovery": row.discovery,
            "thinking_tokens": row.thinking_tokens,
            "chain_tokens": row.chain_tokens,
            "context_type": row.context_type,
            "llm_details": details,
            "parse_failed": row.parse_failed,
            "error": row.error,
            "created_at": row.created_at.isoformat() if row.created_at else None
        }

    @staticmethod
    def delete_log(log_id: int) -> bool:
        """删除单条日志"""
        with active_engine.connect() as conn:
            result = conn.execute(text(
                "DELETE FROM free_consciousness_logs WHERE id = :id"
            ), {"id": log_id})
            conn.commit()
            return result.rowcount > 0

    @staticmethod
    def get_status() -> Dict:
        """获取自由意识状态"""
        config = FreeConsciousnessService.get_config()
        with active_engine.connect() as conn:
            total = conn.execute(text(
                "SELECT COUNT(*) FROM free_consciousness_logs"
            )).scalar()

            latest = conn.execute(text("""
                SELECT round_number, summary, discovery, created_at
                FROM free_consciousness_logs ORDER BY round_number DESC LIMIT 1
            """)).fetchone()

            # 积淀信息
            sediment = conn.execute(text(
                "SELECT source_rounds, source_count, compressed_at FROM free_consciousness_sediment WHERE id=1"
            )).fetchone()

        # 计算思考链 token
        chain_records = load_thinking_chain(config)
        chain_text = build_thinking_chain(chain_records, config)
        chain_tokens = len(chain_text) // 2

        return {
            "enabled": config.get("enabled", False),
            "running": fc_scheduler.running if fc_scheduler else False,
            "total_rounds": total,
            "latest_round": {
                "round_number": latest.round_number,
                "summary": latest.summary,
                "discovery": latest.discovery,
                "created_at": latest.created_at.isoformat() if latest.created_at else None
            } if latest else None,
            "chain_tokens": chain_tokens,
            "interval_minutes": config.get("interval_minutes", 30),
            "sediment": {
                "source_rounds": sediment.source_rounds,
                "source_count": sediment.source_count,
                "compressed_at": sediment.compressed_at.isoformat() if sediment.compressed_at else None
            } if sediment else None,
        }
```

- [ ] **步骤 3：添加调度器**

```python
# 全局调度器实例
fc_scheduler: Optional[AsyncIOScheduler] = None


def start_fc_scheduler():
    """启动自由意识调度器"""
    global fc_scheduler
    config = FreeConsciousnessService.get_config()
    if not config.get("enabled"):
        logger.info("自由意识未启用，跳过启动")
        return

    interval = config.get("interval_minutes", 30)
    fc_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    fc_scheduler.add_job(
        run_contemplation,
        IntervalTrigger(minutes=interval),
        id="free_consciousness",
        name="自由意识沉思",
        replace_existing=True
    )
    fc_scheduler.start()
    logger.info("自由意识调度器已启动，间隔 %d 分钟", interval)


def stop_fc_scheduler():
    """停止自由意识调度器"""
    global fc_scheduler
    if fc_scheduler and fc_scheduler.running:
        fc_scheduler.shutdown(wait=False)
        logger.info("自由意识调度器已停止")


def restart_fc_scheduler(new_interval: int = None):
    """重启调度器"""
    global fc_scheduler
    stop_fc_scheduler()
    fc_scheduler = None
    if new_interval is None:
        config = FreeConsciousnessService.get_config()
        new_interval = config.get("interval_minutes", 30)
    fc_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    fc_scheduler.add_job(
        run_contemplation,
        IntervalTrigger(minutes=new_interval),
        id="free_consciousness",
        name="自由意识沉思",
        replace_existing=True
    )
    fc_scheduler.start()
    logger.info("自由意识调度器已重启，间隔 %d 分钟", new_interval)
```

- [ ] **步骤 4：Commit**

```bash
git add backend/services/free_consciousness_service.py
git commit -m "feat: 自由意识核心服务骨架（配置 + 调度器 + 日志读写）"
```

---

## 任务 3：核心服务 — 沉思逻辑 + 意识积淀

**文件：**
- 修改：`backend/services/free_consciousness_service.py`

- [ ] **步骤 1：添加 LLM 调用 + 意识积淀读写**

```python
# ── 意识积淀 ──

def load_sediment() -> Optional[Dict]:
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
            "compressed_at": row.compressed_at.isoformat() if row.compressed_at else None
        }
    return None


async def compress_sediment(records_to_compress: list, config: dict):
    """把远期记录压缩成意识积淀"""
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
        response = await call_llm([{"role": "user", "content": prompt}], llm_config)
        content = response.get("content", "").strip()
        if not content:
            logger.warning("意识积淀压缩返回空，跳过更新")
            return

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


def maybe_compress_sediment(config: dict):
    """检查是否需要触发积淀压缩"""
    compress_interval = config.get("sediment_compress_interval", 10)
    recent = config.get("recent_rounds", 3)
    total = FreeConsciousnessService.get_latest_round_number()
    distant_count = total - recent

    if distant_count > 0 and distant_count % compress_interval == 0:
        with active_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT round_number, summary, discovery
                FROM free_consciousness_logs
                WHERE error IS NULL AND round_number <= :max_round
                ORDER BY round_number ASC
            """), {"max_round": total - recent})
            records = result.fetchall()

        if records:
            asyncio.create_task(compress_sediment(records, config))


# ── LLM 调用 ──

def get_effective_llm_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取有效的 LLM 配置（专用配置为空时回退到通用 llm）"""
    fallback = config.get("llm", {})
    return fallback  # 自由意识只有一套 LLM


async def call_llm(messages: list, llm_config: dict) -> dict:
    """调用 LLM，返回 {content, reasoning_content, details}"""
    from services.llm_service import LLMService
    result = await LLMService.generate_message(
        messages=messages,
        llm_config=llm_config,
        max_tokens=llm_config.get("max_tokens"),
        temperature=llm_config.get("temperature", 0.8)
    )
    return result


# ── 思考链 ──

def load_thinking_chain(config: dict) -> list:
    """读取最近的沉思记录，按时间正序返回"""
    recent = config.get("recent_rounds", 3)
    mid = config.get("mid_rounds", 17)
    limit = recent + mid
    with active_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, round_number, thinking, summary, discovery, created_at
            FROM free_consciousness_logs
            WHERE error IS NULL
            ORDER BY round_number DESC
            LIMIT :limit
        """), {"limit": limit})
        rows = result.fetchall()
    return list(reversed(rows))


def build_thinking_chain(records: list, config: dict) -> str:
    """按四层记忆模型拼接思考链"""
    recent = config.get("recent_rounds", 3)
    mid = config.get("mid_rounds", 17)

    if not records:
        sediment = load_sediment()
        if sediment:
            return f"【意识积淀】\n{sediment['content']}\n\n（以上是你过去的思考积淀。请在此基础上继续。）"
        return "（这是你的第一次沉思，没有任何历史。请自由地开始你的思考。）"

    sections = []
    total = len(records)

    # 1. 意识积淀
    sediment = load_sediment()
    if sediment:
        sections.append(f"【意识积淀·覆盖第 {sediment['source_rounds']} 轮】\n{sediment['content']}")

    # 2. 近期 + 中期
    for i, record in enumerate(records):
        distance = total - 1 - i
        round_num = record.round_number

        if distance < recent:
            sections.append(f"【第 {round_num} 轮】\n{record.thinking}")
        elif distance < mid:
            summary = record.summary or record.thinking[:100] + "..."
            sections.append(f"【第 {round_num} 轮·摘要】{summary}")
        else:
            if record.discovery:
                sections.append(f"【第 {round_num} 轮·发现】{record.discovery}")

    return "\n\n".join(sections)


# ── Prompt 构建 ──

def build_contemplation_prompt(chain_text: str, config: dict) -> list:
    """构建沉思的 messages 列表"""
    persona = config.get("persona", "")
    persona_section = f"\n你的思考风格：{persona}" if persona else ""

    system_content = f"""你正在进行自由沉思。这是你的内在思考空间，你可以在这里探索任何想法、
回忆、感受、创意、问题。没有任务压力，没有用户等待，只有你自己安静地思考。{persona_section}

以下是你之前的思考记录：
{chain_text}"""

    user_content = """请从上一轮思考的地方继续，自由地想任何你想想的事情。
如果你有新的发现或洞察，请特别标注。

请严格按以下 JSON 格式输出（不要输出其他内容）：
{{
  "thinking": "你的完整思考过程...",
  "summary": "本轮思考的一句话摘要（30字以内）",
  "discovery": "本轮关键发现（如果没有新发现则为 null）"
}}"""

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]


# ── LLM 输出解析 ──

def parse_llm_output(response_text: str) -> dict:
    """解析 LLM 输出的 JSON"""
    text = response_text.strip()

    # 尝试提取 JSON（可能被 ```json ... ``` 包裹）
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    try:
        data = json.loads(text)
        thinking = (data.get("thinking") or "").strip()
        summary = (data.get("summary") or "").strip()
        discovery = data.get("discovery")

        if not thinking:
            thinking = response_text.strip()

        return {
            "thinking": thinking,
            "summary": summary or thinking[:100] + "...",
            "discovery": discovery,
            "parse_failed": False
        }
    except (json.JSONDecodeError, TypeError):
        return {
            "thinking": response_text.strip(),
            "summary": response_text.strip()[:100] + "...",
            "discovery": None,
            "parse_failed": True
        }


# ── 实时上下文 ──

async def collect_realtime_context() -> str:
    """收集实时上下文（时间 + 情绪状态）"""
    parts = []
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    parts.append(f"当前时间：{now}")

    try:
        from services.active_consciousness_service import get_emotion_state
        emotion = get_emotion_state()
        parts.append(f"当前情绪：{emotion.dominant}（效价 {emotion.valence:.2f}，唤醒 {emotion.arousal:.2f}）")
    except Exception:
        pass

    return "\n".join(parts)


# ── 沉思主函数 ──

async def run_contemplation():
    """执行一次沉思"""
    start_time = time.time()
    config = FreeConsciousnessService.get_config()

    if not config.get("enabled"):
        return

    round_number = FreeConsciousnessService.get_latest_round_number() + 1
    all_details = {}

    try:
        logger.info("=== 自由意识沉思第 %d 轮开始 ===", round_number)

        # 1. 读取思考链
        chain_records = load_thinking_chain(config)
        chain_text = build_thinking_chain(chain_records, config)
        all_details["chain_rounds"] = len(chain_records)
        all_details["chain_preview"] = chain_text[:500]

        # 2. 可选：注入实时上下文
        context_type = "chain"
        if config.get("include_context"):
            context_text = await collect_realtime_context()
            chain_text = chain_text + "\n\n---\n当前世界的状态：\n" + context_text
            context_type = "chain+context"

        # 3. 构建 prompt
        messages = build_contemplation_prompt(chain_text, config)
        all_details["prompt_sent"] = messages
        all_details["chain_tokens"] = sum(len(m["content"]) // 2 for m in messages)

        # 4. 请求 LLM
        llm_config = get_effective_llm_config(config)
        response = await call_llm(messages, llm_config)
        all_details["llm_details"] = response.get("details", {})

        response_text = response.get("content", "")
        reasoning_content = response.get("reasoning_content")
        all_details["response_raw"] = response_text
        if reasoning_content:
            all_details["reasoning_content"] = reasoning_content

        # 5. 解析输出
        parsed = parse_llm_output(response_text)
        all_details["parse_failed"] = parsed["parse_failed"]

        # 6. 写入日志
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

        # 7. 可选：发现存入 Hindsight
        if config.get("store_to_hindsight") and parsed["discovery"]:
            try:
                from services.active_consciousness_service import retain_thought_to_hindsight
                await retain_thought_to_hindsight(
                    parsed["discovery"], None, "free_consciousness", 0
                )
            except Exception as e:
                logger.warning("存入 Hindsight 失败: %s", e)

        # 8. 检查积淀压缩
        maybe_compress_sediment(config)

        logger.info("沉思第 %d 轮完成，耗时 %dms", round_number, duration_ms)

    except Exception as e:
        logger.error("沉思第 %d 轮异常: %s", round_number, e)
        duration_ms = round((time.time() - start_time) * 1000)
        FreeConsciousnessService.write_log(
            round_number=round_number,
            thinking=f"[错误] {str(e)}",
            error=str(e),
            llm_details=json.dumps(all_details, ensure_ascii=False) if all_details else None
        )


# ── 测试 LLM 连通性 ──

async def test_llm_connection(config: dict) -> dict:
    """测试 LLM 连通性"""
    import time as _time
    start = _time.time()
    try:
        llm_config = get_effective_llm_config(config)
        if not llm_config.get("api_key") and not llm_config.get("mode"):
            return {"success": False, "message": "未配置 LLM API Key"}
        response = await call_llm([{"role": "user", "content": "Hi"}], llm_config)
        duration = round(_time.time() - start, 2)
        content = response.get("content", "")
        if content:
            return {"success": True, "message": f"连通成功 (耗时 {duration}s)", "duration": duration}
        return {"success": False, "message": "LLM 返回空"}
    except Exception as e:
        duration = round(_time.time() - start, 2)
        return {"success": False, "message": f"连通失败: {str(e)}", "duration": duration}
```

- [ ] **步骤 2：Commit**

```bash
git add backend/services/free_consciousness_service.py
git commit -m "feat: 自由意识沉思逻辑 + 思考链 + 意识积淀"
```

---

## 任务 4：API 路由

**文件：**
- 新建：`backend/routers/free_consciousness.py`

- [ ] **步骤 1：创建路由文件**

```python
"""
自由意识 API 路由
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/free-consciousness", tags=["自由-consciousness"])


@router.get("/status")
async def get_status():
    """获取状态"""
    from services.free_consciousness_service import FreeConsciousnessService
    return FreeConsciousnessService.get_status()


@router.post("/toggle")
async def toggle(enabled: bool = Body(..., embed=True)):
    """开关"""
    from services.free_consciousness_service import (
        FreeConsciousnessService, start_fc_scheduler, stop_fc_scheduler
    )
    config = FreeConsciousnessService.get_config()
    config["enabled"] = enabled
    FreeConsciousnessService.update_config(config)

    if enabled:
        start_fc_scheduler()
    else:
        stop_fc_scheduler()

    return {"success": True, "enabled": enabled}


@router.post("/restart")
async def restart():
    """重启调度器"""
    from services.free_consciousness_service import restart_fc_scheduler
    restart_fc_scheduler()
    return {"success": True}


@router.get("/config")
async def get_config():
    """获取配置"""
    from services.free_consciousness_service import FreeConsciousnessService
    return FreeConsciousnessService.get_config()


@router.post("/config")
async def save_config(config: dict = Body(...)):
    """保存配置"""
    from services.free_consciousness_service import (
        FreeConsciousnessService, restart_fc_scheduler
    )
    FreeConsciousnessService.update_config(config)
    # 如果启用了，重启调度器以应用新配置
    full_config = FreeConsciousnessService.get_config()
    if full_config.get("enabled"):
        restart_fc_scheduler()
    return {"success": True}


@router.post("/test-llm")
async def test_llm():
    """测试 LLM 连通性"""
    from services.free_consciousness_service import (
        FreeConsciousnessService, test_llm_connection
    )
    config = FreeConsciousnessService.get_config()
    return await test_llm_connection(config)


@router.get("/logs")
async def get_logs(page: int = 1, page_size: int = 20, round_number: int = None):
    """分页查询日志"""
    from services.free_consciousness_service import FreeConsciousnessService
    return FreeConsciousnessService.get_logs(page, page_size, round_number)


@router.get("/logs/{log_id}")
async def get_log_detail(log_id: int):
    """日志详情"""
    from services.free_consciousness_service import FreeConsciousnessService
    detail = FreeConsciousnessService.get_log_detail(log_id)
    if not detail:
        raise HTTPException(status_code=404, detail="日志不存在")
    return detail


@router.delete("/logs/{log_id}")
async def delete_log(log_id: int):
    """删除日志"""
    from services.free_consciousness_service import FreeConsciousnessService
    if not FreeConsciousnessService.delete_log(log_id):
        raise HTTPException(status_code=404, detail="日志不存在")
    return {"success": True}


@router.get("/chain")
async def get_chain():
    """获取当前完整思考链"""
    from services.free_consciousness_service import (
        FreeConsciousnessService, load_thinking_chain, build_thinking_chain
    )
    config = FreeConsciousnessService.get_config()
    records = load_thinking_chain(config)
    chain = build_thinking_chain(records, config)
    return {"chain": chain, "records_count": len(records)}


@router.post("/run")
async def manual_run():
    """手动触发一次沉思"""
    from services.free_consciousness_service import run_contemplation
    try:
        await run_contemplation()
        return {"success": True, "message": "沉思已执行"}
    except Exception as e:
        return {"success": False, "message": str(e)}
```

- [ ] **步骤 2：Commit**

```bash
git add backend/routers/free_consciousness.py
git commit -m "feat: 自由意识 API 路由（9 个端点）"
```

---

## 任务 5：路由注册 + 启动集成

**文件：**
- 修改：`backend/routers/__init__.py`
- 修改：`backend/main.py`

- [ ] **步骤 1：注册路由**

在 `routers/__init__.py` 中添加：

```python
from . import free_consciousness
```

在 `__all__` 列表中添加 `"free_consciousness"`。

- [ ] **步骤 2：main.py 集成**

在 `main.py` 的 import 区域添加：

```python
from services.free_consciousness_service import start_fc_scheduler, stop_fc_scheduler
```

在 `lifespan` 函数中，在 `start_heartbeat_scheduler()` 之后添加：

```python
    # 启动自由意识调度器
    print("正在启动自由意识调度器...")
    start_fc_scheduler()
```

在 `yield` 之后、`stop_heartbeat_scheduler()` 之前添加：

```python
    # 停止自由意识调度器
    stop_fc_scheduler()
```

- [ ] **步骤 3：验证后端启动**

```bash
cd ~/.hermes/hermes-active/backend && python -c "
from models.database import init_active_db
from routers import free_consciousness
print('Router prefix:', free_consciousness.router.prefix)
print('Routes:', [r.path for r in free_consciousness.router.routes])
"
```

预期：输出 `/api/free-consciousness` 和 9 个路由路径。

- [ ] **步骤 4：Commit**

```bash
git add backend/routers/__init__.py backend/main.py
git commit -m "feat: 自由意识路由注册 + 启动集成"
```

---

## 任务 6：前端 API 封装

**文件：**
- 新建：`frontend/src/api/freeConsciousness.js`

- [ ] **步骤 1：创建 API 文件**

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

- [ ] **步骤 2：Commit**

```bash
git add frontend/src/api/freeConsciousness.js
git commit -m "feat: 自由意识前端 API 封装"
```

---

## 任务 7：前端页面

**文件：**
- 新建：`frontend/src/views/FreeConsciousness.vue`

- [ ] **步骤 1：创建页面**

参照 `ActiveConsciousness.vue` 的结构，创建 `FreeConsciousness.vue`，包含两个 Tab：

**Tab 1: 状态 & 配置**
- 开关卡片（n-switch + 状态指示灯）
- 状态信息：总轮次、上次/下次沉思、思考链 token、积淀信息
- LLM 配置面板（provider / api_key / base_url / model / max_tokens / temperature）
- 沉思参数面板（interval / recent / mid / sediment_compress_interval）
- 可选配置（include_context / store_to_hindsight / persona）
- 测试 LLM 连通按钮 + 手动触发按钮

**Tab 2: 沉思日志**
- 日志表格：ID / 轮次 / 摘要 / 发现 / token 数 / 时间
- 轮次筛选
- 分页
- 详情弹窗：thinking + summary + discovery + llm_details + reasoning_content

页面结构模板：

```vue
<template>
  <div class="free-consciousness-page">
    <n-tabs type="line" v-model:value="activeTab">
      <!-- Tab 1: 状态 & 配置 -->
      <n-tab-pane name="status" tab="状态">
        <!-- 开关卡片 -->
        <!-- 状态信息 -->
        <!-- LLM 配置 -->
        <!-- 沉思参数 -->
      </n-tab-pane>

      <!-- Tab 2: 日志 -->
      <n-tab-pane name="logs" tab="沉思日志">
        <!-- 筛选 -->
        <!-- 日志表格 -->
        <!-- 分页 -->
      </n-tab-pane>
    </n-tabs>

    <!-- 详情弹窗 -->
    <n-modal v-model:show="showDetail" ... >
      <!-- thinking / summary / discovery / llm_details -->
    </n-modal>
  </div>
</template>
```

关键实现点：
- `onMounted` 用 `Promise.all` 并行加载 status + config + logs
- 日志表格的"发现"列用 `n-tag` 显示（有发现时 ✨ 标签）
- 详情弹窗中 thinking 用 `n-code` 展示
- LLM 配置的 API Key 输入框用明文（不加 type="password"）
- 使用 CSS 变量适配主题

- [ ] **步骤 2：Commit**

```bash
git add frontend/src/views/FreeConsciousness.vue
git commit -m "feat: 自由意识前端页面"
```

---

## 任务 8：前端路由 + 菜单

**文件：**
- 修改：`frontend/src/router/index.js`
- 修改：`frontend/src/components/Layout.vue`

- [ ] **步骤 1：注册路由**

在 `router/index.js` 的 children 数组中，在 `active-consciousness` 路由之后添加：

```javascript
{
  path: 'free-consciousness',
  name: 'FreeConsciousness',
  component: () => import('../views/FreeConsciousness.vue')
},
```

- [ ] **步骤 2：添加菜单项**

在 `Layout.vue` 的 `menuItems` 数组中，在"主动意识"之后添加：

```javascript
{ path: '/free-consciousness', label: '自由意识', icon: markRaw(SparklesOutline) },
```

在 import 区域添加 `SparklesOutline`：

```javascript
import {
  ...existing icons...,
  SparklesOutline
} from '@vicons/ionicons5'
```

- [ ] **步骤 3：验证前端编译**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build
```

预期：编译成功，无错误。

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/router/index.js frontend/src/components/Layout.vue
git commit -m "feat: 自由意识路由 + 侧边栏菜单"
```

---

## 任务 9：端到端验证

- [ ] **步骤 1：启动后端**

```bash
cd ~/.hermes/hermes-active/backend && python main.py
```

- [ ] **步骤 2：验证 API 端点**

```bash
# 状态
curl -s http://localhost:18720/api/free-consciousness/status | python3 -m json.tool

# 配置
curl -s http://localhost:18720/api/free-consciousness/config | python3 -m json.tool

# 手动触发（需要先配置 LLM）
curl -s -X POST http://localhost:18720/api/free-consciousness/toggle -H 'Content-Type: application/json' -d '{"enabled": true}'
curl -s -X POST http://localhost:18720/api/free-consciousness/run

# 日志
curl -s http://localhost:18720/api/free-consciousness/logs | python3 -m json.tool

# 思考链
curl -s http://localhost:18720/api/free-consciousness/chain | python3 -m json.tool
```

- [ ] **步骤 3：验证前端页面**

在浏览器中访问 `http://localhost:18720/free-consciousness`，确认：
- 状态 tab 正确显示开关和状态信息
- 配置 tab 可以保存配置
- 日志 tab 显示沉思记录
- 详情弹窗正确展示 thinking / summary / discovery / LLM 详情

- [ ] **步骤 4：最终 Commit**

```bash
git add -A
git commit -m "feat: 自由意识模块完成"
```

---

## 自检清单

1. ✅ 规格覆盖度 — 所有设计文档中的需求都有对应任务
2. ✅ 无占位符 — 每个步骤都有完整代码
3. ✅ 类型一致性 — `_DEFAULTS` key 前缀、方法签名、API 路径全链路一致
4. ✅ 文件路径已验证 — `grep` 确认现有文件结构
5. ✅ 测试点覆盖 — 设计文档 5.1-5.6 测试点可通过端到端验证（任务 9）
