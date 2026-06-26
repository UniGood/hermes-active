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
          <template v-for="msg in recentMessages" :key="msg.id">
            <div v-if="msg.content" class="message-item">
              <div class="message-header">
                <n-tag :type="msg.role === 'user' ? 'info' : 'default'" :class="msg.role === 'assistant' ? 'tag-assistant' : ''" size="small">
                  {{ msg.role === 'user' ? config.user_name : config.assistant_name }}
                </n-tag>
                <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="message-content">{{ truncate(msg.content, 100) }}</div>
            </div>
          </template>
          <n-empty v-if="!loading && recentMessages.length === 0" description="暂无消息" />
        </div>
      </n-spin>
    </n-card>

    <!-- 平台分布 -->
    <n-card title="平台分布" style="margin-top: 16px">
      <div class="platform-list">
        <div v-for="p in platforms" :key="p.name" class="platform-item">
          <span class="platform-name">{{ p.name }}</span>
          <div class="platform-bar-wrap">
            <div class="platform-bar" :style="{ width: p.percent + '%', background: p.color }"></div>
          </div>
          <span class="platform-percent">{{ p.percent }}%</span>
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
import { useConfig } from '../composables/useConfig'

const loading = ref(false)
const recentMessages = ref([])
const { config, loadConfig } = useConfig()

const stats = ref([
  { label: '总会话数', value: 0, icon: markRaw(ChatbubblesOutline), color: 'var(--theme-primary)' },
  { label: '总消息数', value: 0, icon: markRaw(PeopleOutline), color: 'var(--theme-accent)' },
  { label: '今日消息', value: 0, icon: markRaw(TimeOutline), color: '#a8e6cf' },
  { label: '本周消息', value: 0, icon: markRaw(TrendingUpOutline), color: '#ffd3b6' }
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

    // 加载平台分布
    const total = data.total_messages || 1
    const platformData = await api.get('/stats/platforms')
    const platformColors = { weixin: 'var(--theme-primary)', feishu: 'var(--theme-accent)', cli: '#a8e6cf', cron: '#ffd3b6' }
    const platformNames = { weixin: '微信', feishu: '飞书', cli: 'CLI', cron: '定时任务', unknown: '其他' }
    platforms.value = (platformData || []).map(p => ({
      name: platformNames[p.platform] || p.platform,
      count: p.count,
      percent: Math.round((p.count / total) * 100),
      color: platformColors[p.platform] || '#999'
    }))
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

async function loadRecentMessages() {
  loading.value = true
  try {
    const data = await api.get('/messages/recent', { params: { limit: 20 } })
    recentMessages.value = (data.items || []).filter(msg => msg.content)
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadConfig()
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
  background: var(--theme-card-bg);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s, transform 0.2s;
}

.stat-card:hover {
  box-shadow: 0 4px 20px rgba(var(--theme-primary-rgb), 0.15);
  transform: translateY(-2px);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--theme-text);
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
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
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
  color: #555;
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
  min-width: 56px;
  font-size: 14px;
  color: var(--theme-text);
  white-space: nowrap;
}

.platform-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--theme-bg-muted, #f0f0f0);
  border-radius: 4px;
  overflow: hidden;
}

.platform-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.platform-percent {
  min-width: 36px;
  text-align: right;
  font-size: 13px;
  color: var(--theme-text-secondary, #666);
  font-weight: 500;
}

.platform-count {
  min-width: 32px;
  text-align: right;
  font-size: 13px;
  color: var(--theme-text-muted, #999);
}

.tag-assistant {
  --n-color: #fff0f3 !important;
  --n-color-hover: #ffe0e6 !important;
  --n-text-color: #ff9a9e !important;
  --n-border: 1px solid #ffd0d6 !important;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .dashboard-page {
    max-width: 100%;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .stat-card {
    padding: 12px;
    border-radius: 12px;
    gap: 8px;
  }

  .stat-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
  }

  .stat-value {
    font-size: 20px;
  }

  .stat-label {
    font-size: 11px;
  }

  .platform-name {
    min-width: 48px;
    font-size: 13px;
  }

  .platform-percent {
    min-width: 32px;
    font-size: 12px;
  }

  .platform-count {
    min-width: 28px;
    font-size: 12px;
  }

  .message-content {
    font-size: 13px;
  }
}
</style>