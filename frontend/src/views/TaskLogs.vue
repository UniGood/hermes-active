<template>
  <div class="task-logs-page">
    <!-- 筛选 -->
    <div class="filter-bar">
      <n-select
        v-model:value="statusFilter"
        :options="statusOptions"
        placeholder="状态"
        clearable
        style="width: 120px"
        @update:value="loadLogs"
      />
      <n-select
        v-model:value="typeFilter"
        :options="typeOptions"
        placeholder="类型"
        clearable
        style="width: 160px"
        @update:value="loadLogs"
      />
      <n-button @click="loadLogs" size="small">刷新</n-button>
    </div>

    <!-- 日志列表 -->
    <n-spin :show="loading">
      <div class="log-list">
        <div v-for="log in logs" :key="log.id" class="log-card">
          <div class="log-header">
            <n-tag :type="getStatusType(log.status)" size="small">{{ log.status }}</n-tag>
            <span class="log-type">{{ getTypeLabel(log.task_type) }}</span>
            <span class="log-time">{{ formatTime(log.created_at) }}</span>
          </div>
          <div class="log-message" v-if="log.message">{{ log.message }}</div>
          <div class="log-error" v-if="log.error">{{ log.error }}</div>
          <div class="log-meta">
            <span v-if="log.duration">耗时: {{ log.duration.toFixed(2) }}s</span>
          </div>
        </div>
        <n-empty v-if="!loading && logs.length === 0" description="暂无任务日志" />
      </div>
    </n-spin>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <n-pagination
        v-model:page="currentPage"
        :page-count="Math.ceil(total / pageSize)"
        @update:page="loadLogs"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const loading = ref(false)
const logs = ref([])
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const statusFilter = ref(null)
const typeFilter = ref(null)

const statusOptions = [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' }
]

const typeOptions = [
  { label: '发送消息', value: 'send_message' },
  { label: 'LLM 生成', value: 'generate' },
  { label: '主动消息', value: 'send_proactive' },
  { label: '定时任务', value: 'cron_run' },
  { label: '上下文读取', value: 'test_context' }
]

const typeLabelMap = {
  send_message: '发送消息',
  generate: 'LLM 生成',
  send_proactive: '主动消息',
  cron_run: '定时任务',
  test_context: '上下文读取'
}

function getTypeLabel(type) {
  return typeLabelMap[type] || type
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function getStatusType(status) {
  const map = { success: 'success', failed: 'error', running: 'info' }
  return map[status] || 'default'
}

async function loadLogs() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize
    }
    if (statusFilter.value) params.status = statusFilter.value
    if (typeFilter.value) params.task_type = typeFilter.value

    const data = await api.get('/task-logs', { params })
    logs.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    console.error('加载日志失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)
</script>

<style scoped>
.task-logs-page {
  max-width: 800px;
  margin: 0 auto;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s;
}

.log-card:hover {
  box-shadow: 0 4px 20px rgba(74, 144, 217, 0.12);
}

.log-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.log-type {
  font-size: 14px;
  font-weight: 500;
  color: #2d2d2d;
}

.log-time {
  font-size: 12px;
  color: #999;
  margin-left: auto;
}

.log-message {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.log-error {
  font-size: 13px;
  color: #d03050;
  background: rgba(74, 144, 217, 0.08);
  padding: 8px 12px;
  border-radius: 12px;
  margin-bottom: 8px;
}

.log-meta {
  font-size: 12px;
  color: #999;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .task-logs-page {
    max-width: 100%;
  }

  .filter-bar {
    flex-wrap: wrap;
    gap: 8px;
  }

  .filter-bar :deep(.n-select) {
    flex: 1;
    min-width: 120px;
  }

  .filter-bar :deep(.n-button) {
    flex: 1;
  }

  .log-card {
    padding: 12px;
    border-radius: 12px;
  }

  .log-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .log-time {
    margin-left: 0;
    width: 100%;
  }
}
</style>
