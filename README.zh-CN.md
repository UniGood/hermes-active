<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>

<p align="center">
  <img src="docs/images/zh-hero-banner.svg" width="800">
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
  <img src="docs/images/zh-problem-statement.svg" width="800">
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

> 📸 截图取自运行中的 Web 控制台（`http://localhost:18720`），可用 `scripts/screenshot_readme.py` 重新生成。

<table>
  <tr>
    <td align="center">
      <b>仪表盘</b><br><br>
      <img src="docs/screenshots/dashboard.png" width="400"><br><br>
      <i>系统总览：会话、消息、任务统计、意识状态一屏尽览。</i>
    </td>
    <td align="center">
      <b>主动意识</b><br><br>
      <img src="docs/screenshots/active-consciousness.png" width="400"><br><br>
      <i>实时 VA 情绪仪表盘、心跳日志流、含完整 LLM 推理过程的念头日志。</i>
    </td>
  </tr>
  <tr>
    <td align="center">
      <b>被动意识</b><br><br>
      <img src="docs/screenshots/passive-consciousness.png" width="400"><br><br>
      <i>注入开关、带实时预览的 Jinja2 模板编辑器、每个信号的独立测试按钮。</i>
    </td>
    <td align="center">
      <b>自由意识</b><br><br>
      <img src="docs/screenshots/free-consciousness.png" width="400"><br><br>
      <i>沉思轮次时间线、思考链查看器、意识积淀浏览。</i>
    </td>
  </tr>
  <tr>
    <td align="center">
      <b>定时任务</b><br><br>
      <img src="docs/screenshots/cron-jobs.png" width="400"><br><br>
      <i>可视化 Cron 编辑器、占位符插入、提示词预览、执行日志。</i>
    </td>
    <td align="center">
      <b>注入分析</b><br><br>
      <img src="docs/screenshots/analysis.png" width="400"><br><br>
      <i>ECharts 图表：注入趋势、情绪/想念/热度分布。</i>
    </td>
  </tr>
</table>

---

## 系统架构

<p align="center">
  <img src="docs/images/zh-architecture.svg" width="800">
</p>


### 双数据库设计

| 数据库 | 访问权限 | 内容 | 位置 |
|--------|---------|------|------|
| `state.db` | **只读**（唯一例外：写回主动消息） | Hermes Agent 的会话与消息 | `~/.hermes/state.db` |
| `active.db` | **读写** | 用户、配置、定时任务、任务日志、心跳/念头/沉思/注入日志 | `data/active.db` |

Hermes Active 从不写入 Hermes 的配置，也从不改动历史对话 —— 它只**追加**自己发出的主动消息，并加上可配置的标记（如 `[凯莉 14:30]: …`），让主代理自然地将它们视为自己说过的话。

---

## 核心系统

<p align="center">
  <img src="docs/images/zh-four-systems.svg" width="800">
</p>

### 主动意识 —— 心跳

调度器每隔 N 秒（默认 600）触发一次完整的 感知 → 感受 → 决策 → 行动 循环。没有任何预设脚本：情绪状态、决策分数和消息内容全部由实时上下文涌现。


#### 情绪系统 —— 效价/唤醒度 + 社交需求

助手的心情是一个持久化的三维状态，每次心跳都会先按流逝时间向前推演，再与 LLM 评估融合：

| 维度 | 范围 | 含义 | 自然漂移 | 默认速率（每小时） |
|------|------|------|---------|---------|
| **效价（Valence）** | 0.0 – 1.0 | 愉悦 ↔ 不悦 | 向中性（0.5）回归 | `valence_regression = 0.1` |
| **唤醒度（Arousal）** | 0.0 – 1.0 | 激活 ↔ 平静 | 随时间衰减 | `decay_rate = 0.02` |
| **社交需求（Social Need）** | 0.0 – 1.0 | 想互动的程度 | 随静默增长 | `social_need_growth = 0.01` |

确定性演化将上一次状态按流逝小时数 `hours` 向前推演，三组公式各自带有边界保护：

| 维度 | 演化公式 | 边界 |
|------|---------|------|
| 唤醒度衰减 | `arousal' = max(0.1, arousal − decay_rate × hours)` | 下限 0.1 |
| 社交需求增长 | `social_need' = min(1.0, social_need + social_need_growth × hours)` | 上限 1.0 |
| 效价回归中性 | `valence' = valence + (0.5 − valence) × valence_regression × hours` | clamp 到 [0, 1] |

由这三个值推导出主导情绪标签（优先级从上到下，命中即停）：

| social_need | valence | arousal | 主导情绪 |
|-------------|---------|---------|---------|
| > 0.7 | > 0.5 | - | `yearning` 渴望 |
| > 0.7 | ≤ 0.5 | - | `anxious` 焦虑 |
| > 0.5 | > 0.5 | - | `longing` 想念 |
| > 0.5 | ≤ 0.5 | - | `missing` 思念 |
| - | - | < 0.3 | `calm` 平静 |
| > 0.7 | - | > 0.6 | `happy` 愉悦 |
| > 0.7 | - | ≤ 0.6 | `content` 满足 |
| < 0.3 | - | < 0.4 | `bored` 无聊 |
| < 0.3 | - | ≥ 0.4 | `concerned` 担忧 |
| - | - | - | `calm`（兜底） |

每次心跳都会融合**两个独立来源**的情绪估计：

1. **确定性演化** —— 将上一次状态按流逝时间向前推演（速率可配置：`decay_rate`、`social_need_growth`、`valence_regression`）
2. **LLM 评估** —— 专用提示词让 LLM 阅读最近对话，输出新的 VA 值

融合权重不是连续滑动，而是按置信度**分三档跳变**。置信度本身由 LLM 评估的合理性与一致性打分：

```
confidence = 0.5  （基础分）
           + 0.2  （V、A 均落在 [0, 1] 合理区间）
           + 0.3  （与演化值差值均 < 0.3，方向一致）
           − 0.2  （与演化值差值任一 > 0.5，明显离群）
```

最终 clamp 到 [0, 1]，再按下表分档确定演化值与 LLM 评估的混合权重：

| 置信度 | 演化值权重 | LLM 权重 | 含义 |
|--------|-----------|---------|------|
| `< 0.3` | 0.7 | 0.3 | LLM 评估可疑，信任演化推演 |
| `0.3 – 0.8` | 0.4 | 0.6 | 默认配比，略偏 LLM |
| `> 0.8` | 0.3 | 0.7 | LLM 评估可靠，信任评估 |

三个维度分别加权合并；主导情绪在置信度 `> 0.5` 时取 LLM 的判断，否则沿用演化值。如果 LLM 返回无效值（全零），演化值会静默接管。

#### 决策矩阵

发送是一个评分决策，而不是定时器：

```
score = 情绪强度 × 时间适宜度 × 静默因子 × 频率限制
```

| 因子 | 计算方式 |
|------|---------|
| `情绪强度` | `intensity = social_need × 0.5 + arousal × 0.3 + valence × 0.2`（合并后 VA 状态的加权综合） |
| `时间适宜度` | 时段表 —— 见下，早晚窗口 1.0，工作时间 0.7–0.9，深夜 0.3 |
| `静默因子` | 5 段阶梯 —— 用户最后一条消息 30 分钟内为 0.6，静默 6 小时后为 1.0 |
| `频率限制` | 硬门控：`frequency_limit = 1.0 if 小时发送数 < max_per_hour else 0.0`，达上限直接把 score 置 0 |

**时间适宜度**按当地小时数查表（`time.enabled = false` 时一律返回 1.0）：

| 时段 | fitness | 说明 |
|------|---------|------|
| 7 – 9 | 1.0 | 早安窗口 |
| 9 – 12 | 0.8 | 工作时间 |
| 12 – 14 | 0.9 | 午休时间 |
| 14 – 18 | 0.7 | 工作时间 |
| 18 – 22 | 1.0 | 下班时间 |
| 22 – 23.5 | 0.8 | 睡前时间 |
| 23.5 – 7（跨午夜） | 0.3 | 深夜 |

**静默因子**是分段常数阶梯，而非连续曲线：

| 静默时长 | silence_factor |
|----------|---------------|
| < 30 分钟 | 0.6 |
| 30 – 60 分钟 | 0.75 |
| 1 – 3 小时 | 0.85 |
| 3 – 6 小时 | 0.95 |
| ≥ 6 小时 | 1.0 |

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
- **念头分类** —— 每个念头被归类（`memory`、`env`、`emotion`、`silence`、`time`、`assoc`），并带标签存入 Hindsight（`active_consciousness`、主导情绪、`high_emotion`、`user_related`）。分类按优先级判定：回忆 > 天气（雨/雪/大风/雷阵雨） > 情绪（强度 > 0.6） > 沉默（> 180 分钟） > 时间（7/8/22/23 点） > 默认 `assoc`
- **前缀剥离** —— 若 LLM 自生成的回复带 `[凯莉 HH:MM]` 前缀，解析器会自动剥除，避免重复标记
- **Hindsight Retain 条件** —— 念头在「情绪强度 > `retain_threshold`」或「分数 > `retain_threshold`」或「内容含相关用户」三选一时写入长期记忆，默认 `retain_threshold = 0.5`；被发送保护拦截的念头也会转为记忆而非丢弃

#### 发送保护

三道守卫在念头生成**之后**、实际发送**之前**运行，仅对 `auto_send` 决策生效 —— 被拦截的念头会转为记忆而不是被丢弃。第四道硬门控（频率限制）已在决策矩阵中把 score 置 0，此处不再重复：

| 守卫 | 配置项 | 默认值 | 判定 |
|------|--------|--------|------|
| 静默窗口 —— 用户刚发过消息 | `active.no_send_after_user_msg_minutes` | 5 分钟 | `静默时长 < 阈值` → skip |
| 热度守卫 —— 用户正在热聊 | `active.no_send_while_heat_above` | 1.0 条/小时 | `当前热度 > 阈值` → skip |
| 情绪守卫 —— 情绪强度过低 | `active.no_send_while_vibe_below` | 0.15 | `情绪强度 < 阈值` → skip |

> `active.cooldown_minutes`（默认 30 分钟）作用于 **cron 定时任务**路径，主动意识心跳不读取它 —— 心跳的频率控制完全由决策矩阵中的 `max_per_hour` 承担。

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


#### 注入的信号

| 信号 | 来源 | 计算方式 |
|------|------|---------|
| 💕 想念程度 | `state.db` | 距用户最后一条消息的分钟数 ÷ 300，封顶 1.0 —— 从 `calm` 到 `anxious` 五个等级 |
| 🔥 聊天热度 | `state.db` | 最近一小时的用户消息数 —— `cold / warm / hot / fire` |
| 🎭 情绪强度 | `active.db` | 由主动意识心跳写入 —— `工作 / 日常 / 八卦 / 情感 / 深度情感` |
| 🌤 天气 | 高德 / 和风 | 统一的 `weather.*` 配置，带缓存，含高温/低温提醒 |
| 📖 相关记忆 | Hindsight Recall | 对长期记忆的语义搜索 |
| 💭 综合反思 | Hindsight Reflect | 对当前状况的综合分析 |

各信号的等级阈值统一参考如下（想念、热度、情绪均由后端纯 SQL + 算术计算，不调用 LLM）：

| 信号 | 等级 | 阈值 | 公式 / 来源 |
|------|------|------|-------------|
| 想念程度 | `calm` → `anxious` | 0.1 / 0.3 / 0.5 / 0.7 | `score = min(gap_minutes / 300, 1.0)`，距用户最后一条消息的分钟数 |
| 聊天热度 | `cold` → `fire` | 0.5 / 1.0 / 3.0 | 近 1 小时用户消息数（`cold` 0 条、`hot` 1 条、`fire` ≥ 3 条） |
| 情绪强度 | 工作 → 深度情感 | 0.3 / 0.5 / 0.7 / 0.9 | 由主动意识心跳写入 `active.db`，五档：工作/日常/八卦/情感/深度情感 |
| 天气 | 高温 / 低温 | 30 °C / 5 °C | 模板内提醒（>30°C 防暑、<5°C 保暖） |
| 相关记忆 | Hindsight Recall | 默认上限 5 条 | 超时 3s，`include_types = [episodic, semantic]` 语义检索 |
| 综合反思 | Hindsight Reflect | 默认启用 | 总超时 8s，`budget = low`；未启用时不触发生成式 LLM |

> 情绪强度与天气的提醒阈值由模板内 `{% if %}` 区块判定，可在 Web 界面逐信号测试。

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


#### 四层记忆模型

思考链通过按时间分层，让无限累积的沉思保持在可负担的成本内：

| 层 | 内容 | 成本 |
|----|------|------|
| **意识积淀** | LLM 将所有远期轮次压缩成的连贯叙述，每 10 轮刷新一次 | 总共约 300 字 |
| **近期轮次**（默认 3 轮） | 完整的思考原文 | 高 |
| **中期轮次**（默认 17 轮） | 一句话摘要 | 低 |
| **远期轮次** | 仅保留关键发现 | 极低 |

**加载窗口与压缩触发**：思考链只加载 `recent + mid` 条（默认 3 + 17 = 20）记录，窗口外的真正远期轮次不加载，仅由积淀代表。压缩在「远期轮次数 > 0 且为 `sediment_compress_interval` 的整数倍」时触发，即总轮次达到 13、23、33… 时由 LLM 把所有远期轮次压缩成一段不超过 300 字的连贯叙述，**覆盖式**刷新积淀表（单行，`id = 1`）。首次沉思无记录且无积淀时，思考链回退为「这是你的第一次沉思…」。

最终效果：助手始终能看到*自己曾得出的一切结论*（积淀）、*最近在思考什么*（原文）、以及*中间的重点*（摘要与发现）—— 一条无限延续的内在叙事，却不会撑爆上下文窗口。

所有沉思日志 —— 包括发出的完整提示词、原始响应、推理过程和 token 估算 —— 都可以在界面中浏览。

---

### 定时任务

基座层：带上下文注入的 cron 风格任务，完全在 Web 界面中管理 —— 独立于 Hermes Agent 内置的 cron。


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
  <img src="docs/images/zh-deployment.svg" width="800">
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

<p align="center">
  <img src="docs/images/zh-footer-banner.svg" width="800">
</p>

<p align="center">
  为 <a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a> 社区用 ❤️ 构建
</p>
