# v0.2.1 监控日志入库任务

## 目标
把关键监控数据写入数据库，让前端页面能看到完整的心跳流程日志。

## 严格约束

### 绝对不能动的文件
- `backend/models/passive_consciousness.py`
- `backend/models/passive_consciousness_log.py`
- `backend/services/passive_consciousness_service.py`
- `backend/routers/passive_consciousness.py`
- `frontend/src/views/PassiveConsciousness.vue`
- `frontend/src/api/passive_consciousness.js`

### 可以修改的文件
- `backend/models/active.py` — 添加字段
- `backend/services/active_consciousness_service.py` — 写入日志
- `backend/routers/active_consciousness.py` — API 返回新字段

---

## 任务一：ThoughtLog 添加 details 字段

**文件**: `backend/models/active.py`

在 `ThoughtLog` 类中添加 `details` 字段：

```python
class ThoughtLog(Base):
    """想法日志表"""
    __tablename__ = "active_thought_logs"

    # ... 现有字段 ...
    details = Column(Text, nullable=True)  # JSON格式的详细日志

    def to_dict(self):
        return {
            # ... 现有字段 ...
            "details": self.details,
        }
```

---

## 任务二：心跳日志写入详细监控数据

**文件**: `backend/services/active_consciousness_service.py`

在 `run_heartbeat()` 函数中，确保 `all_details` 包含以下信息：

```python
all_details = {
    "emotion_before": {  # 初始情绪
        "valence": ...,
        "arousal": ...,
        "dominant": ...,
        "social_need": ...,
    },
    "emotion_evolved": {  # 演化后情绪
        "valence": ...,
        "arousal": ...,
        "dominant": ...,
        "social_need": ...,
    },
    "minutes_since_update": 120.5,  # 距上次更新的分钟数
    "emotion_llm": {  # LLM 评估的情绪
        "valence": ...,
        "arousal": ...,
        "dominant": ...,
        "social_need": ...,
    },
    "emotion_merged": {  # 合并后的情绪
        "valence": ...,
        "arousal": ...,
        "dominant": ...,
        "social_need": ...,
    },
    "time_fitness": {
        "score": 0.8,
        "label": "工作时间"
    },
    "decision": {
        "type": "auto_send",
        "reason": "score=0.618 > 0.6 (intensity=0.883, time_fitness=1.000(下班时间), silence_factor=0.700, frequency_limit=1.000)",
        "score": 0.618
    },
    "thought_type": "emotion",  # 念头类型
    "hindsight_tags": ["active_consciousness", "thought", "emotion", "happy"],  # Hindsight 标签
    "hindsight_stored": true,  # 是否存入 Hindsight
    "delay_reeval": {  # 延迟队列重评估
        "sent": 0,
        "discarded": 1,
        "kept": 2
    }
}
```

**关键点**：
1. 情绪演化前后的值都要记录
2. 决策计算的完整参数（intensity, time_fitness, silence_factor, frequency_limit）
3. 念头类型
4. Hindsight 标签
5. 延迟队列重评估结果

---

## 任务三：念头日志写入详细信息

**文件**: `backend/services/active_consciousness_service.py`

在 `generate_and_send_thought_with_emotion()` 函数中，写入念头日志时添加 details：

```python
thought_details = {
    "thought_type": thought_type,
    "emotion_state": {
        "valence": emotion_state.valence,
        "arousal": emotion_state.arousal,
        "dominant": emotion_state.dominant,
        "social_need": emotion_state.social_need,
    },
    "decision": decision_type,
    "score": score,
    "hindsight_tags": tags,
    "hindsight_stored": stored,
    "llm_call": {
        "duration_ms": ...,
        "model": ...,
    }
}

ActiveConsciousnessService.write_thought_log(
    # ... 现有参数 ...
    details=json.dumps(thought_details, ensure_ascii=False)
)
```

---

## 任务四：修改 write_thought_log 支持 details 参数

**文件**: `backend/services/active_consciousness_service.py`

在 `ActiveConsciousnessService.write_thought_log()` 方法中添加 `details` 参数：

```python
@staticmethod
def write_thought_log(
    # ... 现有参数 ...
    details: Optional[str] = None  # 新增
) -> int:
    """记录想法日志"""
    # ... 现有代码 ...
    with active_engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO active_thought_logs
            (heartbeat_id, type, content, intensity, decision, reason, score,
             recall_count, recall_source, chat_heat, emotional_intensity, details, created_at)
            VALUES (:heartbeat_id, :type, :content, :intensity, :decision, :reason, :score,
                    :recall_count, :recall_source, :chat_heat, :emotional_intensity, :details, :created_at)
        """), {
            # ... 现有参数 ...
            "details": details,
        })
```

---

## 任务五：数据库迁移

**文件**: `backend/models/active.py`

添加一个迁移函数，在启动时自动给 `active_thought_logs` 表添加 `details` 列：

```python
def migrate_thought_logs_table():
    """给 active_thought_logs 表添加 details 列（如果不存在）"""
    from models.database import active_engine
    from sqlalchemy import text
    
    try:
        with active_engine.connect() as conn:
            # 检查 details 列是否存在
            result = conn.execute(text("PRAGMA table_info(active_thought_logs)"))
            columns = [row[1] for row in result.fetchall()]
            
            if "details" not in columns:
                conn.execute(text("ALTER TABLE active_thought_logs ADD COLUMN details TEXT"))
                conn.commit()
                logger.info("已添加 details 列到 active_thought_logs 表")
    except Exception as e:
        logger.warning("迁移 active_thought_logs 表失败: %s", e)
```

在 `main.py` 或服务启动时调用此函数。

---

## 验收标准

1. [ ] ThoughtLog 模型添加 details 字段
2. [ ] write_thought_log() 支持 details 参数
3. [ ] 心跳日志的 details 包含完整监控数据
4. [ ] 念头日志的 details 包含详细信息
5. [ ] 数据库迁移函数自动添加 details 列
6. [ ] 被动意识文件未被修改
7. [ ] Python 语法检查通过

---

## 前端页面展示（可选）

如果时间允许，在前端页面展示 details 字段的内容：
- 心跳日志：点击展开显示情绪演化、决策计算等详情
- 念头日志：点击展开显示 Hindsight 标签、LLM 调用等详情
