# 被动意识插件安装指南

## 概述

被动意识插件（passive-consciousness）是 Hermes Agent 的上下文注入插件，它会在用户消息到达时自动注入情绪状态、聊天热度、想念分数、天气信息和 Hindsight 记忆到系统提示词中，让 AI 拥有更丰富的上下文感知能力。

---

## 前置条件

### 1. Hermes Active 后端服务

被动意识插件依赖 Hermes Active 后端服务提供配置管理和模板渲染功能。

```bash
# 确保后端服务正在运行
cd ~/.hermes/hermes-active/backend
python main.py
```

后端服务默认运行在 `http://localhost:18720`。

### 2. Python 依赖

```bash
cd ~/.hermes/hermes-active/backend
pip install -r requirements.txt
```

主要依赖：
- FastAPI
- SQLAlchemy
- Jinja2（模板渲染）
- httpx（HTTP 请求）

---

## 安装步骤

### 步骤 1：确认插件文件

插件文件应位于 `~/.hermes/plugins/passive-consciousness/` 目录：

```
~/.hermes/plugins/passive-consciousness/
├── __init__.py              # 插件入口，注册 hook
├── plugin.yaml              # 插件配置清单
├── config_reader.py         # 配置读取器
├── consciousness_engine.py  # 意识状态计算
└── hindsight_client.py      # Hindsight API 客户端
```

如果插件文件不存在，可以从 hermes-active 项目复制：

```bash
# 检查插件目录
ls -la ~/.hermes/plugins/passive-consciousness/

# 如果不存在，创建目录并复制文件
mkdir -p ~/.hermes/plugins/passive-consciousness/
cp ~/.hermes/hermes-active/plugins/passive-consciousness/* ~/.hermes/plugins/passive-consciousness/
```

### 步骤 2：启用插件

编辑 `~/.hermes/config.yaml`，在 `plugins.enabled` 列表中添加 `passive-consciousness`：

```yaml
plugins:
  disabled: []
  enabled:
    - agnes-ai
    - passive-consciousness  # 添加这一行
```

或者使用命令行工具：

```bash
hermes plugins enable passive-consciousness
```

### 步骤 3：验证插件安装

```bash
# 列出所有插件状态
hermes plugins list

# 应该看到 passive-consciousness 状态为 enabled
```

---

## 配置说明

### 通过 Web UI 配置（推荐）

1. 启动 Hermes Active 前端：

```bash
cd ~/.hermes/hermes-active/frontend
npm run dev
```

2. 访问 `http://localhost:5173`

3. 导航到「被动意识」页面

4. 在「配置」Tab 中进行配置

### 配置项说明

#### 基础配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `enabled` | 总开关 | `false` |
| `passive.enabled` | 启用注入 | `true` |

#### 注入内容配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `passive.inject_emotion` | 注入情绪状态 | `true` |
| `passive.inject_heat` | 注入聊天热度 | `true` |
| `passive.inject_memory` | 注入 Hindsight 记忆 | `true` |
| `passive.inject_thought` | 注入当前想法 | `true` |

#### 平台过滤配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `platforms.enabled` | 启用平台过滤 | `false` |
| `platforms.whitelist` | 启用的平台列表 | `["weixin"]` |

支持的平台：
- `weixin` - 微信
- `feishu` - 飞书
- `telegram` - Telegram
- `discord` - Discord
- `slack` - Slack

#### 天气感知配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `weather.enabled` | 启用天气感知 | `false` |
| `weather.provider` | 天气服务提供商 | `qweather` |
| `weather.city` | 查询城市 | `北京` |
| `weather.cache_hours` | 缓存时间（小时） | `4` |
| `weather.amap_key` | 高德地图 API Key | - |
| `weather.qweather_key` | 和风天气 API Key | - |

#### Hindsight 记忆配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `hindsight.enabled` | 启用 Hindsight | `true` |
| `hindsight.recall_limit` | Recall 结果数 | `5` |
| `hindsight.reflect_enabled` | 启用 Reflect | `true` |

#### 模板配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `templates.active_id` | 当前使用的模板 ID | `default` |

---

## 功能说明

### 1. 上下文注入流程

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

### 2. 注入内容示例

```
--- [CONSCIOUSNESS_CONTEXT] ---
以下是你（凯莉）当前的感知状态，仅供参考，不要在回复中直接提及这些数据：

🎭 情绪状态：八卦（强度 0.7）
🔥 聊天热度：hot（近1小时 5 条消息）
💕 想念程度：missing（分数 0.35）
🌤 天气：济南 多云 33°C
  💨 南风 微风
  💧 湿度 61%

📖 相关记忆：
  1. 上次聊到了天气和心情
  2. 讨论了周末计划

💭 综合反思：用户最近情绪稳定，聊天频率适中

--- /[CONSCIOUSNESS_CONTEXT] ---
```

### 3. 模板自定义

可以通过 Web UI 自定义注入模板，支持：
- Jinja2 模板语法
- 条件渲染（if/else）
- 循环渲染（for）
- 变量替换

可用变量：
- `emotional_intensity` - 情绪强度 (0.0-1.0)
- `emotional_label` - 情绪标签
- `chat_heat` - 聊天热度
- `chat_heat_label` - 热度标签
- `chat_heat_count` - 近 1 小时消息数
- `longing_score` - 想念分数 (0.0-1.0)
- `longing_label` - 想念标签
- `weather` - 天气数据对象
- `memories` - Hindsight 记忆列表
- `reflection` - Hindsight 反思文本
- `inject_emotion` - 是否注入情绪（配置项）
- `inject_heat` - 是否注入热度（配置项）
- `inject_memory` - 是否注入记忆（配置项）
- `platform` - 当前平台
- `sender_id` - 发送者 ID

---

## API 接口

### 平台配置

```
GET  /api/passive-consciousness/platforms          # 获取平台配置
PUT  /api/passive-consciousness/platforms          # 更新平台配置
GET  /api/passive-consciousness/platforms/available # 获取可用平台列表
```

### 天气服务

```
GET  /api/passive-consciousness/weather              # 获取天气数据
POST /api/passive-consciousness/weather/refresh      # 强制刷新天气
GET  /api/passive-consciousness/weather/status       # 获取天气服务状态
```

### 模板管理

```
GET    /api/passive-consciousness/templates           # 获取模板列表
GET    /api/passive-consciousness/templates/{id}       # 获取单个模板
POST   /api/passive-consciousness/templates           # 创建模板
PUT    /api/passive-consciousness/templates/{id}       # 更新模板
DELETE /api/passive-consciousness/templates/{id}       # 删除模板
POST   /api/passive-consciousness/templates/{id}/preview # 预览模板
GET    /api/passive-consciousness/templates/variables  # 获取可用变量
POST   /api/passive-consciousness/templates/render     # 渲染模板
```

### 分析统计

```
GET /api/passive-consciousness/analysis/stats      # 注入统计
GET /api/passive-consciousness/analysis/trends     # 趋势数据
GET /api/passive-consciousness/analysis/sentiment  # 情感分析
```

---

## 故障排除

### 1. 插件未加载

**症状**：消息发送后没有注入上下文

**检查步骤**：

```bash
# 1. 检查插件是否启用
hermes plugins list

# 2. 检查配置文件
cat ~/.hermes/config.yaml | grep -A 5 "plugins:"

# 3. 检查后端服务是否运行
curl http://localhost:18720/api/passive-consciousness/config

# 4. 检查插件日志
tail -f ~/.hermes/logs/hermes.log | grep "passive_consciousness"
```

### 2. 天气数据获取失败

**症状**：天气信息为空或显示错误

**检查步骤**：

```bash
# 1. 测试天气 API
curl -X POST http://localhost:18720/api/passive-consciousness/test/weather

# 2. 检查 API Key 配置
curl http://localhost:18720/api/passive-consciousness/config | jq '.weather'

# 3. 检查天气服务状态
curl http://localhost:18720/api/passive-consciousness/weather/status
```

### 3. Hindsight 记忆获取失败

**症状**：记忆部分为空

**检查步骤**：

```bash
# 1. 测试 Hindsight Recall
curl -X POST http://localhost:18720/api/passive-consciousness/test/hindsight-recall

# 2. 测试 Hindsight Reflect
curl -X POST http://localhost:18720/api/passive-consciousness/test/hindsight-reflect

# 3. 检查 Hindsight 服务是否运行
curl http://localhost:8888/health
```

### 4. 模板渲染失败

**症状**：上下文为空或格式错误

**检查步骤**：

```bash
# 1. 测试模板渲染
curl -X POST http://localhost:18720/api/passive-consciousness/templates/render \
  -H "Content-Type: application/json" \
  -d '{"emotional_label": "测试"}'

# 2. 检查当前模板
curl http://localhost:18720/api/passive-consciousness/templates/default

# 3. 预览模板
curl -X POST http://localhost:18720/api/passive-consciousness/templates/default/preview
```

---

## 卸载插件

### 方法 1：禁用插件（推荐）

编辑 `~/.hermes/config.yaml`，从 `plugins.enabled` 列表中移除：

```yaml
plugins:
  disabled: []
  enabled:
    - agnes-ai
    # - passive-consciousness  # 注释或删除这一行
```

或者使用命令行：

```bash
hermes plugins disable passive-consciousness
```

### 方法 2：删除插件文件

```bash
# 删除插件目录
rm -rf ~/.hermes/plugins/passive-consciousness/

# 删除配置（可选）
# 配置保存在 ~/.hermes/hermes-active/data/active.db 中
```

---

## 开发说明

### 插件架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Hermes 主进程                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  被动意识插件                                        │    │
│  │  - pre_llm_call hook                                │    │
│  │  - 通过 HTTP 调用 Backend API                       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend 服务 (FastAPI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 天气服务     │  │ 模板服务     │  │ 分析服务     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 文件结构

```
~/.hermes/
├── plugins/
│   └── passive-consciousness/    # 插件目录
│       ├── __init__.py           # 入口文件
│       ├── plugin.yaml           # 配置清单
│       ├── config_reader.py      # 配置读取
│       ├── consciousness_engine.py # 状态计算
│       └── hindsight_client.py   # Hindsight 客户端
│
├── hermes-active/                # 后端服务
│   ├── backend/
│   │   ├── services/
│   │   │   ├── template_service.py    # 模板服务
│   │   │   ├── analysis_service.py    # 分析服务
│   │   │   └── weather_service.py     # 天气服务
│   │   └── routers/
│   │       └── passive_consciousness.py # API 路由
│   └── frontend/
│       └── src/
│           └── views/
│               ├── PassiveConsciousness.vue # 配置页面
│               └── Analysis.vue            # 分析页面
│
└── config.yaml                   # Hermes 全局配置
```

---

## 更新日志

### v1.0.0 (2026-07-31)

- 初始版本
- 支持情绪状态、聊天热度、想念分数注入
- 支持天气感知（高德/和风天气）
- 支持 Hindsight 记忆召回
- 支持 Jinja2 模板自定义
- 支持平台过滤（白名单模式）
- 支持注入效果分析

---

## 相关文档

- [被动意识设计文档](./v0.2/passive-consciousness-design.md)
- [天气感知设计文档](./superpowers/specs/2026-07-30-weather-perception-design.md)
- [被动意识重构设计文档](./superpowers/specs/2026-07-31-passive-consciousness-refactor-design.md)
- [实现计划](./superpowers/plans/2026-07-31-passive-consciousness-refactor.md)

---

## 支持

如有问题，请查看：
1. 故障排除章节
2. 后端服务日志：`~/.hermes/hermes-active/backend/logs/`
3. Hermes 日志：`~/.hermes/logs/hermes.log`
