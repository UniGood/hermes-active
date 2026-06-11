<template>
  <div class="messages-page">
    <!-- Session 选择 -->
    <n-select
      v-model:value="selectedSession"
      :options="sessionOptions"
      placeholder="选择会话"
      filterable
      @update:value="loadMessages"
      style="margin-bottom: 16px"
    />

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
        <n-empty v-if="!loading && messages.length === 0" description="暂无消息" />
      </div>
    </n-spin>

    <!-- 发送消息 -->
    <div class="send-bar">
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
import { ref, onMounted, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import api from '../api'

const message = useMessage()
const loading = ref(false)
const sending = ref(false)
const messages = ref([])
const sessions = ref([])
const selectedSession = ref(null)
const newMessage = ref('')
const messageListRef = ref(null)

const sessionOptions = ref([])

function formatContent(content) {
  if (!content) return ''
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

async function loadSessions() {
  try {
    const data = await api.get('/sessions', { params: { limit: 50 } })
    sessions.value = data.sessions || []
    sessionOptions.value = sessions.value.map(s => ({
      label: `${s.title || s.session_id} (${s.source || '未知'})`,
      value: s.session_id
    }))
    if (sessionOptions.value.length > 0 && !selectedSession.value) {
      selectedSession.value = sessionOptions.value[0].value
      loadMessages()
    }
  } catch (e) {
    console.error('加载会话失败:', e)
  }
}

async function loadMessages() {
  if (!selectedSession.value) return
  loading.value = true
  try {
    const data = await api.get(`/messages/${selectedSession.value}`, { params: { limit: 100 } })
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
      session_id: selectedSession.value,
      content: newMessage.value.trim(),
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

onMounted(loadSessions)
</script>

<style scoped>
.messages-page {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
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
  background: #18a058;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant .message-content {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
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
