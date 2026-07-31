<template>
  <div class="api-key-test">
    <!-- 配置区域 -->
    <n-card :title="t('apiKeyTest.config.title')" size="small" style="margin-bottom: 12px">
      <n-space vertical :size="8">
        <div class="config-row">
          <span class="config-label">{{ t('apiKeyTest.config.baseUrl') }}:</span>
          <n-input v-model:value="config.baseUrl" placeholder="https://api.openai.com/v1" size="small" />
        </div>
        <div class="config-row">
          <span class="config-label">{{ t('apiKeyTest.config.apiKey') }}:</span>
          <n-input v-model:value="config.apiKey" placeholder="sk-..." size="small" />
        </div>
        <div class="config-row">
          <span class="config-label">{{ t('apiKeyTest.config.model') }}:</span>
          <n-input v-model:value="config.model" placeholder="gpt-4o" size="small" />
        </div>
        <div class="config-row">
          <span class="config-label">{{ t('apiKeyTest.config.system') }}:</span>
          <n-input v-model:value="config.systemPrompt" placeholder="You are a helpful assistant." size="small" />
        </div>
        <n-space>
          <n-button size="small" type="primary" @click="testConnection" :loading="testing">
            {{ t('apiKeyTest.config.testConnection') }}
          </n-button>
          <n-button size="small" @click="clearChat">{{ t('apiKeyTest.config.clearChat') }}</n-button>
          <n-tag v-if="connectionStatus" :type="connectionStatus === 'success' ? 'success' : 'error'" size="small">
            {{ connectionStatus === 'success' ? t('apiKeyTest.config.connectionSuccess') : t('apiKeyTest.config.connectionFailed') }}
          </n-tag>
          <n-tag v-if="latency" type="info" size="small">{{ latency }}ms</n-tag>
        </n-space>
      </n-space>
    </n-card>

    <!-- 聊天区域 -->
    <n-card :title="t('apiKeyTest.chat.title')" size="small" style="margin-bottom: 12px">
      <div class="chat-container" ref="chatContainer">
        <div v-if="messages.length === 0" class="chat-empty">
          {{ t('apiKeyTest.chat.emptyHint') }}
        </div>
        <div v-for="(msg, i) in messages" :key="i" class="chat-message" :class="msg.role">
          <div class="message-role">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="message-content">
            <div class="message-text" v-html="formatMessage(msg.content)"></div>
            <div v-if="msg.toolCalls" class="message-tools">
              <div v-for="(tc, j) in msg.toolCalls" :key="j" class="tool-call">
                🔧 {{ tc.name }}(<span class="tool-args">{{ tc.arguments }}</span>)
              </div>
            </div>
            <div v-if="msg.usage" class="message-meta">
              prompt: {{ msg.usage.prompt_tokens }} | completion: {{ msg.usage.completion_tokens }} | total: {{ msg.usage.total_tokens }}
            </div>
            <div v-if="msg.error" class="message-error">{{ msg.error }}</div>
          </div>
        </div>
        <div v-if="streaming" class="chat-message assistant">
          <div class="message-role">🤖</div>
          <div class="message-content">
            <div class="message-text">{{ streamingContent || t('apiKeyTest.chat.thinking') }}</div>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <n-input
          v-model:value="inputText"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          :placeholder="t('apiKeyTest.chat.placeholder')"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <n-space style="margin-top: 8px">
          <n-button type="primary" @click="sendMessage" :loading="streaming" :disabled="!inputText.trim()">
            {{ t('apiKeyTest.chat.send') }}
          </n-button>
          <n-checkbox v-model:checked="useStream">{{ t('apiKeyTest.chat.stream') }}</n-checkbox>
          <n-checkbox v-model:checked="useToolCalls">{{ t('apiKeyTest.chat.toolCalls') }}</n-checkbox>
        </n-space>
      </div>
    </n-card>

    <!-- 原始响应 -->
    <n-card :title="t('apiKeyTest.response.title')" size="small" v-if="lastRawResponse">
      <n-input
        :value="lastRawResponse"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 12 }"
        readonly
      />
    </n-card>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const message = useMessage()

const STORAGE_KEY = 'kelly-api-test-config'

const config = ref({
  baseUrl: 'https://xlapis.com/v1',
  apiKey: '',
  model: 'deepseek-v4-pro',
  systemPrompt: 'You are a helpful assistant.'
})

// 从 localStorage 加载缓存
onMounted(() => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      config.value = { ...config.value, ...parsed }
    }
    const savedMessages = localStorage.getItem(STORAGE_KEY + '-messages')
    if (savedMessages) {
      messages.value = JSON.parse(savedMessages)
    }
  } catch {}
})

// 保存到 localStorage
function saveConfig() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config.value))
  } catch {}
}

function saveMessages() {
  try {
    localStorage.setItem(STORAGE_KEY + '-messages', JSON.stringify(messages.value))
  } catch {}
}

const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const useStream = ref(true)
const useToolCalls = ref(false)
const testing = ref(false)
const connectionStatus = ref(null)
const latency = ref(null)
const lastRawResponse = ref('')
const chatContainer = ref(null)

const testTools = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description: t('apiKeyTest.tool.searchWeb'),
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: t('apiKeyTest.tool.searchQuery') }
        },
        required: ['query']
      }
    }
  }
]

function formatMessage(text) {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

async function testConnection() {
  saveConfig()
  testing.value = true
  connectionStatus.value = null
  latency.value = null
  const start = Date.now()

  try {
    const body = {
      model: config.value.model,
      messages: [{ role: 'user', content: 'Hi' }],
      max_tokens: 10,
      stream: false
    }

    const resp = await fetch(`${config.value.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${config.value.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })

    latency.value = Date.now() - start

    if (!resp.ok) {
      const errText = await resp.text()
      connectionStatus.value = 'error'
      lastRawResponse.value = `HTTP ${resp.status}: ${errText}`
      return
    }

    // 检查是否是 SSE 格式
    const contentType = resp.headers.get('content-type') || ''
    const text = await resp.text()
    lastRawResponse.value = text.substring(0, 2000)

    if (text.includes('"choices"') && text.includes('"completion_tokens"')) {
      // 尝试解析
      try {
        // SSE 格式
        if (text.startsWith('data:')) {
          const lines = text.split('\n').filter(l => l.startsWith('data:') && !l.includes('[DONE]'))
          if (lines.length > 0) {
            const data = JSON.parse(lines[0].replace('data: ', ''))
            if (data.choices && data.choices.length > 0) {
              connectionStatus.value = 'success'
            } else {
              connectionStatus.value = 'error'
              message.warning(t('apiKeyTest.errors.emptyChoicesNonStream'))
            }
          }
        } else {
          const data = JSON.parse(text)
          if (data.choices && data.choices.length > 0 && data.choices[0].message) {
            connectionStatus.value = 'success'
          } else {
            connectionStatus.value = 'error'
          }
        }
      } catch {
        connectionStatus.value = 'error'
      }
    } else {
      connectionStatus.value = 'error'
    }
  } catch (e) {
    connectionStatus.value = 'error'
    latency.value = Date.now() - start
    lastRawResponse.value = `Error: ${e.message}`
  } finally {
    testing.value = false
  }
}

function clearChat() {
  messages.value = []
  lastRawResponse.value = ''
  saveMessages()
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return

  saveConfig()
  messages.value.push({ role: 'user', content: text })
  saveMessages()
  inputText.value = ''
  scrollToBottom()

  const apiMessages = []
  if (config.value.systemPrompt) {
    apiMessages.push({ role: 'system', content: config.value.systemPrompt })
  }
  for (const m of messages.value) {
    apiMessages.push({ role: m.role, content: m.content })
  }

  const body = {
    model: config.value.model,
    messages: apiMessages,
    max_tokens: 2000,
    temperature: 0.7,
    stream: useStream.value
  }

  if (useToolCalls.value) {
    body.tools = testTools
    body.tool_choice = 'auto'
  }

  streaming.value = true
  streamingContent.value = ''

  try {
    const resp = await fetch(`${config.value.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${config.value.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })

    if (!resp.ok) {
      const errText = await resp.text()
      messages.value.push({ role: 'assistant', content: '', error: `HTTP ${resp.status}: ${errText}` })
      saveMessages()
      lastRawResponse.value = `HTTP ${resp.status}: ${errText}`
      return
    }

    if (useStream.value) {
      // 流式处理
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      let toolCalls = {}
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ') || line.includes('[DONE]')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (!data.choices || data.choices.length === 0) continue
            const delta = data.choices[0].delta || {}

            if (delta.content) {
              fullContent += delta.content
              streamingContent.value = fullContent
              scrollToBottom()
            }

            if (delta.tool_calls) {
              for (const tc of delta.tool_calls) {
                const idx = tc.index || 0
                if (!toolCalls[idx]) toolCalls[idx] = { name: '', arguments: '' }
                if (tc.function?.name) toolCalls[idx].name = tc.function.name
                if (tc.function?.arguments) toolCalls[idx].arguments += tc.function.arguments
              }
            }

            // 保存原始响应
            lastRawResponse.value = line.slice(0, 500)
          } catch { /* skip parse errors */ }
        }
      }

      const resultMsg = { role: 'assistant', content: fullContent }
      if (Object.keys(toolCalls).length > 0) {
        resultMsg.toolCalls = Object.values(toolCalls)
      }
      messages.value.push(resultMsg)
      saveMessages()
    } else {
      // 非流式
      const text = await resp.text()
      lastRawResponse.value = text.substring(0, 2000)

      try {
        let data
        if (text.startsWith('data:')) {
          // SSE 格式但非流式请求
          const lines = text.split('\n').filter(l => l.startsWith('data:') && !l.includes('[DONE]'))
          if (lines.length > 0) data = JSON.parse(lines[0].replace('data: ', ''))
        } else {
          data = JSON.parse(text)
        }

        if (data?.choices?.length > 0) {
          const choice = data.choices[0]
          const resultMsg = {
            role: 'assistant',
            content: choice.message?.content || '',
            usage: data.usage
          }
          if (choice.message?.tool_calls) {
            resultMsg.toolCalls = choice.message.tool_calls.map(tc => ({
              name: tc.function.name,
              arguments: tc.function.arguments
            }))
          }
          if (!resultMsg.content && !resultMsg.toolCalls) {
            resultMsg.error = t('apiKeyTest.errors.emptyResponse')
          }
          messages.value.push(resultMsg)
          saveMessages()
        } else {
          messages.value.push({ role: 'assistant', content: '', error: t('apiKeyTest.errors.emptyChoices') })
          saveMessages()
        }
      } catch {
        messages.value.push({ role: 'assistant', content: '', error: t('apiKeyTest.errors.jsonParseFailed') })
        saveMessages()
      }
    }
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '', error: e.message })
    saveMessages()
  } finally {
    streaming.value = false
    streamingContent.value = ''
    scrollToBottom()
  }
}
</script>

<style scoped>
.api-key-test {
  padding: 0;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-label {
  min-width: 80px;
  font-size: 13px;
  color: var(--theme-text-muted);
  text-align: right;
}

.chat-container {
  max-height: 500px;
  overflow-y: auto;
  border: 1px solid var(--theme-border-light);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: var(--theme-bg-light);
}

.chat-empty {
  text-align: center;
  color: var(--theme-text-hint);
  padding: 40px 0;
  font-size: 14px;
}

.chat-message {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.chat-message.user .message-content {
  background: var(--theme-user-msg-bg);
}

.chat-message.assistant .message-content {
  background: var(--theme-bg-muted);
}

.message-role {
  font-size: 20px;
  flex-shrink: 0;
  width: 28px;
  text-align: center;
}

.message-content {
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.6;
}

.message-tools {
  margin-top: 8px;
  padding: 6px 10px;
  background: rgba(0,0,0,0.05);
  border-radius: 4px;
  font-size: 13px;
}

.tool-call {
  color: var(--theme-text-secondary);
}

.tool-args {
  color: var(--theme-text-muted);
  font-size: 12px;
}

.message-meta {
  margin-top: 6px;
  font-size: 11px;
  color: var(--theme-text-hint);
}

.message-error {
  margin-top: 6px;
  font-size: 13px;
  color: var(--theme-error-light);
}

.chat-input {
  margin-top: 8px;
}
</style>
