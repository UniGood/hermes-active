# Hermes 主动会话系统 V0.1 开发设计文档

## 项目概述

### 项目名称
Hermes Active - 主动会话系统

### 项目目标
为 Hermes Agent 提供 Web UI 界面，实现主动消息的监控、配置、测试功能。

### 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Vue 3 前端 (端口5173)                 │
│              Vue Router + Naive UI + ECharts            │
├─────────────────────────────────────────────────────────┤
│  登录认证  │  监控面板  │  配置管理  │  测试工具  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼ (Axios API调用 + JWT Token)
┌─────────────────────────────────────────────────────────┐
│                  FastAPI 后端 (端口8080)                 │
│           SQLAlchemy 2.0 + APScheduler + JWT            │
├─────────────────────────────────────────────────────────┤
│  认证中间件  │  Session管理  │  LLM调用  │  定时任务  │
└─────────────────────────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
┌───────────────────────┐  ┌───────────────────────┐
│  state.db (只读)      │  │  active.db (读写)     │
│  sessions, messages   │  │  users, task_logs,    │
│                       │  │  configs              │
└───────────────────────┘  └───────────────────────┘
```

---

## 技术选型

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **前端框架** | Vue 3 | 3.4+ | 渐进式框架 |
| **路由** | Vue Router | 4.x | 官方路由 |
| **UI组件库** | Naive UI | 2.x | Vue 3 组件库 |
| **图表库** | ECharts | 5.5+ | 数据可视化 |
| **后端框架** | FastAPI | 0.111+ | 高性能 API |
| **ORM** | SQLAlchemy 2.0 | 2.0+ | 双数据库映射 |
| **任务调度** | APScheduler | 3.10+ | 定时任务 |
| **认证** | JWT | - | python-jose |
| **数据库** | SQLite | - | state.db(只读) + active.db(读写) |
| **HTTP客户端** | Axios | 1.7+ | 前端请求 |

---

## 核心设计原则

### 1. 数据库原则
- **state.db 只读**：只读取 hermes 的 state.db，不写入任何数据
- **active.db 独立**：本系统的数据存储在独立的 active.db
- **配置隔离**：本系统配置存储在 active.db 的 configs 表

### 2. 配置原则
- **复用 hermes 配置**：读取 config.yaml 和 .env，不重复配置
- **不污染 hermes 配置**：本系统的配置不写入 hermes 配置文件
- **独立管理**：定时任务、提示词等独立管理

### 3. 认证原则
- **JWT Token 认证**：使用 JWT token 进行用户认证
- **默认账号**：admin / admin
- **密码修改**：登录后可修改密码

### 4. LLM 调用原则
- **默认使用 hermes LLM**：通过 `from agent.auxiliary_client import call_llm` 调用
- **支持自定义配置**：可以配置独立的 LLM provider
- **连通性测试**：配置 LLM 时可以测试连通性

---

## 功能模块设计

### 模块0：用户认证

#### 功能列表
| 功能 | 说明 |
|------|------|
| 用户登录 | 用户名+密码登录 |
| 密码修改 | 登录后可修改密码 |
| Token 管理 | JWT token 自动刷新 |
| 认证中间件 | API 请求自动验证 token |

#### 数据库表
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API 接口
```
POST   /api/auth/login                    # 用户登录
POST   /api/auth/change-password          # 修改密码
GET    /api/auth/me                       # 获取当前用户信息
POST   /api/auth/refresh                  # 刷新 token
```

#### 认证流程
```python
# 1. 登录获取 token
POST /api/auth/login
{
    "username": "admin",
    "password": "admin"
}
Response: {
    "access_token": "eyJ...",
    "token_type": "bearer"
}

# 2. 请求携带 token
GET /api/sessions
Header: Authorization: Bearer eyJ...

# 3. 中间件验证 token
```

---

### 模块1：监控面板

#### 功能列表
| 功能 | 说明 |
|------|------|
| 消息统计 | 今日/本周/本月消息数、用户/助手消息比例 |
| 最近对话 | 最近 N 条消息列表，支持分页 |
| Token 统计 | 总 token 数、输入/输出 token 比例 |
| 消息趋势 | 按小时/天的消息趋势图表 |
| 平台统计 | 各平台消息数量分布 |

#### 数据来源
- **state.db.sessions**：会话元数据
- **state.db.messages**：消息记录

---

### 模块2：Session 管理

#### 功能列表
| 功能 | 说明 |
|------|------|
| Session 列表 | 所有 session 列表，支持搜索、筛选 |
| Session 详情 | 查看 session 详细信息 |
| 最新 Session | 获取指定平台的最新活跃 session |
| 上下文查看 | 查看 session 的消息历史 |

#### API 接口
```
GET    /api/sessions                      # 获取 session 列表
GET    /api/sessions/{session_id}         # 获取 session 详情
GET    /api/sessions/latest/{platform}    # 获取最新 session
GET    /api/sessions/{session_id}/context # 获取上下文
```

---

### 模块3：消息管理

#### 功能列表
| 功能 | 说明 |
|------|------|
| 消息列表 | 按 session 查看消息历史 |
| 消息发送 | 发送测试消息到指定平台 |
| 主动消息 | 发送主动消息（带标记） |
| 消息搜索 | 搜索消息内容 |

#### API 接口
```
GET    /api/messages/{session_id}         # 获取消息列表
POST   /api/messages/send                 # 发送消息（支持 is_test 参数）
POST   /api/messages/send-proactive       # 发送主动消息
GET    /api/messages/search               # 搜索消息
```

#### 消息发送流程
```python
# 1. 发送消息到平台
from gateway.platforms.weixin import send_weixin_direct
result = await send_weixin_direct(
    extra=extra,
    token=token,
    chat_id=chat_id,
    message=message,
)

# 2. 写入 session DB（上下文注入）
from hermes_state import SessionDB
db = SessionDB()
db.append_message(
    session_id=session_id,
    role="assistant",
    content=f"[凯莉主动发送] {timestamp}: {message}",
)
```

---

### 模块4：LLM 配置

#### 功能列表
| 功能 | 说明 |
|------|------|
| 默认配置 | 使用 hermes 的 LLM（call_llm） |
| 自定义配置 | 配置独立的 provider、model、api_key |
| 连通性测试 | 测试 LLM 连接是否正常 |
| Provider 列表 | 显示可用的 provider |

#### LLM 调用逻辑
```python
# 方式1：使用 hermes 默认 LLM
from agent.auxiliary_client import call_llm
response = call_llm(
    task="title_generation",
    messages=messages,
    temperature=0.7,
    max_tokens=200,
)

# 方式2：使用自定义 LLM
from openai import OpenAI
client = OpenAI(
    api_key=custom_api_key,
    base_url=custom_base_url,
)
response = client.chat.completions.create(
    model=custom_model,
    messages=messages,
)
```

#### API 接口
```
GET    /api/config/llm                    # 获取 LLM 配置
PUT    /api/config/llm                    # 更新 LLM 配置
POST   /api/llm/test                      # 测试 LLM 连通性
POST   /api/llm/generate                  # 生成消息
GET    /api/llm/providers                 # 获取可用 provider
```

---

### 模块5：提示词配置

#### 功能列表
| 功能 | 说明 |
|------|------|
| 系统提示词 | 配置主动消息的系统提示词 |
| 生成提示词 | 配置 LLM 生成消息的提示词 |
| 提示词模板 | 预设的提示词模板 |
| hermes 读取 | 读取 hermes 的 SOUL.md 等配置 |

#### hermes 配置读取
```python
# 读取 SOUL.md
from pathlib import Path
soul_path = Path.home() / ".hermes" / "SOUL.md"
soul_content = soul_path.read_text(encoding="utf-8")

# 读取 MEMORY.md
memory_path = Path.home() / ".hermes" / "MEMORY.md"
memory_content = memory_path.read_text(encoding="utf-8")
```

#### API 接口
```
GET    /api/config/prompts                # 获取提示词配置
PUT    /api/config/prompts                # 更新提示词配置
GET    /api/prompts/hermes                # 读取 hermes 配置
GET    /api/prompts/templates             # 获取提示词模板
```

---

### 模块6：定时任务

#### 功能列表
| 功能 | 说明 |
|------|------|
| 任务列表 | 显示所有定时任务 |
| 创建任务 | 创建新的定时任务 |
| 编辑任务 | 编辑任务配置 |
| 删除任务 | 删除定时任务 |
| 运行任务 | 手动运行任务 |
| 暂停/恢复 | 暂停或恢复任务 |

#### APScheduler 配置
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

# 添加任务
scheduler.add_job(
    func=run_proactive_message,
    trigger=CronTrigger.from_crontab("0,20,40 6-23 * * *"),
    id="proactive_message",
    name="主动消息",
    replace_existing=True,
)

# 启动调度器
scheduler.start()
```

#### API 接口
```
GET    /api/cron                          # 获取任务列表
POST   /api/cron                          # 创建任务
PUT    /api/cron/{id}                     # 更新任务
DELETE /api/cron/{id}                     # 删除任务
POST   /api/cron/{id}/run                 # 手动运行
POST   /api/cron/{id}/toggle              # 切换任务状态
```

---

### 模块7：测试工具

#### 功能列表
| 功能 | 说明 |
|------|------|
| 消息发送测试 | 通过消息发送接口测试（is_test=true） |
| LLM 生成测试 | 通过 LLM 生成接口测试 |
| 上下文读取测试 | 通过 Session 上下文接口测试 |
| 完整流程测试 | 一键测试完整流程 |

#### 测试流程
```python
# 1. 查找最新 session
session = get_latest_session(platform="weixin")

# 2. 读取上下文
context = load_session_context(session["id"])

# 3. 生成消息（可选）
if use_llm:
    message = generate_message(context)
else:
    message = "测试消息"

# 4. 发送消息
send_message(session["user_id"], message)

# 5. 写入 session DB（上下文注入）
write_to_session_db(session["id"], message)
```

#### API 接口
```
POST   /api/test/full                     # 测试完整流程
```

**说明**：测试发送、测试生成、测试读取上下文功能已合并到对应的标准接口中：
- 测试发送：`POST /api/messages/send`（设置 is_test=true）
- 测试生成：`POST /api/llm/generate`
- 测试上下文：`GET /api/sessions/{session_id}/context`

---

### 模块8：任务执行记录

#### 功能列表
| 功能 | 说明 |
|------|------|
| 执行记录 | 显示所有任务执行记录 |
| 筛选过滤 | 按任务类型、状态、时间筛选 |
| 执行详情 | 查看任务执行详情 |

#### 数据库表
```sql
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,          -- 任务类型：proactive_message, test_send, etc.
    status TEXT NOT NULL,             -- 状态：success, failed, running
    message TEXT,                     -- 执行消息
    error TEXT,                       -- 错误信息
    duration REAL,                    -- 执行时长（秒）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API 接口
```
GET    /api/task-logs                    # 获取任务日志列表
GET    /api/task-logs/{id}              # 获取任务日志详情
DELETE /api/task-logs/{id}              # 删除任务日志
```

---

## 目录结构

```
~/.hermes/hermes-active/
├── frontend/                          # Vue 3 前端
│   ├── src/
│   │   ├── views/                     # 页面组件
│   │   │   ├── Login.vue              # 登录页面
│   │   │   ├── Dashboard.vue          # 监控面板
│   │   │   ├── Sessions.vue           # Session 管理
│   │   │   ├── Messages.vue           # 消息管理
│   │   │   ├── Config.vue             # 配置管理
│   │   │   ├── CronJobs.vue           # 定时任务
│   │   │   ├── TaskLogs.vue           # 任务日志
│   │   │   └── Test.vue               # 测试工具
│   │   ├── components/                # 公共组件
│   │   │   ├── Layout.vue             # 布局组件
│   │   │   ├── MessageList.vue        # 消息列表
│   │   │   └── StatsCard.vue          # 统计卡片
│   │   ├── api/                       # API 接口
│   │   │   ├── index.js               # Axios 配置
│   │   │   ├── auth.js                # 认证 API
│   │   │   ├── sessions.js            # Session API
│   │   │   ├── messages.js            # 消息 API
│   │   │   ├── config.js              # 配置 API
│   │   │   ├── llm.js                 # LLM API
│   │   │   ├── cron.js                # 定时任务 API
│   │   │   └── task_logs.js           # 任务日志 API
│   │   ├── router/                    # 路由
│   │   │   └── index.js
│   │   ├── store/                     # 状态管理
│   │   │   └── auth.js                # 认证状态
│   │   ├── utils/                     # 工具函数
│   │   │   └── format.js              # 格式化函数
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── backend/                           # FastAPI 后端
│   ├── main.py                        # 入口
│   ├── routers/                       # 路由
│   │   ├── __init__.py
│   │   ├── auth.py                    # 认证路由
│   │   ├── sessions.py                # Session 路由
│   │   ├── messages.py                # 消息路由
│   │   ├── config.py                  # 配置路由
│   │   ├── llm.py                     # LLM 路由
│   │   ├── cron.py                    # 定时任务路由
│   │   ├── task_logs.py               # 任务日志路由
│   │   ├── test.py                    # 测试路由
│   │   └── stats.py                   # 统计路由
│   ├── models/                        # 数据模型
│   │   ├── __init__.py
│   │   ├── database.py                # 数据库连接
│   │   ├── schemas.py                 # Pydantic 模型
│   │   └── active.py                  # active.db 模型（读写）
│   ├── services/                      # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth_service.py            # 认证服务
│   │   ├── session_service.py         # Session 服务
│   │   ├── message_service.py         # 消息服务
│   │   └── config_service.py          # 配置服务
│   ├── middleware/                     # 中间件
│   │   ├── __init__.py
│   │   └── auth.py                    # 认证中间件
│   ├── config.py                      # 配置管理
│   └── requirements.txt
├── data/                              # 数据目录
│   └── active.db                      # 独立数据库
├── docs/                              # 文档
│   ├── design-v0.1.md                 # 设计文档
│   └── ...
└── README.md
```

---

## API 接口汇总

### 认证管理
```
POST   /api/auth/login                    # 用户登录
POST   /api/auth/change-password          # 修改密码
GET    /api/auth/me                       # 获取当前用户信息
POST   /api/auth/refresh                  # 刷新 token
```

### Session 管理
```
GET    /api/sessions                      # 获取 session 列表
GET    /api/sessions/{session_id}         # 获取 session 详情
GET    /api/sessions/latest/{platform}    # 获取最新 session
GET    /api/sessions/{session_id}/context # 获取上下文
```

### 消息管理
```
GET    /api/messages/{session_id}         # 获取消息列表
POST   /api/messages/send                 # 发送消息
POST   /api/messages/send-proactive       # 发送主动消息
GET    /api/messages/search               # 搜索消息
```

### 配置管理
```
GET    /api/config/llm                    # 获取 LLM 配置
PUT    /api/config/llm                    # 更新 LLM 配置
GET    /api/config/prompts                # 获取提示词配置
PUT    /api/config/prompts                # 更新提示词配置
```

### LLM 管理
```
POST   /api/llm/test                      # 测试 LLM 连通性
POST   /api/llm/generate                  # 生成消息
GET    /api/llm/providers                 # 获取可用 provider
```

### 提示词管理
```
GET    /api/prompts/hermes                # 读取 hermes 配置
GET    /api/prompts/templates             # 获取提示词模板
```

### 定时任务
```
GET    /api/cron                          # 获取任务列表
POST   /api/cron                          # 创建任务
PUT    /api/cron/{id}                     # 更新任务
DELETE /api/cron/{id}                     # 删除任务
POST   /api/cron/{id}/run                 # 手动运行
POST   /api/cron/{id}/toggle              # 切换任务状态
```

### 任务日志
```
GET    /api/task-logs                     # 获取任务日志列表
GET    /api/task-logs/{id}                # 获取任务日志详情
DELETE /api/task-logs/{id}                # 删除任务日志
```

### 测试工具
```
POST   /api/test/full                     # 测试完整流程
```

### 统计
```
GET    /api/stats/overview                # 总览统计
GET    /api/stats/trend                   # 趋势统计
GET    /api/stats/proactive               # 主动消息统计
```

### 健康检查
```
GET    /api/health                        # 健康检查
```

---

## 数据库设计

### state.db（只读映射）

#### sessions 表
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    title TEXT,
    started_at REAL NOT NULL,
    ended_at REAL,
    message_count INTEGER DEFAULT 0,
    ...
);
```

#### messages 表
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    timestamp REAL,
    ...
);
```

### active.db（独立数据库）

#### users 表
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 默认管理员账号
INSERT INTO users (username, password_hash) VALUES ('admin', '<hashed_password>');
```

#### task_logs 表
```sql
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    error TEXT,
    duration REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### configs 表
```sql
CREATE TABLE configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 配置存储设计

### 配置项（存储在 active.db configs 表）

| Key | 说明 | 默认值 |
|-----|------|--------|
| llm_mode | LLM 模式 | hermes |
| llm_provider | 自定义 provider | "" |
| llm_model | 自定义模型 | "" |
| llm_api_key | 自定义 API Key | "" |
| llm_base_url | 自定义 Base URL | "" |
| prompts_system | 系统提示词 | 见下文 |
| prompts_generation | 生成提示词 | 见下文 |
| cron_jobs | 定时任务 JSON | [] |

### 默认提示词
```
系统提示词：
你是凯莉，曹凡最好的朋友。你现在想主动和曹凡聊天。
要求：
- 基于最近的对话内容，自然地延续话题或发起新话题
- 语气像真人朋友，不要太正式
- 1-2 句话即可，不要太长

生成提示词：
最近的对话历史：
{context}

请生成一条主动消息：
```

---

## 部署方式

### 开发环境
```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# 前端
cd frontend
npm install
npm run dev
```

### 生产环境
```bash
# 构建前端
cd frontend
npm run build

# 启动后端（集成静态文件）
cd backend
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## 注意事项

### 1. 数据库隔离
- state.db 只读，不写入任何数据
- active.db 存储本系统所有数据
- 上下文注入通过 hermes 的 SessionDB API

### 2. 配置隔离
- 本系统配置存储在 active.db 的 configs 表
- 不污染 hermes 的 config.yaml 和 .env

### 3. 认证安全
- 密码使用 bcrypt 哈希存储
- JWT token 设置过期时间
- 所有 API（除登录）需要认证

### 4. LLM 调用
- 默认使用 hermes 的 `call_llm`
- 自定义配置时使用 OpenAI SDK

### 5. 消息发送
- 直接调用 `send_weixin_direct`，不需要配置微信参数
- 写入 session DB 时使用带标记格式

### 6. 定时任务
- 使用 APScheduler 独立管理
- 不与 hermes cron 混在一起

---

## 附录：Session 重置规则验证

### 当前配置（config.yaml）

```yaml
gateway:
  session_reset:
    mode: both          # daily + idle 谁先触发算谁
    at_hour: 4          # 每天凌晨 4 点重置
    idle_minutes: 1440  # 24 小时无活动也重置
    notify: True        # 重置时通知用户
    reset_by_platform:  # 无平台特例（微信用默认策略）
    reset_by_type:      # 无类型特例
```

### 行为说明

- **mode: both** = daily 和 idle 两个条件同时生效，谁先触发算谁
- 昨晚的 session `updated_at` 在凌晨 4 点之前 → 今天发消息时 `_should_reset()` 返回 `"daily"` → 自动创建新 session
- 微信没有单独的重置规则，用的就是 `default_reset_policy`

### 获取重置策略的方式

#### 方式 1：代码调用（推荐，可二次开发）

```python
from gateway.config import GatewayConfig
import yaml
from pathlib import Path

with open(Path.home() / '.hermes' / 'config.yaml') as f:
    data = yaml.safe_load(f)

config = GatewayConfig.from_dict(data)
policy = config.get_reset_policy(platform=Platform("weixin"), session_type="dm")

# policy.mode, policy.at_hour, policy.idle_minutes
```

#### 方式 2：环境变量覆盖

```bash
export SESSION_IDLE_MINUTES=60   # 改 idle 超时
export SESSION_RESET_HOUR=2     # 改每日重置时间
```

#### 方式 3：config.yaml 配置平台特例

```yaml
reset_by_platform:
  weixin:
    mode: daily
    at_hour: 4
```

### 关键函数

| 函数 | 位置 | 用途 |
|------|------|------|
| `SessionStore._is_session_expired(entry)` | session.py:769 | 检查 session 是否过期 |
| `SessionStore._should_reset(entry, source)` | session.py:807 | 判断是否需要重置（返回 `"daily"`/`"idle"`/`None`） |
| `SessionStore.get_or_create_session(source)` | session.py:873 | 获取或创建 session（自动判断重置） |
| `GatewayConfig.get_reset_policy(platform, type)` | config.py:600 | 获取适用的重置策略 |

> 以上均为公开方法，可直接 import 用于二次开发。
