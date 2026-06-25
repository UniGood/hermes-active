# 状态 Tab 页卡片布局重构实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 重构主动意识状态 Tab 页的卡片布局，PC端按功能分组且同行高度对齐，移动端单列布局

**架构：** 使用响应式检测（isMobile），PC端4列→2列→3列→1列布局，移动端全部单列。用 n-divider 分组标题，flex 布局确保高度对齐。

**技术栈：** Vue 3、Naive UI、CSS Flexbox

---

## 文件清单

### 修改文件

| 文件 | 职责 |
|------|------|
| `frontend/src/views/ActiveConsciousness.vue` | 重构状态 Tab 页模板和样式（第1-280行） |

---

## 任务 1：添加响应式检测

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`

- [ ] **步骤 1：在 script setup 中添加响应式检测**

在 `<script setup>` 的 import 之后添加：

```javascript
import { ref, onMounted, onUnmounted, computed } from 'vue'

// 响应式检测
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < 769)

function handleResize() {
  windowWidth.value = window.innerWidth
}

onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active
python3 -c "import subprocess; subprocess.run(['npx', 'vue-tsc', '--noEmit'], cwd='frontend')"
```

- [ ] **步骤 3：Commit**

```bash
cd ~/.hermes/hermes-active
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat(ui): 添加响应式检测 isMobile"
```

---

## 任务 2：重构状态概览区域（4列→移动端单列）

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue:6-61`

- [ ] **步骤 1：替换状态概览区域**

将原来的：
```vue
<!-- 第1行：核心状态（4个卡片） -->
<n-grid :cols="4" :x-gap="12" :y-gap="12">
  <!-- 4个 grid-item -->
</n-grid>
```

替换为：
```vue
<!-- 状态概览 -->
<div class="section-title">
  <n-icon size="18"><StatsChartOutline /></n-icon>
  <span>状态概览</span>
</div>
<n-grid :cols="isMobile ? 1 : 4" :x-gap="12" :y-gap="12">
  <!-- 心跳状态 -->
  <n-grid-item>
    <n-card size="small">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span :class="['breathing-dot', heartbeatHealthy ? 'dot-green' : 'dot-red']"></span>
          <span>心跳状态</span>
        </div>
      </template>
      <n-statistic label="今日心跳" :value="status.heartbeat_count" />
      <div style="margin-top: 4px; font-size: 11px; color: #999;">
        上次：{{ formatTime(status.last_heartbeat_at) || '无' }}
      </div>
      <div style="margin-top: 4px; font-size: 11px; color: #666;">
        下次：{{ nextHeartbeatDisplay }}
      </div>
    </n-card>
  </n-grid-item>
  <!-- 想念分数 -->
  <n-grid-item>
    <n-card size="small" title="想念分数">
      <n-statistic :value="status.longing.score" :precision="3">
        <template #suffix>
          <n-tag :type="longingTagType" size="small">{{ status.longing.label }}</n-tag>
        </template>
      </n-statistic>
      <n-progress :percentage="Number((status.longing.score * 100).toFixed(1))" :color="longingColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
      <div style="margin-top: 4px; font-size: 11px; color: #999;">
        沉默：{{ status.longing.silence_minutes ? Math.round(status.longing.silence_minutes) + '分钟' : '-' }}
      </div>
    </n-card>
  </n-grid-item>
  <!-- 聊天热度 -->
  <n-grid-item>
    <n-card size="small" title="聊天热度">
      <n-statistic :value="status.chat_heat.heat" :precision="2">
        <template #suffix>
          <n-tag :type="heatTagType" size="small">{{ status.chat_heat.label }}</n-tag>
        </template>
      </n-statistic>
      <n-progress :percentage="chatHeatPercentage" :color="heatProgressColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
      <div style="margin-top: 4px; font-size: 11px; color: #999;">
        近1小时：{{ status.chat_heat.recent_count || 0 }} 条
      </div>
    </n-card>
  </n-grid-item>
  <!-- 情绪强度 -->
  <n-grid-item>
    <n-card size="small" title="情绪强度">
      <n-statistic :value="status.emotional_intensity.intensity" :precision="3">
        <template #suffix>
          <n-tag size="small">{{ status.emotional_intensity.label }}</n-tag>
        </template>
      </n-statistic>
      <n-progress :percentage="status.emotional_intensity.intensity * 100" :color="intensityColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
    </n-card>
  </n-grid-item>
</n-grid>
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build 2>&1 | tail -5
```

- [ ] **步骤 3：Commit**

```bash
cd ~/.hermes/hermes-active
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat(ui): 状态概览区域响应式布局"
```

---

## 任务 3：重构情绪系统区域（2列→移动端单列）

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue:63-166`

- [ ] **步骤 1：替换情绪系统区域**

将原来的：
```vue
<!-- 第2行：VA模型 + 决策配置 -->
<n-grid :cols="2" :x-gap="12" :y-gap="12" style="margin-top: 12px;">
  <!-- 2个 grid-item -->
</n-grid>
```

替换为：
```vue
<!-- 情绪系统 -->
<div class="section-title" style="margin-top: 16px;">
  <n-icon size="18"><ColorPaletteOutline /></n-icon>
  <span>情绪系统</span>
</div>
<n-grid :cols="isMobile ? 1 : 2" :x-gap="12" :y-gap="12">
  <!-- VA模型 -->
  <n-grid-item>
    <n-card size="small" title="情绪状态（VA 模型）">
      <!-- 原有内容 -->
    </n-card>
  </n-grid-item>
  <!-- 决策配置 -->
  <n-grid-item>
    <n-card size="small" title="决策配置与阈值">
      <!-- 原有内容 -->
    </n-card>
  </n-grid-item>
</n-grid>
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build 2>&1 | tail -5
```

- [ ] **步骤 3：Commit**

```bash
cd ~/.hermes/hermes-active
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat(ui): 情绪系统区域响应式布局"
```

---

## 任务 4：重构发送统计区域

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue:168-200`

- [ ] **步骤 1：替换发送统计区域**

将原来的：
```vue
<!-- 第3行：发送统计 -->
<n-grid :cols="1" :x-gap="12" :y-gap="12" style="margin-top: 12px;">
  <!-- 发送统计卡片 -->
</n-grid>
```

替换为：
```vue
<!-- 发送统计 -->
<div class="section-title" style="margin-top: 16px;">
  <n-icon size="18"><SendOutline /></n-icon>
  <span>发送统计</span>
</div>
<n-grid :cols="1" :x-gap="12" :y-gap="12">
  <n-grid-item>
    <n-card size="small">
      <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 12px;">
        <!-- 原有内容 -->
      </div>
    </n-card>
  </n-grid-item>
</n-grid>
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build 2>&1 | tail -5
```

- [ ] **步骤 3：Commit**

```bash
cd ~/.hermes/hermes-active
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat(ui): 发送统计区域响应式布局"
```

---

## 任务 5：重构 LLM 统计区域（3列→移动端单列）

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue:202-279`

- [ ] **步骤 1：替换 LLM 统计区域**

将原来的：
```vue
<!-- LLM 调用统计 -->
<n-grid :cols="3" :x-gap="12" :y-gap="12" style="margin-top: 12px;">
  <!-- 3个 grid-item -->
</n-grid>
```

替换为：
```vue
<!-- LLM 统计 -->
<div class="section-title" style="margin-top: 16px;">
  <n-icon size="18"><AnalyticsOutline /></n-icon>
  <span>LLM 统计</span>
</div>
<n-grid :cols="isMobile ? 1 : 3" :x-gap="12" :y-gap="12">
  <!-- 情绪LLM -->
  <n-grid-item>
    <n-card size="small" title="🎭 情绪 LLM">
      <!-- 原有内容 -->
    </n-card>
  </n-grid-item>
  <!-- 念头LLM -->
  <n-grid-item>
    <n-card size="small" title="💭 念头 LLM">
      <!-- 原有内容 -->
    </n-card>
  </n-grid-item>
  <!-- 总LLM -->
  <n-grid-item>
    <n-card size="small" title="📊 总 LLM 调用">
      <!-- 原有内容 -->
    </n-card>
  </n-grid-item>
</n-grid>
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build 2>&1 | tail -5
```

- [ ] **步骤 3：Commit**

```bash
cd ~/.hermes/hermes-active
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat(ui): LLM统计区域响应式布局"
```

---

## 任务 6：添加分组标题样式和 PC 端高度对齐

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`（style 部分）

- [ ] **步骤 1：添加分组标题样式**

在 `<style scoped>` 中添加：

```css
/* 分组标题 */
.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.section-title .n-icon {
  color: var(--theme-primary, #4a90d9);
}
```

- [ ] **步骤 2：添加 PC 端高度对齐样式**

在 `<style scoped>` 中添加：

```css
/* PC 端卡片高度对齐 */
@media (min-width: 769px) {
  .active-consciousness-page .n-grid {
    display: flex !important;
    align-items: stretch !important;
  }
  .active-consciousness-page .n-grid-item {
    display: flex !important;
    align-items: stretch !important;
    flex: 1 !important;
  }
  .active-consciousness-page .n-grid-item .n-card {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
  }
  .active-consciousness-page .n-grid-item .n-card .n-card__content {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
  }
}
```

- [ ] **步骤 3：验证语法**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build 2>&1 | tail -5
```

- [ ] **步骤 4：Commit**

```bash
cd ~/.hermes/hermes-active
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat(ui): 分组标题样式和PC端高度对齐"
```

---

## 任务 7：添加图标 import

**文件：**
- 修改：`frontend/src/views/ActiveConsciousness.vue`（script setup）

- [ ] **步骤 1：添加图标 import**

在 `<script setup>` 的 import 中添加：

```javascript
import { StatsChartOutline, ColorPaletteOutline, AnalyticsOutline, SendOutline } from '@vicons/ionicons5'
```

- [ ] **步骤 2：验证语法**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build 2>&1 | tail -5
```

- [ ] **步骤 3：Commit**

```bash
cd ~/.hermes/hermes-active
git add frontend/src/views/ActiveConsciousness.vue
git commit -m "feat(ui): 添加分组图标"
```

---

## 任务 8：测试和最终验证

- [ ] **步骤 1：构建验证**

```bash
cd ~/.hermes/hermes-active/frontend && npm run build
```

预期：构建成功

- [ ] **步骤 2：重启前端服务**

```bash
systemctl --user restart hermes-active-frontend.service
```

- [ ] **步骤 3：浏览器测试**

1. PC端（≥769px）：验证4列→2列→3列→1列布局，同行卡片高度一致
2. 移动端（<769px）：验证所有卡片单列垂直排列
3. 缩放窗口：验证响应式切换

- [ ] **步骤 4：最终 Commit**

```bash
cd ~/.hermes/hermes-active
git add -A
git commit -m "feat(ui): 状态Tab页布局重构完成"
```

---

## 自检

1. **规格覆盖度**：✅ PC端分组布局、移动端单列、高度对齐、响应式检测
2. **占位符扫描**：✅ 无 TODO/待定
3. **类型一致性**：✅ isMobile 统一使用

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-06-25-status-tab-layout.md`。

**两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
