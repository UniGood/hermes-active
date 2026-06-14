# 自主意识模块 — 配置设计文档

## 一、目标

在配置管理页面（Config.vue）新增「自主意识」配置卡片，让用户可以：
1. 独立开关自主意识功能
2. 配置独立的 LLM（不和主对话共用）
3. 配置心跳频率、决策阈值等所有参数
4. 配置 Hindsight 记忆集成
5. 配置天气感知（高德 API）

**所有阈值从配置读取，不硬编码。**

---

## 二、配置卡片 UI 设计

### 2.1 卡片位置

在 Config.vue 页面中，「自主意识」卡片放在「LLM 配置」之后、「修改密码」之前。

### 2.2 卡片结构

```
┌─────────────────────────────────────────────────┐
│  🧠 自主意识                              [开关] │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─ LLM 配置（独立） ─────────────────────────┐ │
│  │  Provider    [openai          ▾]           │ │
│  │  Model       [deepseek-chat   ]           │ │
│  │  API Key     [••••••••        👁]          │ │
│  │  Base URL    [https://api...  ]           │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 心跳配置 ─────────────────────────────────┐ │
│  │  心跳间隔(秒)  [  300  ]                   │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 决策阈值 ─────────────────────────────────┐ │
│  │  立即发送阈值   [  0.6  ]  > 此值 → 发消息  │ │
│  │  延迟发送阈值   [  0.3  ]  > 此值 → 延迟    │ │
│  │  存为记忆阈值   [  0.1  ]  > 此值 → 存记忆  │ │
│  │  每小时最大消息  [  2    ]                   │ │
│  │  每日最大消息   [  5    ]                   │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ Hindsight 记忆 ───────────────────────────┐ │
│  │  启用 Hindsight  [✓]                       │ │
│  │  Recall 结果数   [  5   ]                   │ │
│  │  Reflect 启用    [✓]                        │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 天气感知（高德 API）──────────────────────┐ │
│  │  启用天气感知    [✓]                        │ │
│  │  城市编码        [  370100  ]               │ │
│  │  API Key         [••••••••  👁]             │ │
│  │  缓存时长(秒)    [  600  ]                  │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ 通知目标 ─────────────────────────────────┐ │
│  │  目标平台  [ weixin ▾]                      │ │
│  │  Chat ID   [                    ]           │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│              [ 保存配置 ]                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 三、配置参数清单

### 3.1 参数总表

| 配置项 | config key | 类型 | 默认值 | 说明 |
|--------|-----------|------|--------|------|
| **开关** | | | | |
| 启用自主意识 | `consciousness.enabled` | bool | `false` | 总开关 |
| **LLM** | | | | |
| Provider | `consciousness.llm.provider` | string | `openai` | 独立 LLM provider |
| Model | `consciousness.llm.model` | string | `deepseek-chat` | 独立 LLM model |
| API Key | `consciousness.llm.api_key` | string | `""` | 独立 API Key |
| Base URL | `consciousness.llm.base_url` | string | `""` | 独立 Base URL |
| **心跳** | | | | |
| 心跳间隔 | `consciousness.heartbeat.interval_seconds` | int | `300` | 心跳周期（秒） |
| **决策阈值** | | | | |
| 立即发送阈值 | `consciousness.decision.send_threshold` | float | `0.6` | score > 此值 → 发送 |
| 延迟发送阈值 | `consciousness.decision.delay_threshold` | float | `0.3` | score > 此值 → 延迟 |
| 存为记忆阈值 | `consciousness.decision.memory_threshold` | float | `0.1` | score > 此值 → 存记忆 |
| 每小时最大消息 | `consciousness.decision.max_per_hour` | int | `2` | 频率限制 |
| 每日最大消息 | `consciousness.decision.max_per_day` | int | `5` | 每日上限 |
| **Hindsight** | | | | |
| 启用 Hindsight | `consciousness.hindsight.enabled` | bool | `true` | 是否集成记忆 |
| Recall 结果数 | `consciousness.hindsight.recall_limit` | int | `5` | 每次 recall 返回条数 |
| Reflect 启用 | `consciousness.hindsight.reflect_enabled` | bool | `true` | 是否启用 reflect |
| **天气** | | | | |
| 启用天气感知 | `consciousness.weather.enabled` | bool | `false` | 是否启用 |
| 城市编码 | `consciousness.weather.adcode` | string | `370100` | 高德城市编码 |
| API Key | `consciousness.weather.amap_key` | string | `""` | 高德 API Key |
| 缓存时长 | `consciousness.weather.cache_ttl` | int | `600` | 缓存秒数 |
| **通知** | | | | |
| 目标平台 | `consciousness.notify.platform` | string | `weixin` | 消息发送平台 |
| Chat ID | `consciousness.notify.chat_id` | string | `""` | 目标聊天 ID |

### 3.2 存储方式

复用现有的 `configs` 表（key-value），所有 key 加 `consciousness.` 前缀：

```
configs 表:
  key = "consciousness.enabled"       value = "false"
  key = "consciousness.llm.provider"  value = "openai"
  key = "consciousness.llm.model"     value = "deepseek-chat"
  ...
```

这样做的好处：
- 不需要新建表
- 复用现有的 `ConfigService.get_config()` / `set_config()` 接口
- 前端通过 `/api/config/get/{key}` 和 `/api/config/set` 读写

---

## 四、后端设计

### 4.1 新增 Schema

**文件**: `backend/models/schemas.py`

```python
class ConsciousnessLLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = ""

class ConsciousnessDecisionConfig(BaseModel):
    send_threshold: float = 0.6
    delay_threshold: float = 0.3
    memory_threshold: float = 0.1
    max_per_hour: int = 2
    max_per_day: int = 5

class ConsciousnessHindsightConfig(BaseModel):
    enabled: bool = True
    recall_limit: int = 5
    reflect_enabled: bool = True

class ConsciousnessWeatherConfig(BaseModel):
    enabled: bool = False
    adcode: str = "370100"
    amap_key: str = ""
    cache_ttl: int = 600

class ConsciousnessNotifyConfig(BaseModel):
    platform: str = "weixin"
    chat_id: str = ""

class ConsciousnessConfig(BaseModel):
    enabled: bool = False
    llm: ConsciousnessLLMConfig = ConsciousnessLLMConfig()
    heartbeat_interval_seconds: int = 300
    decision: ConsciousnessDecisionConfig = ConsciousnessDecisionConfig()
    hindsight: ConsciousnessHindsightConfig = ConsciousnessHindsightConfig()
    weather: ConsciousnessWeatherConfig = ConsciousnessWeatherConfig()
    notify: ConsciousnessNotifyConfig = ConsciousnessNotifyConfig()
```

### 4.2 新增 API 端点

**文件**: `backend/routers/config.py`（追加）

```python
# ============ 自主意识配置 ============

@router.get("/consciousness", response_model=ConsciousnessConfig)
async def get_consciousness_config(...):
    """获取自主意识配置"""
    # 从 configs 表读取所有 consciousness.* 前缀的配置
    # 组装成 ConsciousnessConfig 返回

@router.put("/consciousness", response_model=SuccessResponse)
async def update_consciousness_config(config: ConsciousnessConfig, ...):
    """更新自主意识配置"""
    # 将 ConsciousnessConfig 拆分成 key-value
    # 写入 configs 表
```

### 4.3 ConfigService 新增方法

**文件**: `backend/services/config_service.py`（追加）

```python
@staticmethod
def get_consciousness_config(db: Session) -> dict:
    """获取自主意识配置"""

@staticmethod
def update_consciousness_config(db: Session, config: dict):
    """更新自主意识配置"""
```

---

## 五、前端设计

### 5.1 Config.vue 新增卡片

在 `LLM 配置` 卡片之后、`修改密码` 卡片之前，新增：

```vue
<!-- 自主意识配置 -->
<n-card title="🧠 自主意识" style="margin-bottom: 16px">
  <!-- 开关 -->
  <n-form-item label="启用">
    <n-switch v-model:value="consciousnessConfig.enabled" />
  </n-form-item>

  <template v-if="consciousnessConfig.enabled">
    <!-- LLM 配置（独立） -->
    <n-divider>LLM 配置（独立）</n-divider>
    ...

    <!-- 心跳配置 -->
    <n-divider>心跳配置</n-divider>
    ...

    <!-- 决策阈值 -->
    <n-divider>决策阈值</n-divider>
    ...

    <!-- Hindsight -->
    <n-divider>Hindsight 记忆</n-divider>
    ...

    <!-- 天气感知 -->
    <n-divider>天气感知</n-divider>
    ...

    <!-- 通知目标 -->
    <n-divider>通知目标</n-divider>
    ...
  </template>

  <n-button type="primary" @click="saveConsciousnessConfig">保存</n-button>
</n-card>
```

### 5.2 新增 API 调用

**文件**: `frontend/src/api/config.js`（追加）

```javascript
// 自主意识配置
export const getConsciousnessConfig = () => http.get('/config/consciousness')
export const updateConsciousnessConfig = (data) => http.put('/config/consciousness', data)
```

---

## 六、实施计划

### Phase 1：后端（约 2 小时）

1. `schemas.py` — 新增 ConsciousnessConfig 相关 schema
2. `config_service.py` — 新增 get/update 方法
3. `config.py` (router) — 新增 GET/PUT 端点

### Phase 2：前端（约 2 小时）

1. `config.js` (api) — 新增接口调用
2. `Config.vue` — 新增自主意识配置卡片

### Phase 3：测试（约 1 小时）

1. 前端页面渲染正确
2. 保存/加载配置正常
3. 所有参数可配置

---

## 七、文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `backend/models/schemas.py` | 追加 | 新增 ConsciousnessConfig schema |
| `backend/services/config_service.py` | 追加 | 新增 get/update 方法 |
| `backend/routers/config.py` | 追加 | 新增 API 端点 |
| `frontend/src/api/config.js` | 追加 | 新增 API 调用 |
| `frontend/src/views/Config.vue` | 追加 | 新增配置卡片 |

**不新建文件，不改现有方法，只在现有文件中追加。**
