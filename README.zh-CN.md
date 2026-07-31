<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>


<p align="center">
  <img src="docs/images/zh-hero-banner.jpg" width="800" alt="Hermes Active — 让 AI 助手拥有主动意识">
</p>

<h1 align="center">Hermes Active</h1>

<p align="center">
  <strong><a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a> 主动意识系统</strong>
</p>

<p align="center">
  给你的 AI 助手一颗心跳 —— 让它感知时间流逝、会想念你、能独自思考，<br>
  并带着对你们每一场对话的完整记忆，主动开口。
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/vue-3-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue">
  <img src="https://img.shields.io/badge/fastapi-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/许可证-MIT-yellow" alt="许可证">
</p>

---

## 目录

- [为什么需要 Hermes Active？](#为什么需要-hermes-active)
- [界面截图](#界面截图)
- [系统架构](#系统架构)
- [核心系统](#核心系统)
  - [主动意识 —— 心跳](#主动意识--心跳)
  - [被动意识 —— 上下文注入](#被动意识--上下文注入)
  - [自由意识 —— 内在沉思](#自由意识--内在沉思)
  - [定时任务](#定时任务)
  - [Web 控制台](#web-控制台)
- [外部集成](#外部集成)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 概览](#api-概览)
- [文档](#文档)
- [许可证](#许可证)

---

## 为什么需要 Hermes Active？


<p align="center">
  <img src="docs/images/zh-problem-statement.jpg" width="800" alt="无状态 Cron vs 持久化意识">
</p>

传统 AI 代理的主动消息功能都有同一个缺陷：**每个定时任务都会创建一个全新的、隔离的会话**。

- ❌ 助手主动联系你时，**完全不记得**最近聊过什么
- ❌ 你一回复，上下文就丢了 —— "不好意思，我们刚才在说什么？"
- ❌ 每次运行都是无状态的 —— 没有情绪、没有连续性、没有时间感
- ❌ 回复一条主动消息，感觉像在跟陌生人说话

Hermes Active 通过在 Hermes Agent 旁运行一套**持久化意识层**来解决这个问题：

- ✅ 主动消息**直接写回当前会话** —— 用户的回复天然落在完整上下文里
- ✅ **心跳循环**让助手拥有随时间和互动不断演化的情绪状态
- ✅ 每次思考和每次回复前都会召回**长期记忆**（Hindsight）
- ✅ **内在沉思循环**让助手自由思考，并将思维压缩沉淀为自己的"意识积淀"
- ✅ 作为独立服务运行 —— **零修改 Hermes Agent 核心**（仅一个可选的会话同步小补丁）

> 系统内置的参考人设是**凯莉（Kally）** —— 所有提示词、标记和默认值都可以在 Web 界面上完全自定义。

---

## 界面截图

> 📸 截图占位 —— 从运行中的 Web 控制台（`http://localhost:18720`）截取各页面，存入 `docs/screenshots/`，然后将下方占位块替换为 `<img>` 标签。

<table>
  <tr>
    <td align="center">
      <b>仪表盘</b><br><br>
      <code>docs/screenshots/dashboard.png</code><br><br>
      <i>系统总览：会话、消息、任务统计、意识状态一屏尽览。</i>
    </td>
    <td align="center">
      <b>主动意识</b><br><br>
      <code>docs/screenshots/active-consciousness.png</code><br><br>
      <i>实时 VA 情绪仪表盘、心跳日志流、含完整 LLM 推理过程的念头日志。</i>
    </td>
  </tr>
  <tr>
    <td align="center">
      <b>被动意识</b><br><br>
      <code>docs/screenshots/passive-consciousness.png</code><br><br>
      <i>注入开关、带实时预览的 Jinja2 模板编辑器、每个信号的独立测试按钮。</i>
    </td>
    <td align="center">
      <b>自由意识</b><br><br>
      <code>docs/screenshots/free-consciousness.png</code><br><br>
      <i>沉思轮次时间线、思考链查看器、意识积淀浏览。</i>
    </td>
  </tr>
  <tr>
    <td align="center">
      <b>定时任务</b><br><br>
      <code>docs/screenshots/cron-jobs.png</code><br><br>
      <i>可视化 Cron 编辑器、占位符插入、提示词预览、执行日志。</i>
    </td>
    <td align="center">
      <b>注入分析</b><br><br>
      <code>docs/screenshots/analysis.png</code><br><br>
      <i>ECharts 图表：注入趋势、情绪/想念/热度分布。</i>
    </td>
  </tr>
</table>

---

## 系统架构


<p align="center">
  <img src="docs/images/zh-architecture.jpg" width="800" alt="Hermes Active 系统架构">
</p>

```mermaid
graph TB
    subgraph Console["Web 控制台 — Vue 3 + Naive UI"]
        UI[仪表盘 · 会话 · 消息<br/>定时任务 · 主动/被动/自由意识 · 注入分析]
    end

    subgraph Backend["Hermes Active 后端 — FastAPI :18720"]
        direction TB
        CRON[任务调度器<br/>APScheduler]
        HB[心跳循环<br/>主动意识]
        FC[沉思循环<br/>自由意识]
        PC[上下文构建器<br/>被动意识]
        SHARED[共享服务层<br/>念头引擎 · 上下文收集器 · LLM<br/>消息 · 天气 · Hindsight · 模板]
        CRON --> SHARED
        HB --> SHARED
        FC --> SHARED
        PC --> SHARED
    end

    subgraph Hermes["Hermes Agent — 核心零修改"]
        GW[Gateway<br/>微信 · 飞书]
        HOOK[passive-consciousness 插件<br/>pre_llm_call 钩子]
        LLM[call_llm · SOUL.md · SessionDB]
    end

    ADB[(active.db<br/>读写)]
    SDB[(state.db<br/>只读 + 主动消息写回)]
    HS[[Hindsight<br/>长期记忆]]
    WX[[天气 API<br/>高德 · 和风]]

    UI -->|JWT REST| Backend
    HOOK -->|HTTP：渲染上下文| PC
    SHARED -->|公开 API| LLM
    SHARED -->|发送主动消息| GW
    Backend --> ADB
    Backend --> SDB
    SHARED --> HS
    SHARED --> WX
```

### 双数据库设计

| 数据库 | 访问权限 | 内容 | 位置 |
|--------|---------|------|------|
| `state.db` | **只读**（唯一例外：写回主动消息） | Hermes Agent 的会话与消息 | `~/.hermes/state.db` |
| `active.db` | **读写** | 用户、配置、定时任务、任务日志、心跳/念头/沉思/注入日志 | `data/active.db` |

Hermes Active 从不写入 Hermes 的配置，也从不改动历史对话 —— 它只**追加**自己发出的主动消息，并加上可配置的标记（如 `[凯莉 14:30]: …`），让主代理自然地将它们视为自己说过的话。

---

## 核心系统


<p align="center">
  <img src="docs/images/zh-four-systems.jpg" width="800" alt="四大核心系统">
</p>

### 主动意识 —— 心跳

调度器每隔 N 秒（默认 600）触发一次完整的 感知 → 感受 → 决策 → 行动 循环。没有任何预设脚本：情绪状态、决策分数和消息内容全部由实时上下文涌现。

```mermaid
flowchart TD
    A[⏱ 心跳触发] --> B[读取持久化的情绪状态]
    B --> C[按流逝时间演化情绪<br/>唤醒度衰减 · 社交需求增长 · 效价回归中性]
    C --> D[收集上下文包<br/>对话 · 记忆 · 天气 · 时间 · 用户习惯]
    D --> E[LLM 情绪评估<br/>阅读最近对话，输出 VA 值]
    E --> F[动态权重合并<br/>按置信度融合演化值与评估值]
    F --> G[决策矩阵<br/>分数 = 情绪强度 × 时间适宜度 × 静默因子 × 频率限制]
    G --> H{分数与阈值比较}
    H -->|≥ 发送阈值| I[念头引擎生成念头]
    H -->|≥ 记忆阈值| J[念头引擎生成念头]
    H -->|低于阈值| K[跳过 — 不调 LLM，零成本]
    I --> L{发送保护}
    L -->|通过| M[经微信/飞书发送<br/>带主动标记写回 state.db]
    L -->|拦截| N[念头存入 Hindsight<br/>不浪费任何想法]
    J --> N
    M --> O[念头存入 Hindsight<br/>写入心跳 + 念头日志]
    N --> O
```

#### 情绪系统 —— 效价/唤醒度 + 社交需求

助手的心情是一个持久化的三维状态：

| 维度 | 范围 | 含义 | 自然漂移 |
|------|------|------|---------|
| **效价（Valence）** | 0.0 – 1.0 | 愉悦 ↔ 不悦 | 向中性（0.5）回归 |
| **唤醒度（Arousal）** | 0.0 – 1.0 | 激活 ↔ 平静 | 随时间衰减 |
| **社交需求（Social Need）** | 0.0 – 1.0 | 想互动的程度 | 随静默增长 |

由这三个值推导出主导情绪标签（`calm`、`happy`、`content`、`longing`、`yearning`、`missing`、`anxious`、`bored`、`concerned`）。

每次心跳都会融合**两个独立来源**的情绪估计：

1. **确定性演化** —— 将上一次状态按流逝时间向前推演（速率可配置：`decay_rate`、`social_need_growth`、`valence_regression`）
2. **LLM 评估** —— 专用提示词让 LLM 阅读最近对话，输出新的 VA 值

融合权重不是固定的：**置信度评分**（取值合理性 + 与演化值的一致性）会让混合比例在 0.7/0.3 到 0.3/0.7 之间动态移动。如果 LLM 返回无效值（全零），演化值会静默接管。

#### 决策矩阵

发送是一个评分决策，而不是定时器：

```
score = 情绪强度 × 时间适宜度 × 静默因子 × 频率限制
```

| 因子 | 计算方式 |
|------|---------|
| `情绪强度` | 合并后 VA 状态的综合强度 |
| `时间适宜度` | 时段表 —— 早晚窗口 1.0，工作时间 0.7–0.9，深夜 0.3 |
| `静默因子` | 用户最后一条消息 30 分钟内为 0.6 → 静默 6 小时后为 1.0 |
| `频率限制` | 硬门控：达到每小时发送上限后归 0 |

| 分数 | 决策 | 效果 |
|------|------|------|
| `≥ send_threshold`（默认 0.35） | `auto_send` | 生成念头 → 保护检查 → 发送 |
| `≥ memory_threshold`（默认 0.05） | `memory` | 生成念头 → 仅存入 Hindsight |
| `< memory_threshold` | `skip` | 心跳结束，不调用任何 LLM |

#### 念头引擎

念头由专用管道生成（`ContextCollector → ThoughtEngine → LLM → 解析器`）：

- **上下文包** —— 结构化对话（跨会话、按平台、过滤工具消息）、Hindsight 召回结果、情绪状态、时间上下文（小时/工作日/用餐时间）、天气、来自 `USER.md` 的用户习惯
- **完全模板化的提示词** —— system 和 user 提示词存在数据库中、可在界面编辑，支持占位符：`{session_context}`、`{hindsight_context}`、`{weather_display}`、`{emotion_display}`、`{time}`、`{persona}`
- **SKIP 协议** —— 当 LLM 觉得没什么值得说的，可以回复 `SKIP`；该次心跳随即不存也不发
- **推理过程捕获** —— 思维链通过三层回退提取（`reasoning_content → reasoning → reasoning_details`），展示在念头日志里
- **念头分类** —— 每个念头被归类（`memory`、`env`、`emotion`、`silence`、`time`、`assoc`），并带标签存入 Hindsight（`active_consciousness`、主导情绪、`high_emotion`、`user_related`）

#### 发送保护

三道独立守卫在念头生成**之后**、实际发送**之前**运行 —— 被拦截的念头会转为记忆而不是被丢弃：

| 守卫 | 配置项 | 默认值 |
|------|--------|--------|
| 静默窗口 —— 用户刚发过消息 | `active.no_send_after_user_msg_minutes` | 5 分钟 |
| 热度守卫 —— 用户正在热聊 | `active.no_send_while_heat_above` | 1.0 条/小时 |
| 情绪守卫 —— 情绪强度过低 | `active.no_send_while_vibe_below` | 0.15 |
| 发送冷却 | `active.cooldown_minutes` | 30 分钟 |

#### 分层 LLM 配置

三个独立的 LLM 槽位，逐级回退：

```
thought_llm（念头） → emotion_llm（情绪） → llm（通用）
```

每个槽位都支持 `hermes` 模式（复用 Hermes Agent 自带的 `call_llm`，无需额外密钥）或 `custom` 模式（任意 OpenAI 兼容的 provider/model/key/base_url），并可在界面上逐槽位测试连通性。

#### 可观测性

每次心跳、每个念头都会带着**完整的详情负载**持久化 —— 发出的提示词、LLM 原始响应、推理过程、召回结果、决策输入、保护裁决 —— 全部可以在 Web 界面中查看。每天凌晨 3 点的清理任务会剪除 30 天前的日志。

---

### 被动意识 —— 上下文注入

主动意识负责"行动"，被动意识负责"感知"。每当用户发来消息，一个 Hermes 插件就会组装一份实时的"心境快照"并注入提示词 —— 让回复自然地体现出：距离上次对话过了多久、当前聊天氛围如何、助手心里在想什么、外面天气怎么样。**用户消息这一轮不会额外调用 LLM。**

```mermaid
sequenceDiagram
    participant U as 用户
    participant G as Hermes Gateway
    participant P as passive-consciousness 插件
    participant B as Hermes Active 后端
    participant L as LLM

    U->>G: 发送消息
    G->>P: pre_llm_call 钩子
    P->>B: HTTP — 请求意识上下文
    B->>B: 想念分数 · 聊天热度 · 情绪强度<br/>天气 · Hindsight 召回 + 反思
    B->>B: 渲染当前激活的 Jinja2 模板
    B-->>P: [CONSCIOUSNESS_CONTEXT] 上下文块
    P-->>G: 注入系统提示词
    G->>L: 用户消息 + 意识上下文
    L-->>U: 带有上下文感知的回复
```

#### 注入的信号

| 信号 | 来源 | 计算方式 |
|------|------|---------|
| 💕 想念程度 | `state.db` | 距用户最后一条消息的分钟数 ÷ 300，封顶 1.0 —— 从 `calm` 到 `anxious` 五个等级 |
| 🔥 聊天热度 | `state.db` | 最近一小时的用户消息数 —— `cold / warm / hot / fire` |
| 🎭 情绪强度 | `active.db` | 由主动意识心跳写入 —— `工作 / 日常 / 八卦 / 情感 / 深度情感` |
| 🌤 天气 | 高德 / 和风 | 统一的 `weather.*` 配置，带缓存，含高温/低温提醒 |
| 📖 相关记忆 | Hindsight Recall | 对长期记忆的语义搜索 |
| 💭 综合反思 | Hindsight Reflect | 对当前状况的综合分析 |

#### Jinja2 模板系统

注入的内容块由**用户自行管理的 Jinja2 模板**渲染 —— 可以创建多套模板、切换激活模板、用模拟数据实时预览，并在界面中浏览完整的变量目录。条件区块（`{% if inject_emotion %}`）让一套模板适配多种配置。内容块包裹在可配置的标记里（默认 `[CONSCIOUSNESS_CONTEXT]`），让主代理知道该如何对待它。

#### 平台过滤与效果分析

- **平台白名单** —— 注入只在启用的平台上运行（例如仅微信）
- **注入日志** —— 每次注入（成功/跳过/错误）都会持久化，记录上下文长度、各项分数和模板 ID
- **分析仪表盘** —— 成功率、小时/日/周趋势、情绪与想念与热度分布、关联统计（如高情绪 × 高热度），ECharts 渲染
- **逐信号测试端点** —— 管道的每个环节（想念、热度、情绪、天气、召回、反思、完整拼装）在界面上都有一键测试按钮

> 插件位于 `~/.hermes/plugins/passive-consciousness/` —— 安装方式见 [docs/plugin-installation.md](docs/plugin-installation.md)。

---

### 自由意识 —— 内在沉思

在心跳和用户消息之间，助手可以只是……思考。自由意识是一个定时触发的沉思循环：没有任务、没有等待中的用户、没有预期输出 —— 一个让助手延续自己思绪的内在空间。

```mermaid
flowchart LR
    A[调度器触发<br/>每 N 分钟] --> B[组装思考链]
    B --> C{实时上下文？}
    C -->|启用| D[+ 当前时间<br/>+ 情绪状态<br/>+ 最近对话]
    C -->|禁用| E[纯思考链]
    D --> F[LLM 沉思]
    E --> F
    F --> G[解析结构化输出<br/>thinking · summary · discovery]
    G --> H[写入沉思日志]
    G --> I{有新发现？}
    I -->|可选| J[存入 Hindsight]
    H --> K{到达压缩周期？}
    K -->|每 10 个远期轮次| L[LLM 将旧轮次<br/>压缩为意识积淀]
```

#### 四层记忆模型

思考链通过按时间分层，让无限累积的沉思保持在可负担的成本内：

| 层 | 内容 | 成本 |
|----|------|------|
| **意识积淀** | LLM 将所有远期轮次压缩成的连贯叙述，每 10 轮刷新一次 | 总共约 300 字 |
| **近期轮次**（默认 3 轮） | 完整的思考原文 | 高 |
| **中期轮次**（默认 17 轮） | 一句话摘要 | 低 |
| **远期轮次** | 仅保留关键发现 | 极低 |

最终效果：助手始终能看到*自己曾得出的一切结论*（积淀）、*最近在思考什么*（原文）、以及*中间的重点*（摘要与发现）—— 一条无限延续的内在叙事，却不会撑爆上下文窗口。

所有沉思日志 —— 包括发出的完整提示词、原始响应、推理过程和 token 估算 —— 都可以在界面中浏览。

---

### 定时任务

基座层：带上下文注入的 cron 风格任务，完全在 Web 界面中管理 —— 独立于 Hermes Agent 内置的 cron。

```mermaid
flowchart LR
    A[Cron 触发] --> B[解析会话<br/>带回退与自动重置]
    B --> C[收集上下文]
    C --> D[将占位符渲染<br/>进提示词模板]
    D --> E[LLM 生成<br/>+ 可选 SOUL.md 人设]
    E --> F[经平台 API 发送]
    F --> G[带主动标记<br/>写回 state.db]
    G --> H[写入完整任务日志]
```

- **占位符系统** —— `{session}`（最近的跨会话对话）、`{memory}`（Hindsight 召回 + 反思）、`{weather}`（实时天气）、`{time}`（通过选择器组件自定义 strftime 格式）
- **提示词内联上下文声明** —— 在提示词中直接声明该任务需要的上下文，解析器会在渲染前提取
- **会话回退** —— 当网关内存中的会话消失时，任务会自动从 `state.db` 解析（或重置）活跃会话
- **人设注入** —— 可选将 Hermes 的 `SOUL.md` 拼接到 system 提示词
- **完整日志** —— 每次运行都会保存渲染后的提示词、LLM 请求/响应、发送结果和耗时
- **多平台** —— 通过 Hermes 自己的平台适配器发送微信和飞书消息

---

### Web 控制台

一个完整的管理界面（Vue 3 + Naive UI + Pinia + ECharts），由后端直接托管 —— 无需单独的 Web 服务器：

| 页面 | 功能 |
|------|------|
| **仪表盘** | 会话/消息/任务统计，系统健康状况一屏尽览 |
| **会话 / 消息** | 浏览 `state.db` 中的全部会话与消息，搜索、删除、手动发送 |
| **主动意识** | 实时情绪仪表盘、含完整 LLM 详情的心跳与念头日志、所有阈值和提示词可编辑 |
| **被动意识** | 注入开关、带实时预览的模板增删改查、平台白名单、逐信号测试按钮 |
| **自由意识** | 沉思轮次、思考链查看器、积淀浏览、间隔与提示词配置 |
| **定时任务 / 任务日志** | 可视化 cron 编辑器、占位符插入、立即运行、执行历史 |
| **注入分析** | 趋势 / 分布 / 关联图表的注入效果分析 |
| **配置 / 系统日志** | 所有配置项集中管理，实时后端日志查看器 |

认证基于 JWT（默认 `admin` / `admin` —— 首次登录后请立即修改），前端有路由守卫，每个 API 都有中间件校验。

---

## 外部集成

Hermes Active 仅通过**公开接口**与 Hermes Agent 集成：

| 集成点 | 接口 | 用途 |
|--------|------|------|
| LLM 调用 | `agent.auxiliary_client.call_llm()` | 念头 / 情绪 / 沉思生成 |
| 响应解析 | `extract_content_or_reasoning()` | 内容 + 推理过程提取 |
| 人设 | `agent.prompt_builder.load_soul_md()` | 加载 `SOUL.md` |
| 会话数据 | `hermes_state.SessionDB` | 读取会话与消息、追加主动消息 |
| 微信发送 | `gateway.platforms.weixin.send_weixin_direct()` | 主动消息投递 |
| 飞书发送 | `gateway.platforms.feishu.FeishuAdapter` | 主动消息投递 |
| 会话同步 | `gateway/extensions/session_fallback.py` | ⚠️ 小补丁 —— 当 `state.db` 被外部追加消息时保持网关内存同步 |

外部服务：

- **[Hindsight](https://github.com/NousResearch/hindsight)** —— 长期记忆：`Recall`（语义搜索）、`Reflect`（综合分析）、`Retain`（念头存储）。可选；没有它系统也能优雅降级运行。
- **天气** —— 高德与和风两个提供商统一在一套 `weather.*` 配置之下，带结果缓存和变化阈值检测。

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12+ · FastAPI · SQLAlchemy 2 · APScheduler · Jinja2 |
| 前端 | Vue 3 · Naive UI · Vue Router · Pinia · ECharts · Vite |
| 存储 | SQLite —— 双数据库（`state.db` 只读 / `active.db` 读写） |
| LLM | 任意 OpenAI 兼容 API，或复用 Hermes Agent 自己的客户端 |
| 记忆 | Hindsight（Recall / Reflect / Retain） |
| 天气 | 高德 · 和风 |
| 认证 | JWT（python-jose）· bcrypt |

---

## 项目结构

```
hermes-active/
├── backend/                        # FastAPI 后端（端口 18720）
│   ├── main.py                     # 入口，生命周期中启动全部调度器
│   ├── config.py                   # 服务常量
│   ├── models/                     # SQLAlchemy 表 + Pydantic 模型
│   │   ├── database.py             # 双引擎设置（state.db / active.db）
│   │   ├── active.py               # 用户、配置、任务/心跳/念头/沉思日志
│   │   └── *_consciousness.py      # 意识领域模型
│   ├── routers/                    # REST API 层
│   │   ├── auth.py · sessions.py · messages.py · config.py
│   │   ├── cron.py · task_logs.py · stats.py · system_logs.py
│   │   ├── active_consciousness.py · passive_consciousness.py · free_consciousness.py
│   │   └── hindsight.py · llm.py · test.py
│   ├── services/                   # 业务逻辑层
│   │   ├── active_consciousness_service.py   # 心跳、情绪、决策、念头存储
│   │   ├── thought_engine.py                 # 念头生成管道
│   │   ├── context_collector.py              # 结构化上下文包
│   │   ├── passive_consciousness_service.py  # 信号：想念 / 热度 / 情绪强度
│   │   ├── template_service.py               # Jinja2 注入模板
│   │   ├── analysis_service.py               # 注入效果分析
│   │   ├── free_consciousness_service.py     # 沉思循环 + 意识积淀
│   │   ├── scheduler_service.py              # 带占位符的定时任务
│   │   ├── message_service.py                # 平台发送 + state.db 追加
│   │   ├── weather_service.py                # 高德 / 和风，带缓存
│   │   ├── llm_service.py · config_service.py · auth_service.py
│   │   └── session_service.py · fallback_session_service.py · state_db.py
│   └── tests/                      # pytest 测试（情绪、决策、端到端、天气…）
├── frontend/                       # Vue 3 控制台（开发端口 5173，代理到后端）
│   └── src/
│       ├── views/                  # 每个控制台页面对应一个视图
│       ├── api/                    # 带 JWT 拦截器的 axios 封装
│       ├── components/             # 布局、图表、选择器
│       └── router/ · store/
├── deployment/
│   ├── systemd/                    # 用户级服务单元
│   └── hermes-agent-patches/       # 会话同步补丁 + 说明
└── docs/                           # 设计文档与安装指南
```

---

## 快速开始


<p align="center">
  <img src="docs/images/zh-deployment.jpg" width="800" alt="部署拓扑">
</p>

### 前置条件

- Python 3.12+ 和 Node.js 18+
- 已安装并运行的 [Hermes Agent](https://github.com/NousResearch/hermes-agent)（`~/.hermes/hermes-agent`）
- 可选：[Hindsight](https://github.com/NousResearch/hindsight)，用于长期记忆

### 安装

```bash
# Hermes Active 放在 Hermes 主目录下
cd ~/.hermes
git clone https://github.com/your-org/hermes-active.git
cd hermes-active

# 后端 —— 复用 Hermes Agent 的 venv，使其模块可导入
cd backend
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
npm run build        # 后端直接托管 frontend/dist
```

### 运行

```bash
cd ~/.hermes/hermes-active/backend
python main.py       # http://localhost:18720（admin / admin）
```

开发模式：`npm run dev` 在 `:5173` 启动前端并代理 API。

### 生产部署

- **systemd 单元** —— 现成的用户级服务文件：[deployment/systemd/](deployment/systemd/)
- **会话同步补丁** —— 应用 [deployment/hermes-agent-patches/](deployment/hermes-agent-patches/README.md) 中的 4 文件补丁，让网关感知外部追加的消息
- **passive-consciousness 插件** —— 按 [docs/plugin-installation.md](docs/plugin-installation.md) 安装到 `~/.hermes/plugins/`
- 完整流程：[docs/deployment.md](docs/deployment.md)

> ⚠️ 首次登录后请立即修改默认密码，生产环境务必设置 `JWT_SECRET_KEY`。

---

## 配置说明

所有配置都存放在 `active.db` 的 `configs` 表中，并可在 Web 界面编辑 —— 没有任何硬编码。重点配置：

### 主动意识

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `active_consciousness.enabled` | `false` | 总开关 |
| `active_consciousness.active.heartbeat_interval` | `600` | 心跳周期（秒） |
| `active_consciousness.active.send_tag` | `凯莉` | 写回 `state.db` 的主动消息标记 |
| `active_consciousness.decision.send_threshold` | `0.35` | 自动发送所需分数 |
| `active_consciousness.decision.memory_threshold` | `0.05` | 存为记忆所需分数 |
| `active_consciousness.decision.max_per_hour` / `max_per_day` | `2` / `5` | 发送频率上限 |
| `active_consciousness.emotion.decay_rate` | `0.02` | 唤醒度每小时衰减 |
| `active_consciousness.emotion.social_need_growth` | `0.01` | 社交需求每小时增长 |
| `active_consciousness.emotion.valence_regression` | `0.1` | 效价回归速度 |
| `active_consciousness.llm.*` | hermes 模式 | 通用 LLM（分层：`emotion_llm.*`、`thought_llm.*`） |
| `active_consciousness.hindsight.*` | localhost:8888 | 召回/存储记忆库、数量上限、开关 |

### 被动意识

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `passive_consciousness.enabled` | `false` | 总开关 |
| `passive_consciousness.passive.inject_emotion / inject_heat / inject_memory / inject_thought` | `true` | 逐信号开关 |
| `passive_consciousness.passive.inject_tag` | `[CONSCIOUSNESS_CONTEXT]` | 注入块的包裹标记 |
| `passive_consciousness.platforms.whitelist` | `["weixin"]` | 启用注入的平台 |
| `passive_consciousness.templates.*` | 默认模板 | Jinja2 模板列表 + 激活 ID |
| `passive_consciousness.hindsight.*` | 启用 | 召回数量上限、Reflect 开关 |

### 自由意识

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `free_consciousness.enabled` | `false` | 总开关 |
| `free_consciousness.interval_minutes` | `30` | 沉思周期（分钟） |
| `free_consciousness.recent_rounds` / `mid_rounds` | `3` / `17` | 思考链分层大小 |
| `free_consciousness.sediment_compress_interval` | `10` | 积淀压缩间隔（轮） |
| `free_consciousness.include_context` | `true` | 注入实时时间/情绪/对话 |
| `free_consciousness.store_to_hindsight` | `false` | 将新发现存入长期记忆 |
| `free_consciousness.prompts.system` / `prompts.user` | 内置 | 完全模板化的沉思提示词 |

### 天气（统一配置）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `weather.enabled` | `false` | 定时任务、心跳、注入共用的总开关 |
| `weather.provider` | `qweather` | `amap` 或 `qweather` |
| `weather.city` / `weather.adcode` | `北京` / `370100` | 和风城市名 / 高德城市编码 |
| `weather.amap_key` / `weather.qweather_key` | — | 各提供商 API Key |
| `weather.cache_hours` | `4` | 结果缓存时长 |

环境变量：`JWT_SECRET_KEY` —— JWT 签名密钥（生产环境务必设置）。

---

## API 概览

界面上的所有操作都有对应的 REST API（除 `/health` 和登录外均需 JWT）：

| 分组 | 代表性端点 |
|------|-----------|
| 认证 | `POST /api/auth/login` |
| 会话与消息 | `GET /api/sessions` · `GET /api/messages/{session_id}` · `POST /api/messages/send` · `POST /api/messages/send-and-inject` |
| 定时任务 | `GET/POST/PUT/DELETE /api/cron/jobs` · `POST /api/cron/jobs/{id}/run` · `GET /api/task-logs` |
| 主动意识 | `GET/PUT /api/active-consciousness/config` · `GET .../status` · `GET .../heartbeats` · `GET .../thoughts` · `POST .../test/*` |
| 被动意识 | `GET/PUT /api/passive-consciousness/config` · `GET .../status` · `GET/POST/PUT/DELETE .../templates` · `POST .../test/*` · `GET .../analysis/*` |
| 自由意识 | `GET/POST /api/free-consciousness/config` · `GET .../status` · `GET .../logs` · `POST .../run` |
| 其他 | `GET /api/stats` · `GET /api/system-logs` · `POST /api/llm/test` · `GET /health` |

---

## 文档

| 文档 | 内容 |
|------|------|
| [docs/deployment.md](docs/deployment.md) | 完整部署流程 |
| [docs/plugin-installation.md](docs/plugin-installation.md) | 被动意识插件安装 |
| [deployment/hermes-agent-patches/](deployment/hermes-agent-patches/README.md) | 会话同步补丁说明 |
| [docs/](docs/README.md) | 设计文档与架构深度解析 |

---

## 许可证

MIT 许可证 —— 详见 [LICENSE](LICENSE)。

---

> [!NOTE]
> 🖼️ **信息图占位 — 页脚横幅** · 保存为 `docs/images/zh-footer-banner.png`。
>
> **生成提示词：** *一条极简的开源 README 页脚缎带：一条细渐变线（靛蓝→青色），中央有一个小小的心跳脉冲，配优雅的小号无衬线文字"Hermes Active —— 为 Hermes Agent 社区用 ❤️ 构建"，透明/深色背景，4:1 宽幅比例。*

<p align="center">
  为 <a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a> 社区用 ❤️ 构建
</p>
