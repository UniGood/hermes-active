<template>
  <div class="test-page">
    <!-- 步骤 1: Session 选择区域 -->
    <n-card title="1. Session 选择" style="margin-bottom: 16px">
      <n-spin :show="loadingSession">
        <div class="session-select-area">
          <div class="select-row">
            <span class="select-label">目标平台:</span>
            <n-select
              v-model:value="selectedPlatform"
              :options="platformOptions"
              style="width: 150px"
              @update:value="onPlatformChange"
            />
          </div>
          <div class="select-row">
            <span class="select-label">Session:</span>
            <n-select
              v-model:value="selectedSessionId"
              :options="sessionOptions"
              placeholder="选择 session"
              style="flex: 1"
              filterable
            />
          </div>
          <div class="select-actions">
            <n-button size="small" @click="loadLatestSession" :loading="loadingSession">获取最新</n-button>
            <n-button size="small" @click="loadSessionList" :loading="loadingSessionList">刷新列表</n-button>
          </div>
          <div v-if="selectedSession" class="session-info">
            <div class="info-item">
              <span class="label">Session ID</span>
              <n-text code style="font-size: 12px">{{ selectedSession.id }}</n-text>
            </div>
            <div class="info-item">
              <span class="label">标题</span>
              <span class="value">{{ selectedSession.title || '无标题' }}</span>
            </div>
            <div class="info-item">
              <span class="label">消息数</span>
              <span class="value">{{ selectedSession.message_count || 0 }}</span>
            </div>
            <div class="info-item">
              <span class="label">状态</span>
              <n-tag :type="selectedSession.ended_at ? 'default' : 'success'" size="small">
                {{ selectedSession.ended_at ? '已结束' : '活跃' }}
              </n-tag>
            </div>
          </div>
          <n-empty v-else-if="!loadingSession" description="未找到 Session" />
        </div>
      </n-spin>
    </n-card>

    <!-- 步骤 2: 获取上下文（三个 Tab） -->
    <n-card title="2. 获取上下文" style="margin-bottom: 16px">
      <n-tabs v-model:value="activeContextTab" type="line">
        <!-- Tab 1: Session 上下文 -->
        <n-tab-pane name="session" tab="Session 上下文">
          <div class="tab-content">
            <n-space align="center">
              <n-button @click="loadSessionContext" :loading="loadingContext" :disabled="!selectedSessionId" type="primary">
                读取上下文
              </n-button>
              <n-input-number v-model:value="contextLimit" :min="1" :max="50" style="width: 100px" />
              <span style="color: #999; font-size: 13px">条消息</span>
              <n-checkbox v-model:checked="includeTool">获取tool上下文</n-checkbox>
            </n-space>
            <div v-if="contextMessages.length > 0" class="context-preview">
              <div class="context-header">
                <span>共 {{ contextMessages.length }} 条上下文</span>
              </div>
              <div v-for="(msg, i) in contextMessages" :key="i" class="context-item">
                <span class="context-role" :class="msg.role">{{ msg.role }}:</span>
                <span class="context-content">{{ truncate(msg.content, 100) }}</span>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <!-- Tab 2: Hindsight Recall -->
        <n-tab-pane name="recall" tab="Hindsight Recall">
          <div class="tab-content">
            <n-space vertical>
              <n-space align="center">
                <n-input v-model:value="recallQuery" placeholder="输入搜索关键词" style="width: 300px" />
                <n-input-number v-model:value="recallLimit" :min="1" :max="50" style="width: 100px" />
                <span style="color: #999; font-size: 13px">条</span>
                <n-button @click="doRecall" :loading="loadingRecall" type="primary">Recall</n-button>
              </n-space>
              <div v-if="recallResults.length > 0" class="recall-results">
                <div class="recall-header">
                  <span>共 {{ recallResults.length }} 条结果</span>
                </div>
                <div v-for="(item, i) in recallResults" :key="i" class="recall-item">
                  <div class="recall-text">{{ item.text }}</div>
                  <div class="recall-meta">
                    <n-tag v-if="item.type" size="small" type="info">{{ item.type }}</n-tag>
                    <n-tag v-for="tag in (item.tags || [])" :key="tag" size="small">{{ tag }}</n-tag>
                    <span v-if="item.entities" class="recall-entities">实体: {{ item.entities }}</span>
                  </div>
                </div>
              </div>
              <n-empty v-else-if="recallQueried && !loadingRecall" description="无结果" />
            </n-space>
          </div>
        </n-tab-pane>

        <!-- Tab 3: Hindsight Reflect -->
        <n-tab-pane name="reflect" tab="Hindsight Reflect">
          <div class="tab-content">
            <n-space vertical>
              <n-space align="center">
                <n-input v-model:value="reflectQuery" placeholder="输入问题/查询" style="width: 300px" />
                <n-input-number v-model:value="reflectLimit" :min="1" :max="50" style="width: 100px" />
                <span style="color: #999; font-size: 13px">条记忆</span>
                <n-button @click="doReflect" :loading="loadingReflect" type="primary">Reflect</n-button>
              </n-space>
              <div v-if="reflectResult" class="reflect-result">
                <div class="reflect-label">综合分析结果：</div>
                <div class="reflect-content">{{ reflectResult }}</div>
              </div>
              <n-empty v-else-if="reflectQueried && !loadingReflect" description="无结果" />
            </n-space>
          </div>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 步骤 3: 生成主动消息 -->
    <n-card title="3. 生成主动消息" style="margin-bottom: 16px">
      <n-space vertical>
        <!-- 提示词配置 -->
        <n-divider title-placement="left" style="margin: 0 0 12px 0">提示词配置</n-divider>
        <div class="prompt-config-area">
          <div class="prompt-config-item">
            <div class="prompt-config-label">系统提示词：</div>
            <n-input
              v-model:value="customSystemPrompt"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              placeholder="系统提示词，定义 AI 的角色和行为规则"
            />
            <n-button size="small" @click="loadDefaultSystemPrompt" style="margin-top: 4px">
              填充默认系统提示词
            </n-button>
          </div>
          <div class="prompt-config-item">
            <div class="prompt-config-label">用户提示词：</div>
            <n-input
              v-model:value="customUserPrompt"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              placeholder="用户提示词模板，支持 {context} 占位符"
            />
            <div style="font-size: 12px; color: #999; margin-top: 4px">
              支持 {context} 占位符，运行时替换为实际上下文
            </div>
          </div>
          <n-space align="center">
            <n-checkbox v-model:checked="appendSoulMd">拼接 soul.md</n-checkbox>
            <n-button size="small" @click="previewPrompt" :loading="previewingPrompt" :disabled="!selectedSessionId || !hasContext">
              预览提示词
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
            根据上下文生成消息
          </n-button>
          <n-tag v-if="hasContext" type="success">已获取上下文 ({{ contextSource }})</n-tag>
          <n-tag v-else type="warning">⚠️ 请先获取上下文</n-tag>
        </n-space>

        <!-- 预览结果 -->
        <n-collapse v-if="promptPreviewData" style="margin-top: 12px">
          <n-collapse-item title="查看提示词预览" name="prompt-preview">
            <div class="prompt-preview-section">
              <div class="prompt-section">
                <div class="prompt-label">系统提示词（最终版）：</div>
                <n-input
                  :value="promptPreviewData.system_prompt"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 8 }"
                  readonly
                />
              </div>
              <div class="prompt-section">
                <div class="prompt-label">用户提示词模板：</div>
                <n-input
                  :value="promptPreviewData.user_prompt_template"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 5 }"
                  readonly
                />
              </div>
              <div class="prompt-section">
                <div class="prompt-label">实际上下文内容：</div>
                <n-input
                  :value="promptPreviewData.context_content"
                  type="textarea"
                  :autosize="{ minRows: 3, maxRows: 10 }"
                  readonly
                />
              </div>
              <div class="prompt-section" v-if="promptPreviewData.soul_md">
                <div class="prompt-label">soul.md 内容：</div>
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
          <div class="generated-label">生成结果：</div>
          <div class="generated-content">{{ generatedMessage }}</div>
          <n-button size="small" type="primary" @click="fillToSendBox" style="margin-top: 8px">
            填入发送框
          </n-button>
        </div>
      </n-space>
    </n-card>

    <!-- 步骤 4: 发送消息 -->
    <n-card title="4. 发送消息" style="margin-bottom: 16px">
      <n-input
        v-model:value="testMessage"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 6 }"
        placeholder="输入要发送的消息..."
      />
      <div class="send-options">
        <n-space vertical style="width: 100%">
          <n-space>
            <n-checkbox v-model:checked="writeToDB">写入 Session DB</n-checkbox>
            <n-checkbox v-model:checked="withMark" :disabled="!writeToDB">带标记</n-checkbox>
          </n-space>
          <div v-if="withMark && writeToDB" class="mark-format-section">
            <div class="mark-format-label">标记格式模板：</div>
            <n-input
              v-model:value="markFormat"
              placeholder="[凯莉主动发送] {timestamp}: {content}"
              size="small"
            />
            <div class="mark-format-hint">
              支持占位符: <n-text code>{timestamp}</n-text> <n-text code>{content}</n-text>
            </div>
            <div class="mark-format-preview" v-if="testMessage.trim()">
              预览: {{ previewMark }}
            </div>
          </div>
          <n-space>
            <n-button
              type="primary"
              @click="sendMessage"
              :loading="sending"
              :disabled="!selectedSessionId || !testMessage.trim()"
            >
              发送到 {{ platformLabel }}
            </n-button>
          </n-space>
        </n-space>
      </div>
    </n-card>

    <!-- 一键测试 -->
    <n-card title="一键测试" style="margin-bottom: 16px">
      <n-space>
        <n-button type="warning" @click="fullTest" :loading="fullTesting" :disabled="!selectedSessionId || !hasContext">
          生成 + 发送 + 写入DB
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
import { ref, computed, onMounted, watch } from 'vue'
import { useMessage } from 'naive-ui'
import api from '../api'

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
const markFormat = ref('[凯莉主动发送] {timestamp}: {content}')
const generatedMessage = ref('')
const logs = ref([])

// 提示词预览
const promptPreview = ref(null)

// 标记预览
const previewMark = computed(() => {
  if (!testMessage.value.trim()) return ''
  const now = new Date()
  const ts = `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  return markFormat.value
    .replace('{timestamp}', ts)
    .replace('{content}', testMessage.value.trim())
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
  message.success('已填入发送框')
}

async function loadDefaultSystemPrompt() {
  try {
    const data = await api.get('/config/default-prompts')
    if (data.system_prompt) {
      customSystemPrompt.value = data.system_prompt
    }
    if (data.user_prompt) {
      customUserPrompt.value = data.user_prompt
    }
    appendSoulMd.value = data.append_soul_md !== false
    message.success('已加载默认提示词')
  } catch (e) {
    // 如果没有默认提示词，尝试从 prompts 配置加载
    try {
      const promptsConfig = await api.get('/config/prompts')
      customSystemPrompt.value = promptsConfig.system || ''
      message.success('已加载系统提示词')
    } catch (e2) {
      message.warning('加载默认提示词失败')
    }
  }
}

async function previewPrompt() {
  if (!selectedSessionId.value || !hasContext.value) {
    message.warning('请先选择 Session 并获取上下文')
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
    addLog('success', '提示词预览成功')
  } catch (e) {
    addLog('error', '预览失败: ' + (e?.detail || '未知错误'))
    message.error('预览失败')
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
      label: `${s.title || s.id} (${s.message_count || 0} 条消息)`,
      value: s.id,
      raw: s
    }))
    addLog('info', `加载 ${platformLabel.value} Session 列表: ${sessionOptions.value.length} 个`)
  } catch (e) {
    addLog('error', '加载 Session 列表失败: ' + (e?.detail || '未知错误'))
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
      selectedSession.value = data
      addLog('info', `获取最新 ${platformLabel.value} Session: ${data.id}`)
    } else {
      addLog('error', `未找到 ${platformLabel.value} 的 Session`)
    }
  } catch (e) {
    addLog('error', '获取最新 Session 失败: ' + (e?.detail || '未知错误'))
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
    addLog('success', `读取到 ${contextMessages.value.length} 条 Session 上下文消息`)
  } catch (e) {
    addLog('error', '读取上下文失败: ' + (e?.detail || '未知错误'))
  } finally {
    loadingContext.value = false
  }
}

async function doRecall() {
  if (!recallQuery.value.trim()) {
    message.warning('请输入搜索关键词')
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
      addLog('success', `Recall 成功: ${recallResults.value.length} 条结果`)
    } else {
      recallResults.value = []
      addLog('error', 'Recall 失败: ' + (data.message || '未知错误'))
    }
  } catch (e) {
    recallResults.value = []
    addLog('error', 'Recall 请求失败: ' + (e?.detail || '未知错误'))
  } finally {
    loadingRecall.value = false
  }
}

async function doReflect() {
  if (!reflectQuery.value.trim()) {
    message.warning('请输入问题/查询')
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
      addLog('success', 'Reflect 成功')
    } else {
      reflectResult.value = ''
      addLog('error', 'Reflect 失败: ' + (data.message || '未知错误'))
    }
  } catch (e) {
    reflectResult.value = ''
    addLog('error', 'Reflect 请求失败: ' + (e?.detail || '未知错误'))
  } finally {
    loadingReflect.value = false
  }
}

async function generateMessage() {
  if (!selectedSessionId.value) return
  if (!hasContext.value) {
    message.warning('请先获取上下文（Session/Hindsight）')
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
    addLog('success', `生成消息: ${generatedMessage.value}`)
    message.success('生成成功')

    // 自动预览提示词
    await previewPrompt()
  } catch (e) {
    addLog('error', '生成失败: ' + (e?.detail || '未知错误'))
    message.error('生成失败')
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
      mark_format: markFormat.value
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

async function fullTest() {
  if (!selectedSessionId.value) return
  if (!hasContext.value) {
    message.warning('请先获取上下文（Session/Hindsight）')
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
      throw new Error('生成消息为空')
    }

    // 再发送
    const sendResult = await api.post('/messages/send', {
      session_id: selectedSessionId.value,
      message: generated,
      platform: selectedPlatform.value,
      write_to_db: true,
      with_mark: true,
      mark_format: markFormat.value
    })

    addLog('success', `完整流程测试完成: ${generated}`)
    message.success('完整流程测试成功')
  } catch (e) {
    addLog('error', '完整流程测试失败: ' + (e?.detail || e?.message || '未知错误'))
    message.error('完整流程测试失败')
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
  color: #666;
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
  background: #f5f7fa;
  border-radius: 8px;
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

.tab-content {
  padding: 12px 0;
}

.context-preview {
  margin-top: 12px;
  max-height: 300px;
  overflow-y: auto;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
}

.context-header {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8e8e8;
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

.recall-results {
  margin-top: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.recall-header {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8e8e8;
}

.recall-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 8px;
}

.recall-text {
  font-size: 14px;
  color: #333;
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
  color: #666;
}

.reflect-result {
  margin-top: 12px;
  padding: 16px;
  background: #f0f9eb;
  border-radius: 8px;
}

.reflect-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.reflect-content {
  font-size: 14px;
  color: #333;
  line-height: 1.8;
  white-space: pre-wrap;
}

.send-options {
  margin-top: 12px;
}

.mark-format-section {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 8px;
  margin-top: 8px;
}

.mark-format-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.mark-format-hint {
  font-size: 12px;
  color: #999;
  margin-top: 6px;
}

.mark-format-preview {
  font-size: 12px;
  color: #18a058;
  margin-top: 6px;
  padding: 6px 8px;
  background: #f0f9eb;
  border-radius: 4px;
  word-break: break-all;
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

.prompt-config-area {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 8px;
}

.prompt-config-item {
  margin-bottom: 12px;
}

.prompt-config-item:last-of-type {
  margin-bottom: 8px;
}

.prompt-config-label {
  font-size: 13px;
  color: #666;
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
  color: #666;
  font-weight: 500;
}
</style>
