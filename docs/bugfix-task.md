# Bug修复任务：主动意识功能排查

## 严格规则
- 只修改以下列出的文件，不要改其他文件
- 不要改 config.py, vite.config.js, .env
- 不要运行 git 命令
- 不要改数据库结构

## 需要修复的3个问题

### Bug 1: 心跳次数硬编码为0（关键）

**文件**: `backend/services/active_consciousness_service.py`

**问题**: `get_status()` 方法第 288-313 行，`heartbeat_count` 和 `last_heartbeat_at` 被硬编码为 `0` 和 `None`，没有从数据库查询实际数据。

**当前代码**:
```python
return {
    "enabled": config.get("enabled", False),
    "heartbeat_count": 0,  # 硬编码！
    "last_heartbeat_at": None,  # 硬编码！
    ...
}
```

**修复方案**: 从 `active_heartbeat_logs` 表查询实际的心跳次数和最新心跳时间：
```python
# 查询心跳统计
heartbeat_count = 0
last_heartbeat_at = None
try:
    with active_engine.connect() as conn:
        row = conn.execute(text(
            "SELECT COUNT(*), MAX(created_at) FROM active_heartbeat_logs"
        )).fetchone()
        if row:
            heartbeat_count = row[0] or 0
            if row[1]:
                last_heartbeat_at = str(row[1])
except Exception as e:
    logger.warning("查询心跳统计失败: %s", e)

return {
    "enabled": config.get("enabled", False),
    "heartbeat_count": heartbeat_count,
    "last_heartbeat_at": last_heartbeat_at,
    ...
}
```

### Bug 2: Hindsight Reflect 错误信息丢失

**文件**: `backend/routers/hindsight.py`

**问题**: 第 80-85 行，异常被捕获但 `str(e)` 返回空字符串，无法定位问题。

**当前代码**:
```python
except Exception as e:
    return {
        "success": False,
        "message": f"Reflect 失败: {str(e)}",  # str(e) 可能为空
        "reflection": ""
    }
```

**修复方案**: 使用 `repr(e)` 和记录完整错误信息：
```python
except Exception as e:
    import traceback
    error_detail = repr(e) if str(e) else traceback.format_exc()
    logger.error("Hindsight Reflect 失败: %s", error_detail)
    return {
        "success": False,
        "message": f"Reflect 失败: {error_detail}",
        "reflection": ""
    }
```

同样修复 `hindsight_recall` 方法的错误处理。

### Bug 3: 前端增加 LLM 连通性测试

**文件**: `backend/routers/active_consciousness.py`

**问题**: 只有"想法生成测试"，没有独立的 LLM 连通性测试。

**修复方案**: 新增一个 `/test/llm-connect` 端点：

```python
@router.post("/test/llm-connect")
async def test_llm_connect():
    """测试 LLM 连通性"""
    try:
        config = ActiveConsciousnessService.get_config()
        llm_config = config.get("llm", {})
        
        # 简单测试 prompt
        test_prompt = "请回复'连接成功'两个字"
        
        if llm_config.get("mode") == "hermes":
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path.home() / '.hermes' / 'hermes-agent'))
            from agent.auxiliary_client import call_llm
            
            response = call_llm(
                task='title_generation',
                messages=[{"role": "user", "content": test_prompt}],
                temperature=0.1,
                max_tokens=50,
            )
            result = response.choices[0].message.content
            return {
                "success": True,
                "data": {
                    "mode": "hermes",
                    "response": result,
                    "model": "hermes default"
                }
            }
        else:
            # 自定义 LLM
            if not llm_config.get("api_key"):
                return {"success": False, "error": "未配置 LLM API Key"}
            
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{llm_config.get('base_url', 'https://api.openai.com/v1')}/chat/completions",
                    headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                    json={
                        "model": llm_config.get("model", "deepseek-chat"),
                        "messages": [{"role": "user", "content": test_prompt}],
                        "max_tokens": 50,
                        "temperature": 0.1
                    }
                )
                data = resp.json()
                if "choices" in data and data["choices"]:
                    result = data["choices"][0]["message"]["content"]
                    return {
                        "success": True,
                        "data": {
                            "mode": "custom",
                            "response": result,
                            "model": llm_config.get("model"),
                            "base_url": llm_config.get("base_url")
                        }
                    }
                else:
                    return {"success": False, "error": f"LLM 返回异常: {data}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**文件**: `frontend/src/api/active_consciousness.js`

新增 API 方法：
```javascript
testLLMConnect() {
  return http.post('/active-consciousness/test/llm-connect')
}
```

**文件**: `frontend/src/views/ActiveConsciousness.vue`

在测试 Tab 中增加 LLM 连通性测试按钮：
```vue
<!-- Tab 4: 测试 -->
<n-tab-pane name="test" tab="测试">
  <n-space vertical>
    <n-button @click="testLLMConnect" :loading="testing.llm">
      LLM 连通性测试
    </n-button>
    <n-button @click="testThought" :loading="testing.thought">
      想法生成测试
    </n-button>
  </n-space>
  ...
</n-tab-pane>
```

增加对应的测试函数：
```javascript
const testing = ref({ thought: false, llm: false })

const testLLMConnect = async () => {
  testing.value.llm = true
  try {
    const result = await api.testLLMConnect()
    testResult.value = result
    showTestResult.value = true
  } catch (e) {
    message.error('LLM 测试失败')
  } finally {
    testing.value.llm = false
  }
}
```

## 验证步骤

修复完成后，运行以下命令验证：

```bash
# 1. 测试心跳状态显示
curl -s http://localhost:18720/api/active-consciousness/status | python3 -c "import json,sys; d=json.load(sys.stdin); print('心跳次数:', d.get('heartbeat_count'), '上次心跳:', d.get('last_heartbeat_at'))"

# 2. 测试 reflect API
TOKEN=$(curl -s http://localhost:18720/api/auth/login -X POST -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -s -X POST "http://localhost:18720/api/hindsight/reflect?query=test" -H "Authorization: Bearer $TOKEN"

# 3. 测试 LLM 连通性
curl -s -X POST "http://localhost:18720/api/active-consciousness/test/llm-connect" -H "Authorization: Bearer $TOKEN"
```
