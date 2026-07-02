<template>
  <div class="free-consciousness-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 状态 & 配置 -->
      <n-tab-pane name="status" tab="状态 & 配置">
        <!-- 开关卡片 -->
        <n-card size="small" style="margin-bottom: 16px">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span :class="['breathing-dot', status.enabled ? 'dot-green' : 'dot-gray']"></span>
              <span style="font-size: 16px; font-weight: 600;">
                自由意识 {{ status.enabled ? '运行中' : '已停止' }}
              </span>
            </div>
            <n-switch v-model:value="status.enabled" @update:value="onToggle" />
          </div>
        </n-card>

        <!-- 状态信息 -->
        <n-grid :cols="isMobile ? 1 : 3" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-card size="small" title="总轮次">
              <n-statistic :value="status.total_rounds ?? 0" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="上次沉思">
              <div style="font-size: 14px; color: var(--theme-text-secondary);">
                {{ status.last_run_at ? formatTime(status.last_run_at) : '—' }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="下次沉思">
              <div style="font-size: 14px; color: var(--theme-text-secondary);">
                {{ status.next_run_at ? formatTime(status.next_run_at) : '—' }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="思考链 Token 数">
              <n-statistic :value="status.chain_tokens ?? 0" />
            </n-card>
          </n-grid-item>
          <n-grid-item :span="isMobile ? 1 : 2">
            <n-card size="small" title="积淀信息">
              <div style="font-size: 13px; color: var(--theme-text-secondary); white-space: pre-wrap; word-break: break-all;">
                {{ status.sediment_info || '—' }}
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>

        <!-- 操作按钮 -->
        <n-space style="margin-top: 16px;">
          <n-button type="primary" @click="onManualRun" :loading="running">
            手动触发沉思
          </n-button>
          <n-button @click="onRestart" :loading="restarting">
            重启
          </n-button>
        </n-space>

        <!-- LLM 配置面板 -->
        <n-card title="LLM 配置" size="small" style="margin-top: 16px;">
          <n-grid :cols="isMobile ? 1 : 2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="Provider">
                <n-select v-model:value="config.llm_provider" :options="providerOptions" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="Model">
                <n-input v-model:value="config.llm_model" placeholder="model name" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="API Key">
                <n-input v-model:value="config.llm_api_key" placeholder="输入 API Key" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="Base URL">
                <n-input v-model:value="config.llm_base_url" placeholder="https://api.openai.com/v1" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="Max Tokens">
                <n-input-number v-model:value="config.llm_max_tokens" :min="256" :max="128000" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="Temperature">
                <n-input-number v-model:value="config.llm_temperature" :min="0" :max="2" :step="0.1" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-button size="small" @click="onTestLlm" :loading="testingLlm" style="margin-top: 8px;">
            测试连接
          </n-button>
          <n-alert v-if="llmTestResult !== null" :type="llmTestResult ? 'success' : 'error'" style="margin-top: 8px;" closable @close="llmTestResult = null">
            {{ llmTestResult ? 'LLM 连通成功' : 'LLM 连通失败' }}
          </n-alert>
        </n-card>

        <!-- 沉思参数面板 -->
        <n-card title="沉思参数" size="small" style="margin-top: 16px;">
          <n-grid :cols="isMobile ? 1 : 2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="沉思间隔（分钟）">
                <n-input-number v-model:value="config.interval_minutes" :min="1" :max="1440" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="最近轮次">
                <n-input-number v-model:value="config.recent_rounds" :min="1" :max="100" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="中间轮次">
                <n-input-number v-model:value="config.mid_rounds" :min="0" :max="50" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="积淀压缩间隔">
                <n-input-number v-model:value="config.sediment_compress_interval" :min="1" :max="100" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-card>

        <!-- 可选配置 -->
        <n-card title="可选配置" size="small" style="margin-top: 16px;">
          <n-form-item label="包含上下文">
            <n-switch v-model:value="config.include_context" />
          </n-form-item>
          <n-form-item label="上下文消息条数">
            <n-input-number v-model:value="config.context_limit" :min="5" :max="100" />
          </n-form-item>
          <n-form-item label="存储到 Hindsight">
            <n-switch v-model:value="config.store_to_hindsight" />
          </n-form-item>
          <n-form-item label="Persona（沉思风格）">
            <n-input v-model:value="config.persona" type="textarea" :rows="2" placeholder="如：用第一人称自言自语，像一个安静的少女在深夜写日记" />
          </n-form-item>
        </n-card>

        <!-- 提示词配置 -->
        <n-card title="提示词配置" size="small" style="margin-top: 16px;">
          <n-form-item label="System Prompt（支持 {persona} {chain_text} 占位符）">
            <n-input v-model:value="config.prompts_system" type="textarea" :rows="6" placeholder="沉思的系统提示词" />
          </n-form-item>
          <n-form-item label="User Prompt">
            <n-input v-model:value="config.prompts_user" type="textarea" :rows="4" placeholder="沉思的用户提示词" />
          </n-form-item>
          <n-button type="primary" @click="onSaveConfig" :loading="saving" style="margin-top: 8px;">
            保存配置
          </n-button>
        </n-card>
      </n-tab-pane>

      <!-- Tab 2: 沉思日志 -->
      <n-tab-pane name="logs" tab="沉思日志">
        <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
          <n-input-number v-model:value="logFilter.round" placeholder="轮次筛选" clearable
            :show-button="false" style="width: 140px"
            @update:value="loadLogs(1)" />
          <n-button size="small" quaternary @click="logFilter.round = null; loadLogs(1)">全部</n-button>
        </div>
        <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
          <n-data-table :columns="logColumns" :data="logs.items" :pagination="logPagination"
            @update:page="loadLogs" :scroll-x="900" remote />
        </div>
      </n-tab-pane>
    </n-tabs>

    <!-- 日志详情弹窗 -->
    <n-modal v-model:show="showLogDetail" preset="card" title="沉思详情" style="width: 90%; max-width: 700px;">
      <template v-if="logDetail">
        <n-tabs type="line" animated>
          <n-tab-pane name="thinking" tab="思考过程">
            <div style="white-space: pre-wrap; line-height: 1.8; font-size: 14px; padding: 8px 0;">{{ logDetail.thinking || '（无）' }}</div>
          </n-tab-pane>
          <n-tab-pane name="summary" tab="摘要 & 发现">
            <div style="margin-bottom: 12px;">
              <div style="font-weight: 600; margin-bottom: 4px; color: var(--theme-text-secondary);">摘要</div>
              <div style="white-space: pre-wrap; line-height: 1.6;">{{ logDetail.summary || '（无）' }}</div>
            </div>
            <n-divider />
            <div>
              <div style="font-weight: 600; margin-bottom: 4px; color: var(--theme-text-secondary);">发现</div>
              <div style="white-space: pre-wrap; line-height: 1.6;">{{ logDetail.discovery || '（无）' }}</div>
            </div>
          </n-tab-pane>
          <n-tab-pane name="llm" tab="LLM 详情">
            <template v-if="logDetail.llm_details">
              <!-- 基本信息 -->
              <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;">
                <n-descriptions-item label="模型">{{ logDetail.llm_details.model || '—' }}</n-descriptions-item>
                <n-descriptions-item label="耗时">{{ logDetail.llm_details.duration ? logDetail.llm_details.duration + 's' : '—' }}</n-descriptions-item>
                <n-descriptions-item label="成功">{{ logDetail.llm_details.success ? '是' : '否' }}</n-descriptions-item>
                <n-descriptions-item label="消息">{{ logDetail.llm_details.message || '—' }}</n-descriptions-item>
              </n-descriptions>
              <!-- Prompt -->
              <div v-if="logDetail.llm_details.prompt_sent" style="margin-bottom: 12px;">
                <div style="font-weight: 600; margin-bottom: 4px;">Prompt</div>
                <n-collapse>
                  <n-collapse-item v-for="(msg, i) in logDetail.llm_details.prompt_sent" :key="i" :title="msg.role" :name="i">
                    <n-code :code="msg.content" language="text" word-wrap style="font-size: 12px;" />
                  </n-collapse-item>
                </n-collapse>
              </div>
              <!-- LLM 原始返回 -->
              <div v-if="logDetail.llm_details.response_raw" style="margin-bottom: 12px;">
                <div style="font-weight: 600; margin-bottom: 4px;">LLM 原始返回</div>
                <n-code :code="logDetail.llm_details.response_raw" language="text" word-wrap style="font-size: 12px;" />
              </div>
              <!-- 推理过程 -->
              <div v-if="logDetail.llm_details.reasoning_content">
                <div style="font-weight: 600; margin-bottom: 4px;">推理过程</div>
                <n-code :code="logDetail.llm_details.reasoning_content" language="text" word-wrap style="font-size: 12px;" />
              </div>
            </template>
            <div v-else style="color: var(--theme-text-muted);">无 LLM 详情</div>
          </n-tab-pane>
        </n-tabs>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import { NTag, NButton, NSpace } from 'naive-ui'
import api from '../api/freeConsciousness'

const message = useMessage()
const activeTab = ref('status')

// 移动端检测
const isMobile = computed(() => window.innerWidth <= 768)

// 状态
const status = reactive({
  enabled: false,
  running: false,
  total_rounds: 0,
  last_run_at: null,
  next_run_at: null,
  chain_tokens: 0,
  sediment_info: '',
  interval_minutes: 30,
})

// 配置
const config = reactive({
  llm_provider: 'openai',
  llm_model: '',
  llm_api_key: '',
  llm_base_url: '',
  llm_max_tokens: 4096,
  llm_temperature: 0.7,
  interval_minutes: 60,
  recent_rounds: 10,
  mid_rounds: 3,
  sediment_compress_interval: 10,
  include_context: true,
  context_limit: 20,
  store_to_hindsight: true,
  persona: '',
  prompts_system: '',
  prompts_user: '',
})

// Provider 选项
const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: '自定义', value: 'custom' },
]

// 操作状态
const running = ref(false)
const restarting = ref(false)
const saving = ref(false)
const testingLlm = ref(false)
const llmTestResult = ref(null)

// 日志
const logs = reactive({ total: 0, items: [] })
const logFilter = reactive({ round: null })
const logPage = ref(1)
const showLogDetail = ref(false)
const logDetail = ref(null)

const logPagination = computed(() => ({
  page: logPage.value,
  pageSize: 20,
  pageCount: Math.ceil(logs.total / 20) || 1,
  showSizePicker: false,
}))

// 日志表格列
const logColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '轮次', key: 'round_number', width: 70 },
  {
    title: '摘要',
    key: 'summary',
    ellipsis: { tooltip: true },
    width: 180,
    render: (row) => {
      const s = row.summary || '—'
      return h('span', { style: 'max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-block; vertical-align: middle;' }, s)
    },
  },
  {
    title: '发现',
    key: 'discovery',
    width: 160,
    ellipsis: { tooltip: true },
    render: (row) => {
      if (row.discovery) {
        return h('span', { style: 'max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-block; vertical-align: middle;' }, row.discovery)
      }
      return '—'
    },
  },
  { title: 'Token', key: 'thinking_tokens', width: 70 },
  {
    title: '时间',
    key: 'created_at',
    width: 140,
    render: (row) => formatTime(row.created_at),
  },
  {
    title: '操作',
    key: 'actions',
    width: 130,
    fixed: 'right',
    render: (row) => {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'tiny', onClick: () => viewLogDetail(row.id) }, { default: () => '详情' }),
          h(NButton, { size: 'tiny', type: 'error', onClick: () => deleteLog(row.id) }, { default: () => '删除' }),
        ],
      })
    },
  },
]

// 格式化时间
function formatTime(t) {
  if (!t) return '—'
  try {
    const d = new Date(t)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return t
  }
}

// 加载数据
async function loadStatus() {
  try {
    const data = await api.getStatus()
    status.enabled = data.enabled ?? false
    status.running = data.running ?? false
    status.total_rounds = data.total_rounds ?? 0
    status.chain_tokens = data.chain_tokens ?? 0
    status.interval_minutes = data.interval_minutes ?? 30
    // latest_round 映射
    status.last_run_at = data.latest_round?.created_at || null
    // 计算下次沉思时间
    if (data.latest_round?.created_at) {
      const last = new Date(data.latest_round.created_at)
      last.setMinutes(last.getMinutes() + (data.interval_minutes || 30))
      status.next_run_at = last.toISOString()
    }
    // 积淀信息
    if (data.sediment) {
      status.sediment_info = `覆盖第 ${data.sediment.source_rounds} 轮，${data.sediment.source_count} 轮压缩`
    } else {
      status.sediment_info = ''
    }
  } catch (e) {
    // 静默
  }
}

async function loadConfig() {
  try {
    const data = await api.getConfig()
    // 后端返回嵌套结构 {llm: {provider, model, ...}}，前端用扁平 key
    config.llm_provider = data.llm?.provider || ''
    config.llm_model = data.llm?.model || ''
    config.llm_api_key = data.llm?.api_key || ''
    config.llm_base_url = data.llm?.base_url || ''
    config.llm_max_tokens = data.llm?.max_tokens ?? 2000
    config.llm_temperature = data.llm?.temperature ?? 0.8
    config.interval_minutes = data.interval_minutes ?? 30
    config.recent_rounds = data.recent_rounds ?? 3
    config.mid_rounds = data.mid_rounds ?? 17
    config.sediment_compress_interval = data.sediment_compress_interval ?? 10
    config.include_context = data.include_context ?? false
    config.context_limit = data.context_limit ?? 20
    config.store_to_hindsight = data.store_to_hindsight ?? false
    config.persona = data.persona || ''
    config.prompts_system = data.prompts?.system || ''
    config.prompts_user = data.prompts?.user || ''
  } catch (e) {
    // 静默
  }
}

async function loadLogs(page = 1) {
  logPage.value = page
  try {
    const params = { page, page_size: 20 }
    if (logFilter.round != null && logFilter.round !== '') params.round = logFilter.round
    const data = await api.getLogs(params)
    logs.total = data.total ?? 0
    logs.items = data.items ?? []
  } catch (e) {
    message.error('加载日志失败')
  }
}

// 操作
async function onToggle(enabled) {
  try {
    await api.toggle(enabled)
    message.success(enabled ? '已开启' : '已关闭')
    await loadStatus()
  } catch (e) {
    message.error('操作失败')
    status.enabled = !enabled
  }
}

async function onManualRun() {
  running.value = true
  try {
    await api.manualRun()
    message.success('沉思已触发')
    await loadStatus()
  } catch (e) {
    message.error('触发失败')
  } finally {
    running.value = false
  }
}

async function onRestart() {
  restarting.value = true
  try {
    await api.restart()
    message.success('已重启')
    await loadStatus()
  } catch (e) {
    message.error('重启失败')
  } finally {
    restarting.value = false
  }
}

async function onTestLlm() {
  testingLlm.value = true
  llmTestResult.value = null
  try {
    await api.testLlm()
    llmTestResult.value = true
  } catch (e) {
    llmTestResult.value = false
  } finally {
    testingLlm.value = false
  }
}

async function onSaveConfig() {
  saving.value = true
  try {
    // 前端用扁平 key，后端需要嵌套结构
    const payload = {
      llm: {
        mode: 'custom',
        provider: config.llm_provider,
        model: config.llm_model,
        api_key: config.llm_api_key,
        base_url: config.llm_base_url,
        max_tokens: config.llm_max_tokens,
        temperature: config.llm_temperature,
      },
      interval_minutes: config.interval_minutes,
      recent_rounds: config.recent_rounds,
      mid_rounds: config.mid_rounds,
      sediment_compress_interval: config.sediment_compress_interval,
      include_context: config.include_context,
      context_limit: config.context_limit,
      store_to_hindsight: config.store_to_hindsight,
      persona: config.persona,
      prompts: {
        system: config.prompts_system,
        user: config.prompts_user,
      },
    }
    await api.saveConfig(payload)
    message.success('配置已保存')
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function viewLogDetail(id) {
  try {
    const data = await api.getLogDetail(id)
    logDetail.value = data
    showLogDetail.value = true
  } catch (e) {
    message.error('加载详情失败')
  }
}

async function deleteLog(id) {
  try {
    await api.deleteLog(id)
    message.success('已删除')
    await loadLogs(logPage.value)
  } catch (e) {
    message.error('删除失败')
  }
}

// 初始化并行加载
onMounted(() => {
  Promise.all([loadStatus(), loadConfig(), loadLogs()])
})
</script>

<style scoped>
.free-consciousness-page {
  max-width: 1200px;
}

.breathing-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-green {
  background: #18a058;
  box-shadow: 0 0 8px rgba(24, 160, 88, 0.6);
  animation: pulse 2s infinite;
}

.dot-gray {
  background: #999;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
