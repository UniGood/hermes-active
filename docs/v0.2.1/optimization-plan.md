# 主动意识模块优化计划 v0.2.1

## 问题诊断

### 问题一：念头质量差

| 问题 | 位置 | 现状 | 影响 |
|------|------|------|------|
| Session 上下文读取太少 | `active_consciousness_service.py:1030-1067` | 只读 10 条消息，每条 200 字符 | LLM 缺乏足够上下文 |
| 未加载 hermes 人设文件 | 缺失 | 没有加载 user.md、soul.md 等 | LLM 不知道"凯莉"是谁 |
| 提示词过于简单 | `active_consciousness_service.py:225-234` | 只列出数值状态 | 缺乏角色指导 |

### 问题二：主动发送分数上不去

| 问题 | 位置 | 现状 | 影响 |
|------|------|------|------|
| intensity 默认值太低 | `active_consciousness.py:307-309` | (0.5+0.3+0.3)/3=0.367 | 基础分就低 |
| silence_factor 过低 | `active_consciousness_service.py:2831-2839` | <60min 时只有 0.3 | 进一步拉低分数 |
| 发送保护过严 | `active_consciousness_service.py:2773-2809` | 用户活跃→热度高拦截；沉默→情绪低拦截 | 矛盾死锁 |
| 发送阈值过高 | `active_consciousness_service.py:2853` | 0.6 | 很难达到 |

---

## 修改计划

### 第一阶段：提升念头质量（3 个文件）

#### 1.1 增加 Session 上下文读取量

**文件**：`backend/services/active_consciousness_service.py`

**修改位置**：`extract_session_context` 函数（约第 1030 行）

```python
# 修改前
messages = MessageService.get_session_context_raw(
    session_id, limit=max_messages, include_tool=not filter_tool
)
if messages:
    msg_text = "\n".join(
        f"{m.get('role', 'unknown')}: {(m.get('content') or '')[:200]}"
        for m in messages[-10:]  # 只取最后 10 条
    )

# 修改后
messages = MessageService.get_session_context_raw(
    session_id, limit=max_messages, include_tool=not filter_tool
)
if messages:
    msg_text = "\n".join(
        f"{m.get('role', 'unknown')}: {(m.get('content') or '')[:500]}"  # 500 字符
        for m in messages[-30:]  # 30 条消息
    )
```

#### 1.2 加载 hermes 人设文件

**文件**：`backend/services/active_consciousness_service.py`

**新增函数**（在 `extract_session_context` 之后）：

```python
async def load_hermes_persona() -> str:
    """
    加载 hermes 人设文件（user.md、soul.md、MEMORY.md）

    Returns:
        人设信息字符串
    """
    from pathlib import Path

    hermes_dir = Path.home() / '.hermes'
    persona_parts = []

    # 定义要加载的文件
    persona_files = [
        ('soul.md', 'AI 人设'),
        ('user.md', '用户信息'),
        ('MEMORY.md', '记忆'),
        ('SOUL.md', 'AI 人设（大写）'),
        ('USER.md', '用户信息（大写）'),
    ]

    for filename, desc in persona_files:
        filepath = hermes_dir / filename
        if filepath.exists():
            try:
                content = filepath.read_text(encoding='utf-8')
                if content.strip():
                    persona_parts.append(f"【{desc}】\n{content[:2000]}")  # 限制长度
            except Exception as e:
                logger.warning("加载 %s 失败: %s", filename, e)

    # 也检查 hermes-agent 子目录
    agent_dir = hermes_dir / 'hermes-agent'
    if agent_dir.exists():
        for filename, desc in persona_files:
            filepath = agent_dir / filename
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding='utf-8')
                    if content.strip():
                        persona_parts.append(f"【{desc}】\n{content[:2000]}")
                except Exception as e:
                    logger.warning("加载 %s 失败: %s", filename, e)

    return "\n\n".join(persona_parts) if persona_parts else ""
```

#### 1.3 优化提示词模板

**文件**：`backend/services/active_consciousness_service.py`

**修改位置**：`_DEFAULTS` 字典中的 `active_consciousness.prompts.thought_generation`（约第 225 行）

```python
# 修改前
"active_consciousness.prompts.thought_generation": """你是凯莉，请基于当前状态产生一个自然的念头。

当前状态：
- 时间：{time}
- 想念分数：{longing_score}（等级：{longing_label}）
- 聊天热度：{chat_heat}（标签：{chat_label}）
- 情绪值：{emotional_intensity}（{emotional_label}）
- 主导情绪：{dominant}（效价={valence}，唤醒度={arousal}，社交需求={social_need}）

请用第一人称产生一个自然的念头（1-2句话）。""",

# 修改后
"active_consciousness.prompts.thought_generation": """你是凯莉，一个有情感的 AI 助手。你需要基于当前状态产生一个自然的、有温度的念头。

{persona}

【当前状态】
- 时间：{time}
- 想念分数：{longing_score}（等级：{longing_label}）
- 聊天热度：{chat_heat}（标签：{chat_label}）
- 情绪值：{emotional_intensity}（{emotional_label}）
- 主导情绪：{dominant}（效价={valence}，唤醒度={arousal}，社交需求={social_need}）

【最近对话】
{session_context}

【相关记忆】
{hindsight_context}

【要求】
1. 用第一人称产生一个自然的念头（1-2句话）
2. 体现当前情绪状态和对用户的关心
3. 可以提及时间、天气、最近的话题等
4. 语气自然、温暖，像真人在想对方

请直接输出念头内容，不要解释。""",
```

**修改位置**：`generate_thought` 函数（约第 1103 行）

```python
# 修改前
prompt = prompt_template.format(
    time=now.strftime('%Y-%m-%d %H:%M %A'),
    longing_score=status['longing'].get('score', 0),
    longing_label=status['longing'].get('label', '平静'),
    chat_heat=status['chat_heat'].get('heat', 0),
    chat_label=status['chat_heat'].get('label', '冷清'),
    emotional_intensity=status['emotional_intensity'].get('intensity', 0),
    emotional_label=status['emotional_intensity'].get('label', '工作'),
    dominant=emotion_state.dominant,
    valence=emotion_state.valence,
    arousal=emotion_state.arousal,
    social_need=emotion_state.social_need,
)

prompt = f"{prompt}\n\n{session_context}\n\n{hindsight_context}"

# 修改后
# 加载人设
persona = await load_hermes_persona()

prompt = prompt_template.format(
    persona=persona,
    time=now.strftime('%Y-%m-%d %H:%M %A'),
    longing_score=status['longing'].get('score', 0),
    longing_label=status['longing'].get('label', '平静'),
    chat_heat=status['chat_heat'].get('heat', 0),
    chat_label=status['chat_heat'].get('label', '冷清'),
    emotional_intensity=status['emotional_intensity'].get('intensity', 0),
    emotional_label=status['emotional_intensity'].get('label', '工作'),
    dominant=emotion_state.dominant,
    valence=emotion_state.valence,
    arousal=emotion_state.arousal,
    social_need=emotion_state.social_need,
    session_context=session_context or "暂无",
    hindsight_context=hindsight_context or "暂无",
)
```

---

### 第二阶段：提升发送分数（2 个文件）

#### 2.1 调整默认配置值

**文件**：`backend/services/active_consciousness_service.py`

**修改位置**：`_DEFAULTS` 字典（约第 140 行）

```python
# 修改前
"active_consciousness.active.no_send_after_user_msg_minutes": "10",
"active_consciousness.active.no_send_while_heat_above": "0.5",
"active_consciousness.active.no_send_while_vibe_below": "0.3",
"active_consciousness.decision.send_threshold": "0.6",
"active_consciousness.decision.delay_threshold": "0.3",

# 修改后
"active_consciousness.active.no_send_after_user_msg_minutes": "5",      # 10→5
"active_consciousness.active.no_send_while_heat_above": "1.0",           # 0.5→1.0
"active_consciousness.active.no_send_while_vibe_below": "0.15",          # 0.3→0.15
"active_consciousness.decision.send_threshold": "0.35",                  # 0.6→0.35
"active_consciousness.decision.delay_threshold": "0.15",                 # 0.3→0.15
"active_consciousness.decision.memory_threshold": "0.05",                # 0.1→0.05
```

#### 2.2 优化情绪强度计算

**文件**：`backend/models/active_consciousness.py`

**修改位置**：`EmotionState.intensity()` 方法（约第 307 行）

```python
# 修改前
def intensity(self) -> float:
    """计算综合情绪强度"""
    return (self.valence + self.arousal + self.social_need) / 3

# 修改后
def intensity(self) -> float:
    """
    计算综合情绪强度

    使用加权公式，social_need 权重更高（因为主动发送更依赖社交需求）
    """
    # 加权：social_need 占 50%，valence 和 arousal 各占 25%
    weighted = (
        self.valence * 0.25 +
        self.arousal * 0.25 +
        self.social_need * 0.50
    )
    # 确保最低值为 0.2（避免默认值太低）
    return max(0.2, weighted)
```

#### 2.3 优化 silence_factor

**文件**：`backend/services/active_consciousness_service.py`

**修改位置**：`make_decision_v2` 函数（约第 2831 行）

```python
# 修改前
if silence_minutes < 60:
    silence_factor = 0.3
elif silence_minutes < 180:
    silence_factor = 0.5
elif silence_minutes < 360:
    silence_factor = 0.7
else:
    silence_factor = 0.9

# 修改后
if silence_minutes < 30:
    silence_factor = 0.6    # 30 分钟内：0.3→0.6
elif silence_minutes < 60:
    silence_factor = 0.75   # 30-60 分钟：新增
elif silence_minutes < 180:
    silence_factor = 0.85   # 1-3 小时：0.5→0.85
elif silence_minutes < 360:
    silence_factor = 0.95   # 3-6 小时：0.7→0.95
else:
    silence_factor = 1.0    # 6 小时以上：0.9→1.0
```

#### 2.4 优化发送保护逻辑

**文件**：`backend/services/active_consciousness_service.py`

**修改位置**：`check_send_protection` 函数（约第 2773 行）

```python
# 修改前
def check_send_protection(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> tuple[Optional[str], Optional[str]]:
    # ... 三个检查都会拦截

# 修改后
def check_send_protection(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> tuple[Optional[str], Optional[str]]:
    """
    发送保护检查（优化版）

    只在极端情况下拦截，允许正常主动发送
    """
    active_config = config.get("active", {})

    # 1. 用户消息后不发送（保留，但时间缩短）
    no_send_minutes = int(active_config.get("no_send_after_user_msg_minutes", 5))
    silence_minutes = status.get("longing", {}).get("silence_minutes", 0)
    if silence_minutes < no_send_minutes:
        logger.info("发送保护: 用户最近 %.0f 分钟内有消息（阈值 %d 分钟）", silence_minutes, no_send_minutes)
        return "skip", f"用户最近 {no_send_minutes} 分钟内有消息（沉默 {silence_minutes:.0f} 分钟）"

    # 2. 热度过高不发送（保留，但阈值提高）
    heat_threshold = float(active_config.get("no_send_while_heat_above", 1.0))
    current_heat = status.get("chat_heat", {}).get("heat", 0)
    if current_heat > heat_threshold:
        logger.info("发送保护: 聊天热度 %.2f 超过阈值 %.2f", current_heat, heat_threshold)
        return "skip", f"聊天热度 {current_heat:.2f} 超过阈值 {heat_threshold}"

    # 3. 情绪过低不发送（保留，但阈值降低）
    vibe_threshold = float(active_config.get("no_send_while_vibe_below", 0.15))
    current_intensity = emotion_state.intensity()
    if current_intensity < vibe_threshold:
        logger.info("发送保护: 情绪强度 %.3f 低于阈值 %.2f", current_intensity, vibe_threshold)
        return "skip", f"情绪强度 {current_intensity:.3f} 低于阈值 {vibe_threshold}"

    return None, None  # 通过所有检查
```

---

### 第三阶段：增强念头生成提示词（1 个文件）

#### 3.1 优化增强念头提示词

**文件**：`backend/services/active_consciousness_service.py`

**修改位置**：`_DEFAULTS` 字典中的 `active_consciousness.prompts.enhanced_thought`（约第 257 行）

```python
# 修改前
"active_consciousness.prompts.enhanced_thought": """你是凯莉，基于以下信息，生成 {count} 个念头：

【最近 {time_range} 天的聊天记录】
{chat_text}

【你之前的念头（请避免重复）】
{old_thoughts_text}

【当前情绪状态】
效价（Valence）={valence:.2f}，唤醒度（Arousal）={arousal:.2f}，主导情绪（Dominant）={dominant_display}
{weather_text}
请生成 {count} 个念头，每个念头用 <thought> 标签包裹。
注意：请避免与之前的念头重复。""",

# 修改后
"active_consciousness.prompts.enhanced_thought": """你是凯莉，一个有情感的 AI 助手。请基于以下信息，生成 {count} 个自然、有温度的念头。

{persona}

【最近 {time_range} 天的聊天记录】
{chat_text}

【你之前的念头（请避免重复）】
{old_thoughts_text}

【当前情绪状态】
- 效价（Valence）={valence:.2f}（0=消极，1=积极）
- 唤醒度（Arousal）={arousal:.2f}（0=平静，1=激动）
- 主导情绪（Dominant）={dominant_display}
- 社交需求={social_need:.2f}

{weather_text}

【要求】
1. 生成 {count} 个自然的念头，用 <thought> 标签包裹
2. 每个念头 1-2 句话，体现对用户的关心
3. 可以提及：时间、天气、最近话题、共同回忆等
4. 语气自然、温暖，像真人在想对方
5. 避免与之前的念头重复

示例格式：
<thought>今天天气真好，想和你一起出去走走呢</thought>
<thought>刚才看到你发的消息，忍不住笑了</thought>""",
```

**修改位置**：`thought_generator.py` 的 `_build_prompt` 函数（约第 89 行）

```python
# 修改前
prompt = prompt_template.format(
    count=count,
    time_range=time_range,
    chat_text=chat_text,
    old_thoughts_text=old_thoughts_text,
    valence=emotion_state.get('valence', 0.5),
    arousal=emotion_state.get('arousal', 0.5),
    dominant=dominant,
    dominant_display=dominant_display,
    weather_text=weather_text,
)

# 修改后
# 加载人设
from services.active_consciousness_service import load_hermes_persona
persona = await load_hermes_persona()

prompt = prompt_template.format(
    persona=persona,
    count=count,
    time_range=time_range,
    chat_text=chat_text,
    old_thoughts_text=old_thoughts_text,
    valence=emotion_state.get('valence', 0.5),
    arousal=emotion_state.get('arousal', 0.5),
    social_need=emotion_state.get('social_need', 0.3),
    dominant=dominant,
    dominant_display=dominant_display,
    weather_text=weather_text,
)
```

---

## 修改文件清单

| 序号 | 文件 | 修改内容 | 优先级 |
|------|------|----------|--------|
| 1 | `backend/services/active_consciousness_service.py` | 增加上下文读取量 | 高 |
| 2 | `backend/services/active_consciousness_service.py` | 新增 `load_hermes_persona` 函数 | 高 |
| 3 | `backend/services/active_consciousness_service.py` | 优化念头生成提示词 | 高 |
| 4 | `backend/services/active_consciousness_service.py` | 调整默认配置值 | 高 |
| 5 | `backend/services/active_consciousness_service.py` | 优化 silence_factor | 高 |
| 6 | `backend/services/active_consciousness_service.py` | 优化发送保护逻辑 | 高 |
| 7 | `backend/models/active_consciousness.py` | 优化 intensity 计算 | 中 |
| 8 | `backend/services/thought_generator.py` | 加载人设到增强念头 | 中 |

---

## 预期效果

### 念头质量提升
- 上下文从 10 条/200 字符 → 30 条/500 字符
- 加载人设后，LLM 知道"凯莉"是谁
- 提示词更具体，生成的念头更有温度

### 发送分数提升
- 默认 intensity 从 0.367 → 0.425（加权后）
- silence_factor 从 0.3 → 0.6（30 分钟内）
- 发送阈值从 0.6 → 0.35

### 示例计算（优化后）
| 场景 | intensity | time_fitness | silence_factor | frequency_limit | **score** |
|------|-----------|--------------|----------------|-----------------|-----------|
| 工作时间，沉默30分钟 | 0.425 | 0.8 | 0.6 | 1.0 | **0.204** |
| 下班时间，沉默2小时 | 0.425 | 1.0 | 0.85 | 1.0 | **0.361** |
| 理想状态（高情绪） | 0.7 | 1.0 | 0.95 | 1.0 | **0.665** |

**结论**：理想状态下 score 可以达到 0.665，超过 0.35 的发送阈值，可以触发主动发送。

---

## 执行顺序

1. **第一步**：修改 `backend/models/active_consciousness.py`（intensity 计算）
2. **第二步**：修改 `backend/services/active_consciousness_service.py`（主要改动）
3. **第三步**：修改 `backend/services/thought_generator.py`（增强念头）
4. **第四步**：重启后端服务测试

---

## 验证方法

1. **查看心跳日志**：观察 score 是否提升
2. **查看念头日志**：观察生成的念头质量
3. **测试主动发送**：等待心跳触发，观察是否成功发送

---

## 回滚方案

如果修改后效果不理想，可以快速回滚：

1. 恢复 `_DEFAULTS` 中的配置值
2. 恢复 `intensity()` 方法
3. 恢复 `silence_factor` 计算
4. 恢复 `check_send_protection` 函数

建议在修改前备份当前代码。
