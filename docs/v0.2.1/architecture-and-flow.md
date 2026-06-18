# 主动意识模块架构与执行流程

> v0.2.1 版本 - 主动意识模块闭环优化

---

## 一、系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3)                              │
│   ActiveConsciousness.vue                                       │
│   - 状态面板（心跳、想念、热度、情绪）                             │
│   - 日志面板（心跳日志、念头日志）                                │
│   - 配置面板（LLM、心跳、Session、决策阈值）                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     后端 (FastAPI)                               │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              active_consciousness_service.py             │   │
│   │  - 配置管理    - 状态查询    - 心跳调度                   │   │
│   │  - 情绪演化    - 决策计算    - 念头生成                   │   │
│   │  - 延迟队列    - 日志清理    - Hindsight 集成             │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│          ┌───────────────────┼───────────────────┐              │
│          ▼                   ▼                   ▼              │
│   ┌────────────┐     ┌────────────┐     ┌────────────┐         │
│   │ active.db  │     │ state.db   │     │ Hindsight  │         │
│   │ (读写)     │     │ (只读)     │     │ (外部服务)  │         │
│   └────────────┘     └────────────┘     └────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、Hindsight 双 Bank 设计

### 2.1 设计目标

- **存储念头**（aretain）：使用独立的 `hermes-active` Bank
- **召回记忆**（arecall）：使用 `hermes` Bank（主系统数据）

### 2.2 为什么分离

| 维度 | hermes Bank | hermes-active Bank |
|------|-------------|-------------------|
| 数据来源 | 用户对话、系统事件 | 主动意识生成的念头 |
| 写入方 | Hermes 主系统 | hermes-active |
| 用途 | 召回用户相关记忆 | 存储和召回念头 |
| 生命周期 | 跟随用户对话 | 跟随心跳生成 |

**注意**：
- Hindsight 是记忆系统，只存储可被召回用于上下文的文本内容
- 日志（心跳日志、念头日志）存储在 active.db 中
- 情绪状态是结构化数据，存储在 active.db 中，不存入 Hindsight

### 2.3 配置设计

```python
# backend/services/active_consciousness_service.py

_DEFAULTS = {
    # ... 其他配置 ...
    
    # Hindsight 配置 - 召回（使用 hermes Bank）
    "active_consciousness.hindsight.recall.bank_id": "hermes",
    "active_consciousness.hindsight.recall.base_url": "http://localhost:8888",
    "active_consciousness.hindsight.recall.timeout": "30",
    "active_consciousness.hindsight.recall.limit": "5",
    
    # Hindsight 配置 - 存储（使用 hermes-active Bank）
    "active_consciousness.hindsight.store.bank_id": "hermes-active",
    "active_consciousness.hindsight.store.base_url": "http://localhost:8888",
    "active_consciousness.hindsight.store.timeout": "30",
    
    # Hindsight 配置 - 反思（使用 hermes Bank）
    "active_consciousness.hindsight.reflect.enabled": "true",
    "active_consciousness.hindsight.reflect.bank_id": "hermes",
}
```

### 2.4 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                       心跳执行流程                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. 召回记忆（从 hermes Bank）                                      │
│                                                                 │
│    call_hindsight_with_retry(                                   │
│        query="最近的对话和情绪",                                  │
│        bank_id="hermes",        ← 使用 hermes Bank                │
│        limit=5                                                      
│    )                                                            │
│                                                                 │
│    返回：用户对话历史、系统事件                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 生成念头 + 决策                                               │
│                                                                 │
│    - LLM 评估情绪                                               │
│    - 多维度决策                                                 │
│    - 生成念头内容                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. 存储念头（到 hermes-active Bank）                               │
│                                                                 │
│    retain_thought_to_hindsight(                                 │
│        thought="现在有点想聊天...",                               │
│        emotion_state=...,                                       │
│        thought_type="emotion",                                  │
│        score=0.75                                               │
│    )                                                            │
│                                                                 │
│    内部调用：                                                    │
│    client.aretain(                                              │
│        bank_id="hermes-active",  ← 使用 hermes-active Bank        │
│        content="[emotion] 现在有点想聊天...",                     │
│        tags=["thought", "emotion", "happy", "active_consciousness"]
│    )                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. 下次心跳时召回（从两个 Bank）                                   │
│                                                                 │
│    # 从 hermes Bank召回用户记忆                                    │
│    user_memories = call_hindsight_with_retry(                   │
│        bank_id="hermes",                                        │
│        query="用户最近说了什么"                                   │
│    )                                                            │
│                                                                 │
│    # 从 hermes-active Bank召回头脑念头                             │
│    my_thoughts = call_hindsight_with_retry(                     │
│        bank_id="hermes-active",                                 │
│        query="我最近的想法"                                      │
│    )                                                            │
│                                                                 │
│    # 合并上下文                                                  │
│    context = user_memories + my_thoughts                        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 代码实现

#### 配置结构调整

```python
# backend/models/active_consciousness.py

class ActiveConsciousnessHindsightRecallConfig(BaseModel):
    """Hindsight 召回配置（hermes Bank）"""
    bank_id: str = "hermes"
    base_url: str = "http://localhost:8888"
    timeout: float = 30.0
    limit: int = 5

class ActiveConsciousnessHindsightStoreConfig(BaseModel):
    """Hindsight 存储配置（hermes-active Bank）"""
    bank_id: str = "hermes-active"
    base_url: str = "http://localhost:8888"
    timeout: float = 30.0

class ActiveConsciousnessHindsightConfig(BaseModel):
    """Hindsight 完整配置"""
    enabled: bool = True
    recall: ActiveConsciousnessHindsightRecallConfig = ActiveConsciousnessHindsightRecallConfig()
    store: ActiveConsciousnessHindsightStoreConfig = ActiveConsciousnessHindsightStoreConfig()
    reflect: ActiveConsciousnessHindsightReflectConfig = ActiveConsciousnessHindsightReflectConfig()
```

#### 召回函数修改

```python
# backend/services/active_consciousness_service.py

async def recall_from_hindsight(
    query: str,
    limit: int = 5,
    bank_id: str = "hermes",  # 默认从 hermes Bank召回
    base_url: str = "http://localhost:8888",
    timeout: float = 30.0,
    max_retries: int = 3
) -> List[Dict]:
    """
    从 Hindsight 召回记忆
    
    Args:
        query: 查询内容
        limit: 返回数量
        bank_id: 银行 ID（默认 "hermes"）
        base_url: 基础 URL
        timeout: 超时时间
        max_retries: 最大重试次数
    
    Returns:
        召回结果列表
    """
    for attempt in range(max_retries):
        try:
            client = get_hindsight_client(base_url, timeout)
            response = await client.arecall(
                bank_id=bank_id,
                query=query,
                max_tokens=4096
            )
            return response.get("results", [])
        except ConnectionError as e:
            logger.warning("Hindsight 召回失败，尝试重连 (%d/%d): %s", 
                          attempt + 1, max_retries, e)
            await reset_hindsight_client()
            if attempt == max_retries - 1:
                logger.error("Hindsight 召回重试失败")
                return []
        except Exception as e:
            logger.error("Hindsight 召回异常: %s", e)
            return []
    return []
```

#### 存储函数修改

```python
async def retain_thought_to_hindsight(
    thought: str,
    emotion_state: EmotionState,
    thought_type: str,
    score: float
) -> bool:
    """
    将重要念头存入 Hindsight（使用 hermes-active Bank）
    
    存储条件（满足任一即可）：
    1. 情绪强度 > retain_threshold
    2. 包含用户名字（如"曹凡"）
    3. 分数 > retain_threshold
    
    注意：只存储念头文本，情绪状态存储在 active.db
    """
    config = ActiveConsciousnessService.get_config()
    thought_config = config.get("thought", {})
    
    # 检查是否启用存储
    if not thought_config.get("retain_enabled", False):
        return False
    
    # 检查存储条件
    retain_threshold = float(thought_config.get("retain_threshold", 0.5))
    intensity = emotion_state.intensity()
    
    if intensity < retain_threshold and "曹凡" not in thought:
        return False
    
    try:
        # 获取存储配置（hermes-active Bank）
        store_config = config.get("hindsight", {}).get("store", {})
        bank_id = store_config.get("bank_id", "hermes-active")
        base_url = store_config.get("base_url", "http://localhost:8888")
        timeout = float(store_config.get("timeout", 30))
        
        client = get_hindsight_client(base_url, timeout)
        
        # 构建内容和标签
        content = f"[{thought_type}] {thought}"
        tags = [
            "active_consciousness",
            "thought",
            thought_type,
            emotion_state.dominant,
        ]
        if "曹凡" in thought:
            tags.append("user_related")
        if intensity > 0.7:
            tags.append("high_emotion")
        
        # 存储到 hermes-active Bank
        await client.aretain(
            bank_id=bank_id,  # ← 使用 hermes-active Bank
            content=content,
            tags=tags
        )
        
        logger.info("念头已存入 Hindsight [%s]: %s", bank_id, thought[:50])
        return True
    except Exception as e:
        logger.warning("存入 Hindsight 失败: %s", e)
        return False
```

#### 心跳中的召回逻辑

```python
async def run_heartbeat():
    """执行心跳"""
    # ... 前面的代码 ...
    
    # 5. 获取上下文
    session_config = config.get("session", {})
    hindsight_config = config.get("hindsight", {})
    
    # 5.1 从 hermes Bank召回用户记忆
    recall_config = hindsight_config.get("recall", {})
    user_memories = await recall_from_hindsight(
        query="最近的对话和情绪",
        limit=recall_config.get("limit", 5),
        bank_id=recall_config.get("bank_id", "hermes"),  # ← hermes Bank
        base_url=recall_config.get("base_url", "http://localhost:8888"),
        timeout=float(recall_config.get("timeout", 30)),
        max_retries=3
    )
    
    # 5.2 从 hermes-active Bank召回头脑念头
    store_config = hindsight_config.get("store", {})
    my_thoughts = await recall_from_hindsight(
        query="我最近的想法和情绪",
        limit=5,
        bank_id=store_config.get("bank_id", "hermes-active"),  # ← hermes-active Bank
        base_url=store_config.get("base_url", "http://localhost:8888"),
        timeout=float(store_config.get("timeout", 30)),
        max_retries=3
    )
    
    # 5.3 合并上下文
    hindsight_results = user_memories + my_thoughts
    
    # ... 后续代码 ...
```

### 2.6 配置迁移

对于现有用户，需要在 `_DEFAULTS` 中添加新的配置项，并在 `get_config()` 中做兼容处理：

```python
def get_config():
    """获取配置，兼容旧版本"""
    config = ActiveConsciousnessService.get_config()
    
    # 兼容旧的单 bank_id 配置
    hindsight = config.get("hindsight", {})
    if "bank_id" in hindsight and "recall" not in hindsight:
        # 旧版本配置，迁移到新结构
        old_bank_id = hindsight.get("bank_id", "hermes")
        config["hindsight"] = {
            "enabled": hindsight.get("enabled", True),
            "recall": {
                "bank_id": old_bank_id,
                "base_url": hindsight.get("base_url", "http://localhost:8888"),
                "timeout": hindsight.get("timeout", 30),
                "limit": hindsight.get("recall_limit", 5),
            },
            "store": {
                "bank_id": "hermes-active",
                "base_url": hindsight.get("base_url", "http://localhost:8888"),
                "timeout": hindsight.get("timeout", 30),
            },
            "reflect": {
                "enabled": hindsight.get("reflect_enabled", True),
                "bank_id": old_bank_id,
            }
        }
    
    return config
```

---

## 三、心跳执行流程详解

### 3.1 完整流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    心跳调度器触发（每 10 分钟）                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. 配置检查                                                     │
│    - 读取配置（带验证）                                           │
│    - 检查总开关是否启用                                           │
│    - 检查主动发送是否启用                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 读取上次情绪状态                                               │
│    - 从 configs 表读取 EmotionState                              │
│    - valence, arousal, social_need, dominant                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. 情绪演化                                                     │
│    - 计算距离上次更新的时间间隔                                    │
│    - 调用 evolve_emotion()：                                     │
│      · arousal 自然衰减（越久越平静）                              │
│      · social_need 自然上升（越久越想聊天）                        │
│      · valence 轻微回归中性（0.5）                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. 获取状态信息                                                   │
│    - 想念分数（longing）                                         │
│    - 聊天热度（chat_heat）                                       │
│    - 时间窗口权重：get_time_fitness()                             │
│      · 早安 1.0 / 工作 0.8 / 午休 0.9 / 下班 1.0 / 深夜 0.3     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. 获取上下文（双 Bank 召回）                                      │
│                                                                 │
│    5.1 从 hermes Bank召回用户记忆                                   │
│        - Session 消息上下文                                      │
│        - 用户对话历史                                            │
│                                                                 │
│    5.2 从 hermes-active Bank召回头脑念头                            │
│        - 之前生成的念头                                          │
│        - 情绪记录                                                │
│                                                                 │
│    5.3 合并上下文                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. LLM 情绪评估                                                  │
│    - 调用 call_llm_with_fallback()                               │
│      · 30 秒超时保护                                             │
│      · None 返回检测                                             │
│      · 异常时返回默认 EmotionState                                │
│    - 输出 VA 值（valence, arousal, social_need）                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. 情绪合并                                                      │
│    - 计算 LLM 置信度：calculate_llm_confidence()                 │
│    - 动态权重合并：merge_emotion_dynamic()                        │
│      · 低置信度(<0.3)：演化 70% + LLM 30%                        │
│      · 高置信度(>0.8)：演化 30% + LLM 70%                        │
│      · 默认：演化 40% + LLM 60%                                  │
│    - 保存情绪状态到数据库                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. 多维度决策                                                    │
│    - 调用 make_decision_v2()：                                   │
│      score = intensity × time_fitness × silence × frequency     │
│    - 决策类型：                                                   │
│      · auto_send (>0.6)：立即发送                                │
│      · delay_send (>0.3)：延迟发送                               │
│      · memory (>0.1)：存为记忆                                   │
│      · skip (≤0.1)：跳过                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. 记录心跳日志                                                  │
│    - 先保存情绪，后记录日志（保证一致性）                           │
│    - 记录所有 details（情绪演化、决策、召回等）                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. 执行决策结果                                                  │
│                                                                 │
│     ┌─────────────┬─────────────┬─────────────┬─────────────┐   │
│     │    skip     │   memory    │ delay_send  │  auto_send  │   │
│     └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘   │
│            │             │             │             │           │
│            ▼             ▼             ▼             ▼           │
│         跳过        存为记忆      入延迟队列     生成并发送        │
│                       │             │             │             │
│                       ▼             ▼             ▼             │
│                  存入 Hindsight  记录日志     存入 Hindsight     │
│                  (hermes-active)           (hermes-active)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 11. 延迟队列重评估                                               │
│    - 遍历延迟队列中的念头：                                       │
│      · 检查是否过期（>4小时）→ 过期则丢弃                         │
│      · 检查重试次数（>3次）→ 超限则丢弃                           │
│      · 检查是否到重试时间 → 未到则保持                            │
│      · 重新计算 score → 升级/降级/保持                            │
│    - 队列满时拒绝新念头（硬限制）                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 12. 更新心跳日志                                                  │
│    - 更新 duration_ms、message_sent、details                     │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 念头类型判断顺序

```
determine_thought_type_v2() 优先级：

1. 特殊时间（7-8点早安，22-23点晚安）→ TIME
       ↓ 不满足
2. 长时间沉默（>180分钟）→ SILENCE
       ↓ 不满足
3. 高情绪强度（>0.6）→ EMOTION
       ↓ 不满足
4. 有相关回忆（Hindsight 结果）→ MEMORY
       ↓ 不满足
5. 默认 → ASSOCIATION
```

---

## 四、配置变更流程

```
用户修改配置
      │
      ▼
验证配置（validate_active_consciousness_config）
      │
      ├─ 验证失败 → 返回 400 错误
      │
      ▼ 验证通过
保存配置到数据库
      │
      ▼
检查心跳间隔是否变化
      │
      ├─ 未变化 → 完成
      │
      ▼ 变化
重启心跳调度器（restart_heartbeat_scheduler）
      │
      ▼
使用新的心跳间隔
```

---

## 五、定时任务执行顺序

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用启动                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. 初始化数据库                                                  │
│ 2. 创建默认管理员                                                │
│ 3. 启动心跳调度器（每 10 分钟）                                   │
│ 4. 启动日志清理调度器（每天凌晨 3 点）                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        应用运行中                                 │
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐                          │
│   │ 心跳调度器    │    │ 日志清理调度器│                          │
│   │ 每 10 分钟   │    │ 每天 3:00    │                          │
│   └──────┬───────┘    └──────┬───────┘                          │
│          │                   │                                  │
│          ▼                   ▼                                  │
│     run_heartbeat()    cleanup_old_logs()                       │
│     （执行上述流程）    （删除 30 天前的日志）                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        应用关闭                                  │
│                                                                 │
│   1. 关闭 Hindsight 客户端                                       │
│   2. 停止日志清理调度器                                           │
│   3. 停止心跳调度器                                              │
│   4. 停止主调度器                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、关键改进总结

| 阶段 | 原有逻辑 | 改进后逻辑 |
|------|---------|-----------|
| 情绪读取 | 每次重新评估 | 读取上次状态 + 时间演化 |
| LLM 调用 | 裸调用，失败则崩溃 | 超时保护 + 异常降级 |
| 情绪合并 | 固定权重 40%/60% | 动态权重（基于置信度） |
| 决策 | 简单阈值判断 | 多维度公式计算 |
| 念头类型 | 简单优先级 | 智能判断（时间>沉默>情绪>回忆） |
| 延迟队列 | 软限制，无过期 | 硬限制 + 4小时过期 |
| 配置更新 | 保存后等待下次心跳 | 实时重启调度器 |
| 日志清理 | 无 | 每天清理 30 天前的日志 |
| Hindsight | 无重试，单 Bank | 最多 3 次重试 + 双 Bank 分离 |

---

## 七、Hindsight 双 Bank 配置示例

### 7.1 配置文件示例

```yaml
# ~/.hermes/config.yaml 中的 hermes-active 配置

active_consciousness:
  enabled: true
  
  hindsight:
    enabled: true
    
    # 召回配置（从 hermes Bank读取用户记忆）
    recall:
      bank_id: "hermes"
      base_url: "http://localhost:8888"
      timeout: 30
      limit: 5
    
    # 存储配置（写入 hermes-active Bank）
    store:
      bank_id: "hermes-active"
      base_url: "http://localhost:8888"
      timeout: 30
    
    # 反思配置（使用 hermes Bank）
    reflect:
      enabled: true
      bank_id: "hermes"
```

### 7.2 数据隔离示意

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hindsight 服务                                │
│                     (localhost:8888)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌─────────────────────┐                 ┌─────────────────────┐
│    hermes Bank      │                 │  hermes-active Bank │
│    (用户记忆)       │                 │   (主动意识记忆)    │
│                     │                 │                     │
│  - 用户对话历史     │                 │  - 生成的念头       │
│  - 系统事件         │                 │                     │
│  - 关键词记忆       │                 │                     │
│                     │                 │                     │
│  写入方：Hermes 主系统│                │  写入方：hermes-active│
│  读取方：hermes-active│                │  读取方：hermes-active│
└─────────────────────┘                 └─────────────────────┘

┌─────────────────────┐
│     active.db       │
│   (结构化数据)      │
│                     │
│  - 情绪状态         │
│  - 心跳日志         │
│  - 念头日志         │
│  - 延迟队列         │
│  - 配置数据         │
└─────────────────────┘
```

---

**最后更新**：2026-06-18
**版本**：v0.2.1
