<template>
  <div class="session-detail-page">
    <!-- 返回按钮 -->
    <n-button quaternary @click="router.back()" style="margin-bottom: 16px">
      ← 返回
    </n-button>

    <!-- Session 信息 -->
    <n-card v-if="session">
      <div class="session-info">
        <div class="info-item">
          <span class="label">Session ID</span>
          <span class="value">{{ session.session_id }}</span>
        </div>
        <div class="info-item">
          <span class="label">平台</span>
          <n-tag :type="getPlatformType(session.source)" size="small">
            {{ session.source || '未知' }}
          </n-tag>
        </div>
        <div class="info-item">
          <span class="label">标题</span>
          <span class="value">{{ session.title || '无标题' }}</span>
        </div>
        <div class="info-item">
          <span class="label">消息数</span>
          <span class="value">{{ session.message_count || 0 }}</span>
        </div>
        <div class="info-item">
          <span class="label">状态</span>
          <n-tag :type="session.ended_at ? 'default' : 'success'" size="small">
            {{ session.ended_at ? '已结束' : '活跃' }}
          </n-tag>
        </div>
        <div class="info-item">
          <span class="label">开始时间</span>
          <span class="value">{{ formatTime(session.started_at) }}</span>
        </div>
      </div>
    </n-card>

    <!-- 消息历史 -->
    <n-card title="消息历史" style="margin-top: 16px">
      <n-spin :show="loading">
        <div class="message-list">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="message-item"
            :class="msg.role"
          >
            <div class="message-header">
              <span class="message-role">
                {{ msg.role === 'user' ? '曹凡' : msg.role === 'assistant' ? '凯莉' : msg.role }}
              </span>
              <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
            </div>
            <div class="message-content">{{ msg.content }}</div>
          </div>
          <n-empty v-if="!loading && messages.length === 0" description="暂无消息" />
        </div>
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const session = ref(null)
const messages = ref([])

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function getPlatformType(source) {
  const map = { weixin: 'success', feishu: 'info', cli: 'default', telegram: 'warning' }
  return map[source] || 'default'
}

async function loadSession() {
  const sessionId = route.params.id
  try {
    const data = await api.get(`/sessions/${sessionId}`)
    session.value = data
  } catch (e) {
    console.error('加载会话失败:', e)
  }
}

async function loadMessages() {
  const sessionId = route.params.id
  loading.value = true
  try {
    const data = await api.get(`/messages/${sessionId}`, { params: { page: 1, page_size: 200 } })
    messages.value = data.items || []
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSession()
  loadMessages()
})
</script>

<style scoped>
.session-detail-page {
  max-width: 800px;
  margin: 0 auto;
}

.session-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  color: #999;
}

.info-item .value {
  font-size: 14px;
  color: #333;
  word-break: break-all;
}

.message-list {
  max-height: 60vh;
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
  justify-content: space-between;
  margin-bottom: 4px;
}

.message-role {
  font-size: 12px;
  font-weight: 600;
  color: #333;
}

.message-time {
  font-size: 12px;
  color: #999;
}

.message-content {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
