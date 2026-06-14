1|# hermes-active 自主意识模块 - 设计文档
2|
3|## 架构分析：为什么不用改 hermes 源码
4|
5|### 核心结论
6|
7|**不需要改 hermes 源码，不需要 hook，不需要拦截用户消息。**
8|
9|hermes 有 `write_state_db` 和 `run_cron` 两种"写入能力"。注入上下文最简单的方案是：
10|
11|```
12|hermes-active 调用 hermes 的 API（主动消息专用，注入原生对话上下文）
13|```
14|
15|### 用户消息时为什么不注入
16|
17|用户消息时注入意识上下文，意味着要 hook hermes 的 `pre_llm_call`，修改她的 prompt。这会：
18|- 侵犯凯莉的"人格完整性"
19|- 增加核心 LLM 调用延迟
20|- 需要改 hermes 源码
21|
22|**更好的做法**：自主意识只用"凯莉自己的声音"（hermes-active 的辅助 LLM），通过主动消息说话。凯莉的"人格"属于 hermes，意识属于 hermes-active，互不干涉。
23|
24|### 发送消息的 2 种情况
25|
26|| 情况 | 触发时机 | 谁说话 | 注入方式 |
27||------|---------|--------|---------|
28|| **自动发送** | 心跳 + 情绪值 > 0.5 | hermes-active 辅助 LLM | `inject_love_message` API |
29|| **长期未聊天** | 想念等级 > `longing_gap_threshold`（默认 3） | hermes-active 辅助 LLM | `inject_love_message` API |
30|
31|**两种情况都走同一个 API**：`POST /api/messages/send-and-inject`
32|
33|### 注入方式：inject_love_message
34|
35|```
36|hermes-active 生成消息内容
37|  ↓
38|POST /api/messages/send-and-inject
39|  ├─ step1: send_to_weixin_via_weixin_bot()  → 微信直接送达
40|  └─ step2: inject_love_message(session_id, text, timestamp)
41|       ├─ 写入 state.db（标记 [凯莉主动发送]）
42|       ├─ 写入 hermes session DB（标记 [凯莉主动发送]）
43|       └─ hermes 下次 LLM 调用时自动读取 → 作为上下文的一部分
44|```
45|
46|好处：
47|- 不 hook，不改 hermes 源码
48|- 原生对话上下文注入（hermes 自动读取）
49|- 最小侵入
50|
51|---
52|
53|## coexistence_mode 与 vibe 变量
54|
55|凯莉有三个可配置的共存模式：
56|
57|| 模式 | 行为 | 适用场景 |
58||------|------|---------|
59|| `silent` | 完全不注入，只观察 | 用户希望凯莉安静 |
60|| `independent` | 偶尔注入情绪变化，不影响主对话 | **默认推荐** |
61|| `merged` | 情绪主动融入主对话风格 | 用户希望凯莉有情绪表达 |
62|
63|**`independent` 模式下的 vibe 变量注入**：
64|
65|当 hermes-active 检测到凯莉情绪有显著变化时，通过插件注入 vibe 变量到 hermes 的 system prompt：
66|
67|```
68|[kelly_vibe: excited — 心情好，最近和用户聊了很多有趣的话题]
69|[kelly_vibe: yearning — 有点想念，用户很久没出现了]
70|[kelly_vibe: calm — 平静，最近状态稳定]
71|```
72|
73|hermes 的主 LLM 读到 vibe 变量后，自然调整回复风格。不是修改消息内容，只是让 LLM 知道凯莉现在的情绪状态。
74|
75|**daily_stats 作为 LLM 观察输入**：
76|
77|hermes 插件通过 `pre_llm_call` 钩子读取 `daily_stats`，注入到 system prompt：
78|
79|```
80|[kelly_daily_observation]
81|今日：对话 47 条，主动消息 2 条，话题：工作、晚餐、周末计划
82|情绪轨迹：下午平静 → 傍晚开心 → 现在有点想念
83|聊天热度：warm（0.4）
84|情绪值：0.6
85|[/kelly_daily_observation]
86|```
87|
88|这是**观察输入**，不是修改。LLM 自己决定怎么用这些信息。
89|
90|---
91|
92|## 一、触发发送的 2 种情况
93|
94|### 1.1 自动发送（心跳驱动）
95|
96|```
97|心跳触发（每 N 分钟）
98|  → 想法生成（三步流程）
99|  → 情绪值 > 0.5
100|  → 想念等级 > 0（recent_minutes > 15 分钟）
101|  → 最近 10 分钟无用户消息
102|  → 冷却期已过
103|  → 决策：auto_send
104|  → 生成消息内容
105|  → inject_love_message()
106|```
107|
108|### 1.2 长期未聊天检查（心跳中的特殊条件）
109|
110|```
111|心跳触发
112|  → 想念等级 > longing_gap_threshold（默认 3 = 5 小时）
113|  → 不需要情绪值条件（想念本身就够了）
114|  → 决策：gap_send
115|  → 生成消息内容
116|  → inject_love_message()
117|```
118|
119|---
120|
121|## 二、日志设计
122|
123|### 2.1 独立日志表
124|
125|**表名**: `vibe_logs`（在 active.db 中新建）
126|
127|| 字段 | 类型 | 说明 |
128||------|------|------|
129|| id | INTEGER PK | 自增 ID |
130|| timestamp | DATETIME | 记录时间 |
131|| session_id | TEXT | 关联 session（可空） |
132|| module | TEXT | 模块：`heartbeat` / `thought` / `emotion` / `decision` / `llm` |
133|| level | TEXT | 级别：`info` / `warn` / `error` |
134|| message | TEXT | 日志消息（人类可读） |
135|| data | TEXT | JSON 数据（结构化细节） |
136|| duration_ms | INTEGER | 耗时（可空） |
137|| created_at | DATETIME | 创建时间 |
138|
139|### 2.2 每次 LLM 调用必须记录
140|
141|```
142|module="llm" level="info"
143|message="Step 1: 近期 session 提取"
144|data={
145|  "provider": "deepseek",
146|  "model": "deepseek-chat",
147|  "provider_config": "deepseek (deepseek-chat)",
148|  "session_count": 3,
149|  "message_count": 45,
150|  "input_tokens": 2340,
151|  "output_tokens": 180,
152|  "duration_ms": 3200,
153|  "status": "success"
154|}
155|```
156|
157|### 2.3 每个决策步骤必须记录
158|
159|```
160|module="decision" level="info"
161|message="自动发送决策"
162|data={
163|  "recent_minutes": 25,
164|  "longing_level": 2,
165|  "chat_heat": 0.3,
166|  "emotional_intensity": 0.6,
167|  "vibe_score": 0.18,
168|  "final_decision": "auto_send",
169|  "reason": "vibe_score(0.18) > auto_send_threshold(0.15), 最近25分钟无消息"
170|}
171|```
172|
173|### 2.4 API 设计
174|
175|```python
176|# 前端查看日志
177|GET /api/consciousness/logs?limit=50&module=decision
178|
179|# 后端记录日志
180|def write_vibe_log(db, module, level, message, data=None, session_id=None, duration_ms=None):
181|    """每次 LLM 调用、每个决策步骤都必须调用此方法"""
182|```
183|
184|---
185|
186|## 三、配置参数设计
187|
188|### 3.1 参数总表
189|
190|| 配置项 | key | 类型 | 默认值 | 说明 |
191||--------|-----|------|--------|------|
192|| **开关** | | | | |
193|| 启用自主意识 | `consciousness.enabled` | bool | `false` | 总开关 |
194|| **LLM** | | | | |
195|| Provider | `consciousness.llm.provider` | string | `deepseek` | 独立 LLM |
196|| Model | `consciousness.llm.model` | string | `deepseek-chat` | |
197|| API Key | `consciousness.llm.api_key` | string | `""` | |
198|| Base URL | `consciousness.llm.base_url` | string | `""` | |
199|| **心跳** | | | | |
200|| 心跳间隔 | `consciousness.heartbeat.interval_minutes` | int | `10` | 心跳周期（分钟） |
201|| **想法生成** | | | | |
202|| Session 来源 | `consciousness.thought.session_source` | string | `weixin` | 默认只选微信 session |
203|| 时间范围 | `consciousness.thought.time_range_hours` | int | `24` | 最近 N 小时 |
204|| 每 session 消息数 | `consciousness.thought.messages_per_session` | int | `15` | 最近 N 条 |
205|| 包含 Tool 消息 | `consciousness.thought.include_tool` | bool | `false` | 默认过滤 Tool |
206|| Hindsight Recall 数 | `consciousness.thought.hindsight_recall_limit` | int | `5` | |
207|| Hindsight Reflect | `consciousness.thought.hindsight_reflect_enabled` | bool | `true` | |
208|| **情绪** | | | | |
209|| 冷却期 | `consciousness.emotion.cooldown_minutes` | int | `30` | 发送后冷却 |
210|| 短时窗口 | `consciousness.emotion.recent_window_minutes` | int | `10` | 活跃判定窗口 |
211|| 情绪衰减周期 | `consciousness.emotion.decay_hours` | int | `24` | 聊天热度衰减 |
212|| **触发阈值** | | | | |
213|| 自动发送阈值 | `consciousness.trigger.auto_send_threshold` | float | `0.15` | vibe > 此值 → 发送 |
214|| 想念等级间隔 | `consciousness.trigger.longing_level_minutes` | string | `15,60,180,300` | 各等级触发分钟 |
215|| 长期未聊天阈值 | `consciousness.trigger.longing_gap_threshold` | int | `3` | 想念等级 > 此值 → 发送 |
216|| 每日最大消息 | `consciousness.trigger.max_messages_per_day` | int | `5` | |
217|| 每小时最大消息 | `consciousness.trigger.max_messages_per_hour` | int | `2` | |
218|| **共存模式** | | | | |
219|| 模式 | `consciousness.coexistence.mode` | string | `independent` | silent/independent/merged |
220|| **通知** | | | | |
221|| 目标平台 | `consciousness.notify.platform` | string | `weixin` | |
222|| Chat ID | `consciousness.notify.chat_id` | string | `""` | |
223|| **天气** | | | | |
224|| 启用天气 | `consciousness.weather.enabled` | bool | `false` | |
225|| 城市编码 | `consciousness.weather.adcode` | string | `370100` | |
226|| API Key | `consciousness.weather.amap_key` | string | `""` | 高德 API Key |
227|
228|### 3.2 存储方式
229|
230|复用 `configs` 表（key-value），key 加 `consciousness.` 前缀。
231|
232|---
233|
234|## 四、前端页面设计
235|
236|### 4.1 独立页面
237|
238|侧边栏新增「自主意识」菜单，路由 `/consciousness`，包含：
239|- 配置卡片（所有参数）
240|- 测试按钮（天气/Hindsight/想法生成/发送）
241|- 运行状态
242|- 日志查看
243|
244|### 4.2 测试按钮
245|
246|| 按钮 | API | 说明 |
247||------|-----|------|
248|| 获取天气 | `GET /api/consciousness/test/weather` | 弹窗显示天气 |
249|| Hindsight 测试 | `GET /api/consciousness/test/hindsight?query=曹凡` | 弹窗显示记忆 |
250|| 想法生成测试 | `POST /api/consciousness/test/thought` | 三步流程，弹窗显示 |
251|| 发送测试 | `POST /api/consciousness/test/send` | 发送到微信 |
252|
253|---
254|
255|## 五、数据模型
256|
257|### 5.1 表结构
258|
259|```
260|active.db
261|├── consciousness_state     # 意识状态（单行）
262|├── daily_stats             # 每日统计（per day）
263|├── thought_logs            # 想法日志（每次心跳一条）
264|├── pending_thoughts        # 待发送想法队列
265|├── heartbeat_logs          # 心跳日志
266|├── vibe_logs               # 操作日志（LLM 调用 + 决策 + 错误）
267|└── configs                 # 配置（consciousness.* 前缀）
268|```
269|
270|### 5.2 consciousness_state 表
271|
272|```sql
273|CREATE TABLE consciousness_state (
274|    id              INTEGER PRIMARY KEY CHECK (id = 1),
275|    enabled         INTEGER NOT NULL DEFAULT 0,
276|    chat_heat       REAL NOT NULL DEFAULT 0.0,
277|    emotional_intensity REAL NOT NULL DEFAULT 0.0,
278|    vibe_score      REAL NOT NULL DEFAULT 0.0,
279|    longing_level   INTEGER NOT NULL DEFAULT 0,
280|    recent_minutes  INTEGER NOT NULL DEFAULT 0,
281|    last_user_message_at DATETIME,
282|    last_auto_send_at DATETIME,
283|    last_llm_call_at DATETIME,
284|    total_llm_calls INTEGER NOT NULL DEFAULT 0,
285|    total_auto_sends INTEGER NOT NULL DEFAULT 0,
286|    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
287|);
288|```
289|
290|### 5.3 vibe_logs 表
291|
292|```sql
293|CREATE TABLE vibe_logs (
294|    id          INTEGER PRIMARY KEY AUTOINCREMENT,
295|    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
296|    session_id  TEXT,
297|    module      TEXT NOT NULL,      -- heartbeat/thought/emotion/decision/llm/send/error
298|    level       TEXT NOT NULL DEFAULT 'info',
299|    message     TEXT NOT NULL,
300|    data        TEXT,               -- JSON
301|    duration_ms INTEGER,
302|    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
303|);
304|CREATE INDEX idx_vibe_logs_timestamp ON vibe_logs(timestamp);
305|CREATE INDEX idx_vibe_logs_module ON vibe_logs(module);
306|```
307|
308|---
309|
310|## 六、实施计划
311|
312|### Phase 1：后端基础（Day 1-2）
313|- active.db 建表（consciousness_state, daily_stats, thought_logs, vibe_logs）
314|- ConfigService 新增 consciousness 配置读写
315|- API 端点（配置 CRUD + 测试按钮）
316|
317|### Phase 2：前端页面（Day 2-3）
318|- 侧边栏新增菜单
319|- Consciousness.vue（配置卡片 + 测试按钮 + 状态 + 日志）
320|- API 调用封装
321|
322|### Phase 3：意识引擎（Day 3-5）
323|- 感知处理（时间、空白、天气）
324|- 近期 session 提取（LLM Step 1）
325|- Hindsight Recall/Reflect（Step 2）
326|- 想法生成（Step 3）
327|- 情绪计算（聊天热度 + 情绪值 + 想念等级 + vibe_score）
328|- 决策逻辑（2 种发送情况）
329|
330|### Phase 4：心跳 + 消息发送（Day 5-6）
331|- 心跳引擎（定时器 + 状态更新）
332|- 消息生成（LLM）
333|- 消息发送（inject_love_message API）
334|- pending_thoughts 管理
335|
336|### Phase 5：日志 + 调试（Day 6-7）
337|- vibe_logs 写入（每个 LLM 调用、每个决策步骤）
338|- 前端日志查看
339|- 测试按钮功能
340|