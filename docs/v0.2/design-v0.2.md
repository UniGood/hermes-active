# hermes-active v0.2 设计方案

> 借鉴 [Hermes_Soul_patch](https://github.com/gejifeng/Hermes_Soul_patch) 的 companion layer 思想

## 一、设计背景

v0.1 实现了基础的定时主动消息发送（APScheduler + LLM 生成），但存在以下问题：
- 消息触发逻辑单一（固定 cron 表达式 + 冷却时间）
- 缺乏情感状态感知（不知道凯莉此刻"心情"如何）
- 缺乏世界状态模拟（不知道今天发生了什么）
- 上下文注入有限（只有 session 消息 + Hindsight 记忆）

## 二、核心借鉴

### 2.1 情感状态（Emotion State）

**来源**: `companion/emotion_state.py`

**设计要点**:
- 多维度情感模型：valence（极性）、arousal（激活度）、energy（精力）、social_need（社交需求）、confidence（置信度）、momentum（惯性）
- 存储在 `active.db` 的 `emotion_states` 表（而非文件，更适合 Web 管理）
- 每次 LLM 调用后通过辅助 LLM 推断更新
- 注入到每个 LLM turn 的上下文中

**v0.2 实现**:
```python
class EmotionState(Base):
    __tablename__ = 'emotion_states'
    id = Column(Integer, primary_key=True)
    valence = Column(Float, default=0.2)      # -1.0 ~ 1.0
    arousal = Column(Float, default=0.4)       # 0.0 ~ 1.0
    energy = Column(Float, default=0.45)       # 0.0 ~ 1.0
    social_need = Column(Float, default=0.35)  # 0.0 ~ 1.0
    confidence = Column(Float, default=0.55)   # 0.0 ~ 1.0
    momentum = Column(Float, default=0.0)      # -1.0 ~ 1.0
    dominant = Column(String, default='calm')   # 主导情绪标签
    note = Column(String, default='')           # 状态描述
    updated_at = Column(DateTime)
    source = Column(String, default='default')  # manual/inference/nudge
```

### 2.2 心跳触发器（Heartbeat Trigger）

**来源**: `companion/heartbeat.py`

**设计要点**:
- 不是简单的 cron 触发，而是基于情感状态的智能触发
- `arousal >= threshold` 时触发主动消息
- 冷却机制：同一情绪状态不重复发送
- 内容签名：避免相同 mood 的消息重复

**v0.2 实现**:
```python
class HeartbeatConfig:
    check_interval = 300        # 检查间隔（秒）
    arousal_threshold = 0.70    # 触发阈值
    arousal_cooldown = 3600     # 同状态冷却
    repeat_cooldown = 21600     # 重复内容冷却
    morning_window = 10         # 早安窗口（分钟）
```

### 2.3 世界状态（World State）

**来源**: `companion/world_state.py`

**设计要点**:
- 维护 agent 视角的「今日日程 + 环境事件」
- 事件类型：self（自己安排）、interaction（与用户互动）、ambient（环境观察）
- 跨日自动归档（events/2026-06-13.jsonl）
- 到期事件触发主动消息

**v0.2 实现**:
```python
class WorldEvent(Base):
    __tablename__ = 'world_events'
    id = Column(String, primary_key=True)  # uuid hex[:8]
    date = Column(String)                   # YYYY-MM-DD
    start = Column(DateTime)
    end = Column(DateTime, nullable=True)
    title = Column(String)
    kind = Column(String)  # self/interaction/ambient
    status = Column(String)  # pending/done/missed
    note = Column(String, nullable=True)
```

### 2.4 每日种子（Daily Seed）

**来源**: `companion/daily_seed.py`

**设计要点**:
- 每天凌晨自动生成当日日程
- 固定锚点（起床、午餐、晚餐、睡前）+ LLM 增补
- 基于 SOUL.md 人设生成"今天特别想做"的事件
- 幂等：已有日程不覆盖

**v0.2 实现**:
- 存储在 `active.db` 的 `daily_seeds` 表
- 通过 APScheduler 每天 00:05 触发
- 锚点配置在 Config 管理页面可编辑

### 2.5 世界交互观察器（World Interaction）

**来源**: `companion/world_interaction.py`

**设计要点**:
- 分析用户消息，自动更新世界状态
- 完成/取消/约定/环境变化的关键词匹配
- 保守策略：只处理明显信号

**v0.2 实现**:
- 在 `post_llm_call` hook 中触发
- 使用正则匹配 + 辅助 LLM 判断
- 更新 `world_events` 表

## 三、架构设计

### 3.1 数据流

```
用户消息 → LLM 调用
              ↓
         post_llm_call hook
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
情感推断   世界交互   Hindsight 存储
    ↓         ↓
更新状态   更新事件
    ↓
下次 LLM 调用时注入
    ↓
心跳检查 → 触发主动消息
```

### 3.2 新增模块

```
backend/
├── services/
│   ├── emotion_service.py      # 情感状态管理
│   ├── world_service.py        # 世界状态管理
│   ├── heartbeat_service.py    # 心跳触发器
│   └── daily_seed_service.py   # 每日种子生成
├── models/
│   └── active.py               # 新增 EmotionState, WorldEvent 表
└── routers/
    ├── emotion.py              # 情感状态 API
    └── world.py                # 世界状态 API
```

### 3.3 前端新增

```
frontend/src/views/
├── Emotion.vue                 # 情感状态面板
└── World.vue                   # 世界状态面板（日程、事件）
```

## 四、关键差异（vs Hermes_Soul_patch）

| 维度 | Hermes_Soul_patch | hermes-active v0.2 |
|------|-------------------|---------------------|
| 存储 | 文件（EMOTION_STATE.md） | 数据库（active.db） |
| 触发 | 独立 heartbeat 进程 | APScheduler 集成 |
| 平台 | 单用户（CLI/Gateway） | Web 多用户 |
| 情感推断 | 辅助 LLM（post_llm_call） | 辅助 LLM（定时任务后） |
| 世界状态 | 文件（events.json） | 数据库（world_events 表） |
| UI | Slash commands | Web 管理界面 |

## 五、实施计划

### Phase 1: 情感状态（2天）
- [ ] 数据库表设计（emotion_states）
- [ ] EmotionService 实现
- [ ] 辅助 LLM 推断集成
- [ ] 情感状态注入到 LLM 上下文
- [ ] 前端情感状态面板

### Phase 2: 世界状态（2天）
- [ ] 数据库表设计（world_events）
- [ ] WorldService 实现（CRUD + 归档）
- [ ] 每日种子生成
- [ ] 到期事件触发
- [ ] 前端日程管理面板

### Phase 3: 智能触发（1天）
- [ ] HeartbeatService 实现
- [ ] 基于情感状态的触发逻辑
- [ ] 冷却机制 + 内容签名
- [ ] 与现有 APScheduler 集成

### Phase 4: 世界交互（1天）
- [ ] 用户消息分析
- [ ] 自动更新世界状态
- [ ] 环境事件记录

## 六、配置项

```yaml
# config.yaml 新增
companion:
  emotion:
    enabled: true
    inference_interval: 60  # 推断间隔（秒）
  heartbeat:
    enabled: true
    check_interval: 300
    arousal_threshold: 0.70
    arousal_cooldown: 3600
  world:
    enabled: true
    archive_days: 30  # 归档保留天数
  daily_seed:
    enabled: true
    anchors:
      - { start: "08:00", end: "08:30", title: "起床整理", kind: "self" }
      - { start: "12:30", end: "13:30", title: "午餐休息", kind: "self" }
      - { start: "18:30", end: "19:30", title: "晚餐", kind: "self" }
      - { start: "22:30", end: "23:00", title: "睡前整理", kind: "self" }
```
