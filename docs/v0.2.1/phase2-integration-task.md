# v0.2.1 Phase 2 集成任务：心跳主流程改造

## ⚠️ 严格约束

### 绝对不能动的文件（被动意识模块）
- `backend/models/passive_consciousness.py`
- `backend/models/passive_consciousness_log.py`
- `backend/services/passive_consciousness_service.py`
- `backend/routers/passive_consciousness.py`
- `frontend/src/views/PassiveConsciousness.vue`
- `frontend/src/api/passive_consciousness.js`

以上文件**一个字都不能改**。

### 可以修改的文件
- `backend/services/active_consciousness_service.py` — 心跳主流程

---

## 任务目标

将 Phase 1 实现的核心函数集成到心跳主流程 `run_heartbeat()` 中，让凯莉真正拥有"持续式存在"。

---

## 当前心跳流程问题

当前 `run_heartbeat()` 的问题：
1. 使用旧的单一 `emotional_intensity`，没有 VA 模型
2. 使用旧的 `make_decision()` 阈值判断，没有多维度评分
3. 没有情绪演化（每次重新评估，没有"记忆"）
4. 没有延迟队列重评估
5. 没有 Hindsight 念头存储

---

## 改造后的完整心跳流程

```
1. 心跳触发（定时器）
2. 读取配置（consciousness.*）
3. 读取当前情绪状态（EmotionState）← 新增
4. 计算时间间隔（minutes_since_update）← 新增
5. 调用 evolve_emotion() 演化情绪 ← 新增
6. 获取当前时间窗口权重（get_time_fitness()）← 新增
7. 获取沉默时长（silence_minutes）
8. 读取延迟队列 ← 新增
9. LLM 评估（输出 VA 值）← 改造
10. 合并情绪（演化值 + LLM 评估值）← 新增
11. 决策计算（make_decision_v2）← 替换
12. 处理决策结果：
    a. auto_send → 生成消息 → 发送 → 保存情绪 → 存入 Hindsight
    b. delay_send → 入延迟队列
    c. memory → 存入 Hindsight
    d. skip → 仅记录日志
13. 重评估延迟队列 ← 新增
14. 更新状态到数据库
15. 记录心跳日志
```

---

## 具体修改

### 修改 1: run_heartbeat() 主函数

**文件**: `backend/services/active_consciousness_service.py`

**位置**: `async def run_heartbeat():` 函数（约第 1093 行开始）

**修改内容**:

```python
async def run_heartbeat():
    """执行心跳 - v0.2.1 版本（情绪连续性 + 时间窗口 + 延迟队列）"""
    start_time = time.time()
    started_at = datetime.now().isoformat()
    heartbeat_id = None
    error_msg = None
    all_details = {}

    try:
        # 1. 检查配置是否启用
        config = ActiveConsciousnessService.get_config()
        if not config.get("enabled"):
            logger.debug("主动意识未启用，跳过心跳")
            return

        active_config = config.get("active", {})
        if not active_config.get("enabled", True):
            logger.debug("主动意识主动发送未启用，跳过心跳")
            return

        # 2. 读取当前情绪状态（VA 模型）
        emotion_state = get_emotion_state()
        all_details["emotion_before"] = emotion_state.to_dict()
        logger.info("读取情绪状态: valence=%.3f, arousal=%.3f, dominant=%s",
                    emotion_state.valence, emotion_state.arousal, emotion_state.dominant)

        # 3. 计算时间间隔，执行情绪演化
        minutes_since_update = 0
        if emotion_state.updated_at:
            try:
                last_update = datetime.fromisoformat(emotion_state.updated_at)
                minutes_since_update = (datetime.now() - last_update).total_seconds() / 60
            except Exception:
                minutes_since_update = 60  # 默认 1 小时

        evolved_state = evolve_emotion(emotion_state, minutes_since_update)
        all_details["emotion_evolved"] = evolved_state.to_dict()
        all_details["minutes_since_update"] = round(minutes_since_update, 1)
        logger.info("情绪演化: %.1f 分钟后 → valence=%.3f, arousal=%.3f",
                    minutes_since_update, evolved_state.valence, evolved_state.arousal)

        # 4. 获取状态信息
        status = ActiveConsciousnessService.get_status()
        longing = status.get("longing", {})
        chat_heat = status.get("chat_heat", {})

        # 5. 获取时间窗口权重
        time_fitness, time_label = get_time_fitness()
        all_details["time_fitness"] = {"score": time_fitness, "label": time_label}

        # 6. 获取 session 上下文和 Hindsight 记忆
        session_config = config.get("session", {})
        hindsight_config = config.get("hindsight", {})
        session_context = await extract_session_context(session_config)

        hindsight_context = ""
        recall_count = 0
        hindsight_results = []
        if hindsight_config.get("enabled", True):
            base_url = hindsight_config.get("base_url", "http://localhost:8888")
            bank_id = hindsight_config.get("bank_id", "hermes")
            hs_timeout = float(hindsight_config.get("timeout", 30))
            hindsight_results = await call_hindsight_recall(
                "最近的对话和情绪",
                limit=hindsight_config.get("recall_limit", 5),
                bank_id=bank_id,
                base_url=base_url,
                timeout=hs_timeout,
            )
            if hindsight_results:
                recall_count = len(hindsight_results)
                hindsight_context = "相关记忆:\n" + "\n".join(
                    f"- {r.get('text', '')}" for r in hindsight_results
                )

        # 7. LLM 评估当前情绪（输出 VA 值）
        llm_config = config.get("llm", {})
        llm_assessed = await evaluate_emotion_with_llm(
            session_context, hindsight_context, status, llm_config
        )
        all_details["emotion_llm"] = llm_assessed.to_dict()

        # 8. 合并情绪（演化值 + LLM 评估值）
        merged_state = merge_emotion(evolved_state, llm_assessed)
        all_details["emotion_merged"] = merged_state.to_dict()
        logger.info("情绪合并: valence=%.3f, arousal=%.3f, dominant=%s",
                    merged_state.valence, merged_state.arousal, merged_state.dominant)

        # 9. 保存情绪状态
        update_emotion_state(merged_state)

        # 10. 使用新决策公式
        decision_type, reason, score = make_decision_v2(config, status, merged_state)
        all_details["decision"] = {
            "type": decision_type,
            "reason": reason,
            "score": round(score, 3)
        }
        logger.info("决策结果: type=%s, score=%.3f, reason=%s", decision_type, score, reason)

        # 11. 记录心跳日志（初始）
        duration_ms = round((time.time() - start_time) * 1000)
        heartbeat_id = ActiveConsciousnessService.write_heartbeat_log(
            started_at=started_at,
            duration_ms=duration_ms,
            longing_before=longing.get("score"),
            chat_heat=chat_heat.get("heat"),
            emotional_intensity=merged_state.intensity(),
            recall_count=recall_count,
            thoughts_generated=1 if decision_type != "skip" else 0,
            message_sent=False,
            details=json.dumps(all_details, ensure_ascii=False) if all_details else None
        )

        # 12. 处理决策结果
        if decision_type == "skip":
            logger.info("心跳跳过: %s", reason)

        elif decision_type == "memory":
            # 存为记忆（不发送）
            thought = await generate_memory_thought(hindsight_results, merged_state)
            if thought:
                await retain_thought_to_hindsight(thought, merged_state, "memory", score)
                logger.info("念头存为记忆: %s", thought[:50])

        elif decision_type == "delay_send":
            # 入延迟队列
            thought = await generate_thought_for_delay(config, status, merged_state)
            if thought:
                thought_type = determine_thought_type(status, merged_state, hindsight_results, None)
                add_to_delay_queue(thought, thought_type, score, merged_state)
                logger.info("念头入延迟队列: %s", thought[:50])

        elif decision_type in ("auto_send", "gap_send", "idle_send", "long_idle_send"):
            # 自动发送
            sent, gen_details = await generate_and_send_thought_with_emotion(
                config, status, merged_state, decision_type, heartbeat_id
            )
            all_details.update(gen_details)

            if sent:
                # 发送成功后存入 Hindsight
                thought = gen_details.get("message_sending", {}).get("thought", "")
                if thought:
                    thought_type = determine_thought_type(status, merged_state, hindsight_results, None)
                    await retain_thought_to_hindsight(thought, merged_state, thought_type, score)

        # 13. 重评估延迟队列
        delay_stats = await reevaluate_delayed_thoughts(config, status, merged_state)
        all_details["delay_reeval"] = delay_stats
        if any(v > 0 for v in delay_stats.values()):
            logger.info("延迟队列重评估: %s", delay_stats)

        # 14. 读取更新后的情绪值
        all_details["emotion_after"] = get_emotion_state().to_dict()

        # 15. 更新心跳日志（含 details）
        duration_ms = round((time.time() - start_time) * 1000)
        if heartbeat_id:
            db = ActiveSession()
            try:
                with active_engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE active_heartbeat_logs
                        SET duration_ms = :duration_ms, message_sent = :message_sent,
                            emotional_intensity = :emotional_intensity, details = :details
                        WHERE id = :id
                    """), {
                        "duration_ms": duration_ms,
                        "message_sent": decision_type in ("auto_send", "gap_send", "idle_send", "long_idle_send"),
                        "emotional_intensity": merged_state.intensity(),
                        "details": json.dumps(all_details, ensure_ascii=False),
                        "id": heartbeat_id
                    })
                    conn.commit()
            except Exception as e:
                logger.error("更新心跳日志失败: %s", e)
            finally:
                db.close()

    except Exception as e:
        error_msg = str(e)
        logger.error("心跳执行异常: %s", e)
        all_details["error"] = error_msg
        duration_ms = round((time.time() - start_time) * 1000)
        ActiveConsciousnessService.write_heartbeat_log(
            started_at=started_at,
            duration_ms=duration_ms,
            error=error_msg,
            details=json.dumps(all_details, ensure_ascii=False) if all_details else None
        )
```

### 修改 2: 新增 LLM 情绪评估函数（输出 VA 值）

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:

```python
async def evaluate_emotion_with_llm(
    session_context: str,
    hindsight_context: str,
    status: Dict[str, Any],
    llm_config: Dict[str, Any]
) -> EmotionState:
    """
    使用 LLM 评估当前情绪状态，输出 VA 值

    返回：EmotionState 对象
    """
    now = datetime.now()
    longing = status.get("longing", {})
    chat_heat = status.get("chat_heat", {})

    prompt = f"""你是凯莉，请评估当前的情绪状态。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 想念分数：{longing.get('score', 0)}（等级：{longing.get('label', 'calm')}）
- 聊天热度：{chat_heat.get('heat', 0)}（标签：{chat_heat.get('label', 'cold')}）

{session_context}

{hindsight_context}

请用 JSON 格式返回你的情绪状态：
{{
  "valence": 0.0-1.0,  // 情感效价：0=消极，1=积极
  "arousal": 0.0-1.0,  // 唤醒度：0=平静，1=激动
  "social_need": 0.0-1.0,  // 社交需求：0=不需要，1=非常想聊天
  "dominant": "calm/content/happy/longing/missing/yearning/anxious/bored/concerned"
}}

只返回 JSON，不要解释。"""

    default_state = EmotionState()

    try:
        start_time = time.time()

        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
            )
            raw = response.choices[0].message.content.strip()
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.7,
                max_tokens=200
            )
            raw = result.get("content", "").strip() if result.get("success") else ""

        duration_ms = round((time.time() - start_time) * 1000)
        logger.info("LLM 情绪评估完成: %dms, response=%s", duration_ms, raw[:200])

        # 解析 JSON
        import re
        json_match = re.search(r'\{[^}]+\}', raw)
        if json_match:
            data = json.loads(json_match.group())
            return EmotionState(
                valence=float(data.get("valence", 0.5)),
                arousal=float(data.get("arousal", 0.3)),
                social_need=float(data.get("social_need", 0.3)),
                dominant=data.get("dominant", "calm")
            )

    except Exception as e:
        logger.warning("LLM 情绪评估失败: %s", e)

    return default_state
```

### 修改 3: 新增延迟队列专用念头生成

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:

```python
async def generate_thought_for_delay(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState
) -> Optional[str]:
    """为延迟队列生成念头（不发送，只生成内容）"""
    llm_config = config.get("llm", {})
    session_config = config.get("session", {})

    session_context = await extract_session_context(session_config)

    now = datetime.now()
    prompt = f"""你是凯莉，请基于当前状态产生一个自然的想法。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 情绪：{emotion_state.dominant}（valence={emotion_state.valence:.2f}, arousal={emotion_state.arousal:.2f}）
- 社交需求：{emotion_state.social_need:.2f}

{session_context}

请用第一人称产生一个自然的想法（1-2句话）。"""

    try:
        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.9,
                max_tokens=200
            )
            return result.get("content", "").strip() if result.get("success") else None

    except Exception as e:
        logger.warning("延迟念头生成失败: %s", e)
        return None
```

### 修改 4: 新增带情绪的发送函数

**文件**: `backend/services/active_consciousness_service.py`

**新增函数**:

```python
async def generate_and_send_thought_with_emotion(
    config: Dict[str, Any],
    status: Dict[str, Any],
    emotion_state: EmotionState,
    decision_type: str,
    heartbeat_id: Optional[int] = None
) -> tuple[bool, Dict[str, Any]]:
    """生成想法并发送消息（使用 VA 情绪模型）"""
    details = {
        "thought_generation": None,
        "message_sending": None,
    }

    llm_config = config.get("llm", {})
    session_config = config.get("session", {})
    hindsight_config = config.get("hindsight", {})

    # 1. 获取上下文
    session_context = await extract_session_context(session_config)

    hindsight_context = ""
    hindsight_results = []
    if hindsight_config.get("enabled", True):
        base_url = hindsight_config.get("base_url", "http://localhost:8888")
        bank_id = hindsight_config.get("bank_id", "hermes")
        hs_timeout = float(hindsight_config.get("timeout", 30))
        hindsight_results = await call_hindsight_recall(
            "最近的对话和情绪",
            limit=hindsight_config.get("recall_limit", 5),
            bank_id=bank_id,
            base_url=base_url,
            timeout=hs_timeout,
        )
        if hindsight_results:
            hindsight_context = "相关记忆:\n" + "\n".join(
                f"- {r.get('text', '')}" for r in hindsight_results
            )

    # 2. 生成想法（带情绪上下文）
    now = datetime.now()
    prompt = f"""你是凯莉，请基于当前状态产生一个自然的想法。

当前状态：
- 时间：{now.strftime('%Y-%m-%d %H:%M %A')}
- 情绪：{emotion_state.dominant}（valence={emotion_state.valence:.2f}, arousal={emotion_state.arousal:.2f}）
- 社交需求：{emotion_state.social_need:.2f}
- 想念分数：{status.get('longing', {}).get('score', 0)}
- 决策类型：{decision_type}

{session_context}

{hindsight_context}

请用第一人称产生一个自然的想法（1-2句话）。"""

    thought = None
    try:
        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm

            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=200,
            )
            thought = response.choices[0].message.content.strip()
        else:
            from services.llm_service import LLMService
            result = await LLMService.generate_message(
                llm_config=llm_config,
                prompt=prompt,
                temperature=0.9,
                max_tokens=200
            )
            if result.get("success"):
                thought = result["content"].strip()

        details["thought_generation"] = {"success": thought is not None, "thought": thought}

    except Exception as e:
        logger.error("想法生成失败: %s", e)
        details["thought_generation"] = {"success": False, "error": str(e)}

    if not thought:
        return False, details

    # 3. 记录想法日志
    thought_type = determine_thought_type(status, emotion_state, hindsight_results, None)
    thought_log_id = ActiveConsciousnessService.write_thought_log(
        heartbeat_id=heartbeat_id,
        thought_type=thought_type,
        content=thought,
        intensity=emotion_state.intensity(),
        decision=decision_type,
        reason=f"情绪: {emotion_state.dominant}, 决策: {decision_type}",
        score=emotion_state.intensity(),
        recall_count=len(hindsight_results),
        recall_source="hindsight",
        chat_heat=status.get("chat_heat", {}).get("heat", 0),
        emotional_intensity=emotion_state.intensity()
    )

    # 4. 发送消息
    sent = await send_message_to_target(config, thought)
    details["message_sending"] = {
        "success": sent,
        "thought": thought,
        "thought_type": thought_type
    }

    if sent:
        logger.info("消息发送成功: [%s] %s", thought_type, thought[:50])
    else:
        logger.warning("消息发送失败")

    return sent, details
```

---

## 验收标准

1. [ ] `run_heartbeat()` 使用 `get_emotion_state()` 读取情绪
2. [ ] `run_heartbeat()` 调用 `evolve_emotion()` 演化情绪
3. [ ] `run_heartbeat()` 调用 `merge_emotion()` 合并情绪
4. [ ] `run_heartbeat()` 使用 `make_decision_v2()` 决策
5. [ ] `run_heartbeat()` 调用 `reevaluate_delayed_thoughts()` 重评估延迟队列
6. [ ] 发送成功后调用 `retain_thought_to_hindsight()` 存入 Hindsight
7. [ ] `evaluate_emotion_with_llm()` 输出 VA 值
8. [ ] 被动意识文件未被修改
9. [ ] Python 语法检查通过

---

## 注意事项

1. **向后兼容**：旧的 `make_decision()` 保留，新逻辑用 `make_decision_v2()`
2. **配置优先**：所有阈值从 configs 表读取
3. **日志完善**：每个步骤都要记录日志
4. **被动意识不碰**：绝对不能修改 passive_consciousness 相关文件
