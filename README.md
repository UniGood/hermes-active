# hermers-active

Hermes Agent 主动消息方案 - 方案G实现

## 项目概述

本项目实现了 Hermes Agent 的主动消息功能，让 AI 能够主动与用户发起对话，而不是被动等待用户输入。

## 核心问题

**问题描述**：主动消息和主会话是两条完全独立的数据流，没有交叉。

```
主动消息：cron → 独立 session → delivery → 平台发送（不写入主会话 DB）❌
用户回复：gateway → 加载主会话历史 → 历史中没有主动消息 → 凯莉不知道 ❌
```

**结果**：用户回复时，AI 不知道自己之前说了什么，导致对话脱节。

## 解决方案：方案 G

### 核心思路

```
定时触发（每20分钟）
    ↓
找到主会话 session_id
    ↓
读取最近 20 条对话历史
    ↓
构建 prompt（系统提示 + 历史 + 生成指令）
    ↓
调用 LLM 生成消息
    ↓
通过平台 API 发送到微信
    ↓
写入 session DB（带标记）
```

### 核心优势

| 优势 | 说明 |
|------|------|
| **上下文连贯** | LLM 看到完整对话历史，消息更自然 |
| **话题延续** | 能自然延续最近的聊天话题 |
| **身份一致** | LLM 知道自己是凯莉，知道用户是曹凡 |
| **不依赖 hook** | 不需要 pre_llm_call hook 注入 |

## 开发历史

### 2026-06-11

#### 1. 技术研究

- 深入研究 Hermes 源码，理解 session 管理机制
- 分析 cron scheduler 和 gateway 的关系
- 验证 session DB 写入的可行性

#### 2. 方案设计

- **方案 A**：写入 Session DB（修改 cron/scheduler.py）
- **方案 B**：改进 Hook 注入（改 plugin）
- **方案 C**：写入 Hindsight memory
- **方案 D**：等待官方实现（#5712）

最终选择 **方案 G**：在主会话上下文中生成消息。

#### 3. 测试验证

**测试用例 1**：不带标记格式
```
发送消息：我推荐你一首歌《清明雨上》
写入格式：role=assistant, content=我推荐你一首歌《清明雨上》
结果：❌ 凯莉不知道是自己说的，问"你怎么突然想到这首歌了"
```

**测试用例 2**：带标记格式
```
发送消息：我推荐你一个电视剧《陈情令》
写入格式：[凯莉主动发送] 2026-06-11 13:07:18: 我推荐你一个电视剧《陈情令》
结果：✅ 凯莉能正确识别是自己主动发的
```

**测试用例 3**：完整流程测试
```
LLM 生成：因为觉得魏无羡和蓝忘机那种心意相通的样子很动人呀...
发送到微信：✅ 成功
写入 session DB：✅ 成功
```

#### 4. 关键发现

**正确的存储格式**：
```
[凯莉主动发送] 2026-06-11 13:07:18: 消息内容
```

**格式说明**：
- `[凯莉主动发送]` - 标记发送者身份
- `2026-06-11 13:07:18` - 时间戳
- `: ` - 分隔符
- `消息内容` - 实际消息

## 文件结构

```
hermers-active/
├── README.md                           # 本文件
├── docs/
│   ├── proactive-message-plan-g-dev-doc.md          # 开发文档
│   ├── proactive-message-plan-g-context-gen.md      # 方案G详细设计
│   ├── proactive-message-plan-a-session-db.md       # 方案A设计
│   └── proactive-message-context-injection-research.md  # 技术研究
├── scripts/
│   ├── proactive_context_gen.py        # 完整实现脚本
│   ├── test_context_read.py            # 上下文读取测试
│   └── test_send_message.py            # 消息发送测试
└── references/
    └── (参考文档)
```

## 使用方法

### 前置条件

1. Hermes Agent 已安装并配置
2. 微信平台已配置（WEIXIN_TOKEN, WEIXIN_ACCOUNT_ID）
3. .env 文件已配置

### 运行测试

```bash
# 测试上下文读取
python3 scripts/test_context_read.py

# 测试消息发送
python3 scripts/test_send_message.py

# 运行完整方案
python3 scripts/proactive_context_gen.py
```

### 集成到 Cron Job

```bash
# 创建定时任务
hermes cron create "0,20,40 6-23 * * *" \
  "运行主动消息生成脚本" \
  --name proactive-context-gen \
  --script proactive_context_gen.py \
  --deliver local
```

## 配置项

```yaml
proactive_context_gen:
  enabled: true                    # 总开关
  schedule: "0,20,40 6-23 * * *"  # 触发时间
  platform: weixin                 # 目标平台
  chat_id: "xxx"                   # 目标 chat
  max_context_messages: 20         # 读取的最大消息数
  model: mimo-v2.5-pro             # 使用的模型
  quiet_hours: "23:00-08:00"       # 安静时间
  max_per_day: 8                   # 每日最大发送数
  min_idle_minutes: 15             # 最小空闲时间
```

## 技术细节

### Session 查找

```python
# 查找最新的活跃微信 session
cursor.execute("""
    SELECT id, user_id FROM sessions 
    WHERE source = 'weixin' AND ended_at IS NULL
    ORDER BY started_at DESC LIMIT 1
""")
```

### 消息写入

```python
# 写入带标记的消息
marked_content = f'[凯莉主动发送] {timestamp}: {content}'
db.append_message(
    session_id=session_id,
    role="assistant",
    content=marked_content,
)
```

### 上下文读取

```python
# 读取最近 N 条消息
cursor.execute("""
    SELECT role, content, timestamp
    FROM messages 
    WHERE session_id = ?
    ORDER BY timestamp DESC LIMIT ?
""", (session_id, limit))
```

## 相关 Issue

- #5712: True Autonomy - Automatically Inject Cron Results into Live Gateway Chat Sessions
- #37005: Agent has no awareness of information delivered by its own cron jobs
- #24246: Cron delivery knowledge gap

## 后续计划

1. ✅ 测试验证：带标记格式可以让凯莉正确识别主动消息
2. ⬜ 集成到 cron job 或 plugin
3. ⬜ 配置开关和参数
4. ⬜ 添加安静时间、每日上限等防骚扰机制
5. ⬜ 支持多平台（飞书、Telegram 等）

## License

MIT
