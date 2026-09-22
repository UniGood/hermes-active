# Task: 情绪维度统一（单一真相源）

## STRICT RULES
- ONLY modify these 5 files: `backend/models/active_consciousness.py`、`backend/services/active_consciousness_service.py`、`backend/services/passive_consciousness_service.py`、`frontend/src/views/ActiveConsciousness.vue`、`backend/tests/test_emotion_single_source.py`（新建）。
- Do NOT touch any other files. Do NOT refactor, restructure, or "improve" anything else.
- Do NOT modify `backend/config.py`、`vite.config.js`、`.env`、`package.json`、`backend/database.py`、`backend/main.py`、`backend/models/active.py`。
- Do NOT run git commands. Do NOT delete DB columns（列保留不再写）. Do NOT rename template placeholders（`{valence}` 等名字一律不变）。
- 代码注释用中文。Python：`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`。

## Context
hermes-active（FastAPI + Vue3，cwd 即项目根）。现状：valence/arousal/social 被定义了两遍——`EmotionState` 三轴（`get_emotion_state()`，`evolve_emotion` 演化，单一情绪真相源）和"内心六维"（affection/trust/valence/arousal/social/heat）。目标：**情绪三轴只属于 EmotionState**；关系维度只留 affection/trust/heat（慢变关系）；needs、longing 不动。模板占位符 `{valence}`/`{arousal}`/`{social}` 名字不变，仅数据来源改为 EmotionState。DB 旧列保留不再写。

## Files to Modify（EXACTLY these 5）

### File 1: `backend/tests/test_emotion_single_source.py`（新建，先写并确认失败）
```python
"""情绪单一真相源测试：模板变量的情绪三轴来自 EmotionState"""
from unittest.mock import patch, MagicMock
import inspect

import models.active_consciousness as m


class TestSingleSource:
    @patch("services.passive_consciousness_service.get_emotion_state")
    def test_template_valence_reads_emotion_state(self, mock_state):
        """模板 {valence} 必须读 EmotionState，而非关系六维"""
        from services.passive_consciousness_service import PassiveConsciousnessService
        st = MagicMock()
        st.to_dict.return_value = {"valence": 0.42, "arousal": 0.1, "social": 0.3, "dominant": "calm", "label": "平静"}
        mock_state.return_value = st
        fn = PassiveConsciousnessService._build_emotion_context
        ctx = fn()
        assert abs(ctx["valence"] - 0.42) < 1e-6

    def test_relation_schema_has_no_valence(self):
        """关系维度 schema 不再定义 valence/arousal/social"""
        names = []
        for obj in vars(m).values():
            if inspect.isclass(obj) and obj.__module__ == m.__name__:
                ann = getattr(obj, "model_fields", None) or getattr(obj, "__annotations__", {})
                names += list(ann)
        rel = [n for n in names if n in ("affection", "trust", "heat")]
        dup = [n for n in names if n in ("valence", "arousal", "social") and "Emotion" not in str(n)]
        assert rel and not dup
```
注意：`_build_emotion_context` 是预期函数名——实现前先 `grep -n "def .*emotion\|emotional_label\|valence" backend/services/passive_consciousness_service.py` 定位模板情绪变量的真实构建函数，测试与实现**用同一个函数名**（若是 @staticmethod 记得调用形式对齐）。

### File 2: `backend/models/active_consciousness.py`
`grep -n "affection\|class " backend/models/active_consciousness.py` 定位"内心六维"类，从中**删除** `valence`、`arousal`、`social` 三个字段，保留 `affection`、`trust`、`heat`（`needs`、`longing` 等不动）。若删除导致引用报错，错误的引用方就是要改的下游（见 File 3/4），按下面规则改，不许留双写。

### File 3: `backend/services/active_consciousness_service.py`
- `merge_emotion`、`merge_emotion_dynamic`：删除对关系 valence/arousal/social 的更新逻辑（情绪变化只经 `update_emotion_state` 写 EmotionState）。函数保持可用（affection/trust/heat 的更新逻辑保留）。
- `evaluate_emotion_with_llm`：若有写六维 valence/arousal/social 的分支，改为只调 `update_emotion_state`。
- grep 校验：`grep -n "\.valence\|\.arousal\|\.social" backend/services/active_consciousness_service.py`——这些属性只允许出现在 EmotionState 的读写语境（`get_emotion_state`/`update_emotion_state`/`evolve_emotion` 内部），不允许出现在六维/关系更新语境。

### File 4: `backend/services/passive_consciousness_service.py`
模板变量构建处（`grep -n "valence\|emotional_label" 定位`）：`valence`/`arousal`/`social`/情绪 `label` 改从 `get_emotion_state().to_dict()` 取（`from services.active_consciousness_service import get_emotion_state`）；`affection`/`trust`/`heat` 保持原来源。**占位符名字一律不变**（模板兼容）。实现此函数后，测试里的 `_build_emotion_context` 名与其对齐（若真实名字不同，把测试里的名字也改掉）。

### File 5: `frontend/src/views/ActiveConsciousness.vue`
六维滑块区改为：
- `affection`/`trust`/`heat`：保留可编辑滑块（原绑定不变）。
- `valence`/`arousal`/`social`：改为**只读展示**当前情绪值（数据来自 status/配置接口返回的当前 EmotionState），删除对应的写入绑定（不许保存这三项）。

## Verification（必须全部通过才算完成）
```bash
cd /home/ubuntu/.hermes/hermes-active/backend
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/test_emotion_single_source.py -x -q  # 2 passed
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests/ -x -q    # 全绿（重点 tests/test_v021_emotion.py）
grep -rn "\.valence" backend/services/passive_consciousness_service.py | head -5   # 只从 EmotionState 流出
cd ../frontend && npm run build                                                  # ✓ built
```

## After making changes
输出改动摘要（每文件一行）。不跑 git 命令。
