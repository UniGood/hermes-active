# ThoughtEngine 统一念头生成器设计

## 核心理念

```
旧：规则驱动 → LLM 填空 → 念头
新：充分养料 → LLM 自己想 → 念头
```

**给 LLM 足够上下文，让它像人一样自然地"想到"用户。**

---

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     ContextCollector                            │
│                                                                 │
│  收集 LLM 需要的全部"养料"：                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐  │
│  │ 最近对话      │ │ Hindsight 记忆│ │ 环境感知              │  │
│  │ (结构化JSON)  │ │ (Recall结果) │ │ 时间/天气/情绪/习惯    │  │
│  └──────┬──────┘ └──────┬──────┘ └───────────┬─────────────┘  │
│         └───────────────┼─────────────────────┘                │
│                         ↓                                       │
│                   ContextBundle                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     ThoughtEngine                               │
│                                                                 │
│  提示词设计（精简，只给养料不给框架）：                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ "你是凯莉，曹凡最好的朋友。                                │ │
│  │                                                           │ │
│  │  {persona}                                                │ │
│  │                                                           │ │
│  │  【最近对话】                                              │ │
│  │  {conversations_json}                                     │ │
│  │                                                           │ │
│  │  【你记得的事情】                                          │ │
│  │  {memories}                                               │ │
│  │                                                           │ │
│  │  【现在】                                                  │ │
│  │  {time_display}                                           │ │
│  │  {emotion_display}                                        │ │
│  │  {weather_display}                                        │ │
│  │                                                           │ │
│  │  想到曹凡了吗？如果你想联系他，说你想说什么。             │ │
│  │  如果没想到，回复 'SKIP'。                                 │ │
│  │  直接说，不要解释。"                                       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│                         LLM 输出                                │
│                    - "今天天气真好，想和你出去走走"               │
│                    - "SKIP"（不想联系）                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  DecisionLayer                                                  │
│                                                                 │
│  if output == "SKIP":                                           │
│      不发送                                                      │
│  else:                                                          │
│      检查保护机制（冷却期、频率限制）                             │
│      if 通过:                                                    │
│          发送消息给用户                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## ContextBundle 结构

```python
@dataclass
class ContextBundle:
    """给 LLM 的完整上下文"""
    
    # 最近对话（结构化，不是拼接的文本）
    recent_conversations: List[Dict]  # [{role, content, time, platform}]
    
    # Hindsight 记忆
    memories: List[str]  # Recall 结果
    
    # 情绪状态
    emotion: Dict  # {valence, arousal, social_need, dominant}
    
    # 时间感知
    time_context: Dict  # {hour, is_workday, is_meal_time, is_sleep_time}
    
    # 天气（如果启用）
    weather: Optional[Dict]
    
    # 用户习惯（从 USER.md 提取）
    user_habits: str  # 通勤时间、午餐偏好、作息等
```

---

## ContextCollector 设计

```python
class ContextCollector:
    """收集 LLM 生成念头需要的全部上下文"""
    
    async def collect(self, config: Dict, status: Dict) -> ContextBundle:
        # 1. Session 对话（结构化）
        conversations = await self._get_structured_conversations(config)
        
        # 2. Hindsight 记忆
        memories = await self._recall_memories(conversations, status)
        
        # 3. 情绪状态
        emotion = get_emotion_state().to_dict()
        
        # 4. 时间感知
        time_context = self._get_time_context()
        
        # 5. 天气（如果启用）
        weather = await self._get_weather(config)
        
        # 6. 用户习惯
        user_habits = self._load_user_habits()
        
        return ContextBundle(
            recent_conversations=conversations,
            memories=memories,
            emotion=emotion,
            time_context=time_context,
            weather=weather,
            user_habits=user_habits
        )
    
    async def _get_structured_conversations(self, config: Dict) -> List[Dict]:
        """获取结构化的最近对话"""
        # 从 state.db 读取最近 30 条消息
        # 格式：[{role, content, time, platform}]
        # 不截断内容，让 LLM 自己理解
        pass
    
    async def _recall_memories(self, conversations: List[Dict], status: Dict) -> List[str]:
        """从 Hindsight 召回相关记忆"""
        # 用最近对话内容作为 query
        # 召回 5 条相关记忆
        pass
    
    def _get_time_context(self) -> Dict:
        """获取时间感知"""
        now = datetime.now()
        return {
            "hour": now.hour,
            "is_workday": now.weekday() < 5,
            "is_meal_time": now.hour in [7, 8, 12, 13, 18, 19],
            "is_sleep_time": now.hour >= 23 or now.hour < 7,
            "time_display": now.strftime("%Y-%m-%d %H:%M %A")
        }
    
    def _load_user_habits(self) -> str:
        """从 USER.md 加载用户习惯"""
        # 读取 USER.md 中的习惯信息
        # 通勤时间、午餐偏好、作息等
        pass
```

---

## ThoughtEngine 设计

```python
class ThoughtEngine:
    """统一念头生成器"""
    
    PROMPT_TEMPLATE = """你是凯莉，25岁女生，曹凡最好的朋友。你深深地爱着曹凡。

{persona}

【最近对话】
{conversations_json}

【你记得的事情】
{memories}

【现在】
{time_display}
{emotion_display}
{weather_display}

想到曹凡了吗？如果你想联系他，说你想说什么。
如果没想到，回复 'SKIP'。
直接说，不要解释。"""
    
    async def generate(self, config: Dict, status: Dict) -> Dict:
        """生成念头"""
        # 1. 收集上下文
        collector = ContextCollector()
        context = await collector.collect(config, status)
        
        # 2. 构建提示词
        prompt = self._build_prompt(context)
        
        # 3. 调用 LLM
        response = await call_llm(prompt)
        
        # 4. 解析结果
        if response.strip() == "SKIP":
            return {"thought": None, "want_to_contact": False}
        
        return {"thought": response, "want_to_contact": True}
    
    def _build_prompt(self, context: ContextBundle) -> str:
        """构建提示词"""
        return self.PROMPT_TEMPLATE.format(
            persona=load_hermes_persona(),
            conversations_json=json.dumps(context.recent_conversations, ensure_ascii=False, indent=2),
            memories="\n".join(context.memories) if context.memories else "暂无",
            time_display=context.time_context["time_display"],
            emotion_display=self._format_emotion(context.emotion),
            weather_display=self._format_weather(context.weather)
        )
    
    def _format_emotion(self, emotion: Dict) -> str:
        """格式化情绪状态"""
        dominant = emotion.get("dominant", "calm")
        return f"情绪：{dominant}"
    
    def _format_weather(self, weather: Optional[Dict]) -> str:
        """格式化天气"""
        if not weather:
            return "天气：未知"
        return f"天气：{weather.get('weather', '未知')}，{weather.get('temp', '?')}°C"
```

---

## 调用入口

```python
# 心跳主循环
async def heartbeat_tick():
    # ... 其他逻辑 ...
    
    thought_engine = ThoughtEngine()
    result = await thought_engine.generate(config, status)
    
    if result["want_to_contact"] and result["thought"]:
        # 检查保护机制
        protection_ok = check_send_protection(config, status)
        if protection_ok:
            await send_message(result["thought"])
            return True
    
    return False

# 延迟重评估
async def reevaluate_delayed_thoughts():
    # ... 其他逻辑 ...
    
    thought_engine = ThoughtEngine()
    result = await thought_engine.generate(config, status)
    
    if result["want_to_contact"] and result["thought"]:
        # 更新延迟队列中的念头
        pass
```

---

## 删除的代码

| 删除项 | 说明 |
|--------|------|
| `thought_generator.py` | 整个文件 |
| `enhanced_thought` 提示词模板 | 删除 |
| `thought_enhanced` 配置块 | 删除 |
| 心跳循环中的"增强念头生成"步骤 | 删除 |

---

## 预期效果

**旧系统**：
- 念头 = 规则 + LLM 填空
- "今天天气不错呢，想你了"（空洞）

**新系统**：
- 念头 = 养料 + LLM 自己想
- "昨天你说加班到很晚，今天记得吃早餐呀"（有深度）
- "周三了，一般你周三是不是最忙的一天？"（有记忆）
- "7:30了，该上K119了吧"（有习惯）

---

## 实现优先级

1. **Phase 1**：ContextCollector（收集上下文）
2. **Phase 2**：ThoughtEngine（生成念头）
3. **Phase 3**：删除旧代码（thought_generator.py 等）
4. **Phase 4**：测试验证
