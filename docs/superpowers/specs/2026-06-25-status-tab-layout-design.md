# 状态 Tab 页卡片布局重构设计

**日期**: 2026-06-25
**状态**: 待审批
**作者**: Kelly (AI Assistant)

---

## 背景

当前状态 Tab 页的卡片布局存在问题：
- PC端同一行的卡片高度不一致
- 移动端布局未优化
- 发送统计单独一行，空间利用率低
- 卡片分组不够清晰

---

## 目标

1. **PC端**：按功能重新分组，同一行卡片高度对齐
2. **移动端**：所有卡片单列垂直排列
3. **分组清晰**：状态概览、情绪系统、LLM统计、发送统计

---

## 设计方案

### 分组结构

| 组 | 包含的卡片 | PC端列数 |
|---|----------|---------|
| **状态概览** | 心跳状态、想念分数、聊天热度、情绪强度 | 4列 |
| **情绪系统** | VA模型、决策配置 | 2列 |
| **LLM统计** | 情绪LLM、念头LLM、总LLM | 3列 |
| **发送统计** | 发送统计（本小时/今日/本周/本月/本年） | 独占一行 |

### PC端布局（≥769px）

```
┌─────────────────────────────────────────────────────────────┐
│                     📊 状态概览                              │
├──────────┬──────────┬──────────┬──────────────────────────────┤
│ 心跳状态 │ 想念分数 │ 聊天热度 │ 情绪强度                    │
├──────────┴──────────┴──────────┴──────────────────────────────┤
│                     🎭 情绪系统                              │
├────────────────────────────┬─────────────────────────────────┤
│      VA 模型               │      决策配置与阈值             │
├────────────────────────────┴─────────────────────────────────┤
│                     📈 LLM 统计                              │
├──────────────┬──────────────┬────────────────────────────────┤
│  🎭 情绪LLM  │  💭 念头LLM  │  📊 总LLM调用                 │
├──────────────┴──────────────┴────────────────────────────────┤
│                     📤 发送统计                              │
│  本小时 │ 今日 │ 本周 │ 本月 │ 本年 │ 上次发送              │
└─────────────────────────────────────────────────────────────┘
```

### 移动端布局（<769px）

```
┌─────────────────────────┐
│       📊 状态概览        │
├─────────────────────────┤
│ 心跳状态                │
├─────────────────────────┤
│ 想念分数                │
├─────────────────────────┤
│ 聊天热度                │
├─────────────────────────┤
│ 情绪强度                │
├─────────────────────────┤
│       🎭 情绪系统        │
├─────────────────────────┤
│ VA 模型                 │
├─────────────────────────┤
│ 决策配置与阈值          │
├─────────────────────────┤
│       📈 LLM 统计        │
├─────────────────────────┤
│ 🎭 情绪LLM              │
├─────────────────────────┤
│ 💭 念头LLM              │
├─────────────────────────┤
│ 📊 总LLM调用            │
├─────────────────────────┤
│       📤 发送统计        │
└─────────────────────────┘
```

---

## 技术实现

### 1. 模板结构

使用 `<n-divider title-placement="left">` 作为分组标题，每个分组用 `<n-grid>` 包裹。

```vue
<!-- 状态概览 -->
<n-divider title-placement="left">
  <n-icon><StatsChartOutline /></n-icon> 状态概览
</n-divider>
<n-grid :cols="isMobile ? 1 : 4" :x-gap="12" :y-gap="12">
  <!-- 4个卡片 -->
</n-grid>

<!-- 情绪系统 -->
<n-divider title-placement="left">
  <n-icon><ColorPaletteOutline /></n-icon> 情绪系统
</n-divider>
<n-grid :cols="isMobile ? 1 : 2" :x-gap="12" :y-gap="12">
  <!-- VA模型、决策配置 -->
</n-grid>

<!-- LLM统计 -->
<n-divider title-placement="left">
  <n-icon><AnalyticsOutline /></n-icon> LLM 统计
</n-divider>
<n-grid :cols="isMobile ? 1 : 3" :x-gap="12" :y-gap="12">
  <!-- 情绪LLM、念头LLM、总LLM -->
</n-grid>

<!-- 发送统计 -->
<n-divider title-placement="left">
  <n-icon><SendOutline /></n-icon> 发送统计
</n-divider>
<n-grid :cols="1" :x-gap="12" :y-gap="12">
  <!-- 发送统计卡片 -->
</n-grid>
```

### 2. 响应式检测

使用 `window.innerWidth` 或 CSS media query 检测移动端：

```javascript
import { ref, onMounted, onUnmounted } from 'vue'

const isMobile = ref(window.innerWidth < 769)

function handleResize() {
  isMobile.value = window.innerWidth < 769
}

onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))
```

### 3. PC端卡片高度对齐

使用 flex 布局确保同一行的卡片高度一致：

```css
@media (min-width: 769px) {
  .n-grid {
    display: flex !important;
    align-items: stretch !important;
  }
  .n-grid-item {
    display: flex !important;
    align-items: stretch !important;
    flex: 1 !important;
  }
  .n-grid-item .n-card {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
  }
}
```

### 4. 分组标题样式

使用 Naive UI 的 `n-divider` 组件，带图标：

```vue
<n-divider title-placement="left" style="margin: 16px 0 12px;">
  <template #default>
    <div style="display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: #333;">
      <n-icon size="18"><StatsChartOutline /></n-icon>
      状态概览
    </div>
  </template>
</n-divider>
```

---

## 修改的文件

| 文件 | 改动 |
|------|------|
| `frontend/src/views/ActiveConsciousness.vue` | 重构状态 Tab 页的模板和样式 |

---

## 成功标准

1. **PC端**：同一行的卡片高度一致，分组清晰
2. **移动端**：所有卡片单列垂直排列，宽度100%
3. **响应式**：窗口大小变化时自动切换布局
4. **视觉**：分组标题醒目，间距统一
