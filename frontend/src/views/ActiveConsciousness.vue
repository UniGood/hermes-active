<template>
  <div class="active-consciousness-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 配置 -->
      <n-tab-pane name="config" tab="配置">
        <n-card title="💓 主动意识配置" style="margin-bottom: 16px">
          <!-- 总开关 -->
          <n-form-item label="启用主动意识">
            <n-switch v-model:value="config.enabled" />
          </n-form-item>

          <template v-if="config.enabled">
            <!-- LLM 配置 -->
            <n-divider>LLM 配置</n-divider>
            <n-form-item label="LLM 模式">
              <n-radio-group v-model:value="config.llm.mode">
                <n-radio value="hermes">使用 Hermes LLM</n-radio>
                <n-radio value="custom">自定义 LLM</n-radio>
              </n-radio-group>
            </n-form-item>
            <n-form-item label="Provider" v-if="config.llm.mode === 'custom'">
              <n-select v-model:value="config.llm.provider" :options="providerOptions" />
            </n-form-item>
            <n-form-item label="Model" v-if="config.llm.mode === 'custom'">
              <n-input v-model:value="config.llm.model" placeholder="deepseek-chat" />
            </n-form-item>
            <n-form-item label="API Key" v-if="config.llm.mode === 'custom'">
              <n-input v-model:value="config.llm.api_key" type="password" show-password-on="mousedown" placeholder="输入 API Key" />
            </n-form-item>
            <n-form-item label="Base URL" v-if="config.llm.mode === 'custom'">
              <n-input v-model:value="config.llm.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>

            <!-- 主动意识配置 -->
            <n-divider>心跳配置</n-divider>
            <n-form-item label="启用心跳">
              <n-switch v-model:value="config.active.enabled" />
            </n-form-item>
            <n-form-item label="心跳间隔（秒）">
              <n-input-number v-model:value="config.active.heartbeat_interval" :min="60" :max="3600" />
            </n-form-item>
            <n-form-item label="发送标记">
              <n-input v-model:value="config.active.send_tag" placeholder="[凯莉主动发送]" />
            </n-form-item>
            <n-form-item label="时间格式">
              <n-input v-model:value="config.active.time_format" placeholder="%H:%M" />
            </n-form-item>
            <n-form-item label="禁止窗口（用户消息后分钟）">
              <n-input-number v-model:value="config.active.no_send_after_user_msg_minutes" :min="1" :max="60" />
            </n-form-item>
            <n-form-item label="热度阈值（高于此不发送）">
              <n-input-number v-model:value="config.active.no_send_while_heat_above" :min="0" :max="10" :step="0.1" />
            </n-form-item>
            <n-form-item label="情绪阈值（低于此不发送）">
              <n-input-number v-model:value="config.active.no_send_while_vibe_below" :min="0" :max="1" :step="0.1" />
            </n-form-item>

            <!-- 通知目标 -->
            <n-divider>通知目标</n-divider>
            <n-form-item label="目标平台">
              <n-select v-model:value="config.notify.platform" :options="platformOptions" @update:value="onNotifyPlatformChange" />
            </n-form-item>
            <n-form-item label="Session 来源">
              <n-radio-group v-model:value="notifySessionMode">
                <n-space vertical>
                  <n-radio value="latest">每次获取最新活跃 Session</n-radio>
                  <n-radio value="fixed">指定 Session</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>
            <n-form-item label="指定 Session" v-if="notifySessionMode === 'fixed'">
              <n-select
                v-model:value="config.notify.chat_id"
                :options="notifySessionOptions"
                :loading="loadingNotifySessions"
                placeholder="选择目标 Session"
                filterable
              />
            </n-form-item>

            <!-- Session 来源配置 -->
            <n-divider>Session 来源</n-divider>
            <n-form-item label="来源平台">
              <n-select v-model:value="config.session.sources" multiple :options="platformOptions" />
            </n-form-item>
            <n-form-item label="时间范围（小时）">
              <n-input-number v-model:value="config.session.time_range_hours" :min="1" :max="168" />
            </n-form-item>
            <n-form-item label="每 Session 最大消息">
              <n-input-number v-model:value="config.session.max_messages_per_session" :min="5" :max="100" />
            </n-form-item>
            <n-form-item label="过滤 Tool 消息">
              <n-switch v-model:value="config.session.filter_tool_messages" />
            </n-form-item>
            <n-form-item label="获取测试">
              <n-button @click="testSessionContext" :loading="testingSessionContext">获取 Session 上下文</n-button>
            </n-form-item>

            <!-- 决策阈值 -->
            <n-divider>决策阈值</n-divider>
            <n-form-item label="立即发送阈值">
              <n-input-number v-model:value="config.decision.send_threshold" :min="0" :max="1" :step="0.1" />
            </n-form-item>
            <n-form-item label="延迟发送阈值">
              <n-input-number v-model:value="config.decision.delay_threshold" :min="0" :max="1" :step="0.1" />
            </n-form-item>
            <n-form-item label="存为记忆阈值">
              <n-input-number v-model:value="config.decision.memory_threshold" :min="0" :max="1" :step="0.1" />
            </n-form-item>
            <n-form-item label="每小时最大消息">
              <n-input-number v-model:value="config.decision.max_per_hour" :min="1" :max="10" />
            </n-form-item>
            <n-form-item label="每日最大消息">
              <n-input-number v-model:value="config.decision.max_per_day" :min="1" :max="50" />
            </n-form-item>
          </template>

          <n-button type="primary" @click="saveConfig" :loading="saving" style="margin-top: 16px">
            保存配置
          </n-button>
        </n-card>
      </n-tab-pane>

      <!-- Tab 2: 状态 -->
      <n-tab-pane name="status" tab="状态">
        <n-grid :cols="2" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-card title="心跳状态">
              <n-statistic label="今日心跳次数" :value="status.heartbeat_count" />
              <div style="margin-top: 8px; font-size: 12px; color: #666;">
                上次心跳：{{ formatTime(status.last_heartbeat_at) || '无' }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="想念分数">
              <n-statistic :value="status.longing.score" :precision="3">
                <template #suffix>
                  <n-tag :type="longingTagType" size="small">{{ status.longing.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="status.longing.score * 100" :color="longingColor" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="聊天热度">
              <n-statistic :value="status.chat_heat.heat" :precision="2">
                <template #suffix>
                  <n-tag :type="heatTagType" size="small">{{ status.chat_heat.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="Math.min(status.chat_heat.heat * 20, 100)" :color="heatColor" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="情绪值">
              <n-statistic :value="status.emotional_intensity.intensity" :precision="3">
                <template #suffix>
                  <n-tag size="small">{{ status.emotional_intensity.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="status.emotional_intensity.intensity * 100" :color="intensityColor" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="今日发送">
              <n-statistic :value="status.today_sent_count" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="本小时发送">
              <n-statistic :value="status.hour_sent_count" />
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-tab-pane>

      <!-- Tab 3: 日志 -->
      <n-tab-pane name="logs" tab="日志">
        <n-tabs type="line" animated>
          <n-tab-pane name="thoughts" tab="念头日志">
            <n-data-table :columns="thoughtColumns" :data="thoughts.items" :pagination="thoughtPagination" @update:page="loadThoughts" :scroll-x="700" />
          </n-tab-pane>
          <n-tab-pane name="heartbeats" tab="心跳日志">
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
              <n-data-table :columns="heartbeatColumns" :data="heartbeats.items" :pagination="heartbeatPagination" @update:page="loadHeartbeats" :scroll-x="800" />
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-tab-pane>

      <!-- Tab 4: 测试 -->
      <n-tab-pane name="test" tab="测试">
        <n-space vertical>
          <n-button @click="testLLMConnect" :loading="testing.llm">LLM 连通性测试</n-button>
          <n-button @click="testThought" :loading="testing.thought">想法生成测试</n-button>
        </n-space>

        <n-modal v-model:show="showTestResult" preset="card" title="测试结果" style="width: 800px">
          <pre>{{ JSON.stringify(testResult, null, 2) }}</pre>
        </n-modal>
      </n-tab-pane>
    </n-tabs>

    <!-- Session 上下文测试结果弹窗 -->
    <n-modal v-model:show="showSessionContextModal" preset="card" title="Session 上下文测试结果" style="width: 90vw; max-width: 900px">
      <template v-if="sessionContextResult">
        <n-descriptions :column="2" label-placement="left" bordered size="small" style="margin-bottom: 12px">
          <n-descriptions-item label="有内容">
            <n-tag :type="sessionContextResult.data?.has_content ? 'success' : 'warning'" size="small">
              {{ sessionContextResult.data?.has_content ? '是' : '否' }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="来源平台">
            {{ sessionContextResult.data?.session_config?.sources?.join(', ') || '未配置' }}
          </n-descriptions-item>
          <n-descriptions-item label="时间范围">
            {{ sessionContextResult.data?.session_config?.time_range_hours || 24 }} 小时
          </n-descriptions-item>
          <n-descriptions-item label="最大消息数">
            {{ sessionContextResult.data?.session_config?.max_messages_per_session || 15 }}
          </n-descriptions-item>
        </n-descriptions>

        <n-card title="获取到的上下文内容" size="small">
          <n-code
            :code="sessionContextResult.data?.context || '（空）'"
            language="text"
            word-wrap
          />
        </n-card>
      </template>
      <template v-else>
        <n-empty description="暂无数据" />
      </template>
    </n-modal>

    <!-- 心跳日志详情弹窗 -->
    <n-modal v-model:show="showDetailsModal" preset="card" :title="detailsTitle" style="width: 90vw; max-width: 900px">
      <template v-if="detailsData">
        <!-- 决策信息 -->
        <n-card title="决策" size="small" style="margin-bottom: 12px" v-if="detailsData.decision">
          <n-descriptions :column="2" label-placement="left" bordered size="small">
            <n-descriptions-item label="类型">
              <n-tag :type="detailsData.decision.type === 'skip' ? 'warning' : 'success'" size="small">
                {{ detailsData.decision.type }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="原因">{{ detailsData.decision.reason }}</n-descriptions-item>
          </n-descriptions>
        </n-card>

        <!-- 情绪评估 LLM 调用 -->
        <n-card title="情绪评估 LLM 调用" size="small" style="margin-bottom: 12px" v-if="detailsData.emotional_evaluation">
          <n-descriptions :column="2" label-placement="left" bordered size="small">
            <n-descriptions-item label="模型">{{ detailsData.emotional_evaluation.model }}</n-descriptions-item>
            <n-descriptions-item label="模式">{{ detailsData.emotional_evaluation.mode }}</n-descriptions-item>
            <n-descriptions-item label="温度">{{ detailsData.emotional_evaluation.temperature }}</n-descriptions-item>
            <n-descriptions-item label="最大Token">{{ detailsData.emotional_evaluation.max_tokens }}</n-descriptions-item>
            <n-descriptions-item label="耗时">{{ detailsData.emotional_evaluation.duration_ms }}ms</n-descriptions-item>
            <n-descriptions-item label="返回值">{{ detailsData.emotional_evaluation.response }}</n-descriptions-item>
            <n-descriptions-item label="错误" :span="2" v-if="detailsData.emotional_evaluation.error">
              <n-text type="error">{{ detailsData.emotional_evaluation.error }}</n-text>
            </n-descriptions-item>
          </n-descriptions>
          <n-collapse style="margin-top: 8px">
            <n-collapse-item title="Prompt 预览" name="prompt">
              <n-code :code="detailsData.emotional_evaluation.prompt_preview" language="text" />
            </n-collapse-item>
          </n-collapse>
        </n-card>

        <!-- 想法生成 LLM 调用 -->
        <n-card title="想法生成 LLM 调用" size="small" style="margin-bottom: 12px" v-if="detailsData.thought_generation">
          <n-descriptions :column="2" label-placement="left" bordered size="small">
            <n-descriptions-item label="模型">{{ detailsData.thought_generation.model }}</n-descriptions-item>
            <n-descriptions-item label="模式">{{ detailsData.thought_generation.mode }}</n-descriptions-item>
            <n-descriptions-item label="温度">{{ detailsData.thought_generation.temperature }}</n-descriptions-item>
            <n-descriptions-item label="最大Token">{{ detailsData.thought_generation.max_tokens }}</n-descriptions-item>
            <n-descriptions-item label="耗时">{{ detailsData.thought_generation.duration_ms }}ms</n-descriptions-item>
            <n-descriptions-item label="错误" :span="2" v-if="detailsData.thought_generation.error">
              <n-text type="error">{{ detailsData.thought_generation.error }}</n-text>
            </n-descriptions-item>
          </n-descriptions>
          <n-collapse style="margin-top: 8px">
            <n-collapse-item title="Prompt 预览" name="prompt">
              <n-code :code="detailsData.thought_generation.prompt_preview" language="text" />
            </n-collapse-item>
            <n-collapse-item title="LLM 响应" name="response" v-if="detailsData.thought_generation.response">
              <n-code :code="detailsData.thought_generation.response" language="text" />
            </n-collapse-item>
          </n-collapse>
        </n-card>

        <!-- 消息发送 -->
        <n-card title="消息发送" size="small" style="margin-bottom: 12px" v-if="detailsData.message_sending">
          <n-descriptions :column="1" label-placement="left" bordered size="small">
            <n-descriptions-item label="发送成功">
              <n-tag :type="detailsData.message_sending.success ? 'success' : 'error'" size="small">
                {{ detailsData.message_sending.success ? '是' : '否' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="发送内容" v-if="detailsData.message_sending.thought">
              {{ detailsData.message_sending.thought }}
            </n-descriptions-item>
          </n-descriptions>
        </n-card>

        <!-- 原始JSON -->
        <n-collapse>
          <n-collapse-item title="原始 JSON 数据" name="raw">
            <n-code :code="JSON.stringify(detailsData, null, 2)" language="json" />
          </n-collapse-item>
        </n-collapse>
      </template>
      <template v-else>
        <n-empty description="暂无详情数据" />
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { useMessage, NButton } from 'naive-ui'
import api from '../api/active_consciousness'
import mainApi from '../api'

const message = useMessage()
const activeTab = ref('config')

// 配置
const config = ref({
  enabled: false,
  llm: { mode: 'hermes', provider: 'openai', model: 'deepseek-chat', api_key: '', base_url: '' },
  active: { enabled: true, heartbeat_interval: 600, send_tag: '[凯莉主动发送]', time_format: '%H:%M', no_send_after_user_msg_minutes: 10, no_send_while_heat_above: 0.5, no_send_while_vibe_below: 0.3 },
  session: { sources: ['weixin'], time_range_hours: 24, max_messages_per_session: 15, filter_tool_messages: true },
  decision: { send_threshold: 0.6, delay_threshold: 0.3, memory_threshold: 0.1, max_per_hour: 2, max_per_day: 5 },
  hindsight: { enabled: true, base_url: 'http://localhost:8888', bank_id: 'hermes', recall_limit: 5, reflect_enabled: true, timeout: 30 },
  notify: { platform: 'weixin', chat_id: '' }
})

// 状态
const status = ref({
  enabled: false,
  heartbeat_count: 0,
  last_heartbeat_at: null,
  longing: { score: 0, level: 0, label: 'calm', last_user_msg_at: null, last_self_msg_at: null },
  chat_heat: { heat: 0, label: 'cold', recent_count: 0, recent_hours: 0, recent_user_msg_at: null },
  emotional_intensity: { intensity: 0, label: '工作' },
  today_sent_count: 0,
  hour_sent_count: 0,
  last_sent_at: null
})

// 日志
const thoughts = ref({ total: 0, items: [] })
const heartbeats = ref({ total: 0, items: [] })

// 测试
const testing = ref({ thought: false, llm: false })
const showTestResult = ref(false)
const testResult = ref(null)

// 选项
const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '自定义', value: 'custom' }
]
const platformOptions = [
  { label: '微信', value: 'weixin' },
  { label: '飞书', value: 'feishu' }
]

// 通知目标 Session 选项
const notifySessionMode = ref('latest')
const notifySessionOptions = ref([])
const loadingNotifySessions = ref(false)

async function loadNotifySessions(platform) {
  loadingNotifySessions.value = true
  try {
    const data = await mainApi.get("/sessions", {
      params: { platform, page: 1, page_size: 50, active_only: true }
    })
    notifySessionOptions.value = (data.items || []).map(s => ({
      label: `${s.title || s.id} (${s.message_count || 0} 条消息)`,
      value: s.id
    }))
  } catch (e) {
    console.error("加载 Session 列表失败:", e)
  } finally {
    loadingNotifySessions.value = false
  }
}

function onNotifyPlatformChange(platform) {
  loadNotifySessions(platform)
  // 切换平台时，如果不是指定模式，清空 chat_id
  if (notifySessionMode.value !== 'fixed') {
    config.value.notify.chat_id = ''
  }
}

// 计算属性
const longingTagType = computed(() => {
  const level = status.value.longing.level
  if (level <= 1) return 'success'
  if (level <= 2) return 'warning'
  return 'error'
})
const longingColor = computed(() => {
  const score = status.value.longing.score
  if (score < 0.3) return '#18a058'
  if (score < 0.6) return '#f0a020'
  return '#d03050'
})
const heatTagType = computed(() => {
  const heat = status.value.chat_heat.heat
  if (heat < 1) return 'success'
  if (heat < 3) return 'warning'
  return 'error'
})
const heatColor = computed(() => {
  const heat = status.value.chat_heat.heat
  if (heat < 1) return '#18a058'
  if (heat < 3) return '#f0a020'
  return '#d03050'
})
const intensityColor = computed(() => {
  const intensity = status.value.emotional_intensity.intensity
  if (intensity < 0.3) return '#18a058'
  if (intensity < 0.6) return '#f0a020'
  return '#d03050'
})

// 日志详情弹窗
const showDetailsModal = ref(false)
const detailsData = ref(null)
const detailsTitle = ref('')

function showHeartbeatDetails(row) {
  detailsTitle.value = `心跳日志 #${row.id} 详情`
  detailsData.value = row.details_parsed || null
  showDetailsModal.value = true
}

// 表格列定义
const thoughtColumns = [
  { title: '时间', key: 'created_at', width: 100, render: (row) => formatTime(row.created_at) },
  { title: '类型', key: 'type', width: 80 },
  { title: '内容', key: 'content', ellipsis: { tooltip: true } },
  { title: '强度', key: 'intensity', width: 80 },
  { title: '决策', key: 'decision', width: 80 },
  { title: '来源', key: 'recall_source', width: 100 }
]
const formatTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

const heartbeatColumns = [
  { title: '时间', key: 'created_at', width: 100, render: (row) => formatTime(row.created_at) },
  { title: '耗时(ms)', key: 'duration_ms', width: 80 },
  { title: '召回数量', key: 'recall_count', width: 70 },
  { title: '生成想法', key: 'thoughts_generated', width: 70 },
  { title: '发送消息', key: 'message_sent', width: 70 },
  {
    title: '操作',
    key: 'actions',
    width: 70,
    render(row) {
      return h(
        NButton,
        { size: 'small', type: 'info', onClick: () => showHeartbeatDetails(row) },
        { default: () => '详情' }
      )
    }
  }
]

// 分页
const thoughtPagination = ref({ page: 1, pageSize: 20, pageCount: 1 })
const heartbeatPagination = ref({ page: 1, pageSize: 20, pageCount: 1 })

// 加载数据
const loadConfig = async () => {
  try {
    const data = await api.getConfig()
    config.value = data
  } catch (e) {
    message.error('加载配置失败')
  }
}
const loadStatus = async () => {
  try {
    const data = await api.getStatus()
    status.value = data
  } catch (e) {
    message.error('加载状态失败')
  }
}
const loadThoughts = async (page = 1) => {
  try {
    const data = await api.getThoughts(page)
    thoughts.value = data
    thoughtPagination.value.page = page
    thoughtPagination.value.pageCount = Math.ceil(data.total / 20)
  } catch (e) {
    message.error('加载念头日志失败')
  }
}
const loadHeartbeats = async (page = 1) => {
  try {
    const data = await api.getHeartbeats(page)
    // 解析details JSON
    data.items = (data.items || []).map(item => {
      if (item.details && typeof item.details === 'string') {
        try {
          item.details_parsed = JSON.parse(item.details)
        } catch (e) {
          item.details_parsed = null
        }
      } else {
        item.details_parsed = item.details || null
      }
      return item
    })
    heartbeats.value = data
    heartbeatPagination.value.page = page
    heartbeatPagination.value.pageCount = Math.ceil(data.total / 20)
  } catch (e) {
    message.error('加载心跳日志失败')
  }
}

// 保存配置
const saving = ref(false)
const saveConfig = async () => {
  saving.value = true
  try {
    await api.saveConfig(config.value)
    message.success('配置已保存')
  } catch (e) {
    message.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

// 测试功能
const testLLMConnect = async () => {
  testing.value.llm = true
  try {
    const result = await api.testLLMConnect()
    testResult.value = result
    showTestResult.value = true
  } catch (e) {
    message.error('LLM 测试失败')
  } finally {
    testing.value.llm = false
  }
}

const testThought = async () => {
  testing.value.thought = true
  try {
    const result = await api.testThoughtGeneration()
    testResult.value = result
    showTestResult.value = true
  } catch (e) {
    message.error('测试失败')
  } finally {
    testing.value.thought = false
  }
}

const testingSessionContext = ref(false)
const showSessionContextModal = ref(false)
const sessionContextResult = ref(null)

const testSessionContext = async () => {
  testingSessionContext.value = true
  try {
    const result = await api.testSessionContext()
    sessionContextResult.value = result
    showSessionContextModal.value = true
  } catch (e) {
    message.error('获取 Session 上下文失败')
  } finally {
    testingSessionContext.value = false
  }
}

// 初始化
onMounted(async () => {
  await Promise.all([
    loadConfig(),
    loadStatus(),
    loadThoughts(),
    loadHeartbeats(),
    loadNotifySessions(config.value.notify.platform).then(() => {
      // 如果 chat_id 为空或不在列表中，切换到 latest 模式
      if (!config.value.notify.chat_id || !notifySessionOptions.value.find(s => s.value === config.value.notify.chat_id)) {
        notifySessionMode.value = 'latest'
      } else {
        notifySessionMode.value = 'fixed'
      }
    }),
  ])
})
</script>

<style scoped>
.active-consciousness-page {
  padding: 0;
}
</style>

<style>
/* 分页居中 */
.n-data-table__pagination {
  justify-content: center !important;
}
</style>
