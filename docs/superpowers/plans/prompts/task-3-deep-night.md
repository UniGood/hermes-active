# Task: deep_night 适配激活 + 死字段清理

## STRICT RULES
- ONLY modify these 7 files: `backend/services/active_consciousness_service.py`、`backend/services/thought_engine.py`、`backend/services/context_collector.py`、`backend/models/active_consciousness.py`、`frontend/src/views/ActiveConsciousness.vue`、`frontend/src/i18n/locales/zh-CN/activeConsciousness.json`、`frontend/src/i18n/locales/en-US/activeConsciousness.json`、外加新建 `backend/tests/test_deep_night.py`。
- Do NOT touch any other files. Do NOT refactor, restructure, or "improve" anything else.
- Do NOT modify `backend/config.py`、`vite.config.js`、`.env`、`package.json`、`backend/database.py`、`backend/main.py`。
- Do NOT run git commands. Do NOT delete files（只删下面明确指定的字段/类）。
- 代码注释用中文。Python：`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`。

## Context
hermes-active 项目（FastAPI + Vue3，cwd 即项目根）。`backend/models/active_consciousness.py` 里 `deep_night_start: float = 23.5`（:57）、`deep_night_end: float = 7.0`（:58）、`deep_night_fitness: float = 0.3`（:59）是预留死字段（UI 无、逻辑无读）；`max_messages_per_session: int = 15`（:35）激活为 context 收集上限（顶掉 `context_collector._get_structured_conversations` 写死的 `limit=200`）；`temp_change_threshold`（:74）与 `time_window: ActiveConsciousnessTimeConfig`（:94）零引用，删除。

## Files to Modify（EXACTLY these 8）

### File 1: `backend/tests/test_deep_night.py`（新建，先写并确认失败）
```python
"""深夜适配因子测试"""
from services.active_consciousness_service import _deep_night_factor


class TestDeepNightFactor:
    def test_daytime_full_factor(self):
        assert _deep_night_factor(12.0, 23.5, 7.0, 0.3) == 1.0

    def test_midnight_reduced_factor(self):
        assert _deep_night_factor(2.0, 23.5, 7.0, 0.3) == 0.3

    def test_late_evening_reduced(self):
        assert _deep_night_factor(23.75, 23.5, 7.0, 0.3) == 0.3

    def test_early_morning_reduced(self):
        assert _deep_night_factor(6.5, 23.5, 7.0, 0.3) == 0.3

    def test_boundary_start_exclusive(self):
        assert _deep_night_factor(23.5, 23.5, 7.0, 0.3) == 1.0

    def test_no_midnight_cross(self):
        assert _deep_night_factor(23.0, 22.0, 23.5, 0.5) == 0.5
        assert _deep_night_factor(10.0, 22.0, 23.5, 0.5) == 1.0
```

### File 2: `backend/services/active_consciousness_service.py`
1) 模块级新增（放 `evolve_emotion` 定义之前）：
```python
def _deep_night_factor(hour: float, start: float, end: float, fitness: float) -> float:
    """深夜时段（[start, end)，支持跨午夜）返回 fitness 折减，其余 1.0。"""
    if start <= end:
        in_night = start <= hour < end
    else:  # 跨午夜，如 23.5 → 7.0
        in_night = hour >= start or hour < end
    return fitness if in_night else 1.0
```
2) 定位念头发送决策的打分处：`grep -n "score" backend/services/active_consciousness_service.py` 找 decision="send" 的评分/比较段。在分数计算后乘深夜因子（配置从 `ActiveConsciousnessService.get_config()` 读 deep_night_start/deep_night_end/deep_night_fitness，字段在 `models/active_consciousness.py` 所属类，`grep -n "class " backend/models/active_consciousness.py` 确认类名与 config dict 键；默认值 (23.5, 7.0, 0.3)）：
```python
        from datetime import datetime
        factor = _deep_night_factor(
            datetime.now().hour + datetime.now().minute / 60.0,
            deep_night_start, deep_night_end, deep_night_fitness)
        score *= factor
```

### File 3: `backend/services/thought_engine.py`
`_build_messages` 构造 user content 的末尾追加深夜气质提示（`start/end` 从 `self.config` 读，默认 23.5/7.0）：
```python
        from datetime import datetime
        now_h = datetime.now().hour + datetime.now().minute / 60.0
        dn_start = self.config.get("deep_night_start", 23.5)
        dn_end = self.config.get("deep_night_end", 7.0)
        if (dn_start <= dn_end and dn_start <= now_h < dn_end) or \
           (dn_start > dn_end and (now_h >= dn_start or now_h < dn_end)):
            user_content += "\n（现在是深夜，想得更轻、更安静，一句就好。）"
```
（变量名以 `_build_messages` 实际的 user content 变量为准。）

### File 4: `backend/services/context_collector.py`
`_get_structured_conversations(self, limit: int = 200)` 的调用处（`collect()` 内）改传配置值：`limit=self.context_config.get("max_messages_per_session", 200)`（`self.context_config` 已在 `__init__` 存在）。

### File 5: `backend/models/active_consciousness.py`
- `max_messages_per_session: int = 15` 的注释改为 `# 上下文收集的最大消息条数`
- 删除 `temp_change_threshold: float = 5.0 ...` 整行
- 删除 `time_window: ActiveConsciousnessTimeConfig = ActiveConsciousnessTimeConfig()` 整行，以及 `ActiveConsciousnessTimeConfig` 整个类。先 `grep -rn "ActiveConsciousnessTimeConfig" backend/ frontend/` 确认引用只有这两处。

### File 6: `frontend/src/views/ActiveConsciousness.vue`
配置 tab（时间格式输入区之后）加三个表单行。配置对象的落点键：先 `grep -n "deep_night" backend/services/active_consciousness_service.py` 看 config dict 的嵌套位置——若在 `time` 节点下则绑 `config.time.deep_night_start` 等；若平铺则绑 `config.deep_night_start`。以实际键为准：
```vue
        <n-form-item :label="t('activeConsciousness.configTab.deepNightStart')">
          <n-input-number v-model:value="config.time.deep_night_start" :min="0" :max="24" :step="0.5" style="width: 120px" />
        </n-form-item>
        <n-form-item :label="t('activeConsciousness.configTab.deepNightEnd')">
          <n-input-number v-model:value="config.time.deep_night_end" :min="0" :max="24" :step="0.5" style="width: 120px" />
        </n-form-item>
        <n-form-item :label="t('activeConsciousness.configTab.deepNightFitness')">
          <n-input-number v-model:value="config.time.deep_night_fitness" :min="0" :max="1" :step="0.1" style="width: 120px" />
        </n-form-item>
```

### File 7/8: `frontend/src/i18n/locales/zh-CN/activeConsciousness.json`、`…/en-US/activeConsciousness.json`
`activeConsciousness.configTab` 节点各加三键。zh-CN：
```json
"deepNightStart": "深夜开始（小时，如 23.5）",
"deepNightEnd": "深夜结束（小时，如 7）",
"deepNightFitness": "深夜活跃度权重（0-1）"
```
en-US：`"Deep night start (hour)"`、`"Deep night end (hour)"`、`"Deep night activity weight (0-1)"`。

## Verification（必须全部通过才算完成）
```bash
cd /home/ubuntu/.hermes/hermes-active/backend
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_deep_night.py -x -q   # 6 passed
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -x -q                     # 全绿无回归
grep -rn "ActiveConsciousnessTimeConfig\|temp_change_threshold" backend/ frontend/src | wc -l  # 输出 0
cd ../frontend && npm run build                                                                # ✓ built
```

## After making changes
输出改动摘要（每文件一行）。不跑 git 命令。
