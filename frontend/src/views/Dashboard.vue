<template>
  <div class="dashboard-page">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-icon" :style="{ background: stat.color }">
          <n-icon :size="24" color="#fff"><component :is="stat.icon" /></n-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <!-- 最近消息 -->
    <n-card title="最近消息" style="margin-top: 16px">
      <n-spin :show="loading">
        <div class="message-list">
          <div v-for="msg in recentMessages" :key="msg.id" class="message-item">
            <div class="message-header">
              <n-tag :type="msg.role === 'user' ? 'info' : 'success'" size="small">
                {{ msg.role === 'user' ? '用户' : '凯莉' }}
              </n-tag>
              <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
            </div>
            <div class="message-content">{{ truncate(msg.content, 100) }}</div>
          </div>
          <n-empty v-if="!loading && recentMessages.length === 0" description="暂无消息" />
        </div>
      </n-spin>
    </n-card>

    <!-- 平台分布 -->
    <n-card title="平台分布" style="margin-top: 16px">
      <div class="platform-list">
        <div v-for="p in platforms" :key="p.name" class="platform-item">
          <span class="platform-name">{{ p.name }}</span>
          <n-progress :percentage="p.percent" :color="p.color" />
          <span class="platform-count">{{ p.count }}</span>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, markRaw } from 'vue'
import {
  ChatbubblesOutline,
  PeopleOutline,
  TimeOutline,
  TrendingUpOutline
} from '@vicons/ionicons5'
import api from '../api'

const loading = ref(false)
const recentMessages = ref([])

const stats = ref([
  { label: '总会话数', value: 0, icon: markRaw(ChatbubblesOutline), color: '#18a058' },
  { label: '总消息数', value: 0, icon: markRaw(PeopleOutline), color: '#2080f0' },
  { label: '今日消息', value: 0, icon: markRaw(TimeOutline), color: '#f0a020' },
  { label: '本周消息', value: 0, icon: markRaw(TrendingUpOutline), color: '#d03050' }
])

const platforms = ref([])

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

async function loadStats() {
  try {
    const data = await api.get('/stats/overview')
    stats.value[0].value = data.total_sessions || 0
    stats.value[1].value = data.total_messages || 0
    stats.value[2].value = data.today_messages || 0
    stats.value[3].value = data.week_messages || 0
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

async function loadRecentMessages() {
  loading.value = true
  try {
    const data = await api.get('/sessions', { params: { page: 1, page_size: 5 } })
    if (data.items && data.items.length > 0) {
      const firstSession = data.items[0]
      const msgs = await api.get(`/messages/${firstSession.id}`, { params: { page: 1, page_size: 10 } })
      recentMessages.value = msgs.items || []
    }
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadRecentMessages()
})
</script>

<style scoped>
.dashboard-page {
  max-width: 800px;
  margin: 0 auto;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

@media (min-width: 640px) {
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #999;
}

.message-list {
  max-height: 400px;
  overflow-y: auto;
}

.message-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.message-item:last-child {
  border-bottom: none;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.message-time {
  font-size: 12px;
  color: #999;
}

.message-content {
  font-size: 14px;
  color: #666;
  line-height: 1.5;
}

.platform-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.platform-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.platform-name {
  width: 60px;
  font-size: 14px;
  color: #333;
}

.platform-count {
  width: 40px;
  text-align: right;
  font-size: 14px;
  color: #666;
}
</style>
