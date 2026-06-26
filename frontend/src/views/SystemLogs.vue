<template>
  <div class="system-logs-page">
    <!-- 工具栏 -->
    <div class="toolbar">
      <n-space align="center">
        <n-button @click="loadLogs" :loading="loading" size="small">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新
        </n-button>
        <n-switch v-model:value="autoScroll">
          <template #checked>自动滚动</template>
          <template #unchecked>手动滚动</template>
        </n-switch>
        <n-input-number
          v-model:value="lineCount"
          :min="50"
          :max="2000"
          :step="100"
          size="small"
          style="width: 140px"
          @update:value="loadLogs"
        >
          <template #prefix>行数</template>
        </n-input-number>
      </n-space>
      <n-space align="center">
        <n-tag type="info" size="small">共 {{ logs.length }} 行</n-tag>
      </n-space>
    </div>

    <!-- 日志内容 -->
    <div class="log-container" ref="logContainer">
      <div v-if="message && logs.length === 0" class="empty-message">
        <n-empty :description="message" />
      </div>
      <div v-else class="log-content" ref="logContent">
        <div v-for="(line, index) in logs" :key="index" class="log-line" :class="getLineClass(line)">
          {{ line }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { RefreshOutline } from '@vicons/ionicons5'
import api from '../api'

const loading = ref(false)
const logs = ref([])
const message = ref('')
const autoScroll = ref(true)
const lineCount = ref(500)
const logContainer = ref(null)
const logContent = ref(null)

let refreshTimer = null

function getLineClass(line) {
  const lower = line.toLowerCase()
  if (lower.includes('error') || lower.includes('exception') || lower.includes('traceback')) return 'log-error'
  if (lower.includes('warning') || lower.includes('warn')) return 'log-warn'
  if (lower.includes('info')) return 'log-info'
  return ''
}

async function loadLogs() {
  loading.value = true
  try {
    const data = await api.get('/system/logs', { params: { lines: lineCount.value } })
    logs.value = data.lines || []
    message.value = data.message || ''
    if (autoScroll.value) {
      await nextTick()
      scrollToBottom()
    }
  } catch (e) {
    console.error('加载系统日志失败:', e)
    message.value = '加载失败: ' + (e?.detail || e?.message || '未知错误')
  } finally {
    loading.value = false
  }
}

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

// 自动刷新（每 10 秒）
function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    loadLogs()
  }, 10000)
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(() => {
  loadLogs()
  startAutoRefresh()
})

onBeforeUnmount(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.system-logs-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  max-width: 1200px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px 0;
}

.log-container {
  flex: 1;
  background: var(--theme-card-bg, #1e1e1e);
  border-radius: 16px;
  overflow-y: auto;
  padding: 12px 16px;
  min-height: 0;
}

.empty-message {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.log-content {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--theme-text, #d4d4d4);
  margin: 0;
}

.log-line {
  display: block;
  white-space: pre-wrap;
  word-break: break-all;
  padding: 2px 0;
  border-bottom: 1px solid var(--theme-border, rgba(255, 255, 255, 0.03));
}

.log-error {
  color: var(--theme-error, #f44747);
  font-weight: 500;
}

.log-warn {
  color: var(--theme-warning, #cca700);
}

.log-info {
  color: var(--theme-success, #6a9955);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .system-logs-page {
    height: calc(100vh - 80px);
    max-width: 100%;
  }

  .toolbar {
    flex-direction: column;
    gap: 8px;
    align-items: stretch;
  }

  .toolbar :deep(.n-space) {
    flex-wrap: wrap;
    justify-content: center;
  }

  .toolbar :deep(.n-input-number) {
    width: 120px !important;
  }

  .log-container {
    border-radius: 12px;
    padding: 8px 10px;
  }

  .log-content {
    font-size: 11px;
  }
}
</style>
