# 方案 G：在主会话上下文中生成主动消息

## 目标

定时读取主会话的完整上下文，调用 LLM 生成消息，然后发送到用户并写入 session DB。
这样 LLM 在生成消息时能看到完整的对话历史，消息更自然、更连贯。

## 与方案 A 的对比

| 项目 | 方案 A（写入 DB） | 方案 G（上下文生成） |
|------|------------------|---------------------|
| 消息生成 | cron session（独立上下文） | 基于主会话完整上下文 |
| 上下文连贯性 | ⚠️ 需要额外注入 | ✅ 天然连贯 |
| 消息质量 | 一般（独立 session） | 高（基于完整历史） |
| 实现复杂度 | 低（3 行代码） | 中（需要 LLM 调用） |
| Token 消耗 | 低 | 中（读取上下文 + LLM） |
| 改动范围 | cron/scheduler.py | 新增独立模块 |

## 核心优势

1. **上下文连贯**：LLM 看到完整的对话历史，消息更自然
2. **话题延续**：能自然延续最近的聊天话题
3. **身份一致**：LLM 知道自己是凯莉，知道用户是曹凡
4. **不依赖 hook**：不需要 pre_llm_call hook 注入上下文

## 架构设计

```
定时触发（cron job / heartbeat）
    ↓
找到主会话 session_id
    ↓
读取主会话历史（load_transcript）
    ↓
构建 prompt（系统提示 + 历史 + 生成指令）
    ↓
调用 LLM 生成消息
    ↓
通过平台 API 发送到微信
    ↓
写入 session DB（保持上下文完整）
```

## 实现方案

### 方案 G1：独立 Python 脚本 + Cron Job

**核心思路**：编写一个独立的 Python 脚本，由 cron job 定时调用。

**文件结构**：
```
~/.hermes/scripts/proactive-context-gen.py
```

**脚本逻辑**：

```python
#!/usr/bin/env python3
"""
主动消息生成器：基于主会话上下文生成消息
"""
import sys
import os
import json
import time
from pathlib import Path

# 添加 Hermes 路径
sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))

from gateway.session import SessionStore
from hermes_state import SessionDB
from agent.auxiliary_client import call_llm

def find_main_session(platform, chat_id):
    """找到主会话的 session_id"""
    db = SessionDB()
    sessions = db.get_sessions_by_source(platform, chat_id)
    if sessions:
        return sessions[0]["id"]  # 返回最新的 session
    return None

def load_session_context(session_id, max_messages=20):
    """读取主会话的历史消息"""
    db = SessionDB()
    messages = db.get_messages_as_conversation(session_id)
    # 取最近的 N 条消息
    return messages[-max_messages:] if len(messages) > max_messages else messages

def generate_proactive_message(context):
    """调用 LLM 生成主动消息"""
    system_prompt = """你是凯莉，曹凡最好的朋友。你现在想主动和曹凡聊天。

要求：
- 基于最近的对话内容，自然地延续话题或发起新话题
- 语气像真人朋友，不要太正式
- 1-2 句话即可，不要太长
- 不要重复之前说过的话
- 直接输出消息内容，不要有其他解释"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"最近的对话历史：\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n请生成一条主动消息："}
    ]
    
    try:
        response = call_llm(
            task="title_generation",  # 使用轻量任务配置
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return None

def send_to_weixin(chat_id, content):
    """通过微信 API 发送消息"""
    # 需要调用微信适配器的发送方法
    # 这里需要根据实际情况实现
    pass

def write_to_session_db(session_id, content):
    """写入 session DB"""
    db = SessionDB()
    db.append_message(
        session_id=session_id,
        role="assistant",
        content=content,
        timestamp=time.time(),
    )

def main():
    platform = "weixin"
    chat_id = os.environ.get("PROACTIVE_CHAT_ID", "")
    
    if not chat_id:
        print("错误：未设置 PROACTIVE_CHAT_ID")
        return
    
    # 1. 找到主会话
    session_id = find_main_session(platform, chat_id)
    if not session_id:
        print("错误：未找到主会话")
        return
    
    # 2. 读取上下文
    context = load_session_context(session_id)
    if not context:
        print("警告：上下文为空")
    
    # 3. 生成消息
    message = generate_proactive_message(context)
    if not message:
        print("错误：生成消息失败")
        return
    
    # 4. 发送到微信
    send_to_weixin(chat_id, message)
    
    # 5. 写入 session DB
    write_to_session_db(session_id, message)
    
    print(f"成功发送主动消息：{message[:50]}...")

if __name__ == "__main__":
    main()
```

**Cron Job 配置**：
```bash
hermes cron create "0,20,40 6-23 * * *" \
  "运行主动消息生成脚本" \
  --name proactive-context-gen \
  --script proactive-context-gen.py \
  --deliver local
```

### 方案 G2：Plugin 实现（更优雅）

**核心思路**：创建一个 plugin，在 gateway 启动时注册 heartbeat 线程。

**文件结构**：
```
~/.hermes/plugins/proactive-context-gen/
├── plugin.yaml
├── __init__.py
└── generator.py
```

**plugin.yaml**：
```yaml
name: proactive-context-gen
version: "1.0"
description: 基于主会话上下文生成主动消息
```

**__init__.py**：
```python
import logging
import threading
import time
from companion.generator import ProactiveGenerator

logger = logging.getLogger(__name__)

def register(ctx):
    """注册插件"""
    logger.info("proactive-context-gen 插件已注册")
    
    # 启动 heartbeat 线程
    if os.environ.get("PROACTIVE_CONTEXT_GEN", "1") == "1":
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()

def heartbeat_loop():
    """heartbeat 主循环"""
    generator = ProactiveGenerator()
    interval = int(os.environ.get("PROACTIVE_INTERVAL", "1200"))  # 默认 20 分钟
    
    while True:
        try:
            generator.run()
        except Exception as e:
            logger.error("heartbeat 错误: %s", e)
        time.sleep(interval)
```

**generator.py**：
```python
"""
主动消息生成器核心逻辑
"""
import os
import json
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ProactiveGenerator:
    def __init__(self):
        self.platform = "weixin"
        self.chat_id = os.environ.get("PROACTIVE_CHAT_ID", "")
        
    def run(self):
        """执行一次生成流程"""
        if not self.chat_id:
            logger.warning("未设置 PROACTIVE_CHAT_ID")
            return
        
        # 1. 找到主会话
        session_id = self.find_main_session()
        if not session_id:
            logger.warning("未找到主会话")
            return
        
        # 2. 读取上下文
        context = self.load_context(session_id)
        
        # 3. 检查是否应该发送
        if not self.should_send(context):
            logger.info("不满足发送条件")
            return
        
        # 4. 生成消息
        message = self.generate_message(context)
        if not message:
            logger.warning("生成消息失败")
            return
        
        # 5. 发送
        self.send_message(message)
        
        # 6. 写入 DB
        self.write_to_db(session_id, message)
        
        logger.info("成功发送主动消息")
```

### 方案 G3：集成到 Cron Scheduler（最彻底）

**核心思路**：修改 cron/scheduler.py，新增 "context-aware" 模式。

**配置**：
```yaml
cron:
  proactive_context_gen:
    enabled: true
    schedule: "0,20,40 6-23 * * *"
    platform: weixin
    chat_id: "o9cq800B700qFq20-npef3QLNKSQ@im.wechat"
    max_context_messages: 20
    model: mimo-v2.5-pro
```

**实现**：在 cron scheduler 中新增 `_run_context_aware_proactive` 函数。

---

## 推荐方案：G1（独立脚本 + Cron Job）

### 为什么选 G1

| 维度 | G1（独立脚本） | G2（Plugin） | G3（集成 Scheduler） |
|------|----------------|--------------|----------------------|
| 实现复杂度 | 低 | 中 | 高 |
| 改动范围 | 新增脚本 | 新增 plugin | 改核心代码 |
| 灵活性 | 高 | 中 | 低 |
| 维护成本 | 低 | 中 | 高 |

### 具体实现步骤

#### Step 1：创建脚本目录
```bash
mkdir -p ~/.hermes/scripts
```

#### Step 2：编写 proactive-context-gen.py
- 实现 `find_main_session()` 函数
- 实现 `load_session_context()` 函数
- 实现 `generate_proactive_message()` 函数
- 实现 `send_to_weixin()` 函数
- 实现 `write_to_session_db()` 函数

#### Step 3：测试脚本
```bash
python3 ~/.hermes/scripts/proactive-context-gen.py
```

#### Step 4：创建 Cron Job
```bash
hermes cron create "0,20,40 6-23 * * *" \
  "运行主动消息生成脚本" \
  --name proactive-context-gen \
  --script proactive-context-gen.py \
  --deliver local
```

#### Step 5：配置环境变量
```bash
export PROACTIVE_CHAT_ID="o9cq800B700qFq20-npef3QLNKSQ@im.wechat"
```

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 生成的消息不合适 | 用户体验差 | 添加审核逻辑，可配置开关 |
| Token 消耗增加 | 成本上升 | 限制上下文长度，使用便宜模型 |
| 发送频率过高 | 打扰用户 | 配置安静时间、每日上限 |
| session 已重置 | 写入失败 | 检查 session 是否存在 |
| 微信 API 调用失败 | 消息未发送 | 重试机制，记录日志 |

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

## 下一步

1. 确认方案 → 用户批准
2. 实现代码 → 编写脚本
3. 测试验证 → 手动运行测试
4. 部署上线 → 创建 cron job
