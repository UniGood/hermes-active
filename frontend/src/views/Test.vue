<template>
  <div class="test-page">
    <!-- 最新微信 Session -->
    <n-card title="最新微信 Session" style="margin-bottom: 16px">
      <n-spin :show="loadingSession">
        <div v-if="latestSession" class="session-info">
          <div class="info-item">
            <span class="label">Session ID</span>
            <n-text code style="font-size: 12px">{{ latestSession.id }}</n-text>
          </div>
          <div class="info-item">
            <span class="label">标题</span>
            <span class="value">{{ latestSession.title || '无标题' }}</span>
          </div>
          <div class="info-item">
            <span class="label">消息数</span>
            <span class="value">{{ latestSession.message_count || 0 }}</span>
          </div>
        </div>
        <n-empty v-else description="未找到活跃的微信 Session" />
      </n-spin>
      <n-button @click="loadLatestSession" style="margin-top: 12px" size="small">刷新</n-button>
    </n-card>

    <!-- 消息发送测试 -->
    <n-card title="消息发送测试" style="margin-bottom: 16px">
      <n-input
        v-model:value="testMessage"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 4 }"
        placeholder="输入要发送的消息..."
      />
      <div class="send-options">
        <n-space vertical style="width: 100%">
          <n-space>
            <n-checkbox v-model:checked="writeToDB">写入 Session DB</n-checkbox>
            <n-checkbox v-model:checked="withMark" :disabled="!writeToDB">带 [凯莉主动发送] 标记</n-checkbox>
          </n-space>
          <n-space>
            <n-button
              type="primary"
              @click="sendMessage"
              :loading="sending"
              :disabled="!latestSession || !testMessage.trim()"
            >
              发送到微信
            </n-button>
          </n-space>
        </n-space>
      </div>
    </n-card>

    <!-- 上下文读取测试 -->
    <n-card title="上下文读取测试" style="margin-bottom: 16px">
      <n-space>
        <n-button @click="testContext" :loading="loadingContext" :disabled="!latestSession">
          读取上下文
        </n-button>
        <n-input-number v-model:value="contextLimit" :min="1" :max="50" style="width: 100px" />
      </n-space>
      <div v-if="contextMessages.length > 0" class="context-preview">
        <div v-for="(msg, i) in contextMessages" :key="i" class="context-item">
          <span class="context-role" :class="msg.role">{{ msg.role === 'user' ? '曹凡' : msg.role === 'assistant' ? '凯莉' : msg.role }}:</span>
          <span class="context-content">{{ truncate(msg.content, 100) }}</span>
        </div>
      </div>
    </n-card>

    <!-- LLM 生成测试 -->
    <n-card title="LLM 生成测试" style="margin-bottom: 16px">
      <n-button @click="testGenerate" :loading="generating" :disabled="!latestSession">
        生成主动消息
      </n-button>
      <div v-if="generatedMessage" class="generated-message">
        <div class="generated-label">生成结果：</div>
        <div class="generated-content">{{ generatedMessage }}</div>
        <n-button size="small" @click="testMessage = generatedMessage" style="margin-top: 8px">
          填入发送框
        </n-button>
      </div>
    </n-card>

    <!-- 完整流程测试 -->
    <n-card title="完整流程测试" style="margin-bottom: 16px">
      <n-space>
        <n-button type="warning" @click="fullTest" :loading="fullTesting" :disabled="!latestSession">
          一键测试（生成+发送+写入DB）
        </n-button>
      </n-space>
    </n-card>

    <!-- 执行日志 -->
    <n-card title="执行日志">
      <div class="log-list">
        <div v-for="(log, i) in logs" :key="i" class="log-item" :class="log.type">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <n-empty v-if="logs.length === 0" description="暂无日志" />
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import api from '../api'

const message = useMessage()
const loadingSession = ref(false)
const loadingContext = ref(false)
const sending = ref(false)
const generating = ref(false)
const fullTesting = ref(false)

const latestSession = ref(null)
const contextMessages = ref([])
const contextLimit = ref(10)
const testMessage = ref('')
const writeToDB = ref(true)
const withMark = ref(false)
const generatedMessage = ref('')
const logs = ref([])

function addLog(type, msg) {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  logs.value.unshift({ type, time, message: msg })
  if (logs.value.length > 50) logs.value.pop()
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

async function loadLatestSession() {
  loadingSession.value = true
  try {
    const data = await api.get('/sessions/latest/weixin')
    latestSession.value = data
    addLog('info', `加载最新微信 Session: ${data.id}`)
  } catch (e) {
    addLog('error', '加载失败: ' + (e?.detail || '未知错误'))
  } finally {
    loadingSession.value = false
  }
}

async function testContext() {
  if (!latestSession.value) return
  loadingContext.value = true
  try {
    const data = await api.get(`/sessions/${latestSession.value.id}/context`, {
      params: { limit: contextLimit.value }
    })
    contextMessages.value = Array.isArray(data) ? data : (data?.items || [])
    addLog('success', `读取到 ${contextMessages.value.length} 条上下文消息`)
  } catch (e) {
    addLog('error', '读取上下文失败: ' + (e?.detail || '未知错误'))
  } finally {
    loadingContext.value = false
  }
}

async function sendMessage() {
  if (!latestSession.value || !testMessage.value.trim()) return
  sending.value = true
  try {
    const result = await api.post('/messages/send', {
      session_id: latestSession.value.id,
      message: testMessage.value.trim(),
      write_to_db: writeToDB.value,
      with_mark: withMark.value
    })
    const markLabel = withMark.value ? '带标记' : '不带标记'
    addLog('success', `发送成功（${markLabel}，写入DB=${writeToDB.value}）: ${testMessage.value.trim()}`)
    message.success('发送成功')
  } catch (e) {
    addLog('error', '发送失败: ' + (e?.detail || e?.message || '未知错误'))
    message.error('发送失败')
  } finally {
    sending.value = false
  }
}

async function testGenerate() {
  if (!latestSession.value) return
  generating.value = true
  try {
    const data = await api.post('/messages/send-proactive', {
      session_id: latestSession.value.id,
      use_llm: true,
      message: '',
      write_to_db: false,
      with_mark: false
    })
    generatedMessage.value = data?.detail?.generated_message || data?.message || ''
    addLog('success', `LLM 生成: ${generatedMessage.value}`)
  } catch (e) {
    addLog('error', '生成失败: ' + (e?.detail || '未知错误'))
  } finally {
    generating.value = false
  }
}

async function fullTest() {
  if (!latestSession.value) return
  fullTesting.value = true
  try {
    const data = await api.post('/messages/send-proactive', {
      session_id: latestSession.value.id,
      use_llm: true,
      message: '',
      write_to_db: true,
      with_mark: true
    })
    const result = data?.detail || data
    addLog('success', `完整流程测试完成: ${result.generated_message || result.message}`)
    message.success('完整流程测试成功')
  } catch (e) {
    addLog('error', '完整流程测试失败: ' + (e?.detail || '未知错误'))
    message.error('完整流程测试失败')
  } finally {
    fullTesting.value = false
  }
}

onMounted(loadLatestSession)
</script>

<style scoped>
.test-page {
  max-width: 800px;
  margin: 0 auto;
}

.session-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
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

.send-options {
  margin-top: 12px;
}

.context-preview {
  margin-top: 12px;
  max-height: 300px;
  overflow-y: auto;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
}

.context-item {
  margin-bottom: 8px;
  font-size: 13px;
}

.context-role {
  font-weight: 600;
  margin-right: 4px;
}

.context-role.user {
  color: #2080f0;
}

.context-role.assistant {
  color: #18a058;
}

.context-content {
  color: #666;
}

.generated-message {
  margin-top: 12px;
  padding: 12px;
  background: #f0f9eb;
  border-radius: 8px;
}

.generated-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.generated-content {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
}

.log-list {
  max-height: 300px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
}

.log-item.success {
  color: #18a058;
}

.log-item.error {
  color: #d03050;
}

.log-item.info {
  color: #2080f0;
}

.log-time {
  color: #999;
  flex-shrink: 0;
}
</style>
