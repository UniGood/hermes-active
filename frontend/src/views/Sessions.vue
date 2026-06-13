<template>
  <div class="sessions-page">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <n-input
        v-model:value="searchText"
        placeholder="搜索会话（标题/ID）..."
        clearable
        @clear="loadSessions"
        @keyup.enter="loadSessions"
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
        @update:value="loadSessions"
      />
      <n-select
        v-model:value="statusFilter"
        :options="statusOptions"
        placeholder="状态"
        style="width: 120px"
        @update:value="loadSessions"
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
            <span class="session-time">{{ formatTime(session.started_at) }}</span>
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
import api from '../api'

const router = useRouter()
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

onMounted(loadSessions)
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
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s, transform 0.2s;
}

.session-card:hover {
  box-shadow: 0 4px 20px rgba(255, 154, 158, 0.15);
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

.session-time {
  font-size: 12px;
  color: #999;
}

.session-title {
  font-size: 16px;
  font-weight: 500;
  color: #2d2d2d;
  margin-bottom: 8px;
}

.session-id {
  font-size: 11px;
  color: #bbb;
  font-family: monospace;
  margin-bottom: 4px;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
}

.status-active {
  color: #a8e6cf;
  font-weight: 500;
}

.status-ended {
  color: #999;
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
