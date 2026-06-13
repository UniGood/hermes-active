<template>
  <div class="messages-page">
    <!-- 搜索栏 -->
    <div v-if="!selectedSession" class="search-bar">
      <n-input
        v-model:value="searchText"
        placeholder="搜索 Session ID..."
        clearable
        @clear="clearSearch"
        @keyup.enter="searchSessions"
      >
        <template #prefix>
          <n-icon><SearchOutline /></n-icon>
        </template>
      </n-input>
      <n-button @click="searchSessions" :loading="searching">搜索</n-button>
    </div>

    <!-- 搜索结果列表 -->
    <div v-if="searchResults.length > 0 && !selectedSession" class="search-results">
      <div
        v-for="s in searchResults"
        :key="s.id"
        class="search-result-item"
        @click="selectSession(s)"
      >
        <n-tag :type="getPlatformType(s.source)" size="small">{{ s.source }}</n-tag>
        <span class="result-id">{{ s.id }}</span>
        <span class="result-title">{{ s.title || '无标题' }}</span>
        <span class="result-meta">{{ s.message_count || 0 }} 条消息</span>
      </div>
    </div>

    <!-- Session 详情 -->
    <div v-if="selectedSession" class="session-detail-card">
      <div class="detail-header">
        <n-button size="small" @click="clearSelection">返回搜索</n-button>
        <n-tag :type="getPlatformType(selectedSession.source)" size="small">
          {{ selectedSession.source }}
        </n-tag>
      </div>
      <div class="detail-info">
        <div><strong>Session ID:</strong> {{ selectedSession.id }}</div>
        <div><strong>标题:</strong> {{ selectedSession.title || '无标题' }}</div>
        <div><strong>用户 ID:</strong> {{ selectedSession.user_id || 'N/A' }}</div>
        <div><strong>消息数:</strong> {{ selectedSession.message_count || 0 }}</div>
        <div><strong>状态:</strong> {{ selectedSession.ended_at ? '已结束' : '活跃' }}</div>
      </div>
    </div>

    <!-- 消息列表 -->
    <n-spin :show="loading">
      <div class="message-list" ref="messageListRef">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-bubble"
          :class="msg.role"
        >
          <div class="message-role">
            {{ msg.role === 'user' ? '曹凡' : msg.role === 'assistant' ? '凯莉' : msg.role }}
          </div>
          <div class="message-content" v-html="formatContent(msg.content)"></div>
        </div>
        <n-empty v-if="!loading && messages.length === 0 && selectedSession" description="暂无消息" />
      </div>
    </n-spin>

    <!-- 发送消息 -->
    <div v-if="selectedSession" class="send-bar">
      <n-input
        v-model:value="newMessage"
        placeholder="输入消息..."
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 4 }"
        @keyup.ctrl.enter="sendMessage"
      />
      <n-button type="primary" @click="sendMessage" :loading="sending" :disabled="!newMessage.trim()">
        发送
      </n-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import api from '../api'

const message = useMessage()
const loading = ref(false)
const sending = ref(false)
const searching = ref(false)
const messages = ref([])
const searchText = ref('')
const searchResults = ref([])
const selectedSession = ref(null)
const newMessage = ref('')
const messageListRef = ref(null)

function getPlatformType(source) {
  const map = { weixin: 'success', feishu: 'info', cli: 'default', telegram: 'warning' }
  return map[source] || 'default'
}

function formatContent(content) {
  if (!content) return ''
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

async function searchSessions() {
  if (!searchText.value.trim()) return
  searching.value = true
  try {
    const data = await api.get('/sessions', { params: { search: searchText.value.trim(), page: 1, page_size: 20 } })
    searchResults.value = data.items || []
  } catch (e) {
    console.error('搜索会话失败:', e)
  } finally {
    searching.value = false
  }
}

function clearSearch() {
  searchText.value = ''
  searchResults.value = []
}

async function selectSession(session) {
  selectedSession.value = session
  await loadMessages()
}

function clearSelection() {
  selectedSession.value = null
  messages.value = []
}

async function loadMessages() {
  if (!selectedSession.value) return
  loading.value = true
  try {
    const data = await api.get(`/messages/${selectedSession.value.id}`, { params: { page: 1, page_size: 100 } })
    messages.value = data.items || []
    await nextTick()
    scrollToBottom()
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    loading.value = false
  }
}

async function sendMessage() {
  if (!newMessage.value.trim() || !selectedSession.value) return
  sending.value = true
  try {
    await api.post('/messages/send', {
      session_id: selectedSession.value.id,
      message: newMessage.value.trim(),
      is_test: true
    })
    message.success('发送成功')
    newMessage.value = ''
    await loadMessages()
  } catch (e) {
    message.error('发送失败: ' + (e?.detail || e?.message || '未知错误'))
  } finally {
    sending.value = false
  }
}

function scrollToBottom() {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}
</script>

<style scoped>
.messages-page {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 16px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s, transform 0.2s;
}

.search-result-item:hover {
  box-shadow: 0 4px 20px rgba(255, 154, 158, 0.15);
  transform: translateY(-2px);
}

.result-id {
  font-size: 11px;
  color: #999;
  font-family: monospace;
}

.result-title {
  font-size: 14px;
  color: #2d2d2d;
  flex: 1;
}

.result-meta {
  font-size: 12px;
  color: #999;
}

.session-detail-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.detail-info {
  font-size: 13px;
  color: #555;
  line-height: 1.8;
}

.detail-info strong {
  color: #2d2d2d;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.message-bubble {
  margin-bottom: 16px;
  max-width: 80%;
}

.message-bubble.user {
  margin-left: auto;
}

.message-bubble.assistant {
  margin-right: auto;
}

.message-role {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.message-bubble.user .message-role {
  text-align: right;
}

.message-content {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-bubble.user .message-content {
  background: linear-gradient(135deg, #ff9a9e, #f6d365);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant .message-content {
  background: #fff;
  color: #2d2d2d;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.send-bar {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  align-items: flex-end;
}

.send-bar .n-input {
  flex: 1;
}
</style>
