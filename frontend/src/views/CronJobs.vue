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
            <n-button size="small" @click="viewJobLogs(job)">运行日志</n-button>
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
              <div class="cron-next-title" @click="showNextRuns = !showNextRuns" style="cursor: pointer; user-select: none;">
                未来运行时间：
                <span style="font-size: 12px; color: #999;">{{ showNextRuns ? '▼ 收起' : '▶ 展开' }}</span>
              </div>
              <template v-if="showNextRuns">
                <div v-for="(run, idx) in cronParseResult.next_runs" :key="idx" class="cron-next-item">
                  {{ idx + 1 }}. {{ run }}
                </div>
              </template>
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
              <n-tag v-if="contextConfig.session_enabled" size="small" type="info">
                Session: {{ contextConfig.session_limit }} 条{{ contextConfig.include_tool ? ' (含tool)' : '' }}
              </n-tag>
              <n-tag v-else size="small">无 Session 上下文</n-tag>
              <n-tag v-if="contextConfig.hindsight_recall_enabled" size="small" type="success">
                Recall: {{ contextConfig.hindsight_recall_query || '已启用' }}
              </n-tag>
              <n-tag v-if="contextConfig.hindsight_reflect_enabled" size="small" type="warning">
                Reflect: {{ contextConfig.hindsight_reflect_query || '已启用' }}
              </n-tag>
              <n-tag v-if="contextConfig.session_enabled && !contextConfig.hindsight_recall_enabled && !contextConfig.hindsight_reflect_enabled" size="small">
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
              <n-checkbox v-model:checked="contextConfig.session_enabled">
                获取 Session 上下文
              </n-checkbox>
            </n-space>
            <template v-if="contextConfig.session_enabled">
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
              <n-space align="center">
                <n-checkbox v-model:checked="contextConfig.include_tool">
                  获取 tool 上下文
                </n-checkbox>
                <span style="font-size: 12px; color: #999">
                  {{ contextConfig.include_tool ? '包含 tool 角色消息' : '不包含 tool 角色消息' }}
                </span>
              </n-space>
            </template>
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
        <template v-if="formData.with_mark && formData.write_to_db">
          <n-form-item label="发送标记">
            <n-input v-model:value="formData.send_mark" placeholder="[凯莉主动发送]" style="max-width: 300px" />
          </n-form-item>
          <n-form-item label="时间格式">
            <div class="time-format-selector">
              <div
                v-for="opt in timeFormatOptions" :key="opt.value"
                class="time-format-chip"
                :class="{ active: formData.time_format === opt.value }"
                @click="formData.time_format = opt.value"
              >
                <span class="chip-label">{{ opt.label }}</span>
                <span class="chip-preview">{{ formatWithOption(opt.value) }}</span>
              </div>
            </div>
            <div class="mark-preview" v-if="testMessageForPreview">
              预览: {{ formData.send_mark }} {{ formatWithOption(formData.time_format) }}: {{ testMessageForPreview }}
            </div>
          </n-form-item>
        </template>
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

    <!-- 运行日志弹窗 -->
    <n-modal v-model:show="showJobLogs" preset="card" :title="`运行日志 - ${jobLogsName}`" style="width: 900px">
      <n-spin :show="jobLogsLoading">
        <n-data-table
          v-if="jobLogs.length > 0"
          :columns="jobLogsColumns"
          :data="jobLogs"
          :bordered="false"
          size="small"
          :max-height="500"
        />
        <n-empty v-else description="暂无运行日志" />
      </n-spin>
    </n-modal>

    <!-- 日志详情弹窗 -->
    <n-modal v-model:show="showLogDetail" preset="card" title="运行详情" style="width: 900px">
      <div v-if="logDetailData" style="max-height: 70vh; overflow-y: auto;">
        <!-- 基本信息 -->
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
          <n-descriptions-item label="任务">{{ logDetailData.job_name }}</n-descriptions-item>
          <n-descriptions-item label="Session">{{ logDetailData.session_id }}</n-descriptions-item>
          <n-descriptions-item label="平台">{{ logDetailData.platform }}</n-descriptions-item>
        </n-descriptions>

        <!-- LLM 请求 -->
        <n-divider v-if="logDetailData.llm_request" title-placement="left">LLM 请求</n-divider>
        <n-descriptions v-if="logDetailData.llm_request" bordered :column="2" size="small" style="margin-bottom: 16px">
          <n-descriptions-item label="模式">{{ logDetailData.llm_request.mode }}</n-descriptions-item>
          <n-descriptions-item label="模型">{{ logDetailData.llm_request.model }}</n-descriptions-item>
          <n-descriptions-item label="Temperature">{{ logDetailData.llm_request.temperature }}</n-descriptions-item>
          <n-descriptions-item label="Max Tokens">{{ logDetailData.llm_request.max_tokens }}</n-descriptions-item>
          <n-descriptions-item label="系统提示词" :span="2">
            <pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto; font-size: 12px;">{{ logDetailData.llm_request.system_prompt }}</pre>
          </n-descriptions-item>
          <n-descriptions-item label="用户提示词" :span="2">
            <pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto; font-size: 12px;">{{ logDetailData.llm_request.user_prompt }}</pre>
          </n-descriptions-item>
        </n-descriptions>

        <!-- LLM 返回 -->
        <n-divider v-if="logDetailData.llm_response" title-placement="left">LLM 返回</n-divider>
        <n-descriptions v-if="logDetailData.llm_response" bordered :column="2" size="small" style="margin-bottom: 16px">
          <n-descriptions-item label="生成内容" :span="2">
            <pre style="white-space: pre-wrap; font-size: 12px;">{{ logDetailData.llm_response.content }}</pre>
          </n-descriptions-item>
          <n-descriptions-item label="耗时">{{ logDetailData.llm_response.duration }}s</n-descriptions-item>
          <n-descriptions-item v-if="logDetailData.llm_response.error" label="错误" :span="2">
            <pre style="white-space: pre-wrap; color: #d03050; font-size: 12px;">{{ logDetailData.llm_response.error }}</pre>
          </n-descriptions-item>
        </n-descriptions>

        <!-- 上下文 -->
        <n-divider v-if="logDetailData.context" title-placement="left">上下文</n-divider>
        <div v-if="logDetailData.context" style="margin-bottom: 16px;">
          <n-tag type="info" size="small">Session 消息 ({{ logDetailData.context.session_count }}条)</n-tag>
          <div v-if="logDetailData.context.session_messages && logDetailData.context.session_messages.length" style="max-height: 300px; overflow-y: auto; border: 1px solid #eee; border-radius: 4px; padding: 8px; margin-top: 4px;">
            <div v-for="(msg, idx) in logDetailData.context.session_messages" :key="idx" style="margin-bottom: 4px; font-size: 12px;">
              <n-tag :type="msg.role === 'user' ? 'info' : 'success'" size="tiny">{{ msg.role }}</n-tag>
              <span style="margin-left: 4px;">{{ msg.content }}</span>
            </div>
          </div>
        </div>

        <!-- 发送结果 -->
        <n-divider v-if="logDetailData.send_result" title-placement="left">发送结果</n-divider>
        <n-descriptions v-if="logDetailData.send_result" bordered :column="2" size="small">
          <n-descriptions-item label="状态">{{ logDetailData.send_result.success ? '✅ 成功' : '❌ 失败' }}</n-descriptions-item>
          <n-descriptions-item label="消息">{{ logDetailData.send_result.message }}</n-descriptions-item>
          <n-descriptions-item label="最终发送内容" :span="2">
            <pre style="white-space: pre-wrap; font-size: 12px;">{{ logDetailData.send_result.final_message }}</pre>
          </n-descriptions-item>
        </n-descriptions>
      </div>
    </n-modal>

    <!-- 预览提示词弹窗 -->
    <n-modal v-model:show="showPreview" preset="card" title="预览最终提示词" style="width: 800px">
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
              :autosize="{ minRows: 3, maxRows: 10 }"
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
          <n-form-item label="上下文摘要" v-if="previewData.context_summary">
            <n-tag type="info">{{ previewData.context_summary }}</n-tag>
          </n-form-item>
        </n-form>

        <!-- 实际上下文数据 -->
        <n-divider title-placement="left" v-if="previewData.context_data">实际上下文</n-divider>
        <div v-if="previewData.context_data" class="context-data-section">
          <!-- Session 消息 -->
          <div v-if="previewData.context_data.session_messages && previewData.context_data.session_messages.length > 0" class="context-block">
            <div class="context-block-title">
              <n-tag type="info" size="small">Session 消息</n-tag>
              <span class="context-count">{{ previewData.context_data.session_messages.length }} 条</span>
            </div>
            <div class="context-messages">
              <div v-for="(msg, idx) in previewData.context_data.session_messages" :key="idx" class="context-msg">
                <span class="context-msg-role" :class="msg.role">{{ msg.role }}:</span>
                <span class="context-msg-content">{{ msg.content }}</span>
              </div>
            </div>
          </div>

          <!-- Recall 结果 -->
          <div v-if="previewData.context_data.recall_results && previewData.context_data.recall_results.length > 0" class="context-block">
            <div class="context-block-title">
              <n-tag type="success" size="small">Recall 记忆</n-tag>
              <span class="context-count">{{ previewData.context_data.recall_results.length }} 条</span>
            </div>
            <div class="context-messages">
              <div v-for="(item, idx) in previewData.context_data.recall_results" :key="idx" class="context-msg recall">
                <span class="context-msg-content">{{ item.text || JSON.stringify(item) }}</span>
              </div>
            </div>
          </div>

          <!-- Reflect 结果 -->
          <div v-if="previewData.context_data.reflect_result" class="context-block">
            <div class="context-block-title">
              <n-tag type="warning" size="small">Reflect 分析</n-tag>
            </div>
            <div class="context-messages">
              <div class="context-msg reflect">
                <span class="context-msg-content">{{ previewData.context_data.reflect_result }}</span>
              </div>
            </div>
          </div>

          <!-- 无上下文 -->
          <n-empty
            v-if="!previewData.context_data.session_messages?.length && !previewData.context_data.recall_results?.length && !previewData.context_data.reflect_result"
            description="无上下文数据"
            size="small"
          />
        </div>
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, h } from 'vue'
import { useMessage, useDialog, NButton } from 'naive-ui'
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
const showNextRuns = ref(false)
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
const previewData = ref({ system_prompt: '', user_prompt: '', soul_md: '', context_summary: '', context_data: null })
const previewing = ref(false)

// 运行日志
const showJobLogs = ref(false)
const jobLogs = ref([])
const jobLogsLoading = ref(false)
const jobLogsName = ref('')

// 日志详情
const showLogDetail = ref(false)
const logDetailData = ref(null)

function viewLogDetail(log) {
  logDetailData.value = typeof log.details === 'string' ? JSON.parse(log.details) : log.details
  showLogDetail.value = true
}
const jobLogsColumns = [
  { title: '时间', key: 'created_at', width: 160, render: (row) => formatTime(row.created_at) },
  { title: '状态', key: 'status', width: 80, render: (row) => row.status === 'success' ? '✅ 成功' : '❌ 失败' },
  { title: '消息', key: 'message', ellipsis: { tooltip: true } },
  { title: '错误信息', key: 'error', ellipsis: { tooltip: true }, render: (row) => row.error || '-' },
  { title: '耗时', key: 'duration', width: 80, render: (row) => row.duration ? `${row.duration.toFixed(1)}s` : '-' },
  { title: '详情', key: 'details', width: 80, render: (row) => row.details ? h(NButton, { size: 'tiny', onClick: () => viewLogDetail(row) }, { default: () => '详情' }) : '-' }
]

const platformOptions = [
  { label: '微信', value: 'weixin' },
  { label: '飞书', value: 'feishu' },
  { label: 'CLI', value: 'cli' }
]

const WEEKDAY_NAMES = ['一', '二', '三', '四', '五', '六', '日']

const timeFormatOptions = [
  { label: '简短', value: '%H:%M 星期{weekday}', preview: () => '14:30 星期四' },
  { label: '时分秒', value: '%H:%M:%S', preview: () => '14:30:25' },
  { label: '日期时分', value: '%m/%d %H:%M', preview: () => '06/12 14:30' },
  { label: '完整', value: '%Y-%m-%d %H:%M:%S', preview: () => '2026-06-12 14:30:25' },
  { label: '日期星期', value: '%m/%d 星期{weekday}', preview: () => '06/12 星期四' },
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

const testMessageForPreview = ref('你好，这是测试消息')

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
  mark_format: '[凯莉主动发送] {timestamp}: {content}',
  send_mark: '[凯莉主动发送]',
  time_format: '%H:%M 星期{weekday}'
})

// 上下文配置
const contextConfig = ref({
  session_enabled: true,
  session_limit: 20,
  include_tool: false,
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

async function fillDefaultSystemPrompt() {
  try {
    const data = await api.get('/config/prompts')
    if (data.system) {
      formData.value.system_prompt = data.system
      message.success('已填充默认系统提示词')
    } else {
      message.warning('未配置默认系统提示词')
    }
  } catch (e) {
    message.error('加载默认提示词失败')
  }
}

async function fillDefaultUserPrompt() {
  try {
    const data = await api.get('/config/prompts')
    if (data.generation) {
      formData.value.user_prompt = data.generation
      message.success('已填充默认用户提示词')
    } else {
      message.warning('未配置默认用户提示词')
    }
  } catch (e) {
    message.error('加载默认提示词失败')
  }
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
    mark_format: '[凯莉主动发送] {timestamp}: {content}',
    send_mark: '[凯莉主动发送]',
    time_format: '%H:%M 星期{weekday}'
  }
  contextConfig.value = {
    session_enabled: true,
    session_limit: 20,
    include_tool: false,
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
    const data = await api.get('/config/prompts')
    if (data.system) {
      formData.value.system_prompt = data.system
    }
    if (data.generation) {
      formData.value.user_prompt = data.generation
    }
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
      mark_format: job.mark_format || '[凯莉主动发送] {timestamp}: {content}',
      send_mark: job.send_mark || '[凯莉主动发送]',
      time_format: job.time_format || '%H:%M 星期{weekday}'
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
      mark_format: job.mark_format || '[凯莉主动发送] {timestamp}: {content}',
      send_mark: job.send_mark || '[凯莉主动发送]',
      time_format: job.time_format || '%H:%M 星期{weekday}'
    }
  }
  sessionMode.value = job.session_id ? 'fixed' : 'latest'
  cronParseResult.value = null
  parseCron()
  loadSessions(formData.value.platform)
  showCreate.value = true
}

async function viewJobLogs(job) {
  jobLogsName.value = job.name
  jobLogsLoading.value = true
  showJobLogs.value = true
  try {
    const data = await api.get('/task-logs', { params: { task_type: 'cron_run', message: job.name, page_size: 100 } })
    jobLogs.value = data.items || []
  } catch (e) {
    message.error('加载运行日志失败')
    jobLogs.value = []
  } finally {
    jobLogsLoading.value = false
  }
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
    const data = await api.get('/config/prompts')
    defaultPromptsData.value = {
      system_prompt: data.system || '',
      user_prompt: data.generation || '',
      append_soul_md: true
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
    await api.put('/config/prompts', {
      system: defaultPromptsData.value.system_prompt,
      generation: defaultPromptsData.value.user_prompt
    })
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
    // 确定 session_id：优先使用指定的，否则不传（后端会自动获取最新活跃）
    const sessionId = formData.value.session_id || null
    const data = await api.post('/cron/preview-prompt', {
      system_prompt: formData.value.system_prompt,
      user_prompt: formData.value.user_prompt,
      append_soul_md: formData.value.append_soul_md,
      context_config: contextConfig.value,
      session_id: sessionId
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
  parts.push(`session_enabled=${config.session_enabled !== false ? 'true' : 'false'}`)
  parts.push(`session_limit=${config.session_limit || 20}`)
  parts.push(`include_tool=${config.include_tool ? 'true' : 'false'}`)
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
    session_enabled: true,
    session_limit: 20,
    include_tool: false,
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
      case 'session_enabled':
        config.session_enabled = value === 'true'
        break
      case 'session_limit':
        config.session_limit = parseInt(value) || 20
        break
      case 'include_tool':
        config.include_tool = value === 'true'
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

.context-data-section {
  max-height: 400px;
  overflow-y: auto;
}

.context-block {
  margin-bottom: 16px;
}

.context-block-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.context-count {
  font-size: 12px;
  color: #999;
}

.context-messages {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.context-msg {
  margin-bottom: 6px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}

.context-msg:last-child {
  margin-bottom: 0;
}

.context-msg-role {
  font-weight: 500;
  margin-right: 4px;
}

.context-msg-role.user {
  color: #18a058;
}

.context-msg-role.assistant {
  color: #2080f0;
}

.context-msg-content {
  color: #333;
}

.context-msg.recall .context-msg-content {
  color: #0a7;
}

.context-msg.reflect .context-msg-content {
  color: #f0a020;
  font-style: italic;
}

/* 时间格式选择器 */
.time-format-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.time-format-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 12px;
  border: 1px solid #e0e0e6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
  min-width: 80px;
}

.time-format-chip:hover {
  border-color: #18a058;
  background: #f0f9eb;
}

.time-format-chip.active {
  border-color: #18a058;
  background: #e8f5e9;
  box-shadow: 0 0 0 1px #18a058;
}

.chip-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 2px;
}

.time-format-chip.active .chip-label {
  color: #18a058;
  font-weight: 500;
}

.chip-preview {
  font-size: 13px;
  color: #333;
  font-family: monospace;
}

.mark-preview {
  margin-top: 8px;
  padding: 6px 10px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  font-family: monospace;
  word-break: break-all;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .cron-page {
    max-width: 100%;
  }

  .job-card {
    padding: 12px;
  }

  .job-meta {
    gap: 8px;
  }

  .job-actions {
    flex-wrap: wrap;
  }

  .job-actions .n-button {
    flex: 1;
    min-width: 60px;
  }

  .time-format-selector {
    gap: 6px;
  }
  .time-format-chip {
    padding: 5px 8px;
    min-width: 70px;
  }
  .chip-preview {
    font-size: 11px;
  }
}
</style>
