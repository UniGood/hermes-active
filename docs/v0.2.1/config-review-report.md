# 前端 Tab 切换 + 配置项审查报告

## 一、Tab 切换后不显示的 Bug

### 根因分析

Naive UI 的 `n-tabs` 配合 `animated` 属性时，会在动画容器上设置 `overflow: hidden`。
子 tab-pane 虽然设置了 `style="overflow: visible;"`，但被父级容器的 `overflow: hidden` 覆盖。

```vue
<!-- 问题代码 -->
<n-tabs v-model:value="activeTab" type="line" animated>
  <n-tab-pane name="status" tab="状态">...</n-tab-pane>
  <n-tab-pane name="logs" tab="日志" style="overflow: visible;">
    <n-tabs type="line" animated style="overflow: visible;">
      <!-- 嵌套 tabs 的 overflow: visible 被父级 animated 容器的 overflow: hidden 覆盖 -->
    </n-tabs>
  </n-tab-pane>
</n-tabs>
```

### 修复方案

在全局 CSS 中覆盖 animated 容器的 overflow：

```css
:deep(.n-tabs-tab-pane) {
  overflow: visible !important;
}
:deep(.n-tab-pane) {
  overflow: visible !important;
}
```

---

## 二、配置项审查

### 2.1 数据库中的配置 vs 代码默认值不一致

| 配置项 | 数据库值 | 代码默认值 | 建议 |
|--------|----------|-----------|------|
| `active.no_send_after_user_msg_minutes` | 10 | 5 | 数据库应更新为 5 |
| `active.no_send_while_heat_above` | 0.5 | 1.0 | 数据库应更新为 1.0 |
| `active.no_send_while_vibe_below` | 0.3 | 0.15 | 数据库应更新为 0.15 |
| `decision.send_threshold` | 0.6 | 0.35 | 数据库应更新为 0.35 |
| `decision.delay_threshold` | 0.3 | 0.15 | 数据库应更新为 0.15 |
| `decision.memory_threshold` | 0.1 | 0.05 | 数据库应更新为 0.05 |
| `session.max_messages_per_session` | 100 | 15 | 看需求决定 |
| `prompts.thought_generation` | 旧格式 | 新格式 | **必须更新**（含 SKIP 机制） |

### 2.2 前端默认配置缺失项

| 配置项 | API 返回 | 前端默认值 | 说明 |
|--------|----------|-----------|------|
| `active.cooldown_minutes` | 30 | ❌ 缺失 | 前端需要添加 |
| `decision.longing_gap_threshold` | 3 | ❌ 缺失 | 前端需要添加 |
| `thought_engine` | ✅ | ✅ | 已添加 |
| `context` | ✅ | ✅ | 已添加 |

### 2.3 多余/冗余的配置项

| 配置项 | 位置 | 建议 |
|--------|------|------|
| `decision.longing_gap_threshold` | decision | 移到 active 或删除（ThoughtEngine 已不使用此逻辑） |
| `active.no_send_while_heat_above` | active | **改为 1.0 或直接删除**（当前 0.5 过于严格，几乎拦截所有发送） |
| `time.deep_night_fitness` | time | 保留但改名为更清晰的 `time.deep_night_weight` |

### 2.4 配置项分组优化建议

当前配置项分组比较混乱，建议重新分组：

**当前分组：**
```
enabled, llm, active, session, decision, hindsight, notify, 
weather, emotion, time, delay, thought, thought_engine, context, prompts
```

**建议分组（合并冗余）：**
```
enabled, llm, 
engine (合并 thought_engine + context),
heartbeat (合并 active + delay),
session, 
decision, 
emotion, 
time, 
hindsight, 
weather, 
notify, 
prompts
```

### 2.5 需要从配置中移除的功能

| 功能 | 原因 |
|------|------|
| `decision.longing_gap_threshold` | ThoughtEngine 已不使用此旧逻辑 |
| `active.no_send_while_heat_above = 0.5` | 过于严格，几乎拦截所有发送 |
| `prompts.thought_generation` 中的旧变量 | `{longing_score}`, `{chat_heat}` 等已被新变量替代 |

---

## 三、优化方案

### Phase 1: 修复 Tab 切换 Bug（紧急）
- 添加全局 CSS 覆盖 animated 容器 overflow

### Phase 2: 更新数据库配置值（紧急）
- 将优化后的配置值写入 active.db
- 更新 thought_generation 提示词为新格式

### Phase 3: 清理前端配置项（中等优先级）
- 添加缺失配置项（cooldown_minutes, longing_gap_threshold）
- 删除冗余配置项
- 重新分组配置面板

### Phase 4: 重新分组配置面板（低优先级）
- 按逻辑分组，减少配置项数量
- 合并相关配置到统一面板
