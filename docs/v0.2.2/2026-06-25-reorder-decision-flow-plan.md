# 决策流程重排序 + 阈值校验优化 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 重构心跳决策流程顺序（先生成念头再检查保护），优化阈值校验允许 memory=auto_send

**架构：** 心跳主循环 `run_heartbeat()` 中步骤 10-14 重排：决策评分 → LLM 念头生成 → 发送保护 → 记录日志。阈值校验从 `send > memory` 改为 `send >= memory`。

**技术栈：** FastAPI, Vue 3, Naive UI, SQLite

---

## 涉及文件

| 文件 | 职责 | 操作 |
|------|------|------|
| `backend/services/active_consciousness_service.py` | 心跳主循环 + 决策 + 保护 + 阈值校验 | 修改 |
| `frontend/src/views/ActiveConsciousness.vue` | 运行逻辑 tab + 阈值配置 UI | 修改 |

---

## 任务 1：后端 — 阈值校验改为允许相等

**文件：**
- 修改：`backend/services/active_consciousness_service.py:406`

- [ ] **步骤 1：修改校验逻辑**

将 `send_threshold <= memory_threshold` 改为 `send_threshold < memory_threshold`：

```python
# 修改前
if send_threshold <= memory_threshold:
    errors.append("发送阈值必须大于记忆阈值")

# 修改后
if send_threshold < memory_threshold:
    errors.append("发送阈值必须大于等于记忆阈值")
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "from services.active_consciousness_service import validate_active_consciousness_config; print('ok')"
```

- [ ] **步骤 3：Commit**

```bash
cd ~/.hermes/hermes-active && git add backend/services/active_consciousness_service.py && git commit -m "fix: 阈值校验允许 send_threshold == memory_threshold"
```

---

## 任务 2：后端 — 心跳流程重排序

**文件：**
- 修改：`backend/services/active_consciousness_service.py:1577-1690`（run_heartbeat 的步骤 10-16）

- [ ] **步骤 1：重构步骤 10-14**

将当前顺序：
```
10. 决策评分
11. 发送保护
13. 心跳日志
14. 处理决策（skip/memory/auto_send）
```

改为：
```
10. 决策评分
11. 念头生成（LLM）— skip 不调，memory 和 auto_send 都调
12. 发送保护检查 — 仅拦截 auto_send 的实际发送
13. 心跳日志
14. 执行动作（发送/存记忆/记录）
```

具体代码改动：

**步骤 10 保持不变**（决策评分）

**步骤 11 改为念头生成：**

```python
        # 11. 念头生成（LLM）
        thought = None
        thought_llm_details = {}
        if decision_type == "skip":
            logger.info("心跳跳过（score < memory_threshold）: %s", reason)
        elif decision_type == "memory":
            gen_result = await generate_memory_thought(config, status, hindsight_results, merged_state, context_bundle)
            thought = gen_result.get("thought") if gen_result else None
            thought_llm_details = gen_result.get("llm_details", {}) if gen_result else {}
            if thought:
                all_details["thought_generation"] = {**thought_llm_details, "thought": thought, "success": True}
            else:
                all_details["thought_generation"] = {"success": False, "error": "念头生成返回空"}
        elif decision_type == "auto_send":
            gen_result = await generate_memory_thought(config, status, hindsight_results, merged_state, context_bundle)
            thought = gen_result.get("thought") if gen_result else None
            thought_llm_details = gen_result.get("llm_details", {}) if gen_result else {}
            if thought:
                all_details["thought_generation"] = {**thought_llm_details, "thought": thought, "success": True}
            else:
                all_details["thought_generation"] = {"success": False, "error": "念头生成返回空"}
```

**步骤 12 改为发送保护检查：**

```python
        # 12. 发送保护检查（仅对 auto_send 生效）
        protection_result, protection_reason = check_send_protection(config, status, merged_state)
        blocked_by_protection = False
        if protection_result == "skip" and decision_type == "auto_send":
            blocked_by_protection = True
            all_details["decision"]["blocked_by_protection"] = True
            all_details["decision"]["protection_reason"] = protection_reason
            logger.info("发送保护拦截（保留决策分数 %.3f）: %s", score, protection_reason)
```

**步骤 13 保持不变**（心跳日志）

**步骤 14 改为执行动作：**

```python
        # 14. 执行动作
        if decision_type == "skip":
            pass  # 已在步骤 11 处理

        elif decision_type == "memory":
            # 存为记忆（念头已在步骤 11 生成）
            if thought:
                thought_type = "memory"
                hindsight_tags = ["active_consciousness", "thought", thought_type, merged_state.dominant]
                intensity = merged_state.intensity()
                if "曹凡" in thought:
                    hindsight_tags.append("user_related")
                if intensity > 0.7:
                    hindsight_tags.append("high_emotion")
                stored = await retain_thought_to_hindsight(thought, merged_state, thought_type, score)
                all_details["thought_type"] = thought_type
                all_details["hindsight_tags"] = hindsight_tags
                all_details["hindsight_stored"] = stored
                ActiveConsciousnessService.write_thought_log(
                    heartbeat_id=heartbeat_id, thought_type=thought_type, content=thought,
                    intensity=intensity, decision=decision_type, reason=f"score={score:.3f}",
                    score=score, recall_count=recall_count, recall_source="hindsight",
                    chat_heat=status.get("chat_heat", {}).get("heat", 0),
                    emotional_intensity=intensity, hindsight_stored=bool(stored),
                    details=json.dumps({"emotion_state": merged_state.to_dict(), "hindsight_tags": hindsight_tags}, ensure_ascii=False)
                )
                logger.info("念头存为记忆: %s", thought[:50])

        elif decision_type == "auto_send":
            if blocked_by_protection:
                # 保护拦截，不发送，但念头已生成 → 存入 Hindsight
                logger.info("保护机制拦截，跳过发送，但念头已生成")
                if thought:
                    stored = await retain_thought_to_hindsight(thought, merged_state, "blocked", score)
                    all_details["hindsight_stored"] = stored
            else:
                # 正常发送（念头已在步骤 11 生成，传入发送函数）
                sent, gen_details = await generate_and_send_thought_with_emotion(
                    config, status, merged_state, decision_type, heartbeat_id, score
                )
                all_details.update(gen_details)
                all_details["actual_sent"] = sent
                if sent:
                    thought_content = gen_details.get("message_sending", {}).get("thought", "") or thought
                    if thought_content:
                        weather_info = all_details.get("context_bundle", {}).get("weather")
                        thought_type = determine_thought_type_v2(status, merged_state, hindsight_results, weather_info)
                        hindsight_tags = ["active_consciousness", "thought", thought_type, merged_state.dominant]
                        intensity = merged_state.intensity()
                        if "曹凡" in thought_content:
                            hindsight_tags.append("user_related")
                        if intensity > 0.7:
                            hindsight_tags.append("high_emotion")
                        stored = await retain_thought_to_hindsight(thought_content, merged_state, thought_type, score)
                        all_details["thought_type"] = thought_type
                        all_details["hindsight_tags"] = hindsight_tags
                        all_details["hindsight_stored"] = stored
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active/backend && python -c "from services.active_consciousness_service import ActiveConsciousnessService; print('ok')"
```

- [ ] **步骤 3：Commit**

```bash
cd ~/.hermes/hermes-active && git add backend/services/active_consciousness_service.py && git commit -m "refactor: 心跳流程重排序 — 决策→念头生成→保护检查→执行动作"
```

---

## 任务 3：前端 — 运行逻辑 tab 更新

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`（运行逻辑 tab 步骤描述）

- [ ] **步骤 1：更新步骤 5-8 描述**

将当前 10 步改为 9 步（合并步骤 5+6 为决策评分，步骤 7→6 念头生成，步骤 8→7 保护+执行）：

```
步骤 5: 决策矩阵评分
  score = intensity × time_fitness × silence_factor × frequency_limit
  决策：auto_send（≥send_threshold）、memory（≥memory_threshold）、skip（<memory_threshold）
  skip 不调 LLM，省 token。memory 和 auto_send 阈值可设为相同。

步骤 6: 念头生成（LLM）
  仅 skip 跳过。memory 和 auto_send 都调 LLM 生成念头。
  使用 system/user 消息分离结构，max_tokens=0 不限制。

步骤 7: 发送保护检查 + 执行动作
  保护检查仅拦截 auto_send 的实际发送（等待期/热度/情绪/频率）。
  auto_send 未拦截 → 发送消息。auto_send 被拦截 → 不发送，念头存入 Hindsight。
  memory → 存为记忆。所有路径都写入念头日志。

步骤 8: 情绪状态持久化
  保存更新后的情绪状态，写入心跳日志。
```

- [ ] **步骤 2：更新阈值描述**

在决策阈值详情折叠面板中，将 `auto_send > send_threshold` 改为 `auto_send >= send_threshold`：

```
决策阈值：≥0.35 auto_send | ≥0.05 memory | <0.05 skip
```

- [ ] **步骤 3：更新阈值校验提示**

将"发送阈值必须大于记忆阈值"改为"发送阈值必须大于等于记忆阈值"。

- [ ] **步骤 4：Build + Commit**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build
cd ~/.hermes/hermes-active && git add -A && git commit -m "fix(ui): 运行逻辑 tab 重排序 + 阈值校验提示更新"
```

---

## 任务 4：后端 — 阈值比较改为 >=

**文件：**
- 修改：`backend/services/active_consciousness_service.py:2199-2204`（make_decision_v2）

- [ ] **步骤 1：修改阈值比较**

将 `score > send_threshold` 改为 `score >= send_threshold`：

```python
# 修改前
if score > send_threshold:
    return "auto_send", ...
elif score > memory_threshold:
    return "memory", ...
else:
    return "skip", ...

# 修改后
if score >= send_threshold:
    return "auto_send", ...
elif score >= memory_threshold:
    return "memory", ...
else:
    return "skip", ...
```

- [ ] **步骤 2：Commit**

```bash
cd ~/.hermes/hermes-active && git add backend/services/active_consciousness_service.py && git commit -m "fix: 决策阈值比较改为 >=（允许相等触发）"
```

---

## 任务 5：验证 + 推送

- [ ] **步骤 1：后端语法检查**

```bash
cd ~/.hermes/hermes-active/backend && python -c "from services.active_consciousness_service import ActiveConsciousnessService, make_decision_v2, validate_active_consciousness_config; print('all ok')"
```

- [ ] **步骤 2：前端构建**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build
```

- [ ] **步骤 3：重启后端**

```bash
systemctl --user restart hermes-active-backend.service
sleep 4 && curl -s http://localhost:18720/health
```

- [ ] **步骤 4：推送**

```bash
cd ~/.hermes/hermes-active && https_proxy=http://127.0.0.1:7890 git push
```

---

## 自检

1. **规格覆盖度：** ✅ 流程重排序（任务2）、阈值校验（任务1+4）、前端更新（任务3）
2. **占位符扫描：** ✅ 无 TODO/待定
3. **类型一致性：** ✅ `thought` 变量在步骤 11 赋值，步骤 14 使用
4. **边界情况：** memory=auto_send 时，score 恰好等于阈值 → 走 auto_send（>= 优先匹配）
