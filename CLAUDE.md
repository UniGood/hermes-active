# hermes-active

Hermes 主动会话系统 - 基于 WebUI 的主动消息管理平台

## 项目结构

```
hermes-active/
├── backend/           # FastAPI 后端
├── frontend/          # Vue 3 前端
├── data/              # 独立数据库（任务执行记录、登录信息）
├── docs/              # 设计文档
└── scripts/           # 脚本工具
```

## 核心原则

1. **数据库只读**：只读取 hermes 的 state.db，不写入（除了上下文注入）
2. **配置隔离**：本系统配置独立存储，不污染 hermes 配置
3. **LLM 调用**：默认用 hermes 的 call_llm，支持自定义配置
4. **定时任务**：APScheduler 独立管理，不混入 hermes cron
5. **平台适配**：支持微信、飞书等多平台

## 技术栈

- 前端：Vue 3 + Vue Router + Naive UI + ECharts
- 后端：FastAPI + SQLAlchemy 2.0 + APScheduler
- 数据库：state.db（只读）+ active.db（独立，存储任务记录和登录信息）

## 启动方式

```bash
# 后端
cd backend && python main.py

# 前端（开发模式）
cd frontend && npm run dev
```

## 端口

- 后端 API：8080
- 前端开发：5173
