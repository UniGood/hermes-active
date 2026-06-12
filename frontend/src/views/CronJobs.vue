<template>
  <div class="cron-page">
    <!-- 创建任务按钮 -->
    <n-space style="margin-bottom: 16px">
      <n-button type="primary" @click="openCreate">
        + 创建任务
      </n-button>
      <n-button @click="openDefaultPrompts">
        默认提示词配置
      </n-button>
    </n-space>

    <!-- 任务列表 -->
    <n-spin :show="loading">
      <div class="job-list">
        <div v-for="job in jobs" :key="job.id" class="job-card">
          <div class="job-header">
            <span class="job-name">{{ job.name }}</span>
            <n-switch :value="job.enabled" @update:value="toggleJob(job)" />
          </div>
          <div class="job-meta">
            <span>调度: {{ job.schedule }}</span>
            <span>平台: {{ job.platform || 'weixin' }}</span>
            <span v-if="job.session_id">指定 Session: {{ job.session_id }}</span>
            <span v-else>获取方式: 最新活跃</span>
            <span>LLM: {{ job.use_llm ? '是' : '否' }}</span>
            <span>写入DB: {{ job.write_to_db ? '是' : '否' }}</span>
            <span>带标记: {{ job.with_mark ? '是' : '否' }}</span>
          </div>
          <div class="job-meta" v-if="job.last_run_at">
            <span>上次运行: {{ formatTime(job.last_run_at) }}</span>
          </div>
          <div class="job-actions">
            <n-button size="small" @click="runJob(job)" :loading="job.running">运行</n-button>
            <n-button size="small" @click="editJob(job)">编辑</n-button>
            <n-button size="small" type="error" @click="deleteJob(job)">删除</n-button>
          </div>
        </div>
        <n-empty v-if="!loading && jobs.length === 0" description="暂无定时任务" />
      </div>
    </n-spin>

    <!-- 创建/编辑任务弹窗 -->
    <n-modal v-model:show="showCreate" preset="card" :title="editingJob ? '编辑任务' : '创建任务'" fullscreen>
      <n-form label-placement="left" label-width="120">
        <n-form-item label="任务名称">
          <n-input v-model:value="formData.name" placeholder="主动消息" />
        </n-form-item>
        <n-form-item label="调度表达式">
          <n-input v-model:value="formData.schedule" placeholder="0,20,40 6-23 * * *" @update:value="parseCron" />
        </n-form-item>
        <n-form-item label=" " v-if="cronParseResult">
          <div class="cron-parse-result">
            <div class="cron-freq">频率: {{ cronParseResult.frequency }}</div>
            <div class="cron-next-runs" v-if="cronParseResult.next_runs && cronParseResult.next_runs.length">
              <div class="cron-next-title">未来运行时间：</div>
              <div v-for="(run, idx) in cronParseResult.next_runs" :key="idx" class="cron-next-item">
                {{ idx + 1 }}. {{ run }}
              </div>
            </div>
          </div>
        </n-form-item>
        <n-form-item label="目标平台">
          <n-select
            v-model:value="formData.platform"
            :options="platformOptions"
            placeholder="选择平台"
          />
        </n-form-item>
        <n-form-item label="Session 获取方式">
          <n-radio-group v-model:value="sessionMode">
            <n-space vertical>
              <n-radio value="latest">每次获取最新活跃 Session</n-radio>
              <n-radio value="fixed">指定 Session</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="指定 Session" v-if="sessionMode === 'fixed'">
          <n-select
            v-model:value="formData.session_id"
            :options="sessionOptions"
            placeholder="选择 session"
            filterable
          />
        </n-form-item>
        <!-- 系统提示词 -->
        <n-divider title-placement="left">提示词配置</n-divider>
        <n-form-item label="系统提示词">
          <n-space vertical style="width: 100%">
            <n-input
              v-model:value="formData.system_prompt"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 8 }"
              placeholder="系统提示词，定义 AI 的角色和行为规则"
            />
            <n-space align="center">
              <n-checkbox v-model:checked="formData.append_soul_md">
                拼接 soul.md
              </n-checkbox>
              <span style="font-size: 12px; color: #999">
                {{ formData.append_soul_md ? '将在系统提示词后追加 SOUL.md 内容' : '不追加 SOUL.md' }}
              </span>
            </n-space>
            <n-button size="small" @click="fillDefaultSystemPrompt" style="margin-top: 4px">
              填充默认系统提示词
            </n-button>
          </n-space>
        </n-form-item>

        <!-- 用户提示词 -->
        <n-form-item label="用户提示词">
          <n-space vertical style="width: 100%">
            <n-input
              v-model:value="formData.user_prompt"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 8 }"
              placeholder="生成提示词，支持 {context} 占位符"
            />
            <div style="font-size: 12px; color: #999">
              支持 {context} 占位符，运行时替换为实际上下文
            </div>
            <n-button size="small" @click="fillDefaultUserPrompt" style="margin-top: 4px">
              填充默认用户提示词
            </n-button>
            <!-- 上下文配置状态 -->
            <div class="context-status">
              <span class="context-status-label">当前上下文配置：</span>
              <n-tag size="small" type="info">Session: {{ contextConfig.session_limit }} 条</n-tag>
              <n-tag v-if="contextConfig.hindsight_recall_enabled" size="small" type="success">
                Recall: {{ contextConfig.hindsight_recall_query || '已启用' }}
              </n-tag>
              <n-tag v-if="contextConfig.hindsight_reflect_enabled" size="small" type="warning">
                Reflect: {{ contextConfig.hindsight_reflect_query || '已启用' }}
              </n-tag>
              <n-tag v-if="!contextConfig.hindsight_recall_enabled && !contextConfig.hindsight_reflect_enabled" size="small">
                仅 Session 上下文
              </n-tag>
            </div>
          </n-space>
        </n-form-item>

        <!-- 上下文配置 -->
        <n-divider title-placement="left">上下文配置</n-divider>
        <n-form-item label="Session 上下文">
          <n-space vertical style="width: 100%">
            <n-space align="center">
              <span style="font-size: 13px; color: #666">读取条数：</span>
              <n-input-number
                v-model:value="contextConfig.session_limit"
                :min="1"
                :max="100"
                size="small"
                style="width: 120px"
              />
            </n-space>
          </n-space>
        </n-form-item>
        <n-form-item label="Hindsight Recall">
          <n-space vertical style="width: 100%">
            <n-space align="center">
              <n-switch v-model:value="contextConfig.hindsight_recall_enabled" />
              <span style="font-size: 13px; color: #666">启用 Recall 记忆检索</span>
            </n-space>
            <template v-if="contextConfig.hindsight_recall_enabled">
              <n-space align="center">
                <span style="font-size: 13px; color: #666">关键词：</span>
                <n-input
                  v-model:value="contextConfig.hindsight_recall_query"
                  placeholder="搜索关键词"
                  size="small"
                  style="width: 300px"
                />
                <span style="font-size: 13px; color: #666">数量：</span>
                <n-input-number
                  v-model:value="contextConfig.hindsight_recall_limit"
                  :min="1"
                  :max="50"
                  size="small"
                  style="width: 100px"
                />
              </n-space>
            </template>
          </n-space>
        </n-form-item>
        <n-form-item label="Hindsight Reflect">
          <n-space vertical style="width: 100%">
            <n-space align="center">
              <n-switch v-model:value="contextConfig.hindsight_reflect_enabled" />
              <span style="font-size: 13px; color: #666">启用 Reflect 综合分析</span>
            </n-space>
            <template v-if="contextConfig.hindsight_reflect_enabled">
              <n-space align="center">
                <span style="font-size: 13px; color: #666">问题：</span>
                <n-input
                  v-model:value="contextConfig.hindsight_reflect_query"
                  placeholder="要分析的问题"
                  size="small"
                  style="width: 400px"
                />
              </n-space>
            </template>
          </n-space>
        </n-form-item>
        <n-form-item label="使用 LLM">
          <n-switch v-model:value="formData.use_llm" />
          <span style="margin-left: 8px; color: #999; font-size: 13px">
            {{ formData.use_llm ? '使用 LLM 生成消息' : '直接使用提示词作为消息' }}
          </span>
        </n-form-item>
        <n-form-item label="写入 DB">
          <n-switch v-model:value="formData.write_to_db" />
          <span style="margin-left: 8px; color: #999; font-size: 13px">
            {{ formData.write_to_db ? '消息写入 session 数据库' : '仅发送不写入' }}
          </span>
        </n-form-item>
        <n-form-item label="带标记">
          <n-switch v-model:value="formData.with_mark" :disabled="!formData.write_to_db" />
          <span style="margin-left: 8px; color: #999; font-size: 13px">
            {{ formData.with_mark ? '消息带标记前缀' : '不带标记' }}
          </span>
        </n-form-item>
        <n-form-item label="标记格式" v-if="formData.with_mark && formData.write_to_db">
          <n-input v-model:value="formData.mark_format" placeholder="[凯莉主动发送] {timestamp}: {content}" />
          <div style="font-size: 12px; color: #999; margin-top: 4px">
            支持占位符: {timestamp} {content}
          </div>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showCreate = false">取消</n-button>
          <n-button @click="previewPrompt" :loading="previewing">预览提示词</n-button>
          <n-button type="primary" @click="saveJob" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 默认提示词配置弹窗 -->
    <n-modal v-model:show="showDefaultPrompts" preset="card" title="默认提示词配置" fullscreen>
      <n-form label-placement="left" label-width="120">
        <n-form-item label="默认系统提示词">
          <n-input
            v-model:value="defaultPromptsData.system_prompt"
            type="textarea"
            :autosize="{ minRows: 5, maxRows: 15 }"
            placeholder="系统提示词，定义 AI 的角色和行为规则"
          />
        </n-form-item>
        <n-form-item label="默认用户提示词">
          <n-input
            v-model:value="defaultPromptsData.user_prompt"
            type="textarea"
            :autosize="{ minRows: 5, maxRows: 15 }"
            placeholder="用户提示词模板，支持 {context} 占位符"
          />
        </n-form-item>
        <n-form-item label="拼接 soul.md">
          <n-checkbox v-model:checked="defaultPromptsData.append_soul_md">
            创建新任务时默认拼接 soul.md
          </n-checkbox>
        </n-form-item>
        <n-form-item label=" ">
          <n-button @click="previewDefaultPrompt" :loading="previewingDefault">
            预览完整提示词
          </n-button>
        </n-form-item>
        <!-- 预览结果 -->
        <template v-if="defaultPromptPreview">
          <n-divider title-placement="left">预览结果</n-divider>
          <n-form-item label="系统提示词（最终版）">
            <n-input
              :value="defaultPromptPreview.system_prompt"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 10 }"
              readonly
            />
          </n-form-item>
          <n-form-item label="用户提示词">
            <n-input
              :value="defaultPromptPreview.user_prompt"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 5 }"
              readonly
            />
          </n-form-item>
          <n-form-item label="soul.md 内容" v-if="defaultPromptPreview.soul_md">
            <n-input
              :value="defaultPromptPreview.soul_md"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 10 }"
              readonly
            />
          </n-form-item>
        </template>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showDefaultPrompts = false">取消</n-button>
          <n-button type="primary" @click="saveDefaultPrompts" :loading="savingDefaultPrompts">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 预览提示词弹窗 -->
    <n-modal v-model:show="showPreview" preset="card" title="预览最终提示词" style="width: 700px">
      <n-spin :show="previewing">
        <n-form label-placement="left" label-width="100">
          <n-form-item label="系统提示词">
            <n-input
              :value="previewData.system_prompt"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 10 }"
              readonly
            />
          </n-form-item>
          <n-form-item label="用户提示词">
            <n-input
              :value="previewData.user_prompt"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 5 }"
              readonly
            />
          </n-form-item>
          <n-form-item label="soul.md" v-if="previewData.soul_md">
            <n-input
              :value="previewData.soul_md"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 8 }"
              readonly
            />
          </n-form-item>
          <n-form-item label="上下文配置" v-if="previewData.context_summary">
            <n-tag type="info">{{ previewData.context_summary }}</n-tag>
          </n-form-item>
        </n-form>
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import api from '../api'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const saving = ref(false)
const showCreate = ref(false)
const jobs = ref([])
const editingJob = ref(null)
const sessionOptions = ref([])
const cronParseResult = ref(null)
const defaultPrompt = ref('')
const soulMdContent = ref('')
const sessionMode = ref('latest')

// 默认提示词配置
const showDefaultPrompts = ref(false)
const defaultPromptsData = ref({
  system_prompt: '',
  user_prompt: '',
  append_soul_md: true
})
const defaultPromptPreview = ref(null)
const savingDefaultPrompts = ref(false)
const previewingDefault = ref(false)

// 预览提示词
const showPreview = ref(false)
const previewData = ref({ system_prompt: '', user_prompt: '', soul_md: '', context_summary: '' })
const previewing = ref(false)

const platformOptions = [
  { label: '微信', value: 'weixin' },
  { label: '飞书', value: 'feishu' },
  { label: 'CLI', value: 'cli' }
]

const formData = ref({
  name: '',
  schedule: '0,20,40 6-23 * * *',
  prompt: '',
  system_prompt: '',
  user_prompt: '',
  append_soul_md: true,
  session_id: null,
  platform: 'weixin',
  use_llm: true,
  write_to_db: true,
  with_mark: true,
  mark_format: '[凯莉主动发送] {timestamp}: {content}'
})

// 上下文配置
const contextConfig = ref({
  session_limit: 20,
  hindsight_recall_enabled: false,
  hindsight_recall_query: '',
  hindsight_recall_limit: 10,
  hindsight_reflect_enabled: false,
  hindsight_reflect_query: ''
})

// 监听平台变化，重新加载 session 列表
watch(() => formData.value.platform, (newPlatform) => {
  if (showCreate.value) {
    loadSessions(newPlatform)
  }
})

// 监听 sessionMode 变化
watch(sessionMode, (newMode) => {
  if (newMode === 'latest') {
    formData.value.session_id = null
  }
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

async function loadJobs() {
  loading.value = true
  try {
    const data = await api.get('/cron')
    jobs.value = (data.items || []).map(j => ({ ...j, running: false }))
  } catch (e) {
    console.error('加载任务失败:', e)
  } finally {
    loading.value = false
  }
}

async function loadSessions(platform = 'weixin') {
  try {
    const data = await api.get('/cron/sessions', { params: { platform } })
    sessionOptions.value = (data.items || []).map(s => ({
      label: `${s.title || s.id} (${s.message_count || 0} 条消息)`,
      value: s.id
    }))
  } catch (e) {
    console.error('加载 sessions 失败:', e)
  }
}

async function loadDefaultPrompt() {
  try {
    const data = await api.get('/config/prompts')
    defaultPrompt.value = data.system || ''
  } catch (e) {
    console.error('加载默认提示词失败:', e)
  }
}

async function loadSoulMd() {
  try {
    const data = await api.get('/config/hermes/soul')
    soulMdContent.value = data.content || ''
  } catch (e) {
    console.error('加载 SOUL.md 失败:', e)
  }
}

function fillDefaultSystemPrompt() {
  if (defaultPrompt.value) {
    formData.value.system_prompt = defaultPrompt.value
    message.success('已填充默认系统提示词')
  } else {
    message.warning('未找到默认提示词')
  }
}

function fillDefaultUserPrompt() {
  formData.value.user_prompt = '{context}'
  message.success('已填充默认用户提示词')
}

let cronParseTimer = null
function parseCron() {
  if (cronParseTimer) clearTimeout(cronParseTimer)
  cronParseTimer = setTimeout(async () => {
    const expr = formData.value.schedule.trim()
    if (!expr) {
      cronParseResult.value = null
      return
    }
    try {
      const result = await api.get('/cron/parse-cron', { params: { expression: expr } })
      if (result.success) {
        cronParseResult.value = result
      } else {
        cronParseResult.value = { frequency: result.message || '解析失败', next_runs: [] }
      }
    } catch (e) {
      cronParseResult.value = { frequency: '解析失败', next_runs: [] }
    }
  }, 500)
}

function openCreate() {
  editingJob.value = null
  formData.value = {
    name: '',
    schedule: '0,20,40 6-23 * * *',
    prompt: '',
    system_prompt: '',
    user_prompt: '',
    append_soul_md: true,
    session_id: null,
    platform: 'weixin',
    use_llm: true,
    write_to_db: true,
    with_mark: true,
    mark_format: '[凯莉主动发送] {timestamp}: {content}'
  }
  contextConfig.value = {
    session_limit: 20,
    hindsight_recall_enabled: false,
    hindsight_recall_query: '',
    hindsight_recall_limit: 10,
    hindsight_reflect_enabled: false,
    hindsight_reflect_query: ''
  }
  sessionMode.value = 'latest'
  cronParseResult.value = null
  parseCron()
  loadSessions('weixin')

  // 自动填充默认提示词
  loadDefaultPromptsForNewJob()

  showCreate.value = true
}

async function loadDefaultPromptsForNewJob() {
  try {
    const data = await api.get('/config/default-prompts')
    if (data.system_prompt) {
      formData.value.system_prompt = data.system_prompt
    }
    if (data.user_prompt) {
      formData.value.user_prompt = data.user_prompt
    }
    formData.value.append_soul_md = data.append_soul_md !== false
  } catch (e) {
    // 静默失败，使用空值
    console.warn('加载默认提示词失败:', e)
  }
}

async function saveJob() {
  if (!formData.value.name || !formData.value.schedule) {
    message.warning('请填写任务名称和调度表达式')
    return
  }
  saving.value = true
  try {
    // 如果是 latest 模式，清空 session_id
    const submitData = { ...formData.value }
    if (sessionMode.value === 'latest') {
      submitData.session_id = null
    }

    // 如果使用新的 system_prompt/user_prompt 字段，将上下文配置序列化到 user_prompt 中
    if (submitData.system_prompt || submitData.user_prompt) {
      // 将上下文配置拼接到 user_prompt 中
      submitData.user_prompt = buildPromptWithContext(submitData.user_prompt || '', contextConfig.value)
      // 清空旧的 prompt 字段
      submitData.prompt = null
    } else {
      // 兼容旧的单一 prompt 字段
      submitData.prompt = buildPromptWithContext(formData.value.prompt, contextConfig.value)
    }

    if (editingJob.value) {
      await api.put(`/cron/${editingJob.value.id}`, submitData)
      message.success('任务已更新')
    } else {
      await api.post('/cron', submitData)
      message.success('任务已创建')
    }
    showCreate.value = false
    editingJob.value = null
    await loadJobs()
  } catch (e) {
    message.error('保存失败: ' + (e?.detail || '未知错误'))
  } finally {
    saving.value = false
  }
}

async function toggleJob(job) {
  try {
    await api.post(`/cron/${job.id}/toggle`)
    message.success(job.enabled ? '任务已暂停' : '任务已恢复')
    await loadJobs()
  } catch (e) {
    message.error('操作失败')
  }
}

async function runJob(job) {
  job.running = true
  try {
    await api.post(`/cron/${job.id}/run`)
    message.success('任务已触发')
  } catch (e) {
    message.error('触发失败: ' + (e?.detail || '未知错误'))
  } finally {
    job.running = false
  }
}

function editJob(job) {
  editingJob.value = job
  const rawPrompt = job.prompt || ''

  // 检查是否使用新的 system_prompt/user_prompt 字段
  if (job.system_prompt !== undefined || job.user_prompt !== undefined) {
    // 使用新字段
    const parsedUser = parseContextFromPrompt(job.user_prompt || '')
    contextConfig.value = parsedUser.config
    formData.value = {
      name: job.name,
      schedule: job.schedule,
      prompt: '',
      system_prompt: job.system_prompt || '',
      user_prompt: parsedUser.userPrompt,
      append_soul_md: job.append_soul_md !== false,
      session_id: job.session_id || null,
      platform: job.platform || 'weixin',
      use_llm: job.use_llm !== false,
      write_to_db: job.write_to_db !== false,
      with_mark: job.with_mark !== false,
      mark_format: job.mark_format || '[凯莉主动发送] {timestamp}: {content}'
    }
  } else {
    // 兼容旧的单一 prompt 字段
    const parsed = parseContextFromPrompt(rawPrompt)
    contextConfig.value = parsed.config
    formData.value = {
      name: job.name,
      schedule: job.schedule,
      prompt: parsed.userPrompt,
      system_prompt: '',
      user_prompt: '',
      append_soul_md: true,
      session_id: job.session_id || null,
      platform: job.platform || 'weixin',
      use_llm: job.use_llm !== false,
      write_to_db: job.write_to_db !== false,
      with_mark: job.with_mark !== false,
      mark_format: job.mark_format || '[凯莉主动发送] {timestamp}: {content}'
    }
  }
  sessionMode.value = job.session_id ? 'fixed' : 'latest'
  cronParseResult.value = null
  parseCron()
  loadSessions(formData.value.platform)
  showCreate.value = true
}

function deleteJob(job) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除任务 "${job.name}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.delete(`/cron/${job.id}`)
        message.success('任务已删除')
        await loadJobs()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

// ============ 默认提示词配置 ============

async function openDefaultPrompts() {
  try {
    const data = await api.get('/config/default-prompts')
    defaultPromptsData.value = {
      system_prompt: data.system_prompt || '',
      user_prompt: data.user_prompt || '',
      append_soul_md: data.append_soul_md !== false
    }
    defaultPromptPreview.value = null
    showDefaultPrompts.value = true
  } catch (e) {
    message.error('加载默认提示词配置失败')
  }
}

async function saveDefaultPrompts() {
  savingDefaultPrompts.value = true
  try {
    await api.put('/config/default-prompts', defaultPromptsData.value)
    message.success('默认提示词配置已保存')
    showDefaultPrompts.value = false
    // 重新加载默认提示词
    await loadDefaultPrompt()
  } catch (e) {
    message.error('保存失败: ' + (e?.detail || '未知错误'))
  } finally {
    savingDefaultPrompts.value = false
  }
}

async function previewDefaultPrompt() {
  previewingDefault.value = true
  try {
    const data = await api.post('/cron/preview-prompt', {
      system_prompt: defaultPromptsData.value.system_prompt,
      user_prompt: defaultPromptsData.value.user_prompt,
      append_soul_md: defaultPromptsData.value.append_soul_md,
      context_config: {}
    })
    defaultPromptPreview.value = data
  } catch (e) {
    message.error('预览失败: ' + (e?.detail || '未知错误'))
  } finally {
    previewingDefault.value = false
  }
}

// ============ 预览提示词（编辑弹窗） ============

async function previewPrompt() {
  previewing.value = true
  showPreview.value = true
  try {
    const data = await api.post('/cron/preview-prompt', {
      system_prompt: formData.value.system_prompt,
      user_prompt: formData.value.user_prompt,
      append_soul_md: formData.value.append_soul_md,
      context_config: contextConfig.value
    })
    previewData.value = data
  } catch (e) {
    message.error('预览失败: ' + (e?.detail || '未知错误'))
    showPreview.value = false
  } finally {
    previewing.value = false
  }
}

// 上下文配置序列化/反序列化
const CTX_MARKER_START = '<!--CTX:'
const CTX_MARKER_END = '-->'

function buildPromptWithContext(userPrompt, config) {
  const parts = []
  parts.push(`session_limit=${config.session_limit || 20}`)
  parts.push(`recall=${config.hindsight_recall_enabled ? 'true' : 'false'}`)
  if (config.hindsight_recall_enabled && config.hindsight_recall_query) {
    parts.push(`recall_query=${encodeURIComponent(config.hindsight_recall_query)}`)
    parts.push(`recall_limit=${config.hindsight_recall_limit || 10}`)
  }
  parts.push(`reflect=${config.hindsight_reflect_enabled ? 'true' : 'false'}`)
  if (config.hindsight_reflect_enabled && config.hindsight_reflect_query) {
    parts.push(`reflect_query=${encodeURIComponent(config.hindsight_reflect_query)}`)
  }
  const ctxLine = `${CTX_MARKER_START}${parts.join(';')}${CTX_MARKER_END}`
  return `${ctxLine}\n${userPrompt || ''}`
}

function parseContextFromPrompt(rawPrompt) {
  const defaultConfig = {
    session_limit: 20,
    hindsight_recall_enabled: false,
    hindsight_recall_query: '',
    hindsight_recall_limit: 10,
    hindsight_reflect_enabled: false,
    hindsight_reflect_query: ''
  }

  if (!rawPrompt || !rawPrompt.startsWith(CTX_MARKER_START)) {
    return { config: defaultConfig, userPrompt: rawPrompt || '' }
  }

  const endIdx = rawPrompt.indexOf(CTX_MARKER_END)
  if (endIdx === -1) {
    return { config: defaultConfig, userPrompt: rawPrompt }
  }

  const ctxStr = rawPrompt.substring(CTX_MARKER_START.length, endIdx)
  const userPrompt = rawPrompt.substring(endIdx + CTX_MARKER_END.length).trim()

  const config = { ...defaultConfig }
  const pairs = ctxStr.split(';')
  for (const pair of pairs) {
    const [key, value] = pair.split('=')
    if (!key || value === undefined) continue
    switch (key) {
      case 'session_limit':
        config.session_limit = parseInt(value) || 20
        break
      case 'recall':
        config.hindsight_recall_enabled = value === 'true'
        break
      case 'recall_query':
        config.hindsight_recall_query = decodeURIComponent(value)
        break
      case 'recall_limit':
        config.hindsight_recall_limit = parseInt(value) || 10
        break
      case 'reflect':
        config.hindsight_reflect_enabled = value === 'true'
        break
      case 'reflect_query':
        config.hindsight_reflect_query = decodeURIComponent(value)
        break
    }
  }

  return { config, userPrompt }
}

onMounted(() => {
  loadJobs()
  loadDefaultPrompt()
  loadSoulMd()
})
</script>

<style scoped>
.cron-page {
  max-width: 800px;
  margin: 0 auto;
}

.job-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.job-name {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.job-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.job-actions {
  display: flex;
  gap: 8px;
}

.cron-parse-result {
  background: #f0f9eb;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.cron-freq {
  color: #18a058;
  font-weight: 500;
  margin-bottom: 8px;
}

.cron-next-runs {
  margin-top: 4px;
}

.cron-next-title {
  color: #666;
  font-size: 12px;
  margin-bottom: 4px;
}

.cron-next-item {
  color: #333;
  font-size: 12px;
  line-height: 1.8;
  font-family: monospace;
}

.context-status {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.context-status-label {
  font-size: 12px;
  color: #666;
}
</style>
