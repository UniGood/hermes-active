<template>
  <div class="messages-page">
    <!-- 搜索栏 -->
    <div v-if="!selectedSession" class="search-bar">
      <n-input
        v-model:value="searchText"
        :placeholder="t('messages.searchPlaceholder')"
        clearable
        @clear="clearSearch"
        @keyup.enter="searchMessages"
      >
        <template #prefix>
          <n-icon><SearchOutline /></n-icon>
        </template>
      </n-input>
      <n-button @click="searchMessages" :loading="searching">{{ t('messages.search') }}</n-button>
    </div>

    <!-- 搜索结果列表 -->
    <div v-if="searchResults.length > 0 && !selectedSession" class="search-results">
      <div
        v-for="msg in searchResults"
        :key="msg.id"
        class="search-result-item"
        @click="goToMessage(msg)"
      >
        <n-tag :type="msg.role === 'user' ? 'info' : 'default'" :class="msg.role === 'assistant' ? 'tag-assistant' : ''" size="small">
          {{ msg.role === 'user' ? config.user_name : msg.role === 'assistant' ? config.assistant_name : msg.role }}
        </n-tag>
        <span class="result-content">{{ truncate(msg.content, 60) }}</span>
        <span class="result-time">{{ formatTime(msg.timestamp) }}</span>
      </div>
    </div>

    <!-- Session 详情 -->
    <div v-if="selectedSession" class="session-detail-card">
      <div class="detail-header">
        <n-button size="small" @click="clearSelection">{{ t('messages.backToSearch') }}</n-button>
        <n-tag :type="getPlatformType(selectedSession.source)" size="small">
          {{ selectedSession.source }}
        </n-tag>
      </div>
      <div class="detail-info">
        <div><strong>Session ID:</strong> {{ selectedSession.id }}</div>
        <div><strong>{{ t('messages.title') }}:</strong> {{ selectedSession.title || t('messages.noTitle') }}</div>
        <div><strong>{{ t('messages.userId') }}:</strong> {{ selectedSession.user_id || selectedSession.chat_id || selectedSession.source }}</div>
        <div><strong>{{ t('messages.messageCount') }}:</strong> {{ selectedSession.message_count || 0 }}</div>
        <div><strong>{{ t('messages.status') }}:</strong> {{ selectedSession.ended_at ? t('common.status.ended') : t('common.status.active') }}</div>
      </div>
    </div>

    <!-- 消息列表 -->
    <n-spin :show="loading">
      <div v-if="selectedSession" class="toolbar">
        <n-checkbox v-model:checked="hideTool">{{ t('messages.hideToolMessages') }}</n-checkbox>
        <span class="result-count">{{ t('messages.totalCount', { count: filteredMessages.length }) }}</span>
      </div>
      <div class="message-list" ref="messageListRef">
        <div
          v-for="msg in filteredMessages"
          :key="msg.id"
          class="message-item"
          :class="[msg.role, { 'highlighted': highlightedMessageId === msg.id }]"
          :id="'msg-' + msg.id"
        >
          <div class="message-header">
            <div class="message-header-left">
              <n-tag :type="msg.role === 'user' ? 'info' : 'default'" :class="msg.role === 'assistant' ? 'tag-assistant' : ''" size="small">
                {{ msg.role === 'user' ? config.user_name : msg.role === 'assistant' ? config.assistant_name : msg.role }}
              </n-tag>
            </div>
            <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="message-content" v-html="formatContent(msg.content)"></div>
        </div>
        <n-empty v-if="!loading && filteredMessages.length === 0 && selectedSession" :description="t('messages.noMessages')" />
      </div>
    </n-spin>

    <!-- 发送消息 -->
    <div v-if="selectedSession" class="send-bar">
      <n-input
        v-model:value="newMessage"
        :placeholder="t('messages.inputPlaceholder')"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 4 }"
        @keyup.ctrl.enter="sendMessage"
      />
      <n-button type="primary" @click="sendMessage" :loading="sending" :disabled="!newMessage.trim()">
        {{ t('messages.send') }}
      </n-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { SearchOutline } from '@vicons/ionicons5'
import api from '../api'
import { useConfig } from '../composables/useConfig'

const { t } = useI18n()
const message = useMessage()
const { config, loadConfig } = useConfig()
const loading = ref(false)
const sending = ref(false)
const searching = ref(false)
const messages = ref([])
const searchText = ref('')
const searchResults = ref([])
const selectedSession = ref(null)
const newMessage = ref('')
const messageListRef = ref(null)
const highlightedMessageId = ref(null)
const hideTool = ref(true)

const filteredMessages = computed(() => {
  if (!hideTool.value) return messages.value
  return messages.value.filter(msg => msg.role !== 'tool')
})

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

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

async function searchMessages() {
  if (!searchText.value.trim()) return
  searching.value = true
  try {
    const data = await api.get('/messages/search', { params: { keyword: searchText.value.trim(), page: 1, page_size: 50 } })
    searchResults.value = data.items || []
  } catch (e) {
    console.error('搜索消息失败:', e)
  } finally {
    searching.value = false
  }
}

function clearSearch() {
  searchText.value = ''
  searchResults.value = []
}

async function goToMessage(msg) {
  // 1. 加载该消息所在的 session
  try {
    const sessionData = await api.get(`/sessions/${msg.session_id}`)
    selectedSession.value = sessionData
  } catch (e) {
    // 如果获取 session 详情失败，构造一个最小对象
    selectedSession.value = { id: msg.session_id, source: 'unknown' }
  }

  // 2. 加载 session 的所有消息
  await loadMessages()

  // 3. 等待 DOM 更新后，滚动到目标消息并高亮
  highlightedMessageId.value = msg.id
  await nextTick()

  const targetEl = document.getElementById('msg-' + msg.id)
  if (targetEl) {
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  // 4. 3秒后取消高亮
  setTimeout(() => {
    highlightedMessageId.value = null
  }, 3000)
}

function clearSelection() {
  selectedSession.value = null
  messages.value = []
  highlightedMessageId.value = null
  // 保留搜索结果，不清空
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
    message.success(t('messages.sendSuccess'))
    newMessage.value = ''
    await loadMessages()
  } catch (e) {
    message.error(t('messages.sendFailedWithDetail', { detail: e?.detail || e?.message || t('messages.unknownError') }))
  } finally {
    sending.value = false
  }
}

function scrollToBottom() {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

onMounted(() => {
  // 并行加载，提高页面切换速度
  Promise.all([
    loadConfig(),
    loadRecentMessages()
  ])
})

async function loadRecentMessages() {
  loading.value = true
  try {
    const data = await api.get('/messages/recent', { params: { limit: 50 } })
    searchResults.value = data.items || []
  } catch (e) {
    console.error('加载最新消息失败:', e)
  } finally {
    loading.value = false
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
  background: var(--theme-card-bg);
  border-radius: 16px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s, transform 0.2s;
}

.search-result-item:hover {
  box-shadow: 0 4px 20px rgba(var(--theme-primary-rgb), 0.15);
  transform: translateY(-2px);
}

.result-content {
  flex: 1;
  font-size: 13px;
  color: var(--theme-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-time {
  font-size: 11px;
  color: #999;
}

.session-detail-card {
  background: var(--theme-card-bg);
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
  color: var(--theme-text);
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.message-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--theme-border);
}

.message-item:last-child {
  border-bottom: none;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-time {
  font-size: 12px;
  color: #999;
}

.message-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--theme-text);
  word-break: break-word;
}

.message-item.highlighted {
  background: rgba(var(--theme-primary-rgb), 0.05);
  border-radius: 8px;
  padding: 12px 8px;
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

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  margin-bottom: 4px;
}

.result-count {
  font-size: 12px;
  color: #999;
}

.tag-assistant {
  --n-color: #fff0f3 !important;
  --n-color-hover: #ffe0e6 !important;
  --n-text-color: #ff9a9e !important;
  --n-border: 1px solid #ffd0d6 !important;
}

@media (max-width: 768px) {
  .messages-page {
    max-width: 100%;
    padding: 0 12px;
    height: calc(100vh - 100px);
  }

  .search-bar {
    flex-direction: column;
    gap: 8px;
  }

  .search-result-item {
    flex-wrap: wrap;
    gap: 6px;
    padding: 10px 12px;
    border-radius: 12px;
  }

  .result-content {
    width: 100%;
    order: 3;
    white-space: normal;
    word-break: break-all;
  }

  .result-time {
    font-size: 10px;
  }

  .session-detail-card {
    border-radius: 12px;
    padding: 12px;
  }

  .detail-info {
    font-size: 12px;
    word-break: break-all;
  }

  .message-item {
    padding: 10px 0;
  }

  .message-header {
    flex-wrap: wrap;
    gap: 4px;
  }

  .message-header-left {
    flex-wrap: wrap;
    gap: 4px;
  }

  .message-content {
    font-size: 13px;
    word-break: break-word;
    overflow-wrap: anywhere;
  }

  .send-bar {
    flex-direction: column;
    gap: 8px;
  }

  .toolbar {
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>