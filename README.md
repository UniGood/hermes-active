# Hermes Active

Hermes Agent 主动会话系统 — Web UI 管理界面

## 功能

- 📊 **监控面板**：消息统计、最近对话、平台分布
- 💬 **消息管理**：Session 列表、消息历史、消息发送
- ⚙️ **配置管理**：LLM 配置、提示词配置、Hindsight 配置、天气配置
- 💓 **主动意识**：心跳触发、情绪演化、念头生成、决策矩阵
- 💡 **被动意识**：用户消息时注入上下文（情绪/热度/记忆/天气）
- ⏰ **定时任务**：APScheduler 独立管理，支持 cron 表达式
- 📝 **任务日志**：任务执行记录查看
- 🧪 **测试工具**：上下文读取、消息发送、LLM 生成

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | Vue 3 + Naive UI + Vue Router + Pinia |
| 后端 | FastAPI + SQLAlchemy 2.0 |
| 数据库 | SQLite（state.db 只读 + active.db 读写） |
| 定时任务 | APScheduler |
| 认证 | JWT Token |
| 记忆系统 | Hindsight SDK |
| 天气 API | 高德地图 |

## 快速开始

```bash
# 克隆
git clone https://github.com/UniGood/hermes-active.git
cd hermes-active

# 安装依赖
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# 启动
cd backend && python main.py &
cd frontend && npm run dev -- --host 0.0.0.0 &
```

**访问**：`http://<服务器IP>:5173`
**账号**：`admin` / `admin`

详细部署说明见 [docs/deployment.md](./docs/deployment.md)

## 目录结构

```
hermes-active/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 入口
│   ├── config.py               # 配置常量
│   ├── models/                 # 数据模型
│   │   ├── active.py           # active.db 表定义
│   │   ├── active_consciousness.py  # 主动意识模型
│   │   ├── passive_consciousness.py # 被动意识模型
│   │   ├── database.py         # 数据库连接
│   │   └── schemas.py          # Pydantic 模型
│   ├── routers/                # API 路由
│   │   ├── active_consciousness.py
│   │   ├── passive_consciousness.py
│   │   ├── auth.py
│   │   ├── sessions.py
│   │   ├── messages.py
│   │   ├── config.py
│   │   ├── cron.py
│   │   └── ...
│   ├── services/               # 业务逻辑
│   │   ├── active_consciousness_service.py
│   │   ├── passive_consciousness_service.py
│   │   ├── scheduler_service.py
│   │   ├── weather_service.py
│   │   └── ...
│   ├── middleware/              # 中间件
│   └── tests/                  # 测试
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── api/                # API 封装
│       ├── views/              # 页面组件
│       ├── components/         # 通用组件
│       ├── store/              # Pinia 状态
│       ├── composables/        # 组合式函数
│       └── router/             # 路由配置
├── data/                       # 数据目录（active.db）
├── docs/                       # 设计文档
├── scripts/                    # 脚本
└── README.md                   # 本文件
```

## 版本历史

| 版本 | 说明 | 状态 |
|------|------|------|
| v0.1 | 基础版本 — Web UI、定时任务、消息管理 | ✅ 完成 |
| v0.2.1 | 主动意识 — 情绪演化、念头生成、决策矩阵 | ✅ 完成 |
| v0.2.2 | 被动意识 — 上下文注入、Hindsight 集成 | 🚧 开发中 |

## 核心概念

### 主动意识

心跳调度器定期触发，生成"念头"并决定是否发送消息：

```
心跳触发 → 读取状态 → 情绪演化 → LLM 评估 → 合并情绪
    → 生成念头 → 决策评分 → 发送/延迟/存储
```

### 被动意识

用户消息到达时，自动注入上下文信息到系统提示词：

```
用户消息 → 计算想念分数 → 计算聊天热度 → 获取天气
    → Hindsight Recall → 拼装上下文 → 注入系统提示词
```

### 情绪模型 (VA Model)

- **Valence**（效价）：情感的正负性，0=消极，1=积极
- **Arousal**（唤醒度）：情感的激活程度，0=平静，1=激动
- **Social Need**（社交需求）：想要社交的程度，0=不需要，1=非常想

## 文档

详见 [docs/README.md](./docs/README.md)

## License

MIT
