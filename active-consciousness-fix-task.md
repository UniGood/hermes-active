# Task: 修复主动意识闭环 + LLM请求日志记录

## 目标
1. 修复情绪值从未更新的问题（闭环断裂）
2. 每次心跳的LLM请求参数、推理过程、响应都要记录到心跳日志的details字段

## STRICT RULES
- ONLY modify the files listed below
- Do NOT modify config.yaml, .env, vite.config.js
- Do NOT run git commands
- Do NOT delete any files

## 问题分析

### 问题1：情绪值从未更新
当前代码在 `active_consciousness_service.py` 的 `get_status()` 中读取情绪值：
```python
val = ConfigService.get_config(db, "active_consciousness.current.emotional_intensity")
```
但**没有任何地方写入/更新这个值**，导致情绪值永远是 0.0。

**解决方案**：在心跳流程 `run_heartbeat()` 中，当想法生成成功后，让LLM评估情绪值并更新到configs表。

### 问题2：LLM请求日志缺失
当前 `active_heartbeat_logs` 表有 `details` 字段（或需要添加），但没有记录LLM的请求参数和响应。

**解决方案**：在 `generate_thought()` 函数中，记录完整的LLM调用过程：
- 请求参数（model, temperature, max_tokens, prompt）
- 响应内容（thought文本）
- 耗时（llm_duration）
- 错误信息（如果有）

## Files to Modify

### File 1: `backend/models/active_consciousness.py`
检查 `HeartbeatLog` 模型是否有 `details` 字段，如果没有则添加：
```python
details = Column(Text, nullable=True)  # JSON格式的详细日志
```

### File 2: `backend/services/active_consciousness_service.py`

#### 修改1: `generate_thought()` 函数
在函数中记录完整的LLM调用过程，返回值增加 `llm_details` 字段：
```python
return {
    "thought": thought,
    "recall_count": recall_count,
    "reflect_count": reflect_count,
    "llm_duration": llm_duration,
    "llm_details": {
        "model": llm_config.get("model"),
        "temperature": 0.9,
        "max_tokens": 200,
        "prompt_preview": prompt[:500],  # 前500字符
        "response": thought,
        "error": error_msg if error else None
    }
}
```

#### 修改2: `run_heartbeat()` 函数
在想法生成后，调用LLM评估情绪值并更新：
```python
# 评估情绪值
if thought:
    emotional_score = await evaluate_emotional_intensity(thought, status)
    # 更新到configs表
    ConfigService.set_config(db, "active_consciousness.current.emotional_intensity", str(emotional_score))
```

#### 修改3: 新增 `evaluate_emotional_intensity()` 函数
让LLM根据生成的想法和当前状态评估情绪值（0.0-1.0）：
```python
async def evaluate_emotional_intensity(thought: str, status: Dict[str, Any]) -> float:
    """让LLM评估当前情绪强度"""
    prompt = f"""根据以下想法和状态，评估情绪强度（0.0-1.0）：
    
想法：{thought}
想念分数：{status['longing'].get('score', 0)}
聊天热度：{status['chat_heat'].get('heat', 0)}

只返回一个0.0-1.0的数字，不要解释。"""
    
    # 调用LLM获取数字
    # 解析并返回float
```

#### 修改4: `write_heartbeat_log()` 函数
增加 `details` 参数，记录完整的LLM调用详情：
```python
@staticmethod
def write_heartbeat_log(
    started_at: str,
    duration_ms: int,
    # ... 其他参数 ...
    details: Optional[str] = None  # 新增：JSON格式的详细日志
) -> int:
```

#### 修改5: `generate_and_send_thought()` 函数
收集所有LLM调用的details，传递给心跳日志：
```python
async def generate_and_send_thought(config, status, decision_type, heartbeat_id=None):
    thought_result = await generate_thought(config, status)
    
    # 收集details
    details = {
        "thought_generation": thought_result.get("llm_details"),
        "emotional_evaluation": None,
        "message_sending": None
    }
    
    # 评估情绪值
    if thought_result.get("thought"):
        emotional_score, eval_details = await evaluate_emotional_intensity(...)
        details["emotional_evaluation"] = eval_details
    
    # 发送消息
    sent = await send_message_to_target(config, thought)
    details["message_sending"] = {"success": sent, "thought": thought}
    
    return sent, details
```

### File 3: `backend/routers/active_consciousness.py`
确保心跳日志的API返回details字段。

## 数据库迁移
如果需要添加details字段，执行：
```sql
ALTER TABLE active_heartbeat_logs ADD COLUMN details TEXT;
```

## 验证步骤
1. 重启后端服务
2. 等待一次心跳执行（或手动触发）
3. 检查 `active_heartbeat_logs` 表是否有新的details数据
4. 检查 `configs` 表中 `active_consciousness.current.emotional_intensity` 是否被更新
5. 通过前端页面查看心跳日志详情

## 预期结果
- 情绪值不再永远是0.0，会根据聊天内容动态变化
- 每次心跳日志都有完整的LLM调用记录（请求参数、响应、耗时）
- 决策逻辑正常工作，满足条件时能自动发送消息
