# 被动意识插件开发任务

## 目标

新建 Hermes 插件 `passive-consciousness`，实现被动意识的完整闭环：在用户消息到达时自动注入情绪/热度/记忆/天气上下文。

同时在 hermes-active 前端后端添加完整的测试功能。

## STRICT RULES

- 只修改下面列出的文件，不要改其他文件
- 不要修改 config.py、config.yaml、.env 等配置文件
- 不要修改 hermes-agent 源码
- 不要运行 git 命令
- 使用 sqlite3（标准库），不要引入新的 pip 依赖
- 所有新文件用中文注释

## 项目路径

- hermes-active 项目：`/home/ubuntu/.hermes/hermes-active/`
- 插件目录：`~/.hermes/plugins/passive-consciousness/`（新建）
- state.db：`~/.hermes/state.db`（只读）
- active.db：`~/.hermes/hermes-active/data/active.db`（读写）

## 需要新建的文件

### 文件 1: `~/.hermes/plugins/passive-consciousness/plugin.yaml`

```yaml
name: passive-consciousness
version: "1.0"
description: "被动意识：用户消息到达时注入情绪/热度/记忆/天气上下文"
provides_hooks:
  - pre_llm_call
```

### 文件 2: `~/.hermes/plugins/passive-consciousness/__init__.py`

插件入口，包含 `register(ctx)` 函数和 `pre_llm_call` 钩子。

钩子逻辑：
1. 检查 platform == "weixin"，不是则跳过
2. 检查 state.db 和 active.db 是否存在
3. 读配置（config_reader），检查 enabled
4. 计算状态（consciousness_engine.compute_all）
5. 可选：调天气 API
6. 可选：调 Hindsight recall/reflect
7. 拼装上下文（context_builder）
8. 返回 {"context": "..."} 或 None

错误全部 catch 后 warning 日志，不阻断主流程。

### 文件 3: `~/.hermes/plugins/passive-consciousness/config_reader.py`

从 active.db configs 表读取被动意识配置（前缀 `passive_consciousness.`）。
用 sqlite3 直接读，返回嵌套 dict。
包含类型转换：bool、int、float、json。

### 文件 4: `~/.hermes/plugins/passive-consciousness/consciousness_engine.py`

核心计算引擎，包含：
- `compute_longing(state_db_path)` → `{score, level, label, last_user_msg_at, gap_minutes}`
  - 查最近用户消息时间，gap_minutes / 300 = score（5小时=1.0）
  - 等级：calm(0.0), longing(0.1), missing(0.3), yearning(0.5), anxious(0.7)
- `compute_chat_heat(state_db_path)` → `{heat, label, recent_count, recent_msg_at}`
  - 近1小时用户消息数 / 1.0 = heat
  - 等级：cold(0.0), warm(0.5), hot(1.0), fire(3.0)
- `get_emotional_intensity(active_db_path)` → `{intensity, label, raw_value}`
  - 从 configs 表读 `passive_consciousness.current.emotional_intensity`
  - 标签：<0.3 工作, <0.5 日常, <0.7 八卦, <0.9 情感, >=0.9 深度情感
- `compute_all(state_db_path, active_db_path)` → 合并上述三项

用 sqlite3 直连，查询条件：
- source = 'weixin' AND ended_at IS NULL（活跃微信会话）
- role = 'user'（用户消息）

### 文件 5: `~/.hermes/plugins/passive-consciousness/weather_service.py`

调用高德天气 API：
- URL: `https://restapi.amap.com/v3/weather/weatherInfo?city={adcode}&key={api_key}&extensions=base`
- 用 urllib.request（标准库），不用 requests
- 内存缓存 + TTL
- 返回 `{city, weather, temperature, humidity, winddirection, reporttime}` 或 None

### 文件 6: `~/.hermes/plugins/passive-consciousness/hindsight_client.py`

Hindsight API 客户端：
- `hindsight_recall(query, bank_id, limit, base_url, timeout)` → list[dict]
  - POST `{base_url}/api/v1/recall`
  - body: `{"bank_id": bank_id, "query": query, "max_results": limit, "include_types": ["episodic", "semantic"]}`
- `hindsight_reflect(query, bank_id, base_url, timeout)` → str | None
  - POST `{base_url}/api/v1/reflect`
  - body: `{"bank_id": bank_id, "query": query, "budget": "low"}`

用 urllib.request，超时 recall 10s、reflect 30s。

### 文件 7: `~/.hermes/plugins/passive-consciousness/context_builder.py`

拼装注入上下文：
```
--- [CONSCIOUSNESS_CONTEXT] ---
以下是你（凯莉）当前的感知状态，仅供参考，不要在回复中直接提及这些数据：

🎭 情绪状态：日常（强度 0.45）
🔥 聊天热度：warm（近1小时 2 条消息）
💕 想念程度：longing（分数 0.15）
🌤 天气：济南 晴 28°C 湿度45%

📖 相关记忆：
  1. xxxxxx
  2. xxxxxx

💭 综合反思：xxxxxx
--- /[CONSCIOUSNESS_CONTEXT] ---
```

根据配置的 inject_emotion/inject_heat/inject_memory 开关决定是否包含各部分。
记忆最多 5 条，每条最多 200 字。反思最多 300 字。

## 需要修改的文件

### 文件 8: `/home/ubuntu/.hermes/hermes-active/backend/routers/passive_consciousness.py`

新增以下 API 端点（在现有路由后面追加）：

```python
@router.post("/test/weather")
async def test_weather():
    """测试高德天气 API"""
    # 读 config 获取 weather.enabled, weather.amap_key, weather.adcode
    # 调用高德 API，绕过缓存
    # 返回 {success: bool, data: {...}} 或 {success: bool, error: str}

@router.post("/test/longing")
async def test_longing():
    """测试想念分数计算"""
    # 查 state.db 最近用户消息时间
    # 计算 gap_minutes, score, level, label
    # 返回 {success: bool, data: {score, level, label, last_user_msg_at, gap_minutes}}

@router.post("/test/chat-heat")
async def test_chat_heat():
    """测试聊天热度计算"""
    # 查 state.db 近1小时用户消息数
    # 返回 {success: bool, data: {heat, label, recent_count, recent_msg_at}}

@router.post("/test/emotional-intensity")
async def test_emotional_intensity():
    """测试情绪值读取"""
    # 从 configs 表读 emotional_intensity
    # 返回 {success: bool, data: {intensity, label, raw_value}}

@router.post("/test/context")
async def test_context():
    """测试完整上下文拼装"""
    # 依次调用上面所有测试，收集数据
    # 调用 context_builder 拼装
    # 返回 {steps: [...], context: str, errors: [...]}

@router.get("/test/full")
async def test_full():
    """一键全量测试"""
    # 调用所有测试端点，返回汇总结果
```

注意：
- 天气测试直接用 urllib.request 调用，不依赖插件代码
- 想念/热度测试直接用 SQLAlchemy 的 state_engine 连接查询
- 情绪值测试用 ConfigService 读取
- 上下文测试需要动态导入插件目录的 context_builder（sys.path.insert）

### 文件 9: `/home/ubuntu/.hermes/hermes-active/backend/services/passive_consciousness_service.py`

如果需要，在现有类后面追加测试辅助方法。但大部分测试逻辑直接写在 router 中即可，service 层保持简洁。

### 文件 10: `/home/ubuntu/.hermes/hermes-active/frontend/src/api/passive_consciousness.js`

新增测试 API 调用方法：

```javascript
export default {
  // ... 现有方法 ...
  testLonging: () => request.post('/api/passive-consciousness/test/longing'),
  testChatHeat: () => request.post('/api/passive-consciousness/test/chat-heat'),
  testEmotionalIntensity: () => request.post('/api/passive-consciousness/test/emotional-intensity'),
  testWeather: () => request.post('/api/passive-consciousness/test/weather'),
  testHindsightRecall: () => request.post('/api/passive-consciousness/test/hindsight-recall'),
  testHindsightReflect: () => request.post('/api/passive-consciousness/test/hindsight-reflect'),
  testContext: () => request.post('/api/passive-consciousness/test/context'),
  testFull: () => request.get('/api/passive-consciousness/test/full'),
}
```

### 文件 11: `/home/ubuntu/.hermes/hermes-active/frontend/src/views/PassiveConsciousness.vue`

新增第四个 Tab "测试"，包含：

1. **一键全量测试按钮**（顶部醒目位置）
2. **单项测试卡片**，每个卡片包含：
   - 测试按钮（点击调用对应 API）
   - 结果展示区（用 n-descriptions 展示返回数据）
   - 错误提示（n-alert）
3. **完整上下文预览**：
   - 模拟完整流程按钮
   - 步骤状态列表（每个步骤显示 ok/error）
   - 最终上下文文本展示（n-code）

测试卡片列表：
- 💕 想念分数
- 🔥 聊天热度
- 🎭 情绪值
- 🌤 天气感知（高德 API）
- 📖 Hindsight 记忆（Recall + Reflect 两个按钮）
- 📋 完整上下文预览

UI 要求：
- 按钮用 n-button，loading 状态
- 结果用 n-descriptions 展示
- 错误用 n-alert type="error"
- 上下文用 n-code 展示
- 每个测试卡片用 n-card 包裹

## 验证步骤

完成后：
1. 检查 `~/.hermes/plugins/passive-consciousness/` 目录下有 7 个文件
2. 检查后端新增了 6 个 API 端点
3. 检查前端新增了测试 Tab
4. 构建前端：`cd /home/ubuntu/.hermes/hermes-active/frontend && npm run build`
