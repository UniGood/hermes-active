# 主动消息 Session 过期处理方案

## 问题描述

定时任务发送主动消息时，可能当前活跃的 session 已经过期（如过了凌晨4点），导致：

1. 主动消息被写入**旧 session**
2. 用户在微信发消息时，gateway 检测到 session 过期，创建**新 session**
3. hermes 从新 session 的上下文中**找不到**主动消息
4. 上下文断裂，hermes 不知道自己之前说过什么

## 数据流对比

### 当前（有问题）
```
定时任务 → get_latest_session("weixin") → state.db 按 started_at DESC 取第一条
         → 可能拿到已过期的旧 session
         → 主动消息写入旧 session ❌
```

### 改造后
```
定时任务 → 从 sessions.json 获取 user_id
         → 构造 SessionSource(platform="weixin", chat_id=user_id, chat_type="dm")
         → 调用 SessionStore.get_or_create_session(source)
         → 自动检查过期 → 过期则创建新 session
         → 主动消息写入正确的 session ✅
```

## 技术方案

### 1. 获取 user_id

**来源：`~/.hermes/sessions/sessions.json`**

这是 gateway 维护的实时数据，包含每个 session 的 `origin` 信息：

```json
{
  "agent:main:weixin:dm:o9cq800B700qFq20-npef3QLNKSQ@im.wechat": {
    "session_id": "20260613_084937_462becfb",
    "platform": "weixin",
    "chat_type": "dm",
    "origin": {
      "platform": "weixin",
      "chat_id": "o9cq800B700qFq20-npef3QLNKSQ@im.wechat",
      "user_id": "o9cq800B700qFq20-npef3QLNKSQ@im.wechat"
    }
  }
}
```

**微信 user_id 特点：**
- 格式：`o9cq800B700qFq20-npef3QLNKSQ@im.wechat`（open_id 格式）
- 稳定性：正常使用下不会变化（实测 2 周+无变化）
- 唯一性：一个用户只有一个 user_id

### 2. 构造 SessionSource

```python
from gateway.session import SessionSource
from gateway.config import Platform

source = SessionSource(
    platform=Platform.WEIXIN,     # "weixin"
    chat_id=user_id,              # 从 sessions.json 获取
    chat_type="dm",               # 固定私聊
    user_id=user_id,              # 私聊时 = chat_id
)
```

### 3. 调用 get_or_create_session

```python
from gateway.session import SessionStore
from gateway.config import GatewayConfig

# 初始化 SessionStore
store = SessionStore(
    sessions_dir=Path.home() / '.hermes' / 'sessions',
    config=config
)

# 自动处理过期 + 创建
entry = store.get_or_create_session(source)
session_id = entry.session_id
```

**关键行为：**
- session 没过期 → 返回现有 session
- session 过期 → 创建新 session，写入 state.db + sessions.json
- 下次 gateway 调用同一方法时，会读到这个新 session，不会重复创建

## 需要修改的文件

### 文件 1：`backend/services/session_service.py`

新增两个方法：

```python
@staticmethod
def get_weixin_user_id() -> Optional[str]:
    """从 sessions.json 获取微信用户的 user_id"""
    import json
    sessions_file = Path.home() / '.hermes' / 'sessions' / 'sessions.json'
    if not sessions_file.exists():
        return None
    
    with open(sessions_file) as f:
        sessions = json.load(f)
    
    # 找最新的微信私聊 session
    for key, entry in sessions.items():
        if (entry.get('platform') == 'weixin' 
            and entry.get('chat_type') == 'dm'):
            return entry['origin']['user_id']
    return None

@staticmethod
def get_or_create_active_session(platform: str, user_id: str) -> Optional[Dict[str, Any]]:
    """获取或创建活跃 session（模拟 gateway 行为）"""
    import sys
    sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
    
    from gateway.session import SessionStore, SessionSource
    from gateway.config import GatewayConfig, Platform
    import yaml
    
    # 加载配置
    with open(Path.home() / '.hermes' / 'config.yaml') as f:
        config = GatewayConfig.from_dict(yaml.safe_load(f))
    
    # 创建 SessionStore
    store = SessionStore(
        sessions_dir=Path.home() / '.hermes' / 'sessions',
        config=config
    )
    
    # 构造 SessionSource
    source = SessionSource(
        platform=Platform(platform),
        chat_id=user_id,
        chat_type="dm",
        user_id=user_id,
    )
    
    # 调用 gateway 的方法（自动处理过期 + 创建）
    entry = store.get_or_create_session(source)
    
    return {
        "id": entry.session_id,
        "source": platform,
        "user_id": user_id,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "was_auto_reset": entry.was_auto_reset,
        "auto_reset_reason": entry.auto_reset_reason,
    }
```

### 文件 2：`backend/services/scheduler_service.py`

修改 `run_cron_job()` 中获取 session 的逻辑（约第 90-108 行）：

```python
# 原来的逻辑
session_id = target_job.get("session_id")
platform = target_job.get("platform", "weixin")

if session_id:
    session = SessionService.get_session_by_id(db, session_id)
else:
    session = SessionService.get_latest_session(platform)

# 改为
session_id = target_job.get("session_id")
platform = target_job.get("platform", "weixin")

if session_id:
    # 指定 session_id 的情况，直接使用
    session = SessionService.get_session_by_id(db, session_id)
else:
    # 使用 get_or_create 自动处理过期
    user_id = SessionService.get_weixin_user_id()
    if not user_id:
        logger.error(f"任务 {target_job['name']} 未找到微信用户 ID")
        MessageService.create_task_log(
            task_type="cron_run",
            status="failed",
            message=f"任务 {target_job['name']} 运行失败",
            error="未找到微信用户 ID（sessions.json 中无 weixin dm session）",
            duration=round(datetime.now().timestamp() - start_time, 2)
        )
        return
    
    session = SessionService.get_or_create_active_session(
        platform=platform,
        user_id=user_id
    )
    
    if session and session.get("was_auto_reset"):
        logger.info(f"Session 已自动重置（原因: {session.get('auto_reset_reason')}），新 session: {session['id']}")
```

### 文件 3：`backend/routers/messages.py`

手动发送消息时也加检查（可选，优先级较低）。

## 验证步骤

1. **正常场景**：session 未过期时发送消息，行为不变
2. **过期场景**：
   - 等待凌晨 4 点后，或手动修改 session 的 updated_at
   - 触发定时任务
   - 检查日志是否显示 "Session 已自动重置"
   - 检查主动消息是否写入新 session
3. **用户回复场景**：
   - 定时任务发送主动消息后
   - 用户在微信发消息
   - 检查 hermes 是否能从上下文中看到主动消息

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| sessions.json 并发写入 | 低 | 中 | session 重置一天只发生一次，冲突概率极低 |
| user_id 变化 | 极低 | 高 | 微信 open_id 正常使用下稳定，变化需要重新配置 |
| SessionStore 初始化失败 | 低 | 中 | 添加异常处理，失败时回退到原有逻辑 |

## 回滚方案

如果出现问题，回滚方式：
1. `git checkout backend/services/session_service.py`
2. `git checkout backend/services/scheduler_service.py`
3. 重启后端服务
