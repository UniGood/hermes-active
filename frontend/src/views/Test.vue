<template>
  <div class="test-page">
    <!-- 步骤 1: Session 选择区域 -->
    <n-card :title="t('test.card.sessionSelect')" style="margin-bottom: 16px">
      <n-spin :show="loadingSession">
        <div class="session-select-area">
          <div class="select-row">
            <span class="select-label">{{ t('test.session.platform') }}:</span>
            <n-select
              v-model:value="selectedPlatform"
              :options="platformOptions"
              style="width: 150px"
              @update:value="onPlatformChange"
            />
          </div>
          <div class="select-row">
            <span class="select-label">{{ t('test.session.label') }}:</span>
            <n-select
              v-model:value="selectedSessionId"
              :options="sessionOptions"
              :placeholder="t('test.session.placeholder')"
              style="flex: 1"
              filterable
            />
          </div>
          <div class="select-actions">
            <n-button size="small" @click="loadLatestSession" :loading="loadingSession">{{ t('test.session.getLatest') }}</n-button>
            <n-button size="small" @click="loadSessionList" :loading="loadingSessionList">{{ t('test.session.refresh') }}</n-button>
          </div>
          <div v-if="selectedSession" class="session-info">
            <div class="info-item">
              <span class="label">{{ t('test.session.id') }}</span>
              <n-text code style="font-size: 12px">{{ selectedSession.id }}</n-text>
            </div>
            <div class="info-item">
              <span class="label">{{ t('test.session.title') }}</span>
              <span class="value">{{ selectedSession.title || t('test.session.untitled') }}</span>
            </div>
            <div class="info-item">
              <span class="label">{{ t('test.session.messageCount') }}</span>
              <span class="value">{{ selectedSession.message_count || 0 }}</span>
            </div>
            <div class="info-item">
              <span class="label">{{ t('test.session.status') }}</span>
              <n-tag :type="selectedSession.ended_at ? 'default' : 'success'" size="small">
                {{ selectedSession.ended_at ? t('test.session.ended') : t('test.session.active') }}
              </n-tag>
            </div>
          </div>
          <n-empty v-else-if="!loadingSession" :description="t('test.session.notFound')" />
        </div>
      </n-spin>
    </n-card>

    <!-- 步骤 2: 获取上下文（三个 Tab） -->
    <n-card :title="t('test.card.context')" style="margin-bottom: 16px">
      <n-tabs v-model:value="activeContextTab" type="line">
        <!-- Tab 1: Session 上下文 -->
        <n-tab-pane name="session" :tab="t('test.context.sessionTab')">
          <div class="tab-content">
            <n-space align="center">
              <n-button @click="loadSessionContext" :loading="loadingContext" :disabled="!selectedSessionId" type="primary">
                {{ t('test.context.read') }}
              </n-button>
              <n-input-number v-model:value="contextLimit" :min="1" :max="50" style="width: 100px" />
              <span style="color: var(--theme-text-muted); font-size: 13px">{{ t('test.context.messagesUnit') }}</span>
              <n-checkbox v-model:checked="includeTool">{{ t('test.context.includeTool') }}</n-checkbox>
            </n-space>
            <div v-if="contextMessages.length > 0" class="context-preview">
              <div class="context-header">
                <span>{{ t('test.context.contextCount', { count: contextMessages.length }) }}</span>
              </div>
              <div v-for="(msg, i) in contextMessages" :key="i" class="context-item">
                <span class="context-role" :class="msg.role">{{ msg.role }}:</span>
                <span class="context-content">{{ truncate(msg.content, 100) }}</span>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <!-- Tab 2: Hindsight Recall -->
        <n-tab-pane name="recall" :tab="t('test.context.recallTab')">
          <div class="tab-content">
            <n-space vertical>
              <n-space align="center">
                <n-input v-model:value="recallQuery" :placeholder="t('test.recall.searchPlaceholder')" style="width: 300px" />
                <n-input-number v-model:value="recallLimit" :min="1" :max="50" style="width: 100px" />
                <span style="color: var(--theme-text-muted); font-size: 13px">{{ t('test.recall.unit') }}</span>
                <n-button @click="doRecall" :loading="loadingRecall" type="primary">{{ t('test.recall.button') }}</n-button>
              </n-space>
              <div v-if="recallResults.length > 0" class="recall-results">
                <div class="recall-header">
                  <span>{{ t('test.recall.resultCount', { count: recallResults.length }) }}</span>
                </div>
                <div v-for="(item, i) in recallResults" :key="i" class="recall-item">
                  <div class="recall-text">{{ item.text }}</div>
                  <div class="recall-meta">
                    <n-tag v-if="item.type" size="small" type="info">{{ item.type }}</n-tag>
                    <n-tag v-for="tag in (item.tags || [])" :key="tag" size="small">{{ tag }}</n-tag>
                    <span v-if="item.entities" class="recall-entities">{{ t('test.recall.entity') }}: {{ item.entities }}</span>
                  </div>
                </div>
              </div>
              <n-empty v-else-if="recallQueried && !loadingRecall" :description="t('test.recall.noResult')" />
            </n-space>
          </div>
        </n-tab-pane>

        <!-- Tab 3: Hindsight Reflect -->
        <n-tab-pane name="reflect" :tab="t('test.context.reflectTab')">
          <div class="tab-content">
            <n-space vertical>
              <n-space align="center">
                <n-input v-model:value="reflectQuery" :placeholder="t('test.reflect.queryPlaceholder')" style="width: 300px" />
                <n-input-number v-model:value="reflectLimit" :min="1" :max="50" style="width: 100px" />
                <span style="color: var(--theme-text-muted); font-size: 13px">{{ t('test.reflect.memoryUnit') }}</span>
                <n-button @click="doReflect" :loading="loadingReflect" type="primary">{{ t('test.reflect.button') }}</n-button>
              </n-space>
              <div v-if="reflectResult" class="reflect-result">
                <div class="reflect-label">{{ t('test.reflect.analysisLabel') }}</div>
                <div class="reflect-content">{{ reflectResult }}</div>
              </div>
              <n-empty v-else-if="reflectQueried && !loadingReflect" :description="t('test.reflect.noResult')" />
            </n-space>
          </div>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 步骤 3: 生成主动消息 -->
    <n-card :title="t('test.card.generate')" style="margin-bottom: 16px">
      <n-space vertical>
        <!-- 提示词配置 -->
        <n-divider title-placement="left" style="margin: 0 0 12px 0">{{ t('test.prompt.config') }}</n-divider>
        <div class="prompt-config-area">
          <div class="prompt-config-item">
            <div class="prompt-config-label">{{ t('test.prompt.systemLabel') }}</div>
            <n-input
              v-model:value="customSystemPrompt"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              :placeholder="t('test.prompt.systemPlaceholder')"
            />
            <n-button size="small" @click="loadDefaultSystemPrompt" style="margin-top: 4px">
              {{ t('test.prompt.fillDefault') }}
            </n-button>
          </div>
          <div class="prompt-config-item">
            <div class="prompt-config-label">{{ t('test.prompt.userLabel') }}</div>
            <n-input
              v-model:value="customUserPrompt"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              :placeholder="t('test.prompt.userPlaceholder')"
            />
            <div style="font-size: 12px; color: var(--theme-text-muted); margin-top: 4px">
              {{ t('test.prompt.userHint') }}
            </div>
          </div>
          <n-space align="center">
            <n-checkbox v-model:checked="appendSoulMd">{{ t('test.prompt.appendSoul') }}</n-checkbox>
            <n-button size="small" @click="previewPrompt" :loading="previewingPrompt" :disabled="!selectedSessionId || !hasContext">
              {{ t('test.prompt.preview') }}
            </n-button>
          </n-space>
        </div>

        <n-divider style="margin: 12px 0" />

        <!-- 生成按钮 -->
        <n-space>
          <n-button
            @click="generateMessage"
            :loading="generating"
            :disabled="!selectedSessionId || !hasContext"
            type="primary"
          >
            {{ t('test.generate.button') }}
          </n-button>
          <n-tag v-if="hasContext" type="success">{{ t('test.generate.contextLoaded', { source: contextSource }) }}</n-tag>
          <n-tag v-else type="warning">{{ t('test.generate.noContext') }}</n-tag>
        </n-space>

        <!-- 预览结果 -->
        <n-collapse v-if="promptPreviewData" style="margin-top: 12px">
          <n-collapse-item :title="t('test.prompt.previewTitle')" name="prompt-preview">
            <div class="prompt-preview-section">
              <div class="prompt-section">
                <div class="prompt-label">{{ t('test.prompt.systemFinal') }}</div>
                <n-input
                  :value="promptPreviewData.system_prompt"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 8 }"
                  readonly
                />
              </div>
              <div class="prompt-section">
                <div class="prompt-label">{{ t('test.prompt.userTemplate') }}</div>
                <n-input
                  :value="promptPreviewData.user_prompt_template"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 5 }"
                  readonly
                />
              </div>
              <div class="prompt-section">
                <div class="prompt-label">{{ t('test.prompt.contextContent') }}</div>
                <n-input
                  :value="promptPreviewData.context_content"
                  type="textarea"
                  :autosize="{ minRows: 3, maxRows: 10 }"
                  readonly
                />
              </div>
              <div class="prompt-section" v-if="promptPreviewData.soul_md">
                <div class="prompt-label">{{ t('test.prompt.soulContent') }}</div>
                <n-input
                  :value="promptPreviewData.soul_md"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 6 }"
                  readonly
                />
              </div>
            </div>
          </n-collapse-item>
        </n-collapse>

        <!-- 生成结果 -->
        <div v-if="generatedMessage" class="generated-message">
          <div class="generated-label">{{ t('test.generate.result') }}</div>
          <div class="generated-content">{{ generatedMessage }}</div>
          <n-button size="small" type="primary" @click="fillToSendBox" style="margin-top: 8px">
            {{ t('test.generate.fillToSend') }}
          </n-button>
        </div>
      </n-space>
    </n-card>

    <!-- 步骤 4: 发送消息 -->
    <n-card :title="t('test.card.send')" style="margin-bottom: 16px">
      <n-input
        v-model:value="testMessage"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 6 }"
        :placeholder="t('test.send.placeholder')"
      />
      <div class="send-options">
        <n-space vertical style="width: 100%">
          <n-space>
            <n-checkbox v-model:checked="writeToDB">{{ t('test.send.writeToDB') }}</n-checkbox>
            <n-checkbox v-model:checked="withMark" :disabled="!writeToDB">{{ t('test.send.withMark') }}</n-checkbox>
          </n-space>
          <div v-if="withMark && writeToDB" class="mark-format-section">
            <div class="mark-format-label">{{ t('test.send.markLabel') }}</div>
            <n-input
              v-model:value="sendMark"
              placeholder="凯莉"
              size="small"
              style="max-width: 300px"
            />
            <div class="mark-format-label" style="margin-top: 8px">{{ t('test.send.timeFormat') }}</div>
            <div class="time-format-selector">
              <div
                v-for="opt in timeFormatOptions" :key="opt.value"
                class="time-format-chip"
                :class="{ active: timeFormat === opt.value }"
                @click="timeFormat = opt.value"
              >
                <span class="chip-label">{{ opt.label }}</span>
                <span class="chip-preview">{{ formatWithOption(opt.value) }}</span>
              </div>
            </div>
            <div class="mark-format-preview" v-if="testMessage.trim()">
              {{ t('test.send.preview') }} {{ previewMark }}
            </div>
          </div>
          <n-space>
            <n-button
              type="success"
              @click="sendMessage"
              :loading="sending"
              :disabled="!selectedSessionId || !testMessage.trim()"
            >
              {{ t('test.send.sendTo', { platform: platformLabel }) }}
            </n-button>
          </n-space>
        </n-space>
      </div>
    </n-card>

    <!-- 一键测试 -->
    <n-card :title="t('test.card.oneClick')" style="margin-bottom: 16px">
      <n-space>
        <n-button type="warning" @click="fullTest" :loading="fullTesting" :disabled="!selectedSessionId || !hasContext">
          {{ t('test.oneClick.button') }}
        </n-button>
      </n-space>
    </n-card>

    <!-- 执行日志 -->
    <n-card :title="t('test.card.logs')">
      <div class="log-list">
        <div v-for="(log, i) in logs" :key="i" class="log-item" :class="log.type">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <n-empty v-if="logs.length === 0" :description="t('test.logs.empty')" />
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const message = useMessage()
const loadingSession = ref(false)
const loadingSessionList = ref(false)
const loadingContext = ref(false)
const loadingRecall = ref(false)
const loadingReflect = ref(false)
const sending = ref(false)
const generating = ref(false)
const fullTesting = ref(false)

// 平台选择
const selectedPlatform = ref('weixin')
const platformOptions = [
  { label: '微信', value: 'weixin' },
  { label: '飞书', value: 'feishu' },
  { label: 'CLI', value: 'cli' }
]

// Session 选择
const selectedSessionId = ref(null)
const selectedSession = ref(null)
const sessionOptions = ref([])

// 上下文 Tab
const activeContextTab = ref('session')

// Session 上下文
const contextMessages = ref([])
const contextLimit = ref(10)
const includeTool = ref(false)

// Hindsight Recall
const recallQuery = ref('')
const recallLimit = ref(10)
const recallResults = ref([])
const recallQueried = ref(false)

// Hindsight Reflect
const reflectQuery = ref('')
const reflectLimit = ref(10)
const reflectResult = ref('')
const reflectQueried = ref(false)

// 上下文状态跟踪
const contextSource = ref(null)  // session / recall / reflect
const contextData = ref(null)

// 自定义提示词
const customSystemPrompt = ref('')
const customUserPrompt = ref('{context}')
const appendSoulMd = ref(true)
const promptPreviewData = ref(null)
const previewingPrompt = ref(false)

const hasContext = computed(() => {
  return contextSource.value !== null
})

const platformLabel = computed(() => {
  const p = platformOptions.find(o => o.value === selectedPlatform.value)
  return p ? p.label : selectedPlatform.value
})

// 发送相关
const testMessage = ref('')
const writeToDB = ref(true)
const withMark = ref(false)
const sendMark = ref('凯莉')
const timeFormat = ref('%H:%M 星期{weekday}')
const generatedMessage = ref('')
const logs = ref([])

// 时间格式选项（与 CronJobs.vue 保持一致）
const WEEKDAY_NAMES = ['一', '二', '三', '四', '五', '六', '日']
const timeFormatOptions = [
  { label: t('test.timeFormat.short'), value: '%H:%M 星期{weekday}', preview: () => '14:30 星期四' },
  { label: t('test.timeFormat.hms'), value: '%H:%M:%S', preview: () => '14:30:25' },
  { label: t('test.timeFormat.dateHM'), value: '%m/%d %H:%M', preview: () => '06/12 14:30' },
  { label: t('test.timeFormat.full'), value: '%Y-%m-%d %H:%M:%S', preview: () => '2026-06-12 14:30:25' },
  { label: t('test.timeFormat.dateWeekday'), value: '%m/%d 星期{weekday}', preview: () => '06/12 星期四' },
]

function formatTimeWith(fmt, d) {
  const weekday = WEEKDAY_NAMES[d.getDay() === 0 ? 6 : d.getDay() - 1]
  let s = fmt.replace('{weekday}', weekday)
  const map = { '%Y': d.getFullYear(), '%m': String(d.getMonth() + 1).padStart(2, '0'), '%d': String(d.getDate()).padStart(2, '0'), '%H': String(d.getHours()).padStart(2, '0'), '%M': String(d.getMinutes()).padStart(2, '0'), '%S': String(d.getSeconds()).padStart(2, '0') }
  for (const [k, v] of Object.entries(map)) { s = s.replace(k, v) }
  return s
}

function formatWithOption(fmt) {
  const opt = timeFormatOptions.find(o => o.value === fmt)
  if (opt) return opt.preview()
  return formatTimeWith(fmt, new Date())
}

// 提示词预览
const promptPreview = ref(null)

// 标记预览
const previewMark = computed(() => {
  if (!testMessage.value.trim()) return ''
  const ts = formatTimeWith(timeFormat.value, new Date())
  return `[${sendMark.value} ${ts}]: ${testMessage.value.trim()}`
})

// 监听 selectedSessionId 变化
watch(selectedSessionId, (newId) => {
  if (newId) {
    const s = sessionOptions.value.find(o => o.value === newId)
    selectedSession.value = s ? s.raw : null
    // 重置上下文状态
    resetContext()
  } else {
    selectedSession.value = null
    resetContext()
  }
})

// 监听 Tab 切换
watch(activeContextTab, () => {
  // 切换 tab 时重置上下文状态，因为不同来源的上下文不同
})

function resetContext() {
  contextSource.value = null
  contextData.value = null
  contextMessages.value = []
  recallResults.value = []
  reflectResult.value = ''
  recallQueried.value = false
  reflectQueried.value = false
}

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

function fillToSendBox() {
  testMessage.value = generatedMessage.value
  message.success(t('test.messages.filledToSendBox'))
}

async function loadDefaultSystemPrompt() {
  try {
    const data = await api.get('/config/prompts')
    customSystemPrompt.value = data.system || ''
    customUserPrompt.value = data.generation || ''
    appendSoulMd.value = true
    message.success(t('test.messages.loadedDefaultPrompt'))
  } catch (e) {
    message.warning(t('test.messages.loadDefaultFailed'))
  }
}

async function previewPrompt() {
  if (!selectedSessionId.value || !hasContext.value) {
    message.warning(t('test.messages.selectSessionFirst'))
    return
  }
  previewingPrompt.value = true
  try {
    const data = await api.post('/messages/preview', {
      session_id: selectedSessionId.value,
      context_source: contextSource.value,
      context_data: contextData.value,
      system_prompt: customSystemPrompt.value || null,
      user_prompt: customUserPrompt.value || null,
      append_soul_md: appendSoulMd.value
    })
    promptPreviewData.value = data
    addLog('success', t('test.messages.previewSuccess'))
  } catch (e) {
    addLog('error', t('test.messages.previewFailed') + ': ' + (e?.detail || t('test.messages.previewFailed')))
    message.error(t('test.messages.previewFailed'))
  } finally {
    previewingPrompt.value = false
  }
}

function onPlatformChange() {
  selectedSessionId.value = null
  selectedSession.value = null
  sessionOptions.value = []
  resetContext()
  loadSessionList()
}

async function loadSessionList() {
  loadingSessionList.value = true
  try {
    const data = await api.get('/sessions', {
      params: { platform: selectedPlatform.value, page: 1, page_size: 20, active_only: true }
    })
    sessionOptions.value = (data.items || []).map(s => ({
      label: `${s.title || s.id} (${s.message_count || 0})`,
      value: s.id,
      raw: s
    }))
    addLog('info', `${t('test.messages.loadingSessionList', { platform: platformLabel.value })}: ${sessionOptions.value.length} ${t('test.messages.count')}`)
  } catch (e) {
    addLog('error', t('test.messages.loadSessionListFailed') + ': ' + (e?.detail || t('test.messages.loadSessionListFailed')))
  } finally {
    loadingSessionList.value = false
  }
}

async function loadLatestSession() {
  loadingSession.value = true
  try {
    const data = await api.get(`/sessions/latest/${selectedPlatform.value}`)
    if (data && data.id) {
      selectedSessionId.value = data.id
      selectedSession.value = { ...data, message_count: data.message_count || 0 }
      if (data.was_auto_reset) {
        addLog('info', `${t('test.messages.sessionAutoReset')}（${data.auto_reset_reason}），${data.id}`)
      } else {
        addLog('info', `${t('test.messages.getLatestSession', { platform: platformLabel.value })}: ${data.id}`)
      }
    } else {
      addLog('error', t('test.messages.sessionNotFound', { platform: platformLabel.value }))
    }
  } catch (e) {
    addLog('error', t('test.messages.getLatestFailed') + ': ' + (e?.detail || t('test.messages.getLatestFailed')))
  } finally {
    loadingSession.value = false
  }
}

async function loadSessionContext() {
  if (!selectedSessionId.value) return
  loadingContext.value = true
  try {
    const data = await api.get(`/sessions/${selectedSessionId.value}/context`, {
      params: { limit: contextLimit.value, include_tool: includeTool.value }
    })
    contextMessages.value = Array.isArray(data) ? data : (data?.items || [])
    contextSource.value = 'session'
    contextData.value = contextMessages.value.map(m => `${m.role}: ${m.content}`).join('\n')
    addLog('success', t('test.messages.contextLoaded', { count: contextMessages.value.length }))
  } catch (e) {
    addLog('error', t('test.messages.contextLoadFailed') + ': ' + (e?.detail || t('test.messages.contextLoadFailed')))
  } finally {
    loadingContext.value = false
  }
}

async function doRecall() {
  if (!recallQuery.value.trim()) {
    message.warning(t('test.messages.enterSearchKeyword'))
    return
  }
  loadingRecall.value = true
  recallQueried.value = true
  try {
    const data = await api.post('/hindsight/recall', null, {
      params: { query: recallQuery.value.trim(), limit: recallLimit.value }
    })
    if (data.success) {
      recallResults.value = data.results || []
      contextSource.value = 'recall'
      contextData.value = recallResults.value.map(r => r.text).join('\n')
      addLog('success', `${t('test.messages.recallSuccess')}: ${recallResults.value.length} ${t('test.messages.recallResultCount')}`)
    } else {
      recallResults.value = []
      addLog('error', t('test.messages.recallFailed') + ': ' + (data.message || t('test.messages.recallFailed')))
    }
  } catch (e) {
    recallResults.value = []
    addLog('error', t('test.messages.recallRequestFailed') + ': ' + (e?.detail || t('test.messages.recallRequestFailed')))
  } finally {
    loadingRecall.value = false
  }
}

async function doReflect() {
  if (!reflectQuery.value.trim()) {
    message.warning(t('test.messages.enterQuery'))
    return
  }
  loadingReflect.value = true
  reflectQueried.value = true
  try {
    const data = await api.post('/hindsight/reflect', null, {
      params: { query: reflectQuery.value.trim(), limit: reflectLimit.value }
    })
    if (data.success) {
      reflectResult.value = data.reflection || ''
      contextSource.value = 'reflect'
      contextData.value = reflectResult.value
      addLog('success', t('test.messages.reflectSuccess'))
    } else {
      reflectResult.value = ''
      addLog('error', t('test.messages.reflectFailed') + ': ' + (data.message || t('test.messages.reflectFailed')))
    }
  } catch (e) {
    reflectResult.value = ''
    addLog('error', t('test.messages.reflectRequestFailed') + ': ' + (e?.detail || t('test.messages.reflectRequestFailed')))
  } finally {
    loadingReflect.value = false
  }
}

async function generateMessage() {
  if (!selectedSessionId.value) return
  if (!hasContext.value) {
    message.warning(t('test.messages.getContextFirst'))
    return
  }
  generating.value = true
  promptPreviewData.value = null
  try {
    const data = await api.post('/messages/generate', {
      session_id: selectedSessionId.value,
      context_source: contextSource.value,
      context_data: contextData.value,
      system_prompt: customSystemPrompt.value || null,
      user_prompt: customUserPrompt.value || null,
      append_soul_md: appendSoulMd.value
    })
    generatedMessage.value = data?.message || ''
    addLog('success', `${t('test.messages.generateMessage')}: ${generatedMessage.value}`)
    message.success(t('test.messages.generateSuccess'))

    // 自动预览提示词
    await previewPrompt()
  } catch (e) {
    addLog('error', t('test.messages.generateFailed') + ': ' + (e?.detail || t('test.messages.generateFailed')))
    message.error(t('test.messages.generateFailed'))
  } finally {
    generating.value = false
  }
}

async function sendMessage() {
  if (!selectedSessionId.value || !testMessage.value.trim()) return
  sending.value = true
  try {
    const result = await api.post('/messages/send', {
      session_id: selectedSessionId.value,
      message: testMessage.value.trim(),
      platform: selectedPlatform.value,
      write_to_db: writeToDB.value,
      with_mark: withMark.value,
      send_mark: sendMark.value,
      time_format: timeFormat.value
    })
    addLog('success', `${t('test.messages.sendSuccess')}: ${testMessage.value.trim()}`)
    message.success(t('test.messages.sendSuccess'))
  } catch (e) {
    addLog('error', t('test.messages.sendFailed') + ': ' + (e?.detail || e?.message || t('test.messages.sendFailed')))
    message.error(t('test.messages.sendFailed'))
  } finally {
    sending.value = false
  }
}

async function fullTest() {
  if (!selectedSessionId.value) return
  if (!hasContext.value) {
    message.warning(t('test.messages.getContextFirst'))
    return
  }
  fullTesting.value = true
  try {
    // 先生成
    const genData = await api.post('/messages/generate', {
      session_id: selectedSessionId.value,
      context_source: contextSource.value,
      context_data: contextData.value
    })
    const generated = genData?.message || ''
    if (!generated) {
      throw new Error(t('test.messages.generateFailed'))
    }

    // 再发送
    const sendResult = await api.post('/messages/send', {
      session_id: selectedSessionId.value,
      message: generated,
      platform: selectedPlatform.value,
      write_to_db: true,
      with_mark: true,
      send_mark: sendMark.value,
      time_format: timeFormat.value
    })

    addLog('success', `${t('test.messages.fullTestComplete')}: ${generated}`)
    message.success(t('test.messages.fullTestSuccess'))
  } catch (e) {
    addLog('error', t('test.messages.fullTestFailed') + ': ' + (e?.detail || e?.message || t('test.messages.fullTestFailed')))
    message.error(t('test.messages.fullTestFailed'))
  } finally {
    fullTesting.value = false
  }
}

onMounted(() => {
  loadSessionList()
})
</script>

<style scoped>
.test-page {
  max-width: 900px;
  margin: 0 auto;
}

.session-select-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.select-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.select-label {
  min-width: 80px;
  color: var(--theme-text-secondary);
  font-size: 14px;
}

.select-actions {
  display: flex;
  gap: 8px;
}

.session-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 8px;
  padding: 12px;
  background: var(--theme-bg-muted);
  border-radius: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  color: var(--theme-text-muted);
}

.info-item .value {
  font-size: 14px;
  color: var(--theme-text);
  word-break: break-all;
}

.tab-content {
  padding: 12px 0;
}

.context-preview {
  margin-top: 12px;
  max-height: 300px;
  overflow-y: auto;
  background: var(--theme-bg-muted);
  border-radius: 12px;
  padding: 12px;
}

.context-header {
  font-size: 12px;
  color: var(--theme-text-muted);
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
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
  color: var(--theme-primary);
}

.context-role.assistant {
  color: var(--theme-accent);
}

.context-content {
  color: var(--theme-text-secondary);
}

.recall-results {
  margin-top: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.recall-header {
  font-size: 12px;
  color: var(--theme-text-muted);
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.recall-item {
  padding: 12px;
  background: var(--theme-bg-muted);
  border-radius: 12px;
  margin-bottom: 8px;
}

.recall-text {
  font-size: 14px;
  color: var(--theme-text);
  line-height: 1.6;
  margin-bottom: 8px;
}

.recall-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.recall-entities {
  font-size: 12px;
  color: var(--theme-text-secondary);
}

.reflect-result {
  margin-top: 12px;
  padding: 16px;
  background: rgba(var(--theme-primary-rgb), 0.06);
  border-radius: 12px;
}

.reflect-label {
  font-size: 12px;
  color: var(--theme-text-muted);
  margin-bottom: 8px;
}

.reflect-content {
  font-size: 14px;
  color: var(--theme-text);
  line-height: 1.8;
  white-space: pre-wrap;
}

.send-options {
  margin-top: 12px;
}

.mark-format-section {
  background: var(--theme-bg-muted);
  padding: 12px;
  border-radius: 12px;
  margin-top: 8px;
}

.mark-format-label {
  font-size: 13px;
  color: var(--theme-text-secondary);
  margin-bottom: 8px;
}

.mark-format-hint {
  font-size: 12px;
  color: var(--theme-text-muted);
  margin-top: 6px;
}

.mark-format-preview {
  font-size: 12px;
  color: var(--theme-primary);
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(var(--theme-primary-rgb), 0.06);
  border-radius: 8px;
  word-break: break-all;
}

.generated-message {
  margin-top: 12px;
  padding: 12px;
  background: rgba(var(--theme-primary-rgb), 0.06);
  border-radius: 12px;
}

.generated-label {
  font-size: 12px;
  color: var(--theme-text-muted);
  margin-bottom: 4px;
}

.generated-content {
  font-size: 14px;
  color: var(--theme-text);
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
  border-bottom: 1px solid var(--theme-border-light);
  font-size: 13px;
}

.log-item.success {
  color: var(--theme-status-active);
}

.log-item.error {
  color: var(--theme-primary);
}

.log-item.info {
  color: var(--theme-accent);
}

.log-time {
  color: var(--theme-text-muted);
  flex-shrink: 0;
}

.prompt-config-area {
  background: var(--theme-bg-muted);
  padding: 12px;
  border-radius: 12px;
}

.prompt-config-item {
  margin-bottom: 12px;
}

.prompt-config-item:last-of-type {
  margin-bottom: 8px;
}

.prompt-config-label {
  font-size: 13px;
  color: var(--theme-text-secondary);
  margin-bottom: 4px;
  font-weight: 500;
}

.prompt-preview-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.prompt-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.prompt-label {
  font-size: 13px;
  color: var(--theme-text-secondary);
  font-weight: 500;
}

/* 时间格式选择器 */
.time-format-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.time-format-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border: 1px solid var(--theme-border-light);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--theme-card-bg);
  min-width: 80px;
  min-height: 48px;
}

.time-format-chip:hover {
  border-color: var(--theme-primary);
  background: rgba(var(--theme-primary-rgb), 0.06);
}

.time-format-chip.active {
  border-color: var(--theme-primary);
  background: rgba(var(--theme-primary-rgb), 0.1);
  box-shadow: 0 0 0 1px var(--theme-primary);
}

.chip-label {
  font-size: 12px;
  color: var(--theme-text-secondary);
  margin-bottom: 2px;
}

.time-format-chip.active .chip-label {
  color: var(--theme-primary);
  font-weight: 500;
}

.chip-preview {
  font-size: 13px;
  color: var(--theme-text-primary);
  font-family: monospace;
}

.mark-format-preview {
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--theme-bg-muted);
  border-radius: 10px;
  font-size: 12px;
  color: var(--theme-text-secondary);
  font-family: monospace;
  word-break: break-all;
}

@media (max-width: 768px) {
  .test-page {
    max-width: 100%;
  }

  .session-info {
    grid-template-columns: 1fr;
  }

  .select-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .select-label {
    min-width: auto;
  }

  .select-row :deep(.n-select) {
    width: 100% !important;
  }

  .select-actions {
    flex-wrap: wrap;
  }

  .select-actions .n-button {
    flex: 1;
  }

  .context-preview,
  .recall-results {
    max-height: 200px;
  }

  .prompt-config-area {
    padding: 8px;
  }

  .time-format-selector {
    gap: 6px;
  }

  .time-format-chip {
    padding: 5px 8px;
    min-width: 70px;
    flex: 1 1 calc(50% - 6px);
    min-width: 0;
  }

  .chip-preview {
    font-size: 11px;
  }

  :deep(.n-card) {
    --n-padding: 12px 16px;
  }

  :deep(.n-space) {
    flex-wrap: wrap;
  }

  :deep(.n-input),
  :deep(.n-select),
  :deep(.n-input-number) {
    width: 100% !important;
    max-width: 100% !important;
  }

  .send-options :deep(.n-space) {
    width: 100%;
  }
}
</style>