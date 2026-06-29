# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Hermes Active 是 Hermes Agent 的主动会话管理系统，提供 Web UI 界面来管理消息、监控状态、配置定时任务等。

## 开发命令

```bash
# 后端启动（端口 18720）
cd backend && python main.py

# 前端开发（端口 5173，自动代理 /api 到后端）
cd frontend && npm run dev

# 前端构建
cd frontend && npm run build

# 安装依赖
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

## 架构概览

### 双数据库设计

- `~/.hermes/state.db`：只读，Hermes 主系统的状态数据
- `data/active.db`：读写，本系统独立数据（用户、任务日志、配置等）

### 后端架构 (FastAPI)

```
backend/
├── main.py              # 入口，FastAPI 应用初始化
├── config.py            # 配置常量（端口、路径、默认值）
├── routers/             # API 路由层
│   ├── auth.py          # 认证相关
│   ├── sessions.py      # 会话管理
│   ├── messages.py      # 消息操作
│   ├── active_consciousness.py   # 主动意识系统
│   ├── passive_consciousness.py  # 被动意识系统
│   └── cron.py          # 定时任务管理
├── services/            # 业务逻辑层
│   ├── active_consciousness_service.py  # 主动意识核心逻辑
│   ├── scheduler_service.py             # APScheduler 调度
│   └── session_service.py               # 会话处理
└── models/              # 数据模型
    ├── database.py      # SQLAlchemy 引擎和会话管理
    ├── active.py        # active.db 表定义
    └── schemas.py       # Pydantic 模型
```

### 前端架构 (Vue 3)

```
frontend/src/
├── views/               # 页面组件
│   ├── ActiveConsciousness.vue    # 主动意识管理
│   ├── PassiveConsciousness.vue   # 被动意识管理
│   ├── CronJobs.vue               # 定时任务
│   ├── Sessions.vue               # 会话列表
│   └── Messages.vue               # 消息管理
├── api/                 # API 调用封装
│   ├── http.js          # Axios 实例和拦截器
│   └── *.js             # 各模块 API
├── router/index.js      # Vue Router 配置
├── components/          # 通用组件
└── store/               # Pinia 状态管理
```

## 核心原则

1. **数据库只读**：只读取 hermes 的 state.db，不写入
2. **配置隔离**：本系统配置独立存储在 active.db，不污染 hermes 配置
3. **LLM 调用**：默认用 hermes 的 call_llm，支持自定义配置
4. **定时任务**：APScheduler 独立管理，不混入 hermes cron

## 关键配置

- JWT 密钥：环境变量 `JWT_SECRET_KEY` 或默认值
- 默认管理员：`admin` / `admin`
- Hermes 路径：`~/.hermes/`（SOUL.md、MEMORY.md、config.yaml）

## 认证机制

使用 JWT Token，前端通过 `localStorage` 存储，路由守卫在 `router/index.js` 中实现。API 请求通过 `api/http.js` 的 Axios 拦截器自动添加 Authorization header。

## 版本历史

| 版本 | 说明 | 状态 |
|------|------|------|
| v0.1 | 基础版本 — Web UI、定时任务、消息管理 | ✅ 完成 |
| v0.2.1 | 主动意识 — 情绪演化、念头生成、决策矩阵 | 🚧 开发中 |
| v0.2.2 | 被动意识 — 上下文注入、Hindsight 集成 | 🚧 开发中 |

## 文档结构

```
docs/
├── README.md                    # 文档索引
├── deployment.md                # 部署指南
├── design-v0.1.md               # v0.1 设计文档
├── design-v0.2.md               # v0.2 设计愿景
├── v0.2/                        # 意识系统设计
│   ├── passive-consciousness-design.md  # 被动意识设计 (v0.2.2)
│   └── ...
├── v0.2.1/                      # 主动意识详细设计
│   ├── architecture-and-flow.md
│   ├── implementation-status.md
│   └── ...
└── archive/                     # 历史文档存档
```

## 核心概念

### 主动意识 (v0.2.1)

心跳调度器定期触发，生成"念头"并决定是否发送消息：
- 情绪系统：VA 模型（Valence/Arousal/Social Need），支持演化、LLM 评估、动态合并
- 决策矩阵：多维度评分（情绪强度 × 时间权重 × 沉默时长 × 频率限制）
- 念头类型：time、silence、assoc、memory、emotion、env
- 延迟队列：中分念头入队，后续心跳重评估

### 被动意识 (v0.2.2)

用户消息到达时，自动注入上下文信息到系统提示词：
- 想念分数：基于用户最后消息时间计算
- 聊天热度：消息密度（count ÷ hours）
- Hindsight 集成：Recall（记忆召回）+ Reflect（综合分析）
- 天气感知：高德地图 API