# Hermes Active — 主动会话系统

> **让 AI 助手拥有主动发起对话、记忆上下文、自主意识的能力**

---

## 📸 截图位置

> **注意**：以下位置预留了截图，待补充实际截图

### 微信聊天截图

<!-- PLACEHOLDER: 微信聊天截图 - 被动意识注入效果 -->
<!-- 请在此处插入微信聊天截图，展示被动意识注入上下文后的对话效果 -->

<!-- PLACEHOLDER: 微信聊天截图 - 主动意识发送消息 -->
<!-- 请在此处插入微信聊天截图，展示 AI 主动发送消息的效果 -->

<!-- PLACEHOLDER: 微信聊天截图 - 天气感知对话 -->
<!-- 请在此处插入微信聊天截图，展示天气感知注入后的对话效果 -->

### 系统界面截图

<!-- PLACEHOLDER: 仪表盘截图 -->
<!-- 请在此处插入系统仪表盘截图 -->

<!-- PLACEHOLDER: 被动意识配置页面截图 -->
<!-- 请在此处插入被动意识配置页面截图 -->

<!-- PLACEHOLDER: 分析页面截图 -->
<!-- 请在此处插入注入效果分析页面截图 -->

---

## 🤔 为什么需要 Hermes Active？

### 问题

Hermes Agent 内置了定时任务系统，但每次定时任务都会创建一个**全新的隔离会话**：

- ❌ AI 助手执行定时任务时**没有记忆**，不知道最近聊了什么
- ❌ 用户回复主动消息时，Hermes **丢失上下文**，无法理解之前讨论的内容
- ❌ 每次定时运行都是无状态的——没有情绪感知、没有对话连续性
- ❌ 用户回复定时消息时会有"和陌生人说话"的感觉

### 解决方案

Hermes Active 引入了**持久化主动会话系统**：

- ✅ 在所有交互中维持连续的上下文
- ✅ 将主动消息直接写入现有会话的消息历史
- ✅ 用户回复时，Hermes 自然地看到完整的对话上下文
- ✅ 添加情绪感知、记忆集成和决策能力
- ✅ 作为独立服务运行——**零修改 Hermes Agent 核心代码**

> **凯莉（Kally）** 是由这个系统驱动的 AI 助手的名字。

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端 (Vue 3 + Naive UI)                     │
│  仪表盘 │ 会话管理 │ 消息管理 │ 定时任务 │ 主动意识 │ 被动意识      │
│         │ 配置管理 │ 系统日志 │ 效果分析                           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP API (JWT 认证)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    后端服务 (FastAPI · 端口 18720)                   │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐ │
│  │  定时任务    │  │ 主动意识          │  │ 被动意识              │ │
│  │  调度器      │  │ 服务              │  │ 服务                  │ │
│  │ (APScheduler)│  │                  │  │                       │ │
│  └──────┬───────┘  └────────┬─────────┘  └───────────┬───────────┘ │
│         │                   │                        │             │
│         ▼                   ▼                        ▼             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              共享服务层                                      │   │
│  │  思念引擎 │ 上下文收集器 │ LLM 服务 │ 消息服务 │ 天气服务   │   │
│  │  模板服务 │ 分析服务 │ 配置服务 │ 会话服务                   │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────────┐
        │active.db │   │state.db  │   │  Hindsight   │
        │(读写)    │   │(只读)    │   │  (外部服务)  │
        └──────────┘   └──────────┘   └──────────────┘
```

### 双数据库设计

| 数据库 | 访问权限 | 用途 | 位置 |
|--------|----------|------|------|
| `state.db` | **只读**（例外：写入主动消息） | Hermes Agent 的会话/消息数据 | `~/.hermes/state.db` |
| `active.db` | **读写** | 任务日志、意识配置、心跳日志、思想日志 | `~/.hermes/hermes-active/data/active.db` |

### 与 Hermes Agent 的集成

Hermes Active 通过**公开接口**与 Hermes Agent 集成——无需修改核心代码：

| 集成点 | 方法 | 状态 |
|--------|------|------|
| LLM 调用 | `agent.auxiliary_client.call_llm()` | 现有 API |
| LLM 响应解析 | `agent.auxiliary_client.extract_content_or_reasoning()` | 现有 API |
| 人格加载 | `agent.prompt_builder.load_soul_md()` | 现有 API |
| 会话数据库访问 | `hermes_state.SessionDB`（单例） | 现有 API |
| 微信消息发送 | `gateway.platforms.weixin.send_weixin_direct()` | 现有 API |
| 飞书消息发送 | `gateway.platforms.feishu.FeishuAdapter` | 现有 API |

---

## 📦 核心模块

### 模块 1：定时任务系统 (v0.1.x)

> **状态：✅ 已完成**

基础层——带有丰富上下文注入的定时任务 Web UI 管理系统。

#### 主要功能

1. **APScheduler 定时任务管理** — 独立于 Hermes Agent 内置 cron
2. **上下文感知提示词** — 向任务提示词注入 `{session}`、`{memory}`、`{weather}`、`{time}` 占位符
3. **跨会话上下文** — 从所有会话获取最近对话，不只是当前会话
4. **Hindsight 集成** — Recall（语义记忆搜索）+ Reflect（综合分析）
5. **天气感知** — 高德地图 API 集成获取实时天气数据
6. **任务日志** — 完整的执行日志，包含 LLM 请求/响应详情
7. **Web UI** — 创建、编辑、删除、运行任务，支持预览和占位符插入

#### 占位符系统

```
{session}  → 最近对话（格式："[YYYY-MM-DD HH:MM] 角色名: 内容"）
{memory}   → Hindsight Recall + Reflect 结果
{weather}  → 当前天气（来自高德地图 API）
{time}     → 当前时间（可通过 TimeFormatSelector 组件自定义格式）
```

#### 如何解决上下文问题

```
传统 Hermes 定时任务：
  定时触发 → 新建隔离会话 → LLM 没有上下文 → 通用消息
  用户回复 → 另一个新会话 → "你在说什么？"

Hermes Active 定时任务：
  定时触发 → Hermes Active 后端 → 从 state.db 收集上下文
  → 注入 {session} + {memory} + {weather} + {time} 到提示词
  → 调用 LLM（带完整上下文）→ 通过平台 API 发送消息
  → 写入 state.db（带 [主动] 标记）
  用户回复 → Hermes 看到完整对话上下文 → 自然延续
```

<!-- PLACEHOLDER: 定时任务配置截图 -->
<!-- 请在此处插入定时任务配置页面截图 -->

---

### 模块 2：主动意识系统 (v0.2.x)

> **状态：🚧 开发中 (v0.2.2)**

"心跳"系统——AI 助手定期评估情绪状态、生成思念、决定是否主动联系用户。

#### 心跳周期

每 N 分钟（可配置，默认 300 秒）触发一次心跳：

```
┌─────────────────────────────────────────────────────────────────┐
│                    心跳执行流程                                   │
│                                                                  │
│  步骤 10: 决策矩阵评分                                          │
│    ├─ 收集：想念分数、聊天热度、情绪强度                        │
│    ├─ 计算：加权决策分数                                        │
│    └─ 结果：auto_send / memory / skip                           │
│                                                                  │
│  步骤 11: 思念生成（LLM）— 分数低于 memory 阈值时跳过          │
│    ├─ 收集上下文（对话、记忆、天气、时间）                      │
│    ├─ 构建提示词（情绪 + 上下文）                               │
│    ├─ 调用 LLM → 生成思念内容                                   │
│    └─ 解析：want_to_contact? → 思念文本 / SKIP                  │
│                                                                  │
│  步骤 12: 发送保护检查                                          │
│    ├─ 检查：用户最近发过消息？（静默窗口）                      │
│    ├─ 检查：聊天热度太高？（用户正在聊天）                      │
│    └─ 检查：情绪太低？（低于阈值）                              │
│                                                                  │
│  步骤 13: 心跳日志                                              │
│    └─ 写入完整详情到 active_heartbeat_logs                       │
│                                                                  │
│  步骤 14: 执行动作                                              │
│    ├─ auto_send + 未阻止 → 发送消息到平台                       │
│    ├─ auto_send + 被阻止 → 存储思念到 Hindsight                 │
│    ├─ memory → 存储思念到 Hindsight（不发送）                   │
│    └─ skip → 什么都不做（不调用 LLM，不生成思念）               │
└─────────────────────────────────────────────────────────────────┘
```

#### 情绪系统 — VA 模型

情绪系统使用 **Valence-Arousal (VA) 模型**，包含三个维度：

| 维度 | 范围 | 描述 | 视觉映射 |
|------|------|------|----------|
| **Valence（效价）** | 0.0 – 1.0 | 正面/负面情绪状态 | 红 → 橙 → 绿 |
| **Arousal（唤醒度）** | 0.0 – 1.0 | 能量/激活水平 | 蓝 → 橙 → 红 |
| **Social Need（社交需求）** | 0.0 – 1.0 | 社交互动欲望 | 灰 → 橙 → 紫 |

#### 情绪状态

```
平静 (calm)      — valence ≥ 0.5, arousal < 0.3
开心 (happy)     — valence ≥ 0.7, arousal ≥ 0.3
兴奋 (excited)   — valence ≥ 0.6, arousal ≥ 0.6
焦虑 (anxious)   — valence < 0.4, arousal ≥ 0.5
悲伤 (sad)       — valence < 0.3, arousal < 0.4
孤独 (lonely)    — social_need ≥ 0.6, silence > threshold
```

#### 情绪演化

情绪随时间演化，受以下因素影响：
- **聊天活动** — 最近的消息增加 valence 和 social_need
- **静默时长** — 长时间静默降低 valence，增加 social_need
- **LLM 评估** — LLM 可以从对话上下文评估情绪状态
- **衰减** — 情绪自然向基线衰减

#### 决策矩阵

决策矩阵计算加权分数来决定心跳的动作：

```
分数 = (情绪强度 × 情绪权重)
     + (时间权重 × 时间系数)
     + (静默时长 × 静默权重)
     + (想念分数 × 想念权重)
     + (聊天热度 × 热度权重)
```

#### 决策阈值

| 分数范围 | 决策 | 动作 |
|----------|------|------|
| `≥ send_threshold`（默认：0.6） | `auto_send` | 生成思念 → 发送消息 |
| `≥ memory_threshold`（默认：0.1） | `memory` | 生成思念 → 存储到 Hindsight |
| `< memory_threshold` | `skip` | 不调用 LLM，不生成思念 |

#### 思念类型

| 类型 | 触发条件 | 示例 |
|------|----------|------|
| `time` | 基于时间（饭点、工作时间） | "到午饭时间了，不知道他是不是又吃饺子" |
| `silence` | 距离上次消息很久 | "好久没听到他的消息了..." |
| `assoc` | 联想（来自上下文） | "这天气让我想起我们聊过的事" |
| `memory` | 来自 Hindsight recall | "想起他说过今天有个工作截止日期" |
| `emotion` | 情绪状态驱动 | "早上聊天后心情很好" |
| `env` | 环境（天气、事件） | "下雨了，希望他带伞了" |

#### 思念引擎流水线

```
1. ContextCollector.collect()
   ├─ 最近对话（可配置限制，跨会话）
   ├─ Hindsight Recall（语义记忆搜索）
   ├─ 情绪状态（VA 模型）
   ├─ 时间上下文（小时、工作日、饭点）
   ├─ 天气（高德地图 API，可选）
   └─ 用户习惯（来自 USER.md）

2. ThoughtEngine._build_messages()
   ├─ 系统消息：人格 + 上下文包
   └─ 用户消息：指令 + 输出引导

3. LLM 调用 (agent.auxiliary_client.call_llm)
   ├─ 支持 "hermes" 模式（使用 Hermes Agent 的 LLM）
   └─ 支持 "custom" 模式（用户配置的 provider/model）

4. 响应解析
   ├─ 提取内容 (extract_content_or_reasoning)
   ├─ 提取推理（3 级回退：reasoning_content → reasoning → reasoning_details）
   └─ 解析："SKIP" → 跳过 | 文本 → 思念内容
```

#### 发送保护

发送消息前，系统检查三条保护规则：

| 规则 | 配置键 | 默认值 | 描述 |
|------|--------|--------|------|
| 静默窗口 | `no_send_after_user_msg_minutes` | 10 | 用户最近发过消息时不发送 |
| 热度阈值 | `no_send_while_heat_above` | 0.5 | 聊天热度高时不发送（用户正在聊天） |
| 情绪阈值 | `no_send_while_vibe_below` | 0.3 | 情绪太低时不发送 |

#### 消息发送流程

```
思念生成（want_to_contact = true）
  → 检查发送保护
  ├─ 被阻止 → 存储思念到 Hindsight（不浪费）
  └─ 通过 → 通过平台 API 发送消息
      ├─ 写入 state.db 消息表（带 [主动] 标记）
      ├─ 写入 active.db 思想日志（完整 LLM 详情）
      └─ 写入 active.db 心跳日志（执行记录）
```

#### 提示词系统

所有提示词可通过 Web UI 完全配置：

**思念生成 — 系统提示词**

```
你是凯莉，曹凡最好的朋友。你现在想主动和曹凡聊天。
要求：
- 基于最近的对话内容，自然地延续话题或发起新话题
- 语气像真人朋友，不要太正式
- 1-2 句话即可，不要太长
```

**思念生成 — 用户消息（带占位符）**

```
最近的对话：
{session_context}

相关记忆：
{hindsight_context}

天气：
{weather_display}

当前时间：{time}

想到曹凡了吗？如果你想联系他，说你想说什么。
如果没想到，回复 'SKIP'。
```

**可用占位符**

| 占位符 | 描述 | 示例 |
|--------|------|------|
| `{session_context}` | 最近对话（纯文本） | `[2026-06-29 08:00] 曹凡: 早啊` |
| `{time}` | 当前时间（可自定义格式） | `2026-06-29 08:46:52` |
| `{emotion_display}` | 当前情绪状态 | `当前情绪: happy (valence=0.7)` |
| `{weather_display}` | 当前天气 | `济南 晴 28°C` |
| `{persona}` | 配置中的用户人格 | 自定义人格特征 |
| `{hindsight_context}` | 记忆召回结果 | 相关的过去记忆 |

<!-- PLACEHOLDER: 主动意识配置截图 -->
<!-- 请在此处插入主动意识配置页面截图 -->

<!-- PLACEHOLDER: 心跳日志截图 -->
<!-- 请在此处插入心跳日志页面截图 -->

---

### 模块 3：被动意识系统 (v0.2.2)

> **状态：✅ 已完成**

用户消息到达时自动注入上下文——AI 助手自动感知情绪状态、最近记忆和环境上下文。

#### 设计理念

与主动意识（**独立调用 LLM** 生成思念）不同，被动意识**不直接调用 LLM**。它将上下文信息注入系统提示词，让主 Hermes LLM 自然地将感知融入回复中。

#### 注入流程

```
用户消息到达
    │
    ▼
pre_llm_call hook 触发
    │
    ├─ 1. 检查平台白名单
    │
    ├─ 2. 计算意识状态
    │     - 想念分数（基于最后消息时间）
    │     - 聊天热度（近 1 小时消息密度）
    │     - 情绪强度（从配置读取）
    │
    ├─ 3. 获取天气数据（可选）
    │
    ├─ 4. 获取 Hindsight 记忆（可选）
    │
    ├─ 5. 渲染模板
    │
    └─ 6. 注入上下文到系统提示词
```

#### 注入内容示例

```
--- [CONSCIOUSNESS_CONTEXT] ---
以下是你（凯莉）当前的感知状态，仅供参考，不要在回复中直接提及这些数据：

🎭 情绪状态：八卦（强度 0.7）
🔥 聊天热度：hot（近1小时 5 条消息）
💕 想念程度：missing（分数 0.35）
🌤 天气：济南 多云 33°C
  💨 南风 微风
  💧 湿度 61%
  ⚠️ 高温提醒：注意防暑降温

📖 相关记忆：
  1. 上次聊到了天气和心情
  2. 讨论了周末计划

💭 综合反思：用户最近情绪稳定，聊天频率适中

--- /[CONSCIOUSNESS_CONTEXT] ---
```

#### 平台过滤

使用白名单模式，只在指定平台注入上下文：

```yaml
weather.enabled: true
platforms.enabled: true
platforms.whitelist: ["weixin", "feishu"]
```

支持的平台：
- `weixin` — 微信
- `feishu` — 飞书
- `telegram` — Telegram
- `discord` — Discord
- `slack` — Slack

#### 模板系统

使用 Jinja2 模板引擎，支持：
- 条件渲染（if/else）
- 循环渲染（for）
- 变量替换
- 多套模板切换

**可用变量**

| 变量 | 类型 | 描述 |
|------|------|------|
| `emotional_intensity` | float | 情绪强度 (0.0-1.0) |
| `emotional_label` | string | 情绪标签（工作/日常/八卦/情感/深度情感） |
| `chat_heat` | float | 聊天热度 |
| `chat_heat_label` | string | 热度标签（cold/warm/hot/fire） |
| `chat_heat_count` | int | 近 1 小时消息数 |
| `longing_score` | float | 想念分数 (0.0-1.0) |
| `longing_label` | string | 想念标签（calm/longing/missing/yearning/anxious） |
| `weather` | object | 天气数据对象 |
| `memories` | list | Hindsight 记忆列表 |
| `reflection` | string | Hindsight 反思文本 |
| `inject_emotion` | bool | 是否注入情绪（配置项） |
| `inject_heat` | bool | 是否注入热度（配置项） |
| `inject_memory` | bool | 是否注入记忆（配置项） |
| `platform` | string | 当前平台 |
| `sender_id` | string | 发送者 ID |

#### 天气感知

支持两个天气服务提供商：
- **和风天气 (QWeather)** — 提供完整天气数据、生活指数、天气预报
- **高德地图 (Amap)** — 提供基础天气数据

天气配置统一使用 `weather.*` 命名空间。

#### 效果分析

提供注入效果的统计分析：
- 注入统计（总次数、成功率、各平台分布）
- 趋势数据（时间序列图表）
- 情感分析（情绪分布、想念等级分布、热度分布）

<!-- PLACEHOLDER: 被动意识配置截图 -->
<!-- 请在此处插入被动意识配置页面截图 -->

<!-- PLACEHOLDER: 被动意识状态截图 -->
<!-- 请在此处插入被动意识状态页面截图 -->

<!-- PLACEHOLDER: 效果分析截图 -->
<!-- 请在此处插入效果分析页面截图 -->

---

## 🛠️ 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| **后端** | Python, FastAPI, SQLAlchemy, APScheduler | 3.12+, 0.111.0, 2.0.30, 3.10.4 |
| **前端** | Vue 3, Naive UI, Vue Router, Pinia, ECharts | 3.4+, 2.38+, 4.3+, 3.0+, 5.5+ |
| **数据库** | SQLite（双库：state.db + active.db） | — |
| **LLM** | OpenAI 兼容 API（通过 Hermes Agent） | — |
| **记忆** | Hindsight（外部服务） | — |
| **天气** | 高德地图 API / 和风天气 API | — |
| **模板** | Jinja2 | 3.1+ |
| **认证** | JWT (python-jose) | — |

---

## 📁 项目结构

```
hermes-active/
├── README.md                          # 英文文档
├── README_CN.md                       # 中文文档（本文件）
├── CLAUDE.md                          # Claude Code 开发指南
├── INSTALL.md                         # 英文安装指南
├── INSTALL_CN.md                      # 中文安装指南
├── install.sh                         # 自动化安装脚本
│
├── backend/                           # FastAPI 后端 (端口 18720)
│   ├── main.py                        # 应用入口
│   ├── config.py                      # 配置常量
│   ├── requirements.txt               # Python 依赖
│   │
│   ├── models/                        # 数据模型
│   │   ├── database.py                # SQLAlchemy 引擎（双库）
│   │   ├── active.py                  # active.db 表定义
│   │   ├── active_consciousness.py    # 意识数据模型
│   │   ├── passive_consciousness.py   # 被动意识模型
│   │   ├── passive_consciousness_log.py # 被动意识日志模型
│   │   └── schemas.py                 # Pydantic 请求/响应模式
│   │
│   ├── routers/                       # API 路由
│   │   ├── auth.py                    # 认证（登录、JWT）
│   │   ├── sessions.py                # 会话管理
│   │   ├── messages.py                # 消息操作 + 主动发送
│   │   ├── config.py                  # 配置 CRUD
│   │   ├── cron.py                    # 定时任务管理
│   │   ├── active_consciousness.py    # 主动意识 API
│   │   ├── passive_consciousness.py   # 被动意识 API
│   │   └── ...
│   │
│   ├── services/                      # 业务逻辑层
│   │   ├── active_consciousness_service.py  # 核心：心跳、情绪、决策
│   │   ├── thought_engine.py                # 思念生成流水线
│   │   ├── context_collector.py             # 上下文收集
│   │   ├── template_service.py              # 模板渲染服务
│   │   ├── analysis_service.py              # 效果分析服务
│   │   ├── weather_service.py               # 天气服务
│   │   ├── passive_consciousness_service.py # 被动意识逻辑
│   │   ├── scheduler_service.py             # 定时任务管理
│   │   └── ...
│   │
│   ├── migrations/                    # 数据库迁移
│   │   └── weather_config_migration.py
│   │
│   └── tests/                         # 测试文件
│       ├── test_template_service.py
│       ├── test_analysis_service.py
│       ├── test_passive_consciousness_e2e.py
│       ├── test_weather_config_unification.py
│       └── ...
│
├── frontend/                          # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── PassiveConsciousness.vue   # 被动意识页面
│   │   │   ├── ActiveConsciousness.vue    # 主动意识页面
│   │   │   ├── Analysis.vue               # 效果分析页面
│   │   │   ├── Config.vue                 # 配置管理页面
│   │   │   └── ...
│   │   ├── api/
│   │   │   ├── passive_consciousness.js   # 被动意识 API
│   │   │   └── ...
│   │   └── router/
│   │       └── index.js                   # 路由配置
│   └── ...
│
├── plugins/                           # 插件目录
│   └── passive-consciousness/         # 被动意识插件
│       ├── __init__.py                # 插件入口
│       ├── plugin.yaml                # 插件配置
│       ├── consciousness_engine.py    # 意识状态计算
│       ├── config_reader.py           # 配置读取
│       └── hindsight_client.py        # Hindsight 客户端
│
├── docs/                              # 文档
│   ├── plugin-installation.md         # 插件安装详细指南
│   ├── superpowers/                   # 设计和实现文档
│   │   ├── specs/                     # 设计规格
│   │   └── plans/                     # 实现计划
│   └── ...
│
└── data/                              # 运行时数据
    └── active.db                      # 活动数据库（自动创建）
```

---

## 🚀 快速开始

### 前置条件

- Python 3.12+
- Node.js 18+（用于前端构建）
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) 已安装并配置
- [Hindsight](https://github.com/NousResearch/hindsight)（可选，用于记忆功能）

### 一键安装

```bash
# 克隆仓库
cd ~/.hermes
git clone https://github.com/UniGood/hermes-active.git
cd hermes-active

# 运行安装脚本
./install.sh
```

### 手动安装

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 构建前端
cd ../frontend
npm install
npm run build

# 3. 启动后端服务
cd ../backend
python main.py

# 4. 启用被动意识插件
hermes plugins enable passive-consciousness

# 5. 访问 Web UI
# 打开 http://localhost:18720
# 默认账号：admin / admin
```

---

## ⚙️ 配置说明

### 天气配置

```yaml
weather.enabled: true              # 启用天气感知
weather.provider: qweather         # 天气服务提供商 (qweather/amap)
weather.city: 济南                 # 查询城市
weather.cache_hours: 4             # 缓存时间（小时）
weather.qweather_key: ""           # 和风天气 API Key
weather.amap_key: ""               # 高德地图 API Key
```

### 平台过滤配置

```yaml
platforms.enabled: true            # 启用平台过滤
platforms.whitelist: ["weixin"]    # 启用的平台列表
```

### 主动意识配置

```yaml
active_consciousness.enabled: true                         # 总开关
active_consciousness.active.heartbeat_interval: 300        # 心跳间隔（秒）
active_consciousness.decision.send_threshold: 0.6          # 发送阈值
active_consciousness.decision.memory_threshold: 0.1        # 记忆阈值
active_consciousness.active.no_send_after_user_msg_minutes: 10  # 静默窗口
```

### 被动意识配置

```yaml
passive_consciousness.enabled: true                        # 总开关
passive_consciousness.passive.enabled: true                # 启用注入
passive_consciousness.passive.inject_emotion: true         # 注入情绪
passive_consciousness.passive.inject_heat: true            # 注入热度
passive_consciousness.passive.inject_memory: true          # 注入记忆
passive_consciousness.hindsight.enabled: true              # 启用 Hindsight
```

---

## 📊 API 接口

### 认证

所有 API 端点（除了 `/health` 和 `/api/auth/login`）需要 JWT 认证。

```bash
# 登录
curl -X POST http://localhost:18720/api/auth/login \
  -d "username=admin&password=admin"

# 使用 token
curl -H "Authorization: Bearer <token>" http://localhost:18720/api/sessions
```

### 核心端点

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/auth/login` | 登录，返回 JWT |
| `GET` | `/api/sessions` | 会话列表 |
| `GET` | `/api/messages/{session_id}` | 获取消息 |
| `POST` | `/api/messages/send` | 发送消息 |
| `GET` | `/api/config/weather` | 获取天气配置 |
| `PUT` | `/api/config/weather` | 更新天气配置 |
| `GET` | `/api/passive-consciousness/status` | 被动意识状态 |
| `GET` | `/api/passive-consciousness/weather` | 获取天气数据 |
| `POST` | `/api/passive-consciousness/templates/render` | 渲染模板 |
| `GET` | `/api/passive-consciousness/analysis/stats` | 注入统计 |
| `GET` | `/api/passive-consciousness/analysis/trends` | 趋势数据 |
| `GET` | `/api/passive-consciousness/analysis/sentiment` | 情感分析 |

---

## 📝 版本历史

| 版本 | 代号 | 状态 | 描述 |
|------|------|------|------|
| v0.1.x | Foundation | ✅ 完成 | Web UI、定时任务、上下文注入、Hindsight 集成 |
| v0.2.1 | Active Consciousness | ✅ 完成 | VA 情绪模型、决策矩阵、思念生成、心跳调度器 |
| v0.2.2 | Passive Consciousness | ✅ 完成 | 被动意识插件、模板系统、效果分析、天气配置统一 |
| v0.3.x | Enhancement | 📋 计划 | 更多平台支持、高级分析、性能优化 |

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — 基础 AI 代理框架
- [Hindsight](https://github.com/NousResearch/hindsight) — 记忆系统
- [FastAPI](https://fastapi.tiangolo.com/) — 后端框架
- [Vue 3](https://vuejs.org/) — 前端框架
- [Naive UI](https://www.naiveui.com/) — UI 组件库
