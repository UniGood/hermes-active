# Hermes 主动会话系统 V0.1 开发设计文档

## 项目概述

### 项目名称
Hermes Active - 主动会话系统

### 项目目标
为 Hermes Agent 提供 Web UI 界面，实现主动消息的监控、配置、测试功能。

### 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Vue 3 前端 (端口8080)                 │
│              Vue Router + Naive UI + ECharts            │
├─────────────────────────────────────────────────────────┤
│  监控面板  │  配置管理  │  测试工具  │  上下文查看  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼ (Axios API调用)
┌─────────────────────────────────────────────────────────┐
│                  FastAPI 后端 (端口8080)                 │
│              SQLAlchemy 2.0 + APScheduler               │
├─────────────────────────────────────────────────────────┤
│  Session管理  │  LLM调用  │  消息发送  │  定时任务  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              数据层 (只读 state.db)                      │
├─────────────────────────────────────────────────────────┤
│  state.db (只读)  │  config.yaml (读取)  │  .env (读取) │
└─────────────────────────────────────────────────────────┘
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
| **ORM** | SQLAlchemy 2.0 | 2.0+ | 只读映射 |
| **任务调度** | APScheduler | 3.10+ | 定时任务 |
| **数据库** | SQLite (state.db) | - | 只读，不写入 |
| **HTTP客户端** | Axios | 1.7+ | 前端请求 |

---

## 核心设计原则

### 1. 数据库原则
- **只读 state.db**：不新建数据库，不新建表
- **不写入 hermes 数据**：除了上下文注入，不往 state.db 写入任何数据
- **独立存储**：本系统的配置和数据单独存储

### 2. 配置原则
- **复用 hermes 配置**：读取 config.yaml 和 .env，不重复配置
- **不污染 hermes 配置**：本系统的配置不写入 hermes 配置文件
- **独立管理**：定时任务、提示词等独立管理

### 3. LLM 调用原则
- **默认使用 hermes LLM**：通过 `from agent.auxiliary_client import call_llm` 调用
- **支持自定义配置**：可以配置独立的 LLM provider
- **连通性测试**：配置 LLM 时可以测试连通性

---

## 功能模块设计

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
POST   /api/messages/send                 # 发送消息
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

#### 配置存储
```yaml
# ~/.hermes/hermes-active/config.yaml
llm:
  mode: hermes                    # hermes | custom
  custom:
    provider: xiaomi
    model: mimo-v2.5-pro
    api_key: ""                   # 从 .env 读取
    base_url: ""                  # 从 .env 读取
```

#### API 接口
```
GET    /api/llm/config                # 获取 LLM 配置
PUT    /api/llm/config                # 更新 LLM 配置
POST   /api/llm/test                  # 测试 LLM 连通性
POST   /api/llm/generate              # 生成消息
GET    /api/llm/providers             # 获取可用 provider
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

#### 提示词存储
```yaml
# ~/.hermes/hermes-active/config.yaml
prompts:
  system: |
    你是凯莉，曹凡最好的朋友。你现在想主动和曹凡聊天。
    要求：
    - 基于最近的对话内容，自然地延续话题或发起新话题
    - 语气像真人朋友，不要太正式
    - 1-2 句话即可，不要太长
  generation: |
    最近的对话历史：
    {context}
    
    请生成一条主动消息：
```

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
GET    /api/prompts                     # 获取提示词配置
PUT    /api/prompts                     # 更新提示词配置
GET    /api/prompts/hermes              # 读取 hermes 配置
GET    /api/prompts/templates           # 获取提示词模板
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

#### 任务存储
```yaml
# ~/.hermes/hermes-active/config.yaml
cron_jobs:
  - id: proactive_message
    name: 主动消息
    schedule: "0,20,40 6-23 * * *"
    enabled: true
    prompt: ""
    last_run_at: null
    next_run_at: null
```

#### API 接口
```
GET    /api/cron                        # 获取任务列表
POST   /api/cron                        # 创建任务
PUT    /api/cron/{id}                   # 更新任务
DELETE /api/cron/{id}                   # 删除任务
POST   /api/cron/{id}/run               # 手动运行
POST   /api/cron/{id}/pause             # 暂停任务
POST   /api/cron/{id}/resume            # 恢复任务
```

---

### 模块7：测试工具

#### 功能列表
| 功能 | 说明 |
|------|------|
| 消息发送测试 | 发送写死的消息 |
| LLM 生成测试 | 测试 LLM 生成消息 |
| 上下文读取测试 | 测试读取 session 上下文 |
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
POST   /api/test/send                   # 测试发送消息
POST   /api/test/generate               # 测试生成消息
POST   /api/test/context                # 测试读取上下文
POST   /api/test/full                   # 测试完整流程
```

---

## 目录结构

```
~/.hermes/hermes-active/
├── frontend/                          # Vue 3 前端
│   ├── src/
│   │   ├── views/                     # 页面组件
│   │   │   ├── Dashboard.vue          # 监控面板
│   │   │   ├── Sessions.vue           # Session 管理
│   │   │   ├── Messages.vue           # 消息管理
│   │   │   ├── Config.vue             # 配置管理
│   │   │   ├── CronJobs.vue           # 定时任务
│   │   │   └── Test.vue               # 测试工具
│   │   ├── components/                # 公共组件
│   │   │   ├── Layout.vue             # 布局组件
│   │   │   ├── MessageList.vue        # 消息列表
│   │   │   └── StatsCard.vue          # 统计卡片
│   │   ├── api/                       # API 接口
│   │   │   ├── index.js               # Axios 配置
│   │   │   ├── sessions.js            # Session API
│   │   │   ├── messages.js            # 消息 API
│   │   │   ├── config.js              # 配置 API
│   │   │   ├── llm.js                 # LLM API
│   │   │   └── cron.js                # 定时任务 API
│   │   ├── router/                    # 路由
│   │   │   └── index.js
│   │   ├── store/                     # 状态管理
│   │   │   └── index.js
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
│   │   ├── sessions.py                # Session 路由
│   │   ├── messages.py                # 消息路由
│   │   ├── config.py                  # 配置路由
│   │   ├── llm.py                     # LLM 路由
│   │   ├── cron.py                    # 定时任务路由
│   │   ├── prompts.py                 # 提示词路由
│   │   └── test.py                    # 测试路由
│   ├── models/                        # 数据模型
│   │   ├── __init__.py
│   │   ├── database.py                # 数据库连接
│   │   ├── schemas.py                 # Pydantic 模型
│   │   └── state.py                   # state.db 映射
│   ├── services/                      # 业务逻辑
│   │   ├── __init__.py
│   │   ├── session_service.py         # Session 服务
│   │   ├── message_service.py         # 消息服务
│   │   ├── llm_service.py             # LLM 服务
│   │   ├── weixin_service.py          # 微信服务
│   │   ├── config_service.py          # 配置服务
│   │   └── scheduler_service.py       # 调度服务
│   ├── config.py                      # 配置管理
│   └── requirements.txt
├── config.yaml                        # 本系统配置
├── data/                              # 数据目录
│   └── (运行时数据)
├── docs/                              # 文档
│   ├── design.md                      # 设计文档
│   ├── dev-doc.md                     # 开发文档
│   ├── api.md                         # API 文档
│   └── research.md                    # 技术研究
├── scripts/                           # 脚本
│   ├── proactive_context_gen.py       # 主动消息生成
│   ├── test_context_read.py           # 上下文读取测试
│   └── test_send_message.py           # 消息发送测试
└── README.md
```

---

## API 接口汇总

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
GET    /api/config                        # 获取配置
PUT    /api/config                        # 更新配置
GET    /api/config/llm                    # 获取 LLM 配置
PUT    /api/config/llm                    # 更新 LLM 配置
```

### LLM 管理
```
GET    /api/llm/config                    # 获取 LLM 配置
PUT    /api/llm/config                    # 更新 LLM 配置
POST   /api/llm/test                      # 测试 LLM 连通性
POST   /api/llm/generate                  # 生成消息
GET    /api/llm/providers                 # 获取可用 provider
```

### 提示词管理
```
GET    /api/prompts                       # 获取提示词配置
PUT    /api/prompts                       # 更新提示词配置
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
POST   /api/cron/{id}/pause               # 暂停任务
POST   /api/cron/{id}/resume              # 恢复任务
```

### 测试工具
```
POST   /api/test/send                     # 测试发送消息
POST   /api/test/generate                 # 测试生成消息
POST   /api/test/context                  # 测试读取上下文
POST   /api/test/full                     # 测试完整流程
```

### 统计
```
GET    /api/stats/overview                # 总览统计
GET    /api/stats/trend                   # 趋势统计
GET    /api/stats/proactive               # 主动消息统计
```

---

## 数据库设计（只读映射）

### state.db 表结构（已有）

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

### SQLAlchemy 映射
```python
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import Session

# 连接 state.db（只读）
engine = create_engine(
    "sqlite:///path/to/state.db",
    connect_args={"check_same_thread": False}
)

# 映射现有表
metadata = MetaData()
metadata.reflect(bind=engine)

sessions_table = metadata.tables['sessions']
messages_table = metadata.tables['messages']
```

---

## 配置文件设计

### config.yaml
```yaml
# Hermes Active 配置
server:
  host: "0.0.0.0"
  port: 8080

# 数据库配置
database:
  path: "~/.hermes/state.db"  # 只读

# LLM 配置
llm:
  mode: hermes                # hermes | custom
  custom:
    provider: ""
    model: ""
    api_key: ""
    base_url: ""

# 提示词配置
prompts:
  system: |
    你是凯莉，曹凡最好的朋友。你现在想主动和曹凡聊天。
    要求：
    - 基于最近的对话内容，自然地延续话题或发起新话题
    - 语气像真人朋友，不要太正式
    - 1-2 句话即可，不要太长
  generation: |
    最近的对话历史：
    {context}
    
    请生成一条主动消息：

# 定时任务配置
cron_jobs: []

# 日志配置
logging:
  level: INFO
  file: "~/.hermes/hermes-active/logs/app.log"
```

---

## 开发计划

### Phase 1：基础框架（1-2天）
- [ ] 初始化 Vue 3 + Naive UI 项目
- [ ] 初始化 FastAPI 项目
- [ ] 配置 SQLAlchemy 2.0 映射 state.db
- [ ] 配置跨域、路由
- [ ] 实现基础 API（健康检查）
- [ ] 配置 APScheduler

### Phase 2：Session 管理（1天）
- [ ] 实现 Session 列表 API
- [ ] 实现 Session 详情 API
- [ ] 实现最新微信 Session API
- [ ] 前端 Session 列表页面

### Phase 3：消息管理（1-2天）
- [ ] 实现消息列表 API
- [ ] 实现消息发送 API
- [ ] 实现主动消息发送 API
- [ ] 前端消息历史页面
- [ ] 前端消息发送页面

### Phase 4：LLM 配置（1天）
- [ ] 实现 LLM 配置 API
- [ ] 实现 LLM 连通性测试
- [ ] 实现 LLM 生成 API
- [ ] 前端 LLM 配置页面

### Phase 5：提示词配置（1天）
- [ ] 实现提示词读取 API
- [ ] 实现提示词更新 API
- [ ] 实现 hermes 配置读取
- [ ] 前端提示词配置页面

### Phase 6：定时任务（1天）
- [ ] 集成 APScheduler
- [ ] 实现定时任务 CRUD API
- [ ] 实现任务运行/暂停/恢复 API
- [ ] 前端定时任务页面

### Phase 7：监控统计（1天）
- [ ] 实现统计 API
- [ ] 前端监控面板
- [ ] 图表展示（ECharts）

### Phase 8：测试工具（1天）
- [ ] 实现测试 API
- [ ] 前端测试页面
- [ ] 完整流程测试

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

### 1. 数据库只读
- state.db 只读，不写入任何数据
- 上下文注入通过 hermes 的 SessionDB API

### 2. 配置隔离
- 本系统配置存储在 `~/.hermes/hermes-active/config.yaml`
- 不污染 hermes 的 config.yaml 和 .env

### 3. LLM 调用
- 默认使用 hermes 的 `call_llm`
- 自定义配置时使用 OpenAI SDK

### 4. 消息发送
- 直接调用 `send_weixin_direct`，不需要配置微信参数
- 写入 session DB 时使用带标记格式

### 5. 定时任务
- 使用 APScheduler 独立管理
- 不与 hermes cron 混在一起

---

## 参考资料

- [Hermes Agent 官方文档](https://hermes-agent.nousresearch.com/docs)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Vue 3 文档](https://vuejs.org/)
- [Naive UI 文档](https://www.naiveui.com/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/)
- [APScheduler 文档](https://apscheduler.readthedocs.io/)
