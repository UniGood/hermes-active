# Hermes Active

Hermes Agent 主动会话系统 — Web UI 管理界面

## 功能

- 📊 **监控面板**：消息统计、最近对话、平台分布
- 💬 **消息管理**：Session 列表、消息历史、消息发送
- ⚙️ **配置管理**：LLM 配置、提示词配置、密码修改
- ⏰ **定时任务**：APScheduler 独立管理
- 📝 **任务日志**：任务执行记录查看
- 🧪 **测试工具**：上下文读取、消息发送、LLM 生成

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | Vue 3 + Naive UI + Vue Router |
| 后端 | FastAPI + SQLAlchemy 2.0 |
| 数据库 | SQLite（state.db 只读 + active.db 读写） |
| 定时任务 | APScheduler |
| 认证 | JWT Token |

## 快速开始

```bash
# 克隆
git clone https://github.com/UniGood/hermes-active.git
cd hermes-active

# 安装依赖
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# 启动
cd backend && python3 main.py &
cd frontend && npm run dev -- --host 0.0.0.0 &
```

**访问**：`http://<服务器IP>:5173`
**账号**：`admin` / `admin`

详细部署说明见 [DEPLOY.md](./DEPLOY.md)

## 目录结构

```
hermes-active/
├── backend/        # FastAPI 后端
├── frontend/       # Vue 3 前端
├── data/           # 数据目录（active.db）
├── docs/           # 设计文档
├── scripts/        # 脚本
├── DEPLOY.md       # 部署文档
└── README.md       # 本文件
```

## License

MIT
