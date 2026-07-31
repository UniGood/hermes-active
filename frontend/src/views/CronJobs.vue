<template>
  <div class="cron-page">
    <!-- 创建任务按钮 -->
    <n-space style="margin-bottom: 16px">
      <n-button type="primary" @click="openCreate">
        {{ t('cron-jobs.cronJobs.createJob') }}
      </n-button>
      <n-button @click="openDefaultPrompts">
        {{ t('cron-jobs.cronJobs.defaultPrompts') }}
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
            <span>{{ t('cron-jobs.cronJobs.scheduleInfo', { schedule: job.schedule }) }}</span>
            <span>{{ t('cron-jobs.cronJobs.platformInfo', { platform: job.platform || 'weixin' }) }}</span>
            <span v-if="job.session_id">{{ t('cron-jobs.cronJobs.sessionInfo', { sessionId: job.session_id }) }}</span>
            <span v-else>{{ t('cron-jobs.cronJobs.sessionModeLatestInfo') }}</span>
            <span>{{ t('cron-jobs.cronJobs.llmInfo', { value: job.use_llm ? t('cron-jobs.cronJobs.yes') : t('cron-jobs.cronJobs.no') }) }}</span>
            <span>{{ t('cron-jobs.cronJobs.writeToDbInfo', { value: job.write_to_db ? t('cron-jobs.cronJobs.yes') : t('cron-jobs.cronJobs.no') }) }}</span>
            <span>{{ t('cron-jobs.cronJobs.withMarkInfo', { value: job.with_mark ? t('cron-jobs.cronJobs.yes') : t('cron-jobs.cronJobs.no') }) }}</span>
          </div>
          <div class="job-meta" v-if="job.last_run_at">
            <span>{{ t('cron-jobs.cronJobs.lastRun', { time: formatTime(job.last_run_at) }) }}</span>
          </div>
          <div class="job-actions">
            <n-button size="small" type="success" @click="runJob(job)" :loading="job.running">{{ t('cron-jobs.cronJobs.actions.run') }}</n-button>
            <n-button size="small" @click="editJob(job)">{{ t('cron-jobs.cronJobs.actions.edit') }}</n-button>
            <n-button size="small" type="error" @click="deleteJob(job)">{{ t('cron-jobs.cronJobs.actions.delete') }}</n-button>
            <n-button size="small" @click="viewJobLogs(job)">{{ t('cron-jobs.cronJobs.actions.logs') }}</n-button>
          </div>
        </div>
        <n-empty v-if="!loading && jobs.length === 0" :description="t('cron-jobs.cronJobs.noJobs')" />
      </div>
    </n-spin>

    <!-- 创建/编辑任务弹窗 -->
    <n-modal v-model:show="showCreate" preset="card" :title="editingJob ? t('cron-jobs.cronJobs.editJob') : t('cron-jobs.cronJobs.createJobTitle')" fullscreen>
      <n-form label-placement="left" label-width="120">
        <n-form-item :label="t('cron-jobs.cronJobs.form.name')">
          <n-input v-model:value="formData.name" :placeholder="t('cron-jobs.cronJobs.form.namePlaceholder')" />
        </n-form-item>
        <n-form-item :label="t('cron-jobs.cronJobs.form.schedule')">
          <n-input v-model:value="formData.schedule" :placeholder="t('cron-jobs.cronJobs.form.schedulePlaceholder')" @update:value="parseCron" />
        </n-form-item>
        <n-form-item label=" " v-if="cronParseResult">
          <div class="cron-parse-result">
            <div class="cron-freq">{{ t('cron-jobs.cronJobs.form.frequency') }}: {{ cronParseResult.frequency }}</div>
            <div class="cron-next-runs" v-if="cronParseResult.next_runs && cronParseResult.next_runs.length">
              <div class="cron-next-title" @click="showNextRuns = !showNextRuns" style="cursor: pointer; user-select: none;">
                {{ t('cron-jobs.cronJobs.form.nextRunTimes') }}
                <span style="font-size: 12px; color: #999;">{{ showNextRuns ? t('cron-jobs.cronJobs.form.collapse') : t('cron-jobs.cronJobs.form.expand') }}</span>
              </div>
              <template v-if="showNextRuns">
                <div v-for="(run, idx) in cronParseResult.next_runs" :key="idx" class="cron-next-item">
                  {{ idx + 1 }}. {{ run }}
                </div>
              </template>
            </div>
          </div>
        </n-form-item>
        <n-form-item :label="t('cron-jobs.cronJobs.form.platform')">
          <n-select
            v-model:value="formData.platform"
            :options="platformOptions"
            :placeholder="t('cron-jobs.cronJobs.form.platformPlaceholder')"
          />
        </n-form-item>
        <n-form-item :label="t('cron-jobs.cronJobs.form.sessionMode')">
          <n-radio-group v-model:value="sessionMode">
            <n-space vertical>
              <n-radio value="latest">{{ t('cron-jobs.cronJobs.form.sessionModeLatest') }}</n-radio>
              <n-radio value="fixed">{{ t('cron-jobs.cronJobs.form.sessionModeFixed') }}</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        <n-form-item :label="t('cron-jobs.cronJobs.form.sessionId')" v-if="sessionMode === 'fixed'">
          <n-select
            v-model:value="formData.session_id"
            :options="sessionOptions"
            :placeholder="t('cron-jobs.cronJobs.form.sessionIdPlaceholder')"
            filterable
          />
        </n-form-item>
        <!-- 系统提示词 -->
        <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.form.promptConfig') }}</n-divider>
        <n-form-item :label="t('cron-jobs.cronJobs.form.systemPrompt')">
          <n-space vertical style="width: 100%">
            <n-input
              v-model:value="formData.system_prompt"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 8 }"
              :placeholder="t('cron-jobs.cronJobs.form.systemPromptPlaceholder')"
            />
            <n-space align="center">
              <n-checkbox v-model:checked="formData.append_soul_md">
                {{ t('cron-jobs.cronJobs.form.appendSoulMd') }}
              </n-checkbox>
              <span style="font-size: 12px; color: #999">
                {{ formData.append_soul_md ? t('cron-jobs.cronJobs.form.appendSoulMdHint') : t('cron-jobs.cronJobs.form.noAppendSoulMd') }}
              </span>
            </n-space>
            <n-button size="small" @click="fillDefaultSystemPrompt" style="margin-top: 4px">
              {{ t('cron-jobs.cronJobs.form.fillDefaultSystemPrompt') }}
            </n-button>
          </n-space>
        </n-form-item>

        <!-- 用户提示词 -->
        <n-form-item :label="t('cron-jobs.cronJobs.form.userPrompt')">
          <n-space vertical style="width: 100%">
            <n-input
              v-model:value="formData.user_prompt"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 8 }"
              :placeholder="t('cron-jobs.cronJobs.form.userPromptPlaceholder')"
            />
            <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center;">
              <span style="font-size: 12px; color: var(--theme-text-muted);">{{ t('cron-jobs.cronJobs.form.insertPlaceholder') }}</span>
              <n-tag v-for="ph in placeholderOptions" :key="ph.value" size="small"
                :bordered="false" style="cursor: pointer;"
                @click="insertPlaceholder(ph.value)">
                {{ ph.label }}
              </n-tag>
            </div>
            <n-button size="small" @click="fillDefaultUserPrompt" style="margin-top: 4px">
              {{ t('cron-jobs.cronJobs.form.fillDefaultUserPrompt') }}
            </n-button>
            <!-- 上下文配置状态 -->
            <div class="context-status">
              <span class="context-status-label">{{ t('cron-jobs.cronJobs.form.currentContextConfig') }}</span>
              <n-tag v-if="contextConfig.session_enabled" size="small" type="info">
                Session: {{ contextConfig.session_limit }} {{ t('cron-jobs.cronJobs.form.count').replace('：', '') }}{{ contextConfig.include_tool ? ' (含tool)' : '' }}
              </n-tag>
              <n-tag v-else size="small">{{ t('cron-jobs.cronJobs.form.onlySessionContext') }}</n-tag>
              <n-tag v-if="contextConfig.hindsight_recall_enabled" size="small" type="success">
                Recall: {{ contextConfig.hindsight_recall_query || t('cron-jobs.cronJobs.messages.enabled') }}
              </n-tag>
              <n-tag v-if="contextConfig.hindsight_reflect_enabled" size="small" type="warning">
                Reflect: {{ contextConfig.hindsight_reflect_query || t('cron-jobs.cronJobs.messages.enabled') }}
              </n-tag>
              <n-tag v-if="contextConfig.weather_enabled" size="small" type="error">
                {{ t('cron-jobs.cronJobs.form.weather') }}：{{ weatherDaysLabel }}
              </n-tag>
              <n-tag v-if="contextConfig.session_enabled && !contextConfig.hindsight_recall_enabled && !contextConfig.hindsight_reflect_enabled && !contextConfig.weather_enabled" size="small">
                {{ t('cron-jobs.cronJobs.form.onlySessionContext') }}
              </n-tag>
            </div>
          </n-space>
        </n-form-item>

        <!-- 上下文配置 -->
        <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.form.contextConfig') }}</n-divider>
        <n-form-item :label="t('cron-jobs.cronJobs.form.sessionContext')">
          <n-space vertical style="width: 100%">
            <n-space align="center">
              <n-checkbox v-model:checked="contextConfig.session_enabled">
                {{ t('cron-jobs.cronJobs.form.getSessionContext') }}
              </n-checkbox>
            </n-space>
            <template v-if="contextConfig.session_enabled">
              <n-space align="center">
                <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.readCount') }}</span>
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
                  {{ t('cron-jobs.cronJobs.form.includeToolContext') }}
                </n-checkbox>
                <span style="font-size: 12px; color: #999">
                  {{ contextConfig.include_tool ? t('cron-jobs.cronJobs.form.includeToolHint') : t('cron-jobs.cronJobs.form.excludeToolHint') }}
                </span>
              </n-space>
            </template>
          </n-space>
        </n-form-item>

        <!-- 记忆反思 -->
        <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.form.recall') }}</n-divider>
        <n-form-item :label="t('cron-jobs.cronJobs.form.recallRetrieval')">
          <n-space vertical style="width: 100%">
            <n-space align="center">
              <n-switch v-model:value="contextConfig.hindsight_recall_enabled" />
              <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.enableRecall') }}</span>
            </n-space>
            <template v-if="contextConfig.hindsight_recall_enabled">
              <n-space align="center">
                <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.keyword') }}</span>
                <n-input
                  v-model:value="contextConfig.hindsight_recall_query"
                  :placeholder="t('cron-jobs.cronJobs.form.searchKeyword')"
                  size="small"
                  style="width: 300px"
                />
                <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.count') }}</span>
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
        <n-form-item :label="t('cron-jobs.cronJobs.form.reflectAnalysis')">
          <n-space vertical style="width: 100%">
            <n-space align="center">
              <n-switch v-model:value="contextConfig.hindsight_reflect_enabled" />
              <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.enableReflect') }}</span>
            </n-space>
            <template v-if="contextConfig.hindsight_reflect_enabled">
              <n-space align="center">
                <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.question') }}</span>
                <n-input
                  v-model:value="contextConfig.hindsight_reflect_query"
                  :placeholder="t('cron-jobs.cronJobs.form.analysisQuestion')"
                  size="small"
                  style="width: 400px"
                />
              </n-space>
            </template>
          </n-space>
        </n-form-item>

        <!-- 天气感知 -->
        <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.form.weather') }}</n-divider>
        <n-form-item :label="t('cron-jobs.cronJobs.form.amapWeather')">
          <n-space vertical style="width: 100%">
            <n-space align="center">
              <n-switch v-model:value="contextConfig.weather_enabled" />
              <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.enableWeather') }}</span>
            </n-space>
            <n-text v-if="contextConfig.weather_enabled" depth="3" style="font-size: 12px">
              {{ t('cron-jobs.cronJobs.form.weatherInjectionHint') }}
            </n-text>
            <template v-if="contextConfig.weather_enabled">
              <n-space align="center">
                <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.forecastDays') }}</span>
                <n-radio-group v-model:value="contextConfig.weather_days">
                  <n-radio :value="0">{{ t('cron-jobs.cronJobs.form.today') }}</n-radio>
                  <n-radio :value="2">{{ t('cron-jobs.cronJobs.form.twoDays') }}</n-radio>
                  <n-radio :value="3">{{ t('cron-jobs.cronJobs.form.threeDays') }}</n-radio>
                  <n-radio :value="4">{{ t('cron-jobs.cronJobs.form.fourDays') }}</n-radio>
                </n-radio-group>
                <n-text depth="3" style="font-size: 12px">{{ t('cron-jobs.cronJobs.form.amapMaxDays') }}</n-text>
              </n-space>
            </template>
          </n-space>
        </n-form-item>

        <!-- 时间格式 -->
        <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.form.timeFormat') }}</n-divider>
        <n-form-item label="{time}">
          <n-space vertical style="width: 100%">
            <TimeFormatSelector v-model="contextConfig.time_format" />
            <n-text depth="3" style="font-size: 12px">
              {{ t('cron-jobs.cronJobs.form.insertCurrentTime') }}
            </n-text>
          </n-space>
        </n-form-item>

        <!-- 跳过执行参数 -->
        <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.form.skipParams') }}</n-divider>
        <n-form-item :label="t('cron-jobs.cronJobs.form.chatCooldown')">
          <n-space vertical style="width: 100%">
            <n-space align="center">
              <n-checkbox v-model:checked="formData.cooldown_enabled">
                {{ t('cron-jobs.cronJobs.form.enableCooldown') }}
              </n-checkbox>
              <n-input-number
                v-model:value="formData.cooldown_minutes"
                :min="1"
                :max="120"
                size="small"
                style="width: 120px"
                :disabled="!formData.cooldown_enabled"
              />
              <span style="font-size: 13px; color: #666">{{ t('cron-jobs.cronJobs.form.minutes') }}</span>
            </n-space>
            <div style="font-size: 12px; color: #999; margin-top: 4px;">
              {{ t('cron-jobs.cronJobs.form.cooldownHint') }}
            </div>
          </n-space>
        </n-form-item>
        <!-- 发送消息 -->
        <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.form.sendMessage') }}</n-divider>
        <n-form-item :label="t('cron-jobs.cronJobs.form.useLlm')">
          <n-switch v-model:value="formData.use_llm" />
          <span style="margin-left: 8px; color: #999; font-size: 13px">
            {{ formData.use_llm ? t('cron-jobs.cronJobs.form.llmGenerate') : t('cron-jobs.cronJobs.form.directSend') }}
          </span>
        </n-form-item>
        <n-form-item v-if="formData.use_llm" label="Max Tokens">
          <n-input-number v-model:value="formData.max_tokens" :min="0" :max="8192" :step="100" style="width: 180px" />
          <span style="margin-left: 8px; color: #999; font-size: 13px">{{ t('cron-jobs.cronJobs.form.noLimit') }}</span>
        </n-form-item>
        <n-form-item v-if="!formData.use_llm" :label="t('cron-jobs.cronJobs.form.fixedMessage')">
          <n-input v-model:value="formData.fixed_message" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" :placeholder="t('cron-jobs.cronJobs.form.fixedMessagePlaceholder')" />
        </n-form-item>
        <n-form-item :label="t('cron-jobs.cronJobs.form.writeToDb')">
          <n-switch v-model:value="formData.write_to_db" />
          <span style="margin-left: 8px; color: #999; font-size: 13px">
            {{ formData.write_to_db ? t('cron-jobs.cronJobs.form.writeToDbHint') : t('cron-jobs.cronJobs.form.sendOnly') }}
          </span>
        </n-form-item>

        <div v-if="formData.write_to_db">
          <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.form.messageMark') }}</n-divider>
          <n-form-item :label="t('cron-jobs.cronJobs.form.sendMark')">
            <n-input v-model:value="formData.send_mark" placeholder="凯莉" style="max-width: 300px" />
          </n-form-item>
          <n-form-item :label="t('cron-jobs.cronJobs.form.timeFormat')">
            <TimeFormatSelector v-model="formData.time_format" />
          </n-form-item>
          <n-form-item :label="t('cron-jobs.cronJobs.form.preview')">
            <div class="mark-preview" v-if="testMessageForPreview">
              <template v-if="formData.send_mark || formData.time_format">[<template v-if="formData.send_mark">{{ formData.send_mark }}</template><template v-if="formData.time_format"> {{ formatWithOption(formData.time_format) }}</template>]: </template>{{ testMessageForPreview }}
            </div>
          </n-form-item>
        </div>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showCreate = false">{{ t('common.common.cancel') }}</n-button>
          <n-button @click="previewPrompt" :loading="previewing">{{ t('cron-jobs.cronJobs.logDetail.previewPrompt') }}</n-button>
          <n-button type="primary" @click="saveJob" :loading="saving">{{ t('common.common.save') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 默认提示词配置弹窗 -->
    <n-modal v-model:show="showDefaultPrompts" preset="card" :title="t('cron-jobs.cronJobs.defaultPrompts.title')" fullscreen>
      <n-form label-placement="left" label-width="120">
        <n-form-item :label="t('cron-jobs.cronJobs.defaultPrompts.systemPrompt')">
          <n-input
            v-model:value="defaultPromptsData.system_prompt"
            type="textarea"
            :autosize="{ minRows: 5, maxRows: 15 }"
            :placeholder="t('cron-jobs.cronJobs.defaultPrompts.systemPromptPlaceholder')"
          />
        </n-form-item>
        <n-form-item :label="t('cron-jobs.cronJobs.defaultPrompts.userPrompt')">
          <n-input
            v-model:value="defaultPromptsData.user_prompt"
            type="textarea"
            :autosize="{ minRows: 5, maxRows: 15 }"
            :placeholder="t('cron-jobs.cronJobs.defaultPrompts.userPromptPlaceholder')"
          />
        </n-form-item>
        <n-form-item :label="t('cron-jobs.cronJobs.defaultPrompts.appendSoulMd')">
          <n-checkbox v-model:checked="defaultPromptsData.append_soul_md">
            {{ t('cron-jobs.cronJobs.defaultPrompts.appendSoulMdDefault') }}
          </n-checkbox>
        </n-form-item>
        <n-form-item label=" ">
          <n-button @click="previewDefaultPrompt" :loading="previewingDefault">
            {{ t('cron-jobs.cronJobs.defaultPrompts.previewFullPrompt') }}
          </n-button>
        </n-form-item>
        <!-- 预览结果 -->
        <template v-if="defaultPromptPreview">
          <n-divider title-placement="left">{{ t('cron-jobs.cronJobs.defaultPrompts.previewResult') }}</n-divider>
          <n-form-item :label="t('cron-jobs.cronJobs.defaultPrompts.systemPromptFinal')">
            <n-input
              :value="defaultPromptPreview.system_prompt"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 10 }"
              readonly
            />
          </n-form-item>
          <n-form-item :label="t('cron-jobs.cronJobs.form.userPrompt')">
            <n-input
              :value="defaultPromptPreview.user_prompt"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 5 }"
              readonly
            />
          </n-form-item>
          <n-form-item :label="t('cron-jobs.cronJobs.defaultPrompts.soulMdContent')" v-if="defaultPromptPreview.soul_md">
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
          <n-button @click="showDefaultPrompts = false">{{ t('common.common.cancel') }}</n-button>
          <n-button type="primary" @click="saveDefaultPrompts" :loading="savingDefaultPrompts">{{ t('common.common.save') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 日志弹窗 -->
    <n-modal v-model:show="showJobLogs" preset="card" :title="t('cron-jobs.cronJobs.logDetail.logTitle', { name: jobLogsName })" fullscreen>
      <n-spin :show="jobLogsLoading">
        <n-data-table
          v-if="jobLogs.length > 0"
          :columns="jobLogsColumns"
          :data="jobLogsPaged"
          :bordered="false"
          size="small"
        />
        <n-empty v-else :description="t('cron-jobs.cronJobs.logDetail.noLogs')" />
        <div v-if="jobLogsTotalPages > 1" class="log-pagination">
          <n-pagination v-model:page="jobLogsPage" :page-count="jobLogsTotalPages" :page-slot="5" />
          <span class="log-total">{{ t('cron-jobs.cronJobs.logDetail.logTotal', { count: jobLogs.length }) }}</span>
        </div>
      </n-spin>
    </n-modal>

    <!-- 日志详情弹窗 -->
    <n-modal v-model:show="showLogDetail" preset="card" :title="t('cron-jobs.cronJobs.logDetail.title')" fullscreen>
      <div v-if="logDetailData">
        <!-- 执行概要 -->
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.status')">
            <n-tag :type="logDetailData._status === 'success' ? 'success' : logDetailData._status === 'skipped' ? 'warning' : 'error'" size="small">
              {{ logDetailData._status === 'success' ? t('cron-jobs.cronJobs.logDetail.success') : logDetailData._status === 'skipped' ? t('cron-jobs.cronJobs.logDetail.skipped') : t('cron-jobs.cronJobs.logDetail.failed') }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.duration')">{{ logDetailData._duration ? logDetailData._duration.toFixed(1) + 's' : '-' }}</n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.time')">{{ formatTime(logDetailData._created_at) }}</n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.task')">{{ logDetailData.job_name || '-' }}</n-descriptions-item>
          <n-descriptions-item label="Session" :span="2" v-if="logDetailData.session_id">
            <span style="font-family: monospace; font-size: 12px;">{{ logDetailData.session_id }}</span>
          </n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.platform')">{{ logDetailData.platform || '-' }}</n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.message')" :span="2" v-if="logDetailData._message">{{ logDetailData._message }}</n-descriptions-item>
        </n-descriptions>

        <!-- 错误信息 -->
        <n-alert v-if="logDetailData._error" type="error" style="margin-bottom: 16px;" :title="t('cron-jobs.cronJobs.logDetail.errorInfo')">
          <pre style="white-space: pre-wrap; font-size: 13px; color: #d03050;">{{ logDetailData._error }}</pre>
        </n-alert>

        <!-- 跳过原因 -->
        <n-alert v-if="logDetailData.skip_reason" type="warning" style="margin-bottom: 16px;" :title="t('cron-jobs.cronJobs.logDetail.skipReason')">
          <div style="font-size: 13px;">
            {{ logDetailData.skip_reason }}
            <span v-if="logDetailData.cooldown_minutes">{{ t('cron-jobs.cronJobs.logDetail.cooldownInfo', { cooldown: logDetailData.cooldown_minutes, elapsed: logDetailData.elapsed_minutes }) }}</span>
          </div>
        </n-alert>

        <!-- LLM 请求 -->
        <n-divider v-if="logDetailData.llm_request" title-placement="left">{{ t('cron-jobs.cronJobs.logDetail.llmRequest') }}</n-divider>
        <n-descriptions v-if="logDetailData.llm_request" bordered :column="2" size="small" style="margin-bottom: 16px">
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.mode')">{{ logDetailData.llm_request.mode }}</n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.model')">{{ logDetailData.llm_request.model }}</n-descriptions-item>
          <n-descriptions-item label="Temperature">{{ logDetailData.llm_request.temperature }}</n-descriptions-item>
          <n-descriptions-item label="Max Tokens">{{ logDetailData.llm_request.max_tokens }}</n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.systemPrompt')" :span="2">
            <pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto; font-size: 12px;">{{ logDetailData.llm_request.system_prompt }}</pre>
          </n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.userPrompt')" :span="2">
            <pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto; font-size: 12px;">{{ logDetailData.llm_request.user_prompt }}</pre>
          </n-descriptions-item>
        </n-descriptions>

        <!-- LLM 返回 -->
        <n-divider v-if="logDetailData.llm_response" title-placement="left">{{ t('cron-jobs.cronJobs.logDetail.llmRequest') }} {{ t('cron-jobs.cronJobs.logDetail.generatedContent') }}</n-divider>
        <n-descriptions v-if="logDetailData.llm_response" bordered :column="2" size="small" style="margin-bottom: 16px">
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.generatedContent')" :span="2">
            <pre style="white-space: pre-wrap; font-size: 12px;">{{ logDetailData.llm_response.content }}</pre>
          </n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.duration')">{{ logDetailData.llm_response.duration }}s</n-descriptions-item>
          <n-descriptions-item v-if="logDetailData.llm_response.error" :label="t('cron-jobs.cronJobs.logDetail.error')" :span="2">
            <pre style="white-space: pre-wrap; color: #d03050; font-size: 12px;">{{ logDetailData.llm_response.error }}</pre>
          </n-descriptions-item>
        </n-descriptions>

        <!-- 基本详情（_minimal 兜底 details 时显示，仅有 message/error/task_type 等基础字段） -->
        <n-alert v-if="logDetailData._minimal && !logDetailData.llm_request && !logDetailData.context && !logDetailData.send_result" type="info" style="margin-bottom: 16px;">
          <div style="font-size: 13px;">
            <div><strong>{{ t('cron-jobs.cronJobs.logDetail.taskType') }}</strong>{{ logDetailData.task_type }}</div>
            <div v-if="logDetailData.summary"><strong>{{ t('cron-jobs.cronJobs.logDetail.description') }}</strong>{{ logDetailData.summary }}</div>
            <div v-if="logDetailData.error"><strong>{{ t('cron-jobs.cronJobs.logDetail.error') }}：</strong>{{ logDetailData.error }}</div>
            <div v-if="logDetailData.failure_stage"><strong>{{ t('cron-jobs.cronJobs.logDetail.failureStage') }}</strong>{{ logDetailData.failure_stage }}</div>
            <div v-if="logDetailData.duration"><strong>{{ t('cron-jobs.cronJobs.logDetail.duration') }}：</strong>{{ logDetailData.duration }}s</div>
            <div v-if="logDetailData.session_id"><strong>Session：</strong><span style="font-family: monospace; font-size: 12px;">{{ logDetailData.session_id }}</span></div>
            <div v-if="logDetailData.platform"><strong>{{ t('cron-jobs.cronJobs.logDetail.platform') }}：</strong>{{ logDetailData.platform }}</div>
            <div style="margin-top: 6px; font-size: 12px; color: #999;">
              {{ t('cron-jobs.cronJobs.logDetail.simplifiedLog') }}
            </div>
          </div>
        </n-alert>

        <!-- 上下文 -->
        <n-divider v-if="logDetailData.context" title-placement="left">{{ t('cron-jobs.cronJobs.logDetail.context') }}</n-divider>
        <div v-if="logDetailData.context" style="margin-bottom: 16px;">
          <n-tag type="info" size="small">{{ t('cron-jobs.cronJobs.logDetail.sessionMessageCount', { count: logDetailData.context.session_count }) }}</n-tag>
          <div v-if="logDetailData.context.session_messages && logDetailData.context.session_messages.length" style="max-height: 300px; overflow-y: auto; border: 1px solid var(--theme-border); border-radius: 4px; padding: 8px; margin-top: 4px;">
            <div v-for="(msg, idx) in logDetailData.context.session_messages" :key="idx" style="margin-bottom: 4px; font-size: 12px;">
              <n-tag :type="msg.role === 'user' ? 'info' : 'default'" :class="msg.role === 'assistant' ? 'tag-assistant' : ''" size="tiny">{{ msg.role }}</n-tag>
              <span style="margin-left: 4px;">{{ msg.content }}</span>
            </div>
          </div>
        </div>

        <!-- 发送结果 -->
        <n-divider v-if="logDetailData.send_result" title-placement="left">{{ t('cron-jobs.cronJobs.logDetail.sendResult') }}</n-divider>
        <n-descriptions v-if="logDetailData.send_result" bordered :column="2" size="small">
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.status')">
            <n-tag :type="logDetailData.send_result.success ? 'success' : 'error'" size="small">
              {{ logDetailData.send_result.success ? t('cron-jobs.cronJobs.logDetail.success') : t('cron-jobs.cronJobs.logDetail.failed') }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.message')">{{ logDetailData.send_result.message || '-' }}</n-descriptions-item>
          <n-descriptions-item :label="t('cron-jobs.cronJobs.logDetail.finalMessage')" :span="2">
            <pre style="white-space: pre-wrap; font-size: 12px; max-height: 200px; overflow-y: auto;">{{ logDetailData.send_result.final_message }}</pre>
          </n-descriptions-item>
        </n-descriptions>
      </div>
    </n-modal>

    <!-- 预览提示词弹窗 -->
    <n-modal v-model:show="showPreview" preset="card" :title="t('cron-jobs.cronJobs.logDetail.previewPrompt')" fullscreen>
      <n-spin :show="previewing">
        <n-form label-placement="left" label-width="100">
          <n-form-item :label="t('cron-jobs.cronJobs.logDetail.systemPrompt')">
            <n-input
              :value="previewData.system_prompt"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 10 }"
              readonly
            />
          </n-form-item>
          <n-form-item :label="t('cron-jobs.cronJobs.logDetail.userPrompt')">
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
          <n-form-item :label="t('cron-jobs.cronJobs.logDetail.contextSummary')" v-if="previewData.context_summary">
            <n-tag type="info">{{ previewData.context_summary }}</n-tag>
          </n-form-item>
        </n-form>

        <!-- 实际上下文数据 -->
        <n-divider title-placement="left" v-if="previewData.context_data">{{ t('cron-jobs.cronJobs.logDetail.actualContext') }}</n-divider>
        <div v-if="previewData.context_data" class="context-data-section">
          <!-- Session 消息 -->
          <div v-if="previewData.context_data.session_messages && previewData.context_data.session_messages.length > 0" class="context-block">
            <div class="context-block-title">
              <n-tag type="info" size="small">{{ t('cron-jobs.cronJobs.logDetail.sessionMessages') }}</n-tag>
              <span class="context-count">{{ previewData.context_data.session_messages.length }} {{ t('cron-jobs.cronJobs.form.count').replace('：', '') }}</span>
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
              <n-tag type="success" size="small">{{ t('cron-jobs.cronJobs.logDetail.recallTag') }}</n-tag>
              <span class="context-count">{{ previewData.context_data.recall_results.length }} {{ t('cron-jobs.cronJobs.form.count').replace('：', '') }}</span>
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
              <n-tag type="warning" size="small">{{ t('cron-jobs.cronJobs.logDetail.reflectTag') }}</n-tag>
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
            :description="t('cron-jobs.cronJobs.logDetail.noContextData')"
            size="small"
          />
        </div>
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed, h } from 'vue'
import { useMessage, useDialog, NButton } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import api from '../api'
import TimeFormatSelector from '../components/TimeFormatSelector.vue'

const { t } = useI18n()
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

// 占位符选项
const placeholderOptions = [
  { label: '{session}', value: '{session}', desc: '最近对话' },
  { label: '{memory}', value: '{memory}', desc: '记忆反思' },
  { label: '{weather}', value: '{weather}', desc: '天气感知' },
  { label: '{time}', value: '{time}', desc: '当前时间' },
]

function insertPlaceholder(placeholder) {
  // 简单追加到 user_prompt 末尾
  const cur = formData.value.user_prompt || ''
  formData.value.user_prompt = cur + placeholder
}

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

// 日志
const showJobLogs = ref(false)
const jobLogs = ref([])
const jobLogsLoading = ref(false)
const jobLogsName = ref('')

// 日志详情
const showLogDetail = ref(false)
const logDetailData = ref(null)

function viewLogDetail(log) {
  const details = typeof log.details === 'string' ? JSON.parse(log.details) : (log.details || {})
  // 兜底：历史日志 details 为 NULL 时构造一个最简 details，确保弹窗能展示基本信息
  const baseDetails = details._minimal || details.llm_request || details.context || details.send_result
    ? details
    : {
        ...details,
        _minimal: true,
        task_type: log.task_type,
        summary: log.message,
        error: log.error,
        duration: log.duration,
      }
  logDetailData.value = {
    ...baseDetails,
    _status: log.status,
    _message: log.message,
    _error: log.error,
    _duration: log.duration,
    _created_at: log.created_at
  }
  showLogDetail.value = true
}
const jobLogsColumns = computed(() => [
  { title: t('cron-jobs.cronJobs.logDetail.details'), key: 'details', width: 70, render: (row) => row.details ? h(NButton, { size: 'tiny', onClick: () => viewLogDetail(row) }, { default: () => t('cron-jobs.cronJobs.logDetail.details') }) : '-' },
  { title: t('cron-jobs.cronJobs.logDetail.time'), key: 'created_at', width: 140, render: (row) => formatTime(row.created_at) },
  { title: t('cron-jobs.cronJobs.logDetail.status'), key: 'status', width: 80, render: (row) => row.status === 'success' ? t('cron-jobs.cronJobs.logDetail.success') : row.status === 'skipped' ? t('cron-jobs.cronJobs.logDetail.skipped') : t('cron-jobs.cronJobs.logDetail.failed') },
  { title: t('cron-jobs.cronJobs.logDetail.message'), key: 'message', width: 200, ellipsis: { tooltip: true } },
  { title: t('cron-jobs.cronJobs.logDetail.error'), key: 'error', width: 120, ellipsis: { tooltip: true }, render: (row) => row.error || '-' },
  { title: t('cron-jobs.cronJobs.logDetail.duration'), key: 'duration', width: 70, render: (row) => row.duration ? `${row.duration.toFixed(1)}s` : '-' }
])

// 日志分页
const jobLogsPage = ref(1)
const jobLogsPageSize = 20
const jobLogsTotalPages = computed(() => Math.max(1, Math.ceil(jobLogs.value.length / jobLogsPageSize)))
const jobLogsPaged = computed(() => {
  const start = (jobLogsPage.value - 1) * jobLogsPageSize
  return jobLogs.value.slice(start, start + jobLogsPageSize)
})

const platformOptions = computed(() => [
  { label: t('cron-jobs.cronJobs.platforms.weixin'), value: 'weixin' },
  { label: t('cron-jobs.cronJobs.platforms.feishu'), value: 'feishu' },
  { label: t('cron-jobs.cronJobs.platforms.cli'), value: 'cli' }
])

const WEEKDAY_NAMES = ['一', '二', '三', '四', '五', '六', '日']

const timeFormatOptions = [
  { label: '无', value: '', preview: () => '' },
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
  send_mark: '凯莉',
  time_format: '%H:%M 星期{weekday}',
  cooldown_enabled: false,
  cooldown_minutes: 10,
  fixed_message: '',
  max_tokens: 0
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
  hindsight_reflect_query: '',
  weather_enabled: false,
  weather_days: 0,
  time_format: '%H:%M 星期{weekday}'
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

// 天气预报天数显示
const weatherDaysLabel = computed(() => {
  const v = Number(contextConfig.value.weather_days)
  if (v === 2) return '今+明'
  if (v === 3) return '今+明+后'
  if (v === 4) return '今+明+后+大后'
  return '今天实况'
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
      label: `${s.title || s.id} (${s.message_count || 0} ${t('cron-jobs.cronJobs.form.sessionMessagesLabel')})`,
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
      message.success(t('cron-jobs.cronJobs.messages.fillSystemPromptSuccess'))
    } else {
      message.warning(t('cron-jobs.cronJobs.messages.noDefaultSystemPrompt'))
    }
  } catch (e) {
    message.error(t('cron-jobs.cronJobs.messages.loadDefaultPromptFailed'))
  }
}

async function fillDefaultUserPrompt() {
  try {
    const data = await api.get('/config/prompts')
    if (data.generation) {
      formData.value.user_prompt = data.generation
      message.success(t('cron-jobs.cronJobs.messages.fillUserPromptSuccess'))
    } else {
      message.warning(t('cron-jobs.cronJobs.messages.noDefaultUserPrompt'))
    }
  } catch (e) {
    message.error(t('cron-jobs.cronJobs.messages.loadDefaultPromptFailed'))
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
        cronParseResult.value = { frequency: result.message || t('cron-jobs.cronJobs.messages.parseFailed'), next_runs: [] }
      }
    } catch (e) {
      cronParseResult.value = { frequency: t('cron-jobs.cronJobs.messages.parseFailed'), next_runs: [] }
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
    send_mark: '凯莉',
    time_format: '%H:%M 星期{weekday}',
    cooldown_enabled: false,
    cooldown_minutes: 10,
    fixed_message: ''
  }
  contextConfig.value = {
    session_enabled: true,
    session_limit: 20,
    include_tool: false,
    hindsight_recall_enabled: false,
    hindsight_recall_query: '',
    hindsight_recall_limit: 10,
    hindsight_reflect_enabled: false,
    hindsight_reflect_query: '',
    weather_enabled: false
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
    message.warning(t('cron-jobs.cronJobs.messages.fillNameAndSchedule'))
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
      message.success(t('cron-jobs.cronJobs.messages.taskUpdated'))
    } else {
      await api.post('/cron', submitData)
      message.success(t('cron-jobs.cronJobs.messages.taskCreated'))
    }
    showCreate.value = false
    editingJob.value = null
    await loadJobs()
  } catch (e) {
    message.error(t('cron-jobs.cronJobs.messages.saveFailed') + ': ' + (e?.detail || ''))
  } finally {
    saving.value = false
  }
}

async function toggleJob(job) {
  try {
    await api.post(`/cron/${job.id}/toggle`)
    message.success(job.enabled ? t('cron-jobs.cronJobs.messages.taskPaused') : t('cron-jobs.cronJobs.messages.taskResumed'))
    await loadJobs()
  } catch (e) {
    message.error(t('cron-jobs.cronJobs.messages.toggleFailed'))
  }
}

async function runJob(job) {
  job.running = true
  try {
    await api.post(`/cron/${job.id}/run`)
    message.success(t('cron-jobs.cronJobs.messages.taskTriggered'))
  } catch (e) {
    message.error(t('cron-jobs.cronJobs.messages.triggerFailed') + ': ' + (e?.detail || ''))
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
      send_mark: job.send_mark || '',
      time_format: job.time_format || '',
      cooldown_enabled: job.cooldown_enabled || false,
      cooldown_minutes: job.cooldown_minutes || 10,
      fixed_message: job.fixed_message || '',
      max_tokens: job.max_tokens || 0
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
      send_mark: job.send_mark || '',
      time_format: job.time_format || '',
      fixed_message: job.fixed_message || '',
      max_tokens: job.max_tokens || 0
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
  jobLogsPage.value = 1
  try {
    // 用 job_id 精确查询，改名不影响日志
    const data = await api.get('/task-logs', { params: { task_type: 'cron_run', job_id: job.id, page_size: 100 } })
    jobLogs.value = data.items || []
  } catch (e) {
    message.error(t('cron-jobs.cronJobs.messages.loadLogsFailed'))
    jobLogs.value = []
  } finally {
    jobLogsLoading.value = false
  }
}

function deleteJob(job) {
  dialog.warning({
    title: t('cron-jobs.cronJobs.confirmDelete'),
    content: t('cron-jobs.cronJobs.confirmDeleteMessage', { name: job.name }),
    positiveText: t('common.common.delete'),
    negativeText: t('common.common.cancel'),
    onPositiveClick: async () => {
      try {
        await api.delete(`/cron/${job.id}`)
        message.success(t('cron-jobs.cronJobs.messages.taskDeleted'))
        await loadJobs()
      } catch (e) {
        message.error(t('cron-jobs.cronJobs.messages.deleteFailed'))
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
    message.error(t('cron-jobs.cronJobs.messages.loadDefaultPromptConfigFailed'))
  }
}

async function saveDefaultPrompts() {
  savingDefaultPrompts.value = true
  try {
    await api.put('/config/prompts', {
      system: defaultPromptsData.value.system_prompt,
      generation: defaultPromptsData.value.user_prompt
    })
    message.success(t('cron-jobs.cronJobs.messages.defaultPromptConfigSaved'))
    showDefaultPrompts.value = false
    // 重新加载默认提示词
    await loadDefaultPrompt()
  } catch (e) {
    message.error(t('cron-jobs.cronJobs.messages.saveFailed') + ': ' + (e?.detail || ''))
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
    message.error(t('cron-jobs.cronJobs.messages.previewFailed') + ': ' + (e?.detail || ''))
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
    message.error(t('cron-jobs.cronJobs.messages.previewFailed') + ': ' + (e?.detail || ''))
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
  parts.push(`weather=${config.weather_enabled ? 'true' : 'false'}`)
  if (config.weather_enabled) {
    parts.push(`weather_days=${Number(config.weather_days) || 0}`)
  }
  if (config.time_format) {
    parts.push(`time_format=${encodeURIComponent(config.time_format)}`)
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
    hindsight_reflect_query: '',
    weather_enabled: false,
    weather_days: 0,
    time_format: '%H:%M 星期{weekday}'
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
      case 'weather':
        config.weather_enabled = value === 'true'
        break
      case 'weather_days':
        config.weather_days = parseInt(value) || 0
        break
      case 'time_format':
        config.time_format = decodeURIComponent(value)
        break
    }
  }

  return { config, userPrompt }
}

onMounted(() => {
  // 并行加载，提高页面切换速度
  Promise.all([
    loadJobs(),
    loadDefaultPrompt(),
    loadSoulMd()
  ])
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
  background: var(--theme-card-bg);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s;
}

.job-card:hover {
  box-shadow: 0 4px 20px rgba(var(--theme-primary-rgb), 0.12);
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
  color: var(--theme-text);
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
  align-items: center;
}

.cron-parse-result {
  background: rgba(var(--theme-primary-rgb), 0.06);
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
}

.cron-freq {
  color: var(--theme-primary);
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
  color: #4a90d9;
}

.context-msg-role.assistant {
  color: #ff9a9e;
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
  justify-content: center;
  padding: 6px 12px;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--theme-card-bg);
  min-width: 80px;
  min-height: 48px;
}

.time-format-chip:hover {
  border-color: var(--theme-primary);
  background: var(--theme-tag-bg);
}

.time-format-chip.active {
  border-color: var(--theme-primary);
  background: var(--theme-tag-bg);
  box-shadow: 0 0 0 1px var(--theme-primary);
}

.chip-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 2px;
}

.time-format-chip.active .chip-label {
  color: var(--theme-primary);
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
    border-radius: 12px;
  }

  .job-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .job-name {
    font-size: 15px;
    flex: 1;
  }

  .job-meta {
    gap: 6px;
    font-size: 11px;
  }

  .job-actions {
    flex-wrap: wrap;
    gap: 6px;
  }

  .job-actions .n-button {
    flex: 1;
    min-width: 60px;
  }

  /* 编辑弹窗移动端优化 */
  :deep(.n-form-item) {
    margin-bottom: 12px;
  }

  :deep(.n-form-item-label) {
    font-size: 13px;
    padding-bottom: 4px;
  }

  :deep(.n-input),
  :deep(.n-select),
  :deep(.n-input-number) {
    width: 100% !important;
    max-width: 100% !important;
  }

  :deep(.n-radio-group) {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .time-format-selector {
    gap: 6px;
  }

  /* 表格横向滚动 */
  :deep(.n-data-table) {
    overflow-x: auto;
  }

  /* 表格容器底部留出分页空间 */
  :deep(.n-spin-content) {
    padding-bottom: 80px;
  }

  :deep(.n-data-table-wrapper) {
    min-width: 600px;
  }

  /* 分页固定在底部，避免被浏览器菜单栏遮挡 */
  .log-pagination {
    position: sticky;
    bottom: 0;
    background: var(--theme-card-bg);
    padding: 12px 0;
    padding-bottom: calc(12px + env(safe-area-inset-bottom, 20px));
    border-top: 1px solid var(--theme-border);
    z-index: 10;
  }

  .time-format-chip {
    padding: 5px 8px;
    min-width: 70px;
    font-size: 12px;
    flex: 1 1 calc(50% - 8px);
    min-width: 0;
  }

  .chip-preview {
    font-size: 11px;
  }

  /* 提示词输入框移动端 */
  :deep(.n-input--textarea textarea) {
    min-height: 80px;
  }

  .context-status {
    flex-direction: column;
    align-items: flex-start;
  }

  .log-pagination {
    flex-direction: column;
    gap: 8px;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--theme-card-bg);
    padding: 12px 16px;
    padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
    border-top: 1px solid var(--theme-border);
    z-index: 100;
    box-shadow: 0 -2px 8px rgba(0,0,0,0.06);
  }
}

.tag-assistant {
  --n-color: #fff0f3 !important;
  --n-color-hover: #ffe0e6 !important;
  --n-text-color: #ff9a9e !important;
  --n-border: 1px solid #ffd0d6 !important;
}

.log-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px 0 8px;
}

.log-total {
  font-size: 12px;
  color: #999;
}
</style>
