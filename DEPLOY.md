# Hermes Active - 部署指南

## 系统要求

- Python 3.10+
- Node.js 18+
- npm 9+
- Hermes Agent 已安装并配置

## 快速部署

### 1. 克隆仓库

```bash
cd ~/.hermes
git clone https://github.com/UniGood/hermes-active.git
cd hermes-active
```

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 安装前端依赖

```bash
cd ../frontend
npm install
```

### 4. 创建数据目录

```bash
mkdir -p ~/.hermes/hermes-active/data
```

### 5. 启动服务

**启动后端（端口 18720）：**

```bash
cd ~/.hermes/hermes-active/backend
python3 main.py
```

**启动前端（端口 5173）：**

```bash
cd ~/.hermes/hermes-active/frontend
npm run dev -- --host 0.0.0.0
```

### 6. 访问系统

- **前端地址**：`http://<服务器IP>:5173`
- **后端地址**：`http://<服务器IP>:18720`
- **默认账号**：`admin` / `admin`

---

## 后台运行（推荐）

### 使用 nohup

```bash
# 启动后端
cd ~/.hermes/hermes-active/backend
nohup python3 main.py > ~/.hermes/hermes-active/logs/backend.log 2>&1 &
echo $! > ~/.hermes/hermes-active/backend.pid

# 启动前端
cd ~/.hermes/hermes-active/frontend
nohup npm run dev -- --host 0.0.0.0 > ~/.hermes/hermes-active/logs/frontend.log 2>&1 &
echo $! > ~/.hermes/hermes-active/frontend.pid
```

### 停止服务

```bash
# 停止后端
kill $(cat ~/.hermes/hermes-active/backend.pid)

# 停止前端
kill $(cat ~/.hermes/hermes-active/frontend.pid)
```

### 查看日志

```bash
# 后端日志
tail -f ~/.hermes/hermes-active/logs/backend.log

# 前端日志
tail -f ~/.hermes/hermes-active/logs/frontend.log
```

---

## systemd 服务（生产环境）

### 后端服务

创建 `/etc/systemd/system/hermes-active-backend.service`：

```ini
[Unit]
Description=Hermes Active Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/.hermes/hermes-active/backend
ExecStart=/home/ubuntu/.hermes/hermes-agent/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 前端服务

创建 `/etc/systemd/system/hermes-active-frontend.service`：

```ini
[Unit]
Description=Hermes Active Frontend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/.hermes/hermes-active/frontend
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 启用服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable hermes-active-backend
sudo systemctl enable hermes-active-frontend
sudo systemctl start hermes-active-backend
sudo systemctl start hermes-active-frontend
```

### 查看状态

```bash
sudo systemctl status hermes-active-backend
sudo systemctl status hermes-active-frontend
```

---

## 防火墙配置

```bash
# 开放端口
sudo ufw allow 5173/tcp  # 前端
sudo ufw allow 18720/tcp  # 后端

# 重载防火墙
sudo ufw reload
```

---

## 配置说明

### LLM 配置

系统支持两种 LLM 模式：

1. **Hermes 模式**（默认）：使用 `from agent.auxiliary_client import call_llm` 调用 Hermes 的 LLM
2. **自定义模式**：配置独立的 provider、model、api_key、base_url

### 数据存储

- **state.db**（只读）：Hermes 的会话和消息数据库
- **active.db**（读写）：本系统的用户、任务日志、配置存储

路径：`~/.hermes/hermes-active/data/active.db`

### 定时任务

使用 APScheduler 独立管理，不与 Hermes 的 cron 系统混用。

配置存储在 `active.db` 的 `cron_jobs` 表中。

---

## 目录结构

```
~/.hermes/hermes-active/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 入口
│   ├── config.py               # 配置
│   ├── requirements.txt        # 依赖
│   ├── middleware/             # 中间件
│   ├── models/                 # 数据模型
│   ├── routers/                # API 路由
│   └── services/               # 业务逻辑
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── views/             # 页面组件
│   │   ├── components/        # 公共组件
│   │   ├── api/               # API 接口
│   │   ├── router/            # 路由
│   │   └── store/             # 状态管理
│   ├── package.json
│   └── vite.config.js
├── data/                       # 数据目录
│   └── active.db              # 本系统数据库
├── docs/                       # 文档
│   └── design-v0.1.md         # 设计文档
├── scripts/                    # 脚本
├── DEPLOY.md                   # 部署文档（本文件）
└── README.md                   # 项目说明
```

---

## API 文档

后端启动后访问：`http://<服务器IP>:18720/docs`

### 主要 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 登录 |
| `/api/auth/change-password` | POST | 修改密码 |
| `/api/sessions` | GET | Session 列表 |
| `/api/sessions/{id}` | GET | Session 详情 |
| `/api/sessions/latest/{platform}` | GET | 最新平台 Session |
| `/api/messages/{session_id}` | GET | 消息列表 |
| `/api/messages/send` | POST | 发送消息 |
| `/api/config/llm` | GET/PUT | LLM 配置 |
| `/api/config/prompts` | GET/PUT | 提示词配置 |
| `/api/llm/test` | POST | LLM 连通性测试 |
| `/api/llm/generate` | POST | 生成消息 |
| `/api/cron` | GET/POST | 定时任务 |
| `/api/task-logs` | GET | 任务日志 |
| `/api/stats/overview` | GET | 统计总览 |

---

## 故障排查

### bcrypt 版本冲突

```bash
pip install bcrypt==4.0.1
pip install passlib==1.7.4
```

### 前端无法访问

1. 检查防火墙是否开放 5173 端口
2. 确认前端服务已启动：`ps aux | grep vite`
3. 检查日志：`tail -f ~/.hermes/hermes-active/logs/frontend.log`

### 后端 API 返回 403

1. 确认 Token 未过期
2. 重新登录获取新 Token

### 数据库锁定

```bash
# 检查是否有进程占用
lsof ~/.hermes/state.db

# 重启后端服务
kill $(cat ~/.hermes/hermes-active/backend.pid)
cd ~/.hermes/hermes-active/backend && python3 main.py &
```
