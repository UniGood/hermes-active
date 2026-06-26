<template>
  <div class="sessions-page">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <n-input
        v-model:value="searchText"
        placeholder="搜索会话（标题/ID）..."
        clearable
        @clear="onSearch"
        @keyup.enter="onSearch"
      >
        <template #prefix>
          <n-icon><SearchOutline /></n-icon>
        </template>
      </n-input>
      <n-select
        v-model:value="platformFilter"
        :options="platformOptions"
        placeholder="平台"
        style="width: 100px"
        @update:value="onFilterChange"
      />
      <n-select
        v-model:value="statusFilter"
        :options="statusOptions"
        placeholder="状态"
        style="width: 120px"
        @update:value="onFilterChange"
      />
    </div>

    <!-- 会话列表 -->
    <n-spin :show="loading">
      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-card"
          @click="goToDetail(session.id)"
        >
          <div class="session-header">
            <n-tag :type="getPlatformType(session.source)" size="small">
              {{ session.source || '未知' }}
            </n-tag>
            <div class="session-actions">
              <span class="session-time">{{ formatTime(session.started_at) }}</span>
              <n-button size="tiny" type="error" quaternary @click.stop="handleDelete(session)">
                删除
              </n-button>
            </div>
          </div>
          <div class="session-title">{{ session.title || '无标题' }}</div>
          <div class="session-id">{{ session.id }}</div>
          <div class="session-meta">
            <span>消息数: {{ session.message_count || 0 }}</span>
            <span :class="{ 'status-active': !session.ended_at, 'status-ended': session.ended_at }">
              {{ session.ended_at ? '已结束' : '活跃' }}
            </span>
          </div>
        </div>
        <n-empty v-if="!loading && sessions.length === 0" description="暂无会话" />
      </div>
    </n-spin>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <n-pagination
        v-model:page="currentPage"
        :page-count="Math.ceil(total / pageSize)"
        @update:page="loadSessions"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { SearchOutline } from '@vicons/ionicons5'
import { useMessage, useDialog } from 'naive-ui'
import api from '../api'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const sessions = ref([])
const searchText = ref('')
const platformFilter = ref(null)
const statusFilter = ref(null)
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)

const platformOptions = [
  { label: '全部', value: null },
  { label: '微信', value: 'weixin' },
  { label: '飞书', value: 'feishu' },
  { label: 'CLI', value: 'cli' }
]

const statusOptions = [
  { label: '全部', value: null },
  { label: '活跃', value: 'active' },
  { label: '已结束', value: 'ended' }
]

// 从 localStorage 恢复查询条件
function restoreFilters() {
  try {
    const saved = localStorage.getItem('sessions_filters')
    if (saved) {
      const filters = JSON.parse(saved)
      if (filters.searchText !== undefined) searchText.value = filters.searchText
      if (filters.platformFilter !== undefined) platformFilter.value = filters.platformFilter
      if (filters.statusFilter !== undefined) statusFilter.value = filters.statusFilter
      if (filters.currentPage !== undefined) currentPage.value = filters.currentPage
    }
  } catch (e) {
    // 忽略解析错误
  }
}

// 保存查询条件到 localStorage
function saveFilters() {
  try {
    localStorage.setItem('sessions_filters', JSON.stringify({
      searchText: searchText.value,
      platformFilter: platformFilter.value,
      statusFilter: statusFilter.value,
      currentPage: currentPage.value
    }))
  } catch (e) {
    // 忽略存储错误
  }
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function getPlatformType(source) {
  const map = { weixin: 'success', feishu: 'info', cli: 'default', telegram: 'warning' }
  return map[source] || 'default'
}

function goToDetail(sessionId) {
  router.push(`/sessions/${sessionId}`)
}

function handleDelete(session) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除会话 "${session.title || session.id}" 及其所有消息？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.delete(`/sessions/${session.id}`)
        message.success('会话已删除')
        loadSessions()
      } catch (e) {
        message.error('删除失败: ' + (e.response?.data?.detail || e.message))
      }
    }
  })
}

async function loadSessions() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize
    }
    if (searchText.value) params.search = searchText.value
    if (platformFilter.value) params.platform = platformFilter.value
    if (statusFilter.value === 'active') params.active_only = true

    const data = await api.get('/sessions', { params })
    sessions.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    console.error('加载会话失败:', e)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  currentPage.value = 1
  saveFilters()
  loadSessions()
}

function onFilterChange() {
  currentPage.value = 1
  saveFilters()
  loadSessions()
}

onMounted(() => {
  restoreFilters()
  loadSessions()
})
</script>

<style scoped>
.sessions-page {
  max-width: 800px;
  margin: 0 auto;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.session-card {
  background: var(--theme-card-bg);
  border-radius: 16px;
  padding: 16px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s, transform 0.2s;
}

.session-card:hover {
  box-shadow: 0 4px 20px rgba(var(--theme-primary-rgb), 0.15);
  transform: translateY(-2px);
}

.session-card:active {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-time {
  font-size: 12px;
  color: var(--theme-text-muted);
}

.session-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--theme-text);
  margin-bottom: 8px;
}

.session-id {
  font-size: 11px;
  color: var(--theme-text-muted);
  font-family: monospace;
  margin-bottom: 4px;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--theme-text-muted);
}

.status-active {
  color: var(--theme-status-active);
  font-weight: 500;
}

.status-ended {
  color: var(--theme-text-muted);
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .sessions-page {
    max-width: 100%;
  }

  .search-bar {
    flex-direction: column;
    gap: 8px;
  }

  .search-bar :deep(.n-input),
  .search-bar :deep(.n-select) {
    width: 100% !important;
  }

  .session-card {
    padding: 12px;
    border-radius: 12px;
  }

  .session-title {
    font-size: 15px;
  }

  .session-id {
    font-size: 10px;
  }
}
</style>
