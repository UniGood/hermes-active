<template>
  <div class="active-consciousness-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 状态 -->
      <n-tab-pane name="status" :tab="t('activeConsciousness.tabs.status')">
        <!-- 状态概览 -->
        <div class="section-title">
          <n-icon size="18"><StatsChartOutline /></n-icon>
          <span>{{ t('activeConsciousness.status.overview') }}</span>
        </div>
        <n-grid :cols="isMobile ? 1 : 4" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.status.heartbeat')">
              <template #header-extra>
                <span :class="['breathing-dot', heartbeatHealthy ? 'dot-green' : 'dot-red']"></span>
              </template>
              <n-statistic :label="t('activeConsciousness.status.todayHeartbeat')" :value="status.heartbeat.count" />
              <div style="margin-top: 4px; font-size: 11px; color: var(--theme-text-muted);">
                {{ t('activeConsciousness.status.lastTime') }}{{ formatTimeHMS(status.heartbeat.last_at) || t('activeConsciousness.messages.empty') }}
              </div>
              <div style="margin-top: 4px; font-size: 11px; color: var(--theme-text-secondary);">
                {{ t('activeConsciousness.status.nextTime') }}{{ nextHeartbeatDisplay }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.status.longingScore')">
              <n-statistic :value="status.longing.score" :precision="3">
                <template #suffix>
                  <n-tag :type="longingTagType" size="small">{{ status.longing.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="Number((status.longing.score * 100).toFixed(1))" :color="longingColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
              <div style="margin-top: 4px; font-size: 11px; color: var(--theme-text-muted);">
                {{ t('activeConsciousness.status.silence', { minutes: status.longing.silence_minutes ? Math.round(status.longing.silence_minutes) : '-' }) }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.status.chatHeat')">
              <n-statistic :value="status.chat_heat.heat" :precision="2">
                <template #suffix>
                  <n-tag :type="heatTagType" size="small">{{ status.chat_heat.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="chatHeatPercentage" :color="heatProgressColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
              <div style="margin-top: 4px; font-size: 11px; color: var(--theme-text-muted);">
                {{ t('activeConsciousness.status.recentHour', { count: status.chat_heat.recent_count || 0 }) }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.status.emotionalIntensity')">
              <n-statistic :value="status.emotional_intensity.intensity" :precision="3">
                <template #suffix>
                  <n-tag size="small">{{ status.emotional_intensity.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="status.emotional_intensity.intensity * 100" :color="intensityColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>

        </n-grid>

        <!-- 情绪系统 -->
        <div class="section-title" style="margin-top: 16px;">
          <n-icon size="18"><ColorPaletteOutline /></n-icon>
          <span>{{ t('activeConsciousness.emotion.system') }}</span>
        </div>
        <n-grid :cols="isMobile ? 1 : 2" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.emotion.stateVA')">
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 13px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.emotion.valence') }}</span>
                    <span style="font-weight: 600;">{{ status.emotion_state?.valence ?? '-' }}</span>
                  </div>
                  <n-progress :percentage="(status.emotion_state?.valence ?? 0) * 100" :show-indicator="false" :height="8"
                    :color="valenceColor" />
                </div>
                <div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 13px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.emotion.arousal') }}</span>
                    <span style="font-weight: 600;">{{ status.emotion_state?.arousal ?? '-' }}</span>
                  </div>
                  <n-progress :percentage="(status.emotion_state?.arousal ?? 0) * 100" :show-indicator="false" :height="8"
                    :color="arousalColor" />
                </div>
                <div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 13px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.emotion.socialNeed') }}</span>
                    <span style="font-weight: 600;">{{ status.emotion_state?.social_need ?? '-' }}</span>
                  </div>
                  <n-progress :percentage="(status.emotion_state?.social_need ?? 0) * 100" :show-indicator="false" :height="8"
                    :color="socialNeedColor" />
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                  <span style="font-size: 13px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.emotion.dominant') }}</span>
                  <n-tag :type="getEmotionTagType(status.emotion_state?.dominant)" size="small">
                    {{ emotionLabelCn(status.emotion_state?.dominant) }}
                  </n-tag>
                </div>
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.decision.configThreshold')">
              <div style="display: flex; flex-direction: column; gap: 12px;">
                <div>
                  <div style="font-size: 13px; color: var(--theme-text-secondary); margin-bottom: 8px;">{{ t('activeConsciousness.decision.threshold') }}</div>
                  <div style="display: flex; gap: 12px;">
                    <div style="flex: 1; text-align: center;">
                      <div style="font-size: 18px; font-weight: bold; color: var(--theme-success);">{{ decisionConfig.send_threshold }}</div>
                      <div style="font-size: 11px; color: var(--theme-text-muted);">{{ t('activeConsciousness.decision.send') }}</div>
                    </div>
                    <div style="flex: 1; text-align: center;">
                      <div style="font-size: 18px; font-weight: bold; color: var(--theme-error);">{{ decisionConfig.memory_threshold }}</div>
                      <div style="font-size: 11px; color: var(--theme-text-muted);">{{ t('activeConsciousness.decision.memory') }}</div>
                    </div>
                  </div>
                </div>
                <n-divider style="margin: 0;" />
                <div>
                  <div style="font-size: 13px; color: var(--theme-text-secondary); margin-bottom: 8px;">{{ t('activeConsciousness.decision.frequencyLimit') }}</div>
                  <div style="display: flex; gap: 12px;">
                    <div style="flex: 1;">
                      <div style="display: flex; justify-content: space-between;">
                        <span style="font-size: 12px;">{{ t('activeConsciousness.decision.thisHour') }}</span>
                        <span style="font-weight: 600;">{{ status.decision.hour_sent_count }}/{{ decisionConfig.max_per_hour }}</span>
                      </div>
                      <n-progress :percentage="frequencyHourPercentage" :show-indicator="false" :height="4"
                        :color="frequencyHourPercentage >= 100 ? '#d03050' : '#18a058'" />
                    </div>
                    <div style="flex: 1;">
                      <div style="display: flex; justify-content: space-between;">
                        <span style="font-size: 12px;">{{ t('activeConsciousness.decision.today') }}</span>
                        <span style="font-weight: 600;">{{ status.sent_stats.today }}/{{ decisionConfig.max_per_day }}</span>
                      </div>
                      <n-progress :percentage="frequencyDayPercentage" :show-indicator="false" :height="4"
                        :color="frequencyDayPercentage >= 100 ? '#d03050' : '#18a058'" />
                    </div>
                  </div>
                </div>
                <n-divider style="margin: 0;" />
                <div>
                  <div style="font-size: 13px; color: var(--theme-text-secondary); margin-bottom: 8px;">{{ t('activeConsciousness.decision.protection') }}</div>
                  <div style="display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; justify-content: space-between;">
                      <span style="font-size: 12px;">{{ t('activeConsciousness.decision.cooldown') }}</span>
                      <n-tag :type="isCoolingDown ? 'warning' : 'success'" size="small">
                        {{ isCoolingDown ? t('activeConsciousness.decision.coolingDown') : t('activeConsciousness.decision.normal') }}
                      </n-tag>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                      <span style="font-size: 12px;">{{ t('activeConsciousness.decision.userJustSent') }}</span>
                      <n-tag :type="userJustSent ? 'warning' : 'success'" size="small">
                        {{ userJustSent ? t('activeConsciousness.decision.waiting') : t('activeConsciousness.decision.normal') }}
                      </n-tag>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                      <span style="font-size: 12px;">{{ t('activeConsciousness.decision.heatProtection') }}</span>
                      <n-tag :type="heatProtected ? 'warning' : 'success'" size="small">
                        {{ heatProtected ? t('activeConsciousness.decision.triggered') : t('activeConsciousness.decision.normal') }}
                      </n-tag>
                    </div>
                  </div>
                </div>
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>

        <!-- LLM 统计 -->
        <div class="section-title" style="margin-top: 16px;">
          <n-icon size="18"><AnalyticsOutline /></n-icon>
          <span>{{ t('activeConsciousness.llmStats.title') }}</span>
        </div>
        <n-grid :cols="isMobile ? 1 : 3" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.llmStats.emotionLLM')">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.recentEval') }}</span>
                  <n-tag :type="getEmotionTagType(status.llm_stats?.last_emotion_dominant)" size="small">
                    {{ emotionLabelCn(status.llm_stats?.last_emotion_dominant) || '-' }}
                  </n-tag>
                </div>
                <n-divider style="margin: 4px 0;" />
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.today') }}</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.emotion_today ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.thisWeek') }}</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.emotion_week ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.thisMonth') }}</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.emotion_month ?? 0 }}</span>
                </div>
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.llmStats.thoughtsAndSend')">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="font-size: 11px; color: var(--theme-text-muted); font-weight: 600; letter-spacing: 1px;">{{ t('activeConsciousness.llmStats.llmThoughts') }}</div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.todayCalls') }}</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.thought_today ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.todayGenerated') }}</span>
                  <span style="font-size: 14px; font-weight: bold; color: var(--theme-success);">{{ status.llm_stats?.thought_generated_today ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.weekCalls') }}</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.thought_week ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.weekGenerated') }}</span>
                  <span style="font-size: 14px; font-weight: bold; color: var(--theme-success);">{{ status.llm_stats?.thought_generated_week ?? 0 }}</span>
                </div>
                <n-divider style="margin: 4px 0;" />
                <div style="font-size: 11px; color: var(--theme-text-muted); font-weight: 600; letter-spacing: 1px;">{{ t('activeConsciousness.llmStats.messageSend') }}</div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.today') }}</span>
                  <span style="font-size: 14px; font-weight: bold; color: var(--theme-success);">{{ status.sent_stats.today ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.thisWeek') }}</span>
                  <span style="font-size: 14px; font-weight: bold; color: var(--theme-success);">{{ status.sent_stats.week ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.thisMonth') }}</span>
                  <span style="font-size: 14px; font-weight: bold; color: var(--theme-success);">{{ status.sent_stats.month ?? 0 }}</span>
                </div>
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" :title="t('activeConsciousness.llmStats.totalLLMCalls')">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.today') }}</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ (status.llm_stats?.emotion_today ?? 0) + (status.llm_stats?.thought_today ?? 0) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.thisWeek') }}</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ (status.llm_stats?.emotion_week ?? 0) + (status.llm_stats?.thought_week ?? 0) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: var(--theme-text-secondary);">{{ t('activeConsciousness.llmStats.thisMonth') }}</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ (status.llm_stats?.emotion_month ?? 0) + (status.llm_stats?.thought_month ?? 0) }}</span>
                </div>
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-tab-pane>
      <n-tab-pane name="logs" :tab="t('activeConsciousness.tabs.logs')" style="overflow: visible;">
        <n-tabs type="line" animated style="overflow: visible;">
          <n-tab-pane name="heartbeats" :tab="t('activeConsciousness.tabs.heartbeatLogs')" style="overflow: visible;">
            <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
              <n-date-picker v-model:value="heartbeatDate" type="date" clearable
                @update:value="onHeartbeatDateChange" style="width: 160px" />
              <n-input-number v-model:value="heartbeatIdFilter" :placeholder="t('activeConsciousness.logFilters.heartbeatIdPlaceholder')" clearable
                :show-button="false" style="width: 120px"
                @update:value="() => { saveFilters(); loadHeartbeats(1) }" />
              <n-button size="small" @click="heartbeatDate = Date.now(); heartbeatIdFilter = null; saveFilters(); loadHeartbeats(1)">{{ t('activeConsciousness.logFilters.today') }}</n-button>
              <n-button size="small" quaternary @click="heartbeatDate = null; heartbeatIdFilter = null; saveFilters(); loadHeartbeats(1)">{{ t('activeConsciousness.logFilters.all') }}</n-button>
            </div>
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
              <n-data-table :columns="heartbeatColumns" :data="heartbeats.items" :pagination="heartbeatPagination" @update:page="loadHeartbeats" :scroll-x="1030" remote v-model:checked-row-keys="heartbeatCheckedKeys" :row-key="row => row.id" />
              <n-popconfirm v-if="heartbeatCheckedKeys.length" @positive-click="batchDeleteHeartbeats" :positive-text="t('activeConsciousness.batch.positiveText')" :negative-text="t('activeConsciousness.batch.negativeText')">
                <template #trigger>
                  <n-button size="small" type="error" style="margin-top: 8px;">{{ t('activeConsciousness.batch.delete') }} ({{ heartbeatCheckedKeys.length }})</n-button>
                </template>
                {{ t('activeConsciousness.batch.confirmHeartbeats', { count: heartbeatCheckedKeys.length }) }}
              </n-popconfirm>
            </div>
          </n-tab-pane>
          <n-tab-pane name="thoughts" :tab="t('activeConsciousness.tabs.thoughtLogs')" style="overflow: visible;">
            <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
              <n-date-picker v-model:value="thoughtDate" type="date" clearable
                @update:value="onThoughtDateChange" style="width: 160px" />
              <n-input-number v-model:value="thoughtIdFilter" :placeholder="t('activeConsciousness.logFilters.thoughtIdPlaceholder')" clearable
                :show-button="false" style="width: 120px"
                @update:value="() => { saveFilters(); loadThoughts(1) }" />
              <n-input-number v-model:value="thoughtHeartbeatIdFilter" :placeholder="t('activeConsciousness.logFilters.heartbeatIdPlaceholder')" clearable
                :show-button="false" style="width: 120px"
                @update:value="() => { saveFilters(); loadThoughts(1) }" />
              <n-button size="small" @click="thoughtDate = Date.now(); thoughtIdFilter = null; thoughtHeartbeatIdFilter = null; saveFilters(); loadThoughts(1)">{{ t('activeConsciousness.logFilters.today') }}</n-button>
              <n-button size="small" quaternary @click="thoughtDate = null; thoughtIdFilter = null; thoughtHeartbeatIdFilter = null; saveFilters(); loadThoughts(1)">{{ t('activeConsciousness.logFilters.all') }}</n-button>
            </div>
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
              <n-data-table :columns="thoughtColumns" :data="thoughts.items" :pagination="thoughtPagination" @update:page="loadThoughts" :scroll-x="1250" remote :loading="thoughtsLoading" v-model:checked-row-keys="thoughtCheckedKeys" :row-key="row => row.id" />
              <n-popconfirm v-if="thoughtCheckedKeys.length" @positive-click="batchDeleteThoughts" :positive-text="t('activeConsciousness.batch.positiveText')" :negative-text="t('activeConsciousness.batch.negativeText')">
                <template #trigger>
                  <n-button size="small" type="error" style="margin-top: 8px;">{{ t('activeConsciousness.batch.delete') }} ({{ thoughtCheckedKeys.length }})</n-button>
                </template>
                {{ t('activeConsciousness.batch.confirmThoughts', { count: thoughtCheckedKeys.length }) }}
              </n-popconfirm>
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-tab-pane>

      <!-- Tab 3: 配置 -->
      <n-tab-pane name="config" :tab="t('activeConsciousness.tabs.config')">
        <n-card :title="t('activeConsciousness.configTab.title')" style="margin-bottom: 16px">
          <!-- 总开关 -->
          <n-form-item :label="t('activeConsciousness.configTab.enable')">
            <n-switch v-model:value="config.enabled" />
          </n-form-item>

          <template v-if="config.enabled">
            <!-- 基础设置 -->
            <n-divider>{{ t('activeConsciousness.configTab.basicSettings') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.enableHeartbeat')">
              <n-switch v-model:value="config.active.enabled" />
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.heartbeatInterval')">
              <n-input-number v-model:value="config.active.heartbeat_interval" :min="60" :max="3600" />
            </n-form-item>
            <!-- 发送标记 -->
            <n-divider>{{ t('activeConsciousness.configTab.sendMark') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.enableSendMark')">
              <n-switch v-model:value="config.active.send_mark_enabled" />
              <span class="form-item-hint">{{ t('activeConsciousness.configTab.sendMarkHint') }}</span>
            </n-form-item>
            <template v-if="config.active.send_mark_enabled">
              <n-form-item :label="t('activeConsciousness.configTab.sendTag')">
                <n-input v-model:value="config.active.send_tag" :placeholder="t('activeConsciousness.configTab.sendTag')" />
              </n-form-item>
              <n-form-item :label="t('activeConsciousness.configTab.timeFormat')">
                <n-input v-model:value="config.active.time_format" placeholder="%H:%M" />
                <span class="form-item-hint">{{ t('activeConsciousness.configTab.timeFormatHint') }}</span>
              </n-form-item>
              <n-form-item :label="t('activeConsciousness.configTab.formatPreview')">
                <n-tag type="info" size="large">{{ sendMarkPreview }}</n-tag>
              </n-form-item>
            </template>

            <!-- 决策阈值 -->
            <n-divider>{{ t('activeConsciousness.configTab.decisionThreshold') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.sendThreshold')">
              <n-input-number v-model:value="config.decision.send_threshold" :min="0" :max="1" :step="0.1" />
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.memoryThreshold')">
              <n-input-number v-model:value="config.decision.memory_threshold" :min="0" :max="1" :step="0.1" />
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.maxPerHour')">
              <n-input-number v-model:value="config.decision.max_per_hour" :min="1" :max="1000" />
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.maxPerDay')">
              <n-input-number v-model:value="config.decision.max_per_day" :min="1" :max="1000" />
            </n-form-item>

            <!-- 发送保护 -->
            <n-divider>{{ t('activeConsciousness.configTab.sendProtection') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.noSendWindow')">
              <n-input-number v-model:value="config.active.no_send_after_user_msg_minutes" :min="1" :max="60" />
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.heatThreshold')">
              <n-input-number v-model:value="config.active.no_send_while_heat_above" :min="0" :max="1000" :step="0.1" />
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.vibeThreshold')">
              <n-input-number v-model:value="config.active.no_send_while_vibe_below" :min="0" :max="1" :step="0.1" />
            </n-form-item>

            <!-- 念头存储 -->
            <n-divider>{{ t('activeConsciousness.configTab.thoughtStorage') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.storeToHindsight')">
              <n-switch v-model:value="config.thought.retain_enabled" />
              <span style="margin-left: 8px; font-size: 12px; color: var(--theme-text-muted);">{{ t('activeConsciousness.configTab.hindsightHint') }}</span>
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.bankId')">
              <n-input v-model:value="config.hindsight.store.bank_id" placeholder="hermes-active" />
              <span style="margin-left: 8px; font-size: 12px; color: var(--theme-text-muted);">{{ t('activeConsciousness.configTab.bankIdHint') }}</span>
            </n-form-item>

            <!-- 上下文收集配置 -->
            <n-divider>{{ t('activeConsciousness.configTab.contextCollection') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.sourcePlatform')">
              <n-select v-model:value="config.context.sources" multiple :options="platformOptions" />
              <span class="form-item-hint">{{ t('activeConsciousness.configTab.sourcePlatformHint') }}</span>
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.filterToolMessages')">
              <n-switch v-model:value="config.context.filter_tool_messages" />
              <span class="form-item-hint">{{ t('activeConsciousness.configTab.filterToolHint') }}</span>
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.conversationLimit')">
              <n-input-number v-model:value="config.context.conversation_limit" :min="10" :max="1000" :step="10" />
              <span class="form-item-hint">{{ t('activeConsciousness.configTab.conversationLimitHint') }}</span>
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.memoryLimit')">
              <n-input-number v-model:value="config.context.memory_limit" :min="1" :max="10" />
              <span class="form-item-hint">{{ t('activeConsciousness.configTab.memoryLimitHint') }}</span>
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.weatherEnabled')">
              <n-switch v-model:value="config.context.weather_enabled" />
              <span class="form-item-hint">{{ t('activeConsciousness.configTab.weatherHint') }}</span>
            </n-form-item>

            <!-- 想念分数配置 -->
            <n-divider>{{ t('activeConsciousness.configTab.longingConfig') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.longingGapMinutes')">
              <n-input-number v-model:value="config.longing.gap_minutes" :min="60" :max="1440" :step="30" />
              <span style="margin-left: 8px; font-size: 12px; color: var(--theme-text-muted);">
                {{ t('activeConsciousness.configTab.longingGapHint') }}
              </span>
            </n-form-item>

            <!-- 等级配置 -->
            <n-divider>{{ t('activeConsciousness.configTab.levelConfig') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.longingLevels')">
              <n-input v-model:value="config.levels.longing" type="textarea" :rows="3" placeholder='[0.0, 0, "calm"], [0.1, 1, "longing"], ...' />
              <span style="margin-left: 8px; font-size: 12px; color: var(--theme-text-muted);">
                {{ t('activeConsciousness.configTab.longingLevelsHint') }}
              </span>
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.heatLevels')">
              <n-input v-model:value="config.levels.heat" type="textarea" :rows="2" placeholder='[0.0, "cold"], [0.5, "warm"], ...' />
              <span style="margin-left: 8px; font-size: 12px; color: var(--theme-text-muted);">
                {{ t('activeConsciousness.configTab.heatLevelsHint') }}
              </span>
            </n-form-item>

            <!-- 通知目标 -->
            <n-divider>{{ t('activeConsciousness.configTab.notifyTarget') }}</n-divider>
            <n-form-item :label="t('activeConsciousness.configTab.targetPlatform')">
              <n-select v-model:value="config.notify.platform" :options="platformOptions" @update:value="onNotifyPlatformChange" />
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.sessionSource')">
              <n-radio-group v-model:value="notifySessionMode">
                <n-space vertical>
                  <n-radio value="latest">{{ t('activeConsciousness.configTab.latestSession') }}</n-radio>
                  <n-radio value="fixed">{{ t('activeConsciousness.configTab.fixedSession') }}</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.configTab.fixedSessionLabel')" v-if="notifySessionMode === 'fixed'">
              <n-select
                v-model:value="config.notify.chat_id"
                :options="notifySessionOptions"
                :loading="loadingNotifySessions"
                :placeholder="t('activeConsciousness.configTab.selectSession')"
                filterable
              />
            </n-form-item>
          </template>

          <n-button type="primary" @click="saveConfig" :loading="saving" style="margin-top: 16px">
            {{ t('activeConsciousness.configTab.save') }}
          </n-button>
        </n-card>
      </n-tab-pane>

      <!-- Tab: LLM -->
      <n-tab-pane name="llm" :tab="t('activeConsciousness.tabs.llm')">
        <!-- 通用 LLM（默认/回退） -->
        <n-card :title="t('activeConsciousness.llmTab.generalLLM')" size="small" style="margin-bottom: 16px">
          <n-form-item :label="t('activeConsciousness.llmTab.llmMode')">
            <n-radio-group v-model:value="config.llm.mode">
              <n-radio value="hermes">{{ t('activeConsciousness.llmTab.useHermes') }}</n-radio>
              <n-radio value="custom">{{ t('activeConsciousness.llmTab.customLLM') }}</n-radio>
            </n-radio-group>
          </n-form-item>
          <template v-if="config.llm.mode === 'custom'">
            <n-form-item label="Provider">
              <n-select v-model:value="config.llm.provider" :options="providerOptions" />
            </n-form-item>
            <n-form-item label="Model">
              <n-input v-model:value="config.llm.model" placeholder="deepseek-chat" />
            </n-form-item>
            <n-form-item label="API Key">
              <n-input v-model:value="config.llm.api_key" :placeholder="t('activeConsciousness.llmTab.apiKeyPlaceholder')" />
            </n-form-item>
            <n-form-item label="Base URL">
              <n-input v-model:value="config.llm.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>
          </template>
          <n-button type="primary" @click="testLLMConnect" :loading="testing.llm" size="small" style="margin-top: 8px">
            {{ t('activeConsciousness.llmTab.testConnectivity') }}
          </n-button>
          <n-alert v-if="llmTestResult" :type="llmTestResult.success ? 'success' : 'error'" style="margin-top: 8px" closable @close="llmTestResult = null">
            {{ llmTestResult.success ? t('activeConsciousness.llmTab.connectSuccess') : t('activeConsciousness.llmTab.connectFail') + ': ' + (llmTestResult.error || '') }}
          </n-alert>
        </n-card>

        <!-- 🕐 提示词时间格式 -->
        <n-card :title="t('activeConsciousness.llmTab.promptTimeFormat')" size="small" style="margin-bottom: 16px">
          <div style="font-size: 12px; color: var(--theme-text-secondary); margin-bottom: 8px;">
            {{ t('activeConsciousness.llmTab.promptTimeFormatHint') }}
          </div>
          <TimeFormatSelector v-model="config.prompts.time_format" />
        </n-card>

        <!-- 🎭 情绪评估 LLM -->
        <n-card :title="t('activeConsciousness.llmTab.emotionEvalLLM')" size="small" style="margin-bottom: 16px">
          <n-form-item :label="t('activeConsciousness.llmTab.llmMode')">
            <n-radio-group v-model:value="config.emotion_llm.mode">
              <n-radio value="">{{ t('activeConsciousness.llmTab.followGeneral') }}</n-radio>
              <n-radio value="hermes">{{ t('activeConsciousness.llmTab.useHermes') }}</n-radio>
              <n-radio value="custom">{{ t('activeConsciousness.llmTab.customLLM') }}</n-radio>
            </n-radio-group>
          </n-form-item>
          <template v-if="config.emotion_llm.mode === 'custom'">
            <n-form-item label="Provider">
              <n-select v-model:value="config.emotion_llm.provider" :options="providerOptions" />
            </n-form-item>
            <n-form-item label="Model">
              <n-input v-model:value="config.emotion_llm.model" placeholder="agnes-2.0-flash" />
            </n-form-item>
            <n-form-item label="API Key">
              <n-input v-model:value="config.emotion_llm.api_key" :placeholder="t('activeConsciousness.llmTab.apiKeyPlaceholder')" />
            </n-form-item>
            <n-form-item label="Base URL">
              <n-input v-model:value="config.emotion_llm.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>
          </template>
          <n-form-item :label="t('activeConsciousness.llmTab.emotionEvalPrompt')">
            <n-input v-model:value="config.prompts.emotion_evaluation" type="textarea" :rows="6" :placeholder="t('activeConsciousness.llmTab.emotionEvalPrompt')" />
          </n-form-item>
          <div style="font-size: 11px; color: var(--theme-text-muted); margin-bottom: 8px;">
            {{ t('activeConsciousness.llmTab.emotionEvalVars') }}
          </div>
          <n-button type="primary" @click="testEmotionLLM" :loading="testing.emotionLLM" size="small">
            {{ t('activeConsciousness.llmTab.testEmotionLLM') }}
          </n-button>
          <n-alert v-if="emotionLLMTestResult" :type="emotionLLMTestResult.success ? 'success' : 'error'" style="margin-top: 8px" closable @close="emotionLLMTestResult = null">
            <template v-if="emotionLLMTestResult.success">
              {{ t('activeConsciousness.llmTab.emotionTestSuccess') }}
              <div v-if="emotionLLMTestResult.data" style="font-size: 12px; margin-top: 4px;">
                {{ t('activeConsciousness.llmTab.model') }} {{ emotionLLMTestResult.data.model || '-' }} | {{ t('activeConsciousness.llmTab.duration') }} {{ emotionLLMTestResult.data.duration_ms || '-' }}ms
              </div>
            </template>
            <template v-else>
              {{ t('activeConsciousness.llmTab.emotionTestFail') }}: {{ emotionLLMTestResult.error || '' }}
            </template>
          </n-alert>
        </n-card>

        <!-- 💭 念头生成 LLM -->
        <n-card :title="t('activeConsciousness.llmTab.thoughtGenLLM')" size="small" style="margin-bottom: 16px">
          <n-form-item :label="t('activeConsciousness.llmTab.enableThoughtEngine')">
            <n-switch v-model:value="config.thought_engine.enabled" />
            <span class="form-item-hint">{{ t('activeConsciousness.llmTab.thoughtEngineHint') }}</span>
          </n-form-item>
          <template v-if="config.thought_engine.enabled">
            <n-form-item :label="t('activeConsciousness.llmTab.maxTokens')">
              <n-input-number v-model:value="config.thought_engine.max_tokens" :min="0" :max="2000" />
              <span class="form-item-hint">{{ t('activeConsciousness.llmTab.maxTokensHint') }}</span>
            </n-form-item>
            <n-form-item :label="t('activeConsciousness.llmTab.temperature')">
              <n-input-number v-model:value="config.thought_engine.temperature" :min="0" :max="2" :step="0.1" />
              <span class="form-item-hint">{{ t('activeConsciousness.llmTab.temperatureHint') }}</span>
            </n-form-item>
          </template>
          <n-form-item :label="t('activeConsciousness.llmTab.llmMode')">
            <n-radio-group v-model:value="config.thought_llm.mode">
              <n-radio value="">{{ t('activeConsciousness.llmTab.followGeneral') }}</n-radio>
              <n-radio value="hermes">{{ t('activeConsciousness.llmTab.useHermes') }}</n-radio>
              <n-radio value="custom">{{ t('activeConsciousness.llmTab.customLLM') }}</n-radio>
            </n-radio-group>
          </n-form-item>
          <template v-if="config.thought_llm.mode === 'custom'">
            <n-form-item label="Provider">
              <n-select v-model:value="config.thought_llm.provider" :options="providerOptions" />
            </n-form-item>
            <n-form-item label="Model">
              <n-input v-model:value="config.thought_llm.model" placeholder="mimo-v2.5-pro" />
            </n-form-item>
            <n-form-item label="API Key">
              <n-input v-model:value="config.thought_llm.api_key" :placeholder="t('activeConsciousness.llmTab.apiKeyPlaceholder')" />
            </n-form-item>
            <n-form-item label="Base URL">
              <n-input v-model:value="config.thought_llm.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>
          </template>
          <n-form-item :label="t('activeConsciousness.llmTab.thoughtSystemPrompt')">
            <n-input v-model:value="config.prompts.thought_generation" type="textarea" :rows="6" :placeholder="t('activeConsciousness.llmTab.thoughtSystemPrompt')" />
          </n-form-item>
          <div style="font-size: 11px; color: var(--theme-text-muted); margin-bottom: 8px;">
            {{ t('activeConsciousness.llmTab.thoughtSystemVars') }}
          </div>
          <n-form-item :label="t('activeConsciousness.llmTab.thoughtUserInstruction')">
            <n-input v-model:value="config.prompts.thought_generation_instruction" type="textarea" :rows="4" :placeholder="t('activeConsciousness.llmTab.thoughtUserInstruction')" />
          </n-form-item>
          <div style="font-size: 11px; color: var(--theme-text-muted); margin-bottom: 8px;">
            {{ t('activeConsciousness.llmTab.thoughtUserVars') }}
          </div>
          <n-button type="primary" @click="testThoughtLLM" :loading="testing.thoughtLLM" size="small">
            {{ t('activeConsciousness.llmTab.testThoughtLLM') }}
          </n-button>
          <n-alert v-if="thoughtLLMTestResult" :type="thoughtLLMTestResult.success ? 'success' : 'error'" style="margin-top: 8px" closable @close="thoughtLLMTestResult = null">
            <template v-if="thoughtLLMTestResult.success">
              {{ t('activeConsciousness.llmTab.thoughtTestSuccess') }}
              <div v-if="thoughtLLMTestResult.data" style="font-size: 12px; margin-top: 4px;">
                {{ t('activeConsciousness.llmTab.model') }} {{ thoughtLLMTestResult.data.model || '-' }} | {{ t('activeConsciousness.llmTab.duration') }} {{ thoughtLLMTestResult.data.duration_ms || '-' }}ms
              </div>
            </template>
            <template v-else>
              {{ t('activeConsciousness.llmTab.thoughtTestFail') }}: {{ thoughtLLMTestResult.error || '' }}
            </template>
          </n-alert>
        </n-card>
        
        <!-- 保存按钮 -->
        <div style="text-align: center; padding: 16px 0;">
          <n-button type="primary" @click="saveConfig" :loading="saving" size="large">
            {{ t('activeConsciousness.llmTab.saveLLM') }}
          </n-button>
        </div>
      </n-tab-pane>

      <!-- Tab: 运行逻辑 -->
      <n-tab-pane name="logic" :tab="t('activeConsciousness.tabs.logic')">
        <n-card :title="t('activeConsciousness.logicTab.title')" size="small" class="run-logic-card">
          <n-steps vertical :current="8" size="small">
            <n-step :title="t('activeConsciousness.logicTab.step1')">
              <div style="font-size: 13px; color: var(--theme-text-secondary); line-height: 1.6;">
                {{ t('activeConsciousness.logicTab.step1Desc') }}
              </div>
            </n-step>
            <n-step :title="t('activeConsciousness.logicTab.step2')">
              <div style="font-size: 13px; color: var(--theme-text-secondary); line-height: 1.6;">
                {{ t('activeConsciousness.logicTab.step2Desc') }}
              </div>
            </n-step>
            <n-step :title="t('activeConsciousness.logicTab.step3')">
              <div style="font-size: 13px; color: var(--theme-text-secondary); line-height: 1.6;">
                {{ t('activeConsciousness.logicTab.step3Desc') }}
              </div>
            </n-step>
            <n-step :title="t('activeConsciousness.logicTab.step4')">
              <div style="font-size: 13px; color: var(--theme-text-secondary); line-height: 1.6;">
                {{ t('activeConsciousness.logicTab.step4Desc') }}
              </div>
            </n-step>
            <n-step :title="t('activeConsciousness.logicTab.step5')">
              <div style="font-size: 13px; color: var(--theme-text-secondary); line-height: 1.6;">
                {{ t('activeConsciousness.logicTab.step5Desc') }}
              </div>
            </n-step>
            <n-step :title="t('activeConsciousness.logicTab.step6')">
              <div style="font-size: 13px; color: var(--theme-text-secondary); line-height: 1.6;">
                {{ t('activeConsciousness.logicTab.step6Desc') }}
              </div>
            </n-step>
            <n-step :title="t('activeConsciousness.logicTab.step7')">
              <div style="font-size: 13px; color: var(--theme-text-secondary); line-height: 1.6;">
                {{ t('activeConsciousness.logicTab.step7Desc') }}
              </div>
            </n-step>
            <n-step :title="t('activeConsciousness.logicTab.step8')">
              <div style="font-size: 13px; color: var(--theme-text-secondary); line-height: 1.6;">
                {{ t('activeConsciousness.logicTab.step8Desc') }}
              </div>
            </n-step>
          </n-steps>

          <!-- 参考信息折叠区 -->
          <n-collapse style="margin-top: 16px;">
            <n-collapse-item :title="t('activeConsciousness.logicTab.terminology')" name="overview">
              <div style="font-size: 13px; line-height: 1.8;">
                <div v-html="t('activeConsciousness.logicTab.terminologyContent')"></div>
              </div>
            </n-collapse-item>

            <n-collapse-item :title="t('activeConsciousness.logicTab.decisionDetail')" name="decision_detail">
              <div style="font-size: 13px; line-height: 1.8;">
                <div v-html="t('activeConsciousness.logicTab.decisionDetailContent')"></div>
              </div>
            </n-collapse-item>

            <n-collapse-item :title="t('activeConsciousness.logicTab.protectionRules')" name="protection">
              <div style="font-size: 13px; line-height: 1.8;">
                <div v-html="t('activeConsciousness.logicTab.protectionRulesContent')"></div>
              </div>
            </n-collapse-item>

            <n-collapse-item :title="t('activeConsciousness.logicTab.heatLevelsInfo')" name="heat">
              <div style="font-size: 13px; line-height: 1.8;">
                <div v-html="t('activeConsciousness.logicTab.heatLevelsContent')"></div>
              </div>
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </n-tab-pane>

      <!-- Tab: 测试 -->
      <n-tab-pane name="test" :tab="t('activeConsciousness.tabs.test')">

        <!-- 测试按钮组 -->
        <n-card :title="t('activeConsciousness.testTab.nodeTest')" size="small" style="margin-bottom: 16px">
          <n-space vertical>
            <n-grid :cols="2" :x-gap="12" :y-gap="12">
              <n-grid-item>
                <n-button block @click="testLLMConnect" :loading="testing.llm">
                  {{ t('activeConsciousness.testTab.llmConnectTest') }}
                </n-button>
                <div style="font-size: 11px; color: var(--theme-text-muted); margin-top: 4px;">{{ t('activeConsciousness.testTab.llmConnectTestHint') }}</div>
              </n-grid-item>
              <n-grid-item>
                <n-button block @click="testSessionContext" :loading="testing.sessionContext">
                  {{ t('activeConsciousness.testTab.sessionContextTest') }}
                </n-button>
                <div style="font-size: 11px; color: var(--theme-text-muted); margin-top: 4px;">{{ t('activeConsciousness.testTab.sessionContextTestHint') }}</div>
              </n-grid-item>
              <n-grid-item>
                <n-button block @click="testContextCollector" :loading="testing.contextCollector">
                  {{ t('activeConsciousness.testTab.contextCollectorTest') }}
                </n-button>
                <div style="font-size: 11px; color: var(--theme-text-muted); margin-top: 4px;">{{ t('activeConsciousness.testTab.contextCollectorTestHint') }}</div>
              </n-grid-item>
              <n-grid-item>
                <n-button block type="primary" @click="testThoughtEngine" :loading="testing.thoughtEngine">
                  {{ t('activeConsciousness.testTab.thoughtEngineTest') }}
                </n-button>
                <div style="font-size: 11px; color: var(--theme-text-muted); margin-top: 4px;">{{ t('activeConsciousness.testTab.thoughtEngineTestHint') }}</div>
              </n-grid-item>
            </n-grid>
          </n-space>
        </n-card>


        <!-- 测试结果展示 -->
        <n-card v-if="testResult" :title="t('activeConsciousness.testTab.testResults')" size="small">
          <template #header-extra>
            <n-button text @click="testResult = null">{{ t('activeConsciousness.testTab.clear') }}</n-button>
          </template>
          
          <!-- 状态标签 -->
          <n-space style="margin-bottom: 12px;">
            <n-tag :type="testResult.success ? 'success' : 'error'" size="small">
              {{ testResult.success ? t('activeConsciousness.testTab.success') : t('activeConsciousness.testTab.failure') }}
            </n-tag>
            <n-tag v-if="testResult.data?.want_to_contact !== undefined" 
                   :type="testResult.data.want_to_contact ? 'success' : 'warning'" size="small">
              {{ testResult.data.want_to_contact ? t('activeConsciousness.testTab.wantToContact') : t('activeConsciousness.testTab.skipNoContact') }}
            </n-tag>
          </n-space>

          <!-- ThoughtEngine 结果 -->
          <template v-if="testResult.data?.thought">
            <n-divider title-placement="left">{{ t('activeConsciousness.testTab.generatedThoughts') }}</n-divider>
            <n-card size="small" style="margin-bottom: 12px;">
              <div style="font-size: 14px; white-space: pre-wrap;">{{ testResult.data.thought }}</div>
            </n-card>
          </template>

          <!-- 上下文信息 -->
          <template v-if="testResult.data?.context_bundle || testResult.data?.conversations_count !== undefined">
            <n-divider title-placement="left">{{ t('activeConsciousness.testTab.contextInfo') }}</n-divider>
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;">
              <n-descriptions-item :label="t('activeConsciousness.testTab.conversationCount')">
                {{ testResult.data.context_bundle?.conversations_count || testResult.data.conversations_count || 0 }}
              </n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.memoryCount')">
                {{ testResult.data.context_bundle?.memories_count || testResult.data.memories_count || 0 }}
              </n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.dominantEmotion')">
                {{ testResult.data.context_bundle?.emotion?.dominant || testResult.data.emotion?.dominant || '-' }}
              </n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.timeAwareness')">
                {{ testResult.data.context_bundle?.time_context?.time_display || testResult.data.time_context?.time_display || '-' }}
              </n-descriptions-item>
            </n-descriptions>
          </template>

          <!-- LLM 调用详情 -->
          <template v-if="testResult.data?.llm_details">
            <n-divider title-placement="left">{{ t('activeConsciousness.testTab.llmCallDetails') }}</n-divider>
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;">
              <n-descriptions-item :label="t('activeConsciousness.testTab.model')">{{ testResult.data.llm_details.model || '-' }}</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.duration')">{{ testResult.data.llm_details.duration_ms || '-' }}ms</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.promptTokens')">{{ testResult.data.llm_details.prompt_tokens ?? '-' }}</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.completionTokens')">{{ testResult.data.llm_details.completion_tokens ?? '-' }}</n-descriptions-item>
              <n-descriptions-item v-if="testResult.data.llm_details.error" :label="t('activeConsciousness.testTab.error')" :span="2">
                <span style="color: var(--theme-error);">{{ testResult.data.llm_details.error }}</span>
              </n-descriptions-item>
            </n-descriptions>
          </template>

          <!-- 错误信息 -->
          <template v-if="testResult.error">
            <n-divider title-placement="left">{{ t('activeConsciousness.testTab.errorMessage') }}</n-divider>
            <n-alert type="error" style="margin-bottom: 12px;">
              {{ testResult.error }}
            </n-alert>
            <n-collapse v-if="testResult.traceback">
              <n-collapse-item :title="t('activeConsciousness.testTab.stackTrace')" name="traceback">
                <n-code :code="testResult.traceback" language="text" word-wrap />
              </n-collapse-item>
            </n-collapse>
          </template>

          <!-- 完整 JSON -->
          <n-collapse>
            <n-collapse-item :title="t('activeConsciousness.testTab.fullJsonData')" name="json">
              <n-code :code="formatJson(testResult)" language="json" word-wrap />
            </n-collapse-item>
          </n-collapse>
        </n-card>


      </n-tab-pane>
    </n-tabs>

    <!-- 上下文测试结果弹窗 -->
    <n-modal v-model:show="showSessionContextModal" preset="card" :title="t('activeConsciousness.modals.contextTestResult')" style="width: 90vw; max-width: 900px">
      <template v-if="sessionContextResult">
        <n-descriptions :column="2" label-placement="left" bordered size="small" style="margin-bottom: 12px">
          <n-descriptions-item :label="t('activeConsciousness.modals.conversationCount')">
            {{ sessionContextResult.data?.conversations_count ?? '-' }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.memoryCount')">
            {{ sessionContextResult.data?.memories_count ?? '-' }}
          </n-descriptions-item>
        </n-descriptions>

        <n-card :title="t('activeConsciousness.modals.fetchedContext')" size="small">
          <n-code
            :code="sessionContextResult.data?.context || t('activeConsciousness.messages.empty')"
            language="text"
            word-wrap
          />
        </n-card>
      </template>
      <template v-else>
        <n-empty :description="t('activeConsciousness.modals.noData')" />
      </template>
    </n-modal>

    <!-- 召回内容弹窗 -->
    <n-modal v-model:show="showRecallModal" preset="card" :title="t('activeConsciousness.modals.recallContent')" style="width: 90vw; max-width: 900px">
      <n-list bordered v-if="recallItems.length">
        <n-list-item v-for="(item, idx) in recallItems" :key="idx">
          <div style="font-size: 13px; white-space: pre-wrap;">{{ item.content || item.text || formatJson(item) }}</div>
        </n-list-item>
      </n-list>
      <n-empty v-else-if="!recallLoading" :description="t('activeConsciousness.modals.noRecallContent')" />
      <div v-else style="display: flex; justify-content: center; padding: 40px 0;">
        <n-spin size="medium" />
      </div>
    </n-modal>

    <!-- 念头内容弹窗（生成念头列点击） -->
    <n-modal v-model:show="showThoughtContentModal" preset="card" :title="t('activeConsciousness.modals.thoughtDetail')" style="width: 90vw; max-width: 900px">
      <template v-if="thoughtContentData">
        <!-- 念头内容（最醒目） -->
        <n-card size="small" style="margin-bottom: 12px;">
          <div style="white-space: pre-wrap; font-size: 14px; line-height: 1.6;">{{ thoughtContentData.thought_content || '{{ t('activeConsciousness.modals.noThoughtContent') }}' }}</div>
        </n-card>
        <!-- 基本信息 -->
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;" :label-style="{ width: '100px' }">
          <n-descriptions-item :label="t('activeConsciousness.modals.decisionType')" v-if="thoughtContentData.decision?.type">
            <n-tag :type="getDecisionTagType(thoughtContentData.decision.type)" size="small">
              {{ getDecisionLabelCn(thoughtContentData.decision.type) }}
            </n-tag>
            <span v-if="thoughtContentData.decision.score" style="margin-left: 8px; font-size: 12px; color: var(--theme-text-muted);">
              {{ t('activeConsciousness.modals.score') }} {{ thoughtContentData.decision.score?.toFixed(3) }}
            </span>
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.thoughtType')" v-if="thoughtContentData.thought_type">
            {{ thoughtTypeLabelCn(thoughtContentData.thought_type) }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.wantToContactLabel')" v-if="thoughtContentData.want_to_contact !== null">
            <n-tag :type="thoughtContentData.want_to_contact ? 'success' : 'default'" size="small">
              {{ thoughtContentData.want_to_contact ? t('activeConsciousness.modals.yes') : t('activeConsciousness.modals.noSkip') }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.heartbeatIdLabel')">{{ thoughtContentData.id }}</n-descriptions-item>
        </n-descriptions>
        <!-- LLM 信息 -->
        <n-divider title-placement="left" style="margin: 12px 0 8px;">{{ t('activeConsciousness.modals.llmCall') }}</n-divider>
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;" :label-style="{ width: '100px' }">
          <n-descriptions-item :label="t('activeConsciousness.testTab.duration')" v-if="thoughtContentData.llm_duration_ms">
            {{ thoughtContentData.llm_duration_ms }}ms
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.totalTokens')" v-if="thoughtContentData.llm_total_tokens">
            {{ thoughtContentData.llm_total_tokens }}（{{ t('activeConsciousness.modals.input') }} {{ thoughtContentData.llm_prompt_tokens }} / {{ t('activeConsciousness.modals.output') }} {{ thoughtContentData.llm_completion_tokens }}）
          </n-descriptions-item>
        </n-descriptions>
        <!-- Prompt 和 LLM 返回（默认折叠） -->
        <n-collapse style="margin-bottom: 12px;">
          <n-collapse-item :title="t('activeConsciousness.modals.sentPrompt')" name="prompt">
            <n-code :code="formatPrompt(thoughtContentData.llm_prompt_sent)" language="text" word-wrap />
          </n-collapse-item>
          <n-collapse-item :title="t('activeConsciousness.modals.llmRawResponse')" name="response">
            <n-code :code="thoughtContentData.llm_response_received || t('activeConsciousness.messages.empty')" language="text" word-wrap />
          </n-collapse-item>
        </n-collapse>
      </template>
      <n-empty v-else-if="!thoughtContentLoading" description="{{ t('activeConsciousness.modals.noThoughtContent') }}" />
      <div v-else style="display: flex; justify-content: center; padding: 40px 0;">
        <n-spin size="medium" />
      </div>
    </n-modal>

    <!-- 发送详情弹窗（发送消息列点击） -->
    <n-modal v-model:show="showSendDetailModal" preset="card" :title="t('activeConsciousness.modals.sendDetail')" style="width: 90vw; max-width: 900px">
      <template v-if="sendDetailData">
        <n-descriptions :column="1" label-placement="left" bordered size="small" :label-style="{ width: '100px' }">
          <n-descriptions-item :label="t('activeConsciousness.modals.heartbeatIdLabel')">{{ sendDetailData.id }}</n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.whetherSent')">
            <n-tag :type="getSendResultTagType(sendDetailData)" size="small">
              {{ getSendResultLabel(sendDetailData) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.failureReason')" v-if="getSendResultTagType(sendDetailData) === 'error'">
            <pre style="white-space: pre-wrap; color: var(--theme-error); font-size: 12px; margin: 0;">{{ getSendFailureReason(sendDetailData) }}</pre>
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.sendStatus')" v-if="sendDetailData.message_sending">
            <n-tag :type="sendDetailData.message_sending.success ? 'success' : 'error'" size="small">
              {{ sendDetailData.message_sending.success ? t('activeConsciousness.modals.sendSuccess') : t('activeConsciousness.modals.sendFailure') }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.sendContent')" v-if="sendDetailData.sent_content">
            <div style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">{{ sendDetailData.sent_content }}</div>
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.thoughtType')" v-if="sendDetailData.thought_type">
            {{ thoughtTypeLabelCn(sendDetailData.thought_type) }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.decisionType')" v-if="sendDetailData.decision?.type">
            <n-tag :type="getDecisionTagType(sendDetailData.decision.type)" size="small">
              {{ sendDetailData.decision.type }}
            </n-tag>
          </n-descriptions-item>
        </n-descriptions>
      </template>
      <n-empty v-else-if="!sendDetailLoading" :description="t('activeConsciousness.modals.noSendDetail')" />
      <div v-else style="display: flex; justify-content: center; padding: 40px 0;">
        <n-spin size="medium" />
      </div>
    </n-modal>

    <!-- 心跳日志详情弹窗 -->
    <n-modal v-model:show="showDetailsModal" preset="card" :title="detailsTitle" fullscreen :mask-closable="false">
      <div v-if="detailsData && isHeartbeatDetails">
        
        <!-- ===== 结果总览（最醒目） ===== -->
        <n-card size="small" style="margin-bottom: 16px;">
          <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
            <!-- 结果标签 -->
            <n-tag :type="getHeartbeatResultTagType(detailsData)" size="large">
              {{ getHeartbeatResultTitle(detailsData) }}
            </n-tag>
            <!-- 结果信息 -->
            <div style="flex: 1; min-width: 200px;">
              <div style="font-size: 13px; color: var(--theme-text-secondary); margin-bottom: 2px;">
                {{ getHeartbeatResultReason(detailsData) }}
              </div>
              <div style="font-size: 12px; color: var(--theme-text-muted);">
                {{ detailsData.duration_ms ? `${t('activeConsciousness.testTab.duration')} ${detailsData.duration_ms}ms` : '' }}
              </div>
            </div>
            <!-- 关键指标 -->
            <div style="display: flex; gap: 16px;">
              <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: var(--theme-success);">
                  {{ detailsData.decision?.score?.toFixed(2) || '0.00' }}
                </div>
                <div style="font-size: 11px; color: var(--theme-text-muted);">{{ t('activeConsciousness.modals.decisionScore') }}</div>
              </div>
              <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: var(--theme-info);">
                  {{ detailsData.chat_heat?.toFixed(1) || '0.0' }}
                </div>
                <div style="font-size: 11px; color: var(--theme-text-muted);">{{ t('activeConsciousness.status.chatHeat') }}</div>
              </div>
              <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: var(--theme-warning);">
                  {{ detailsData.emotional_intensity?.toFixed(2) || '0.00' }}
                </div>
                <div style="font-size: 11px; color: var(--theme-text-muted);">{{ t('activeConsciousness.status.emotionalIntensity') }}</div>
              </div>
            </div>
          </div>
        </n-card>


        <!-- ===== 执行流程（可折叠） ===== -->
        <n-collapse default-expanded-names="">
          <n-collapse-item :title="t('activeConsciousness.modals.executionFlow')" name="timeline">
            <n-timeline>
              <!-- 1. 心跳触发 -->
              <n-timeline-item type="success" :title="t('activeConsciousness.modals.heartbeatTrigger')">
                <template #icon>
                  <n-icon size="16"><CheckmarkCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: var(--theme-text-secondary);">
                  {{ detailsData.started_at || '-' }}
                </div>
              </n-timeline-item>

              <!-- 2. 情绪演化 -->
              <n-timeline-item v-if="detailsData.emotion_before" type="success" :title="t('activeConsciousness.modals.emotionEvolution')">
                <template #icon>
                  <n-icon size="16"><CheckmarkCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: var(--theme-text-secondary);">
                  {{ t('activeConsciousness.modals.minutesSince', { minutes: detailsData.minutes_since_update?.toFixed(0) || '0' }) }}
                  <n-tag size="tiny" :type="getEmotionTagType(detailsData.emotion_merged?.dominant)">
                    {{ emotionLabelCn(detailsData.emotion_merged?.dominant) }}
                  </n-tag>
                </div>
              </n-timeline-item>

              <!-- 3. 上下文收集 -->
              <n-timeline-item v-if="detailsData.session_context !== undefined" type="success" :title="t('activeConsciousness.modals.contextCollection')">
                <template #icon>
                  <n-icon size="16"><CheckmarkCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: var(--theme-text-secondary);">
                  {{ t('activeConsciousness.modals.conversation') }} {{ detailsData.session_context ? '✓' : '✗' }}
                  | {{ t('activeConsciousness.modals.memory') }} {{ detailsData.recall_results?.length || 0 }} {{ t('activeConsciousness.modals.items') }}
                  | Hindsight {{ detailsData.hindsight_context ? '✓' : '✗' }}
                </div>
              </n-timeline-item>

              <!-- 4. 决策计算 -->
              <n-timeline-item v-if="detailsData.decision" :type="getDecisionTimelineType(detailsData.decision)" :title="t('activeConsciousness.modals.decisionCalculation')">
                <template #icon>
                  <n-icon size="16"><CheckmarkCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: var(--theme-text-secondary);">
                  {{ t('activeConsciousness.modals.scoreLabel') }} {{ detailsData.decision.score?.toFixed(3) || '0.000' }}
                  → <n-tag size="tiny" :type="getDecisionTagType(detailsData.decision.type)">
                    {{ getDecisionLabelCn(detailsData.decision.type) }}
                  </n-tag>
                </div>
              </n-timeline-item>

              <!-- 5. 发送保护 -->
              <n-timeline-item 
                v-if="detailsData.decision?.blocked_by_protection" 
                type="error" 
                :title="t('activeConsciousness.modals.sendProtectionBlock')"
              >
                <template #icon>
                  <n-icon size="16"><CloseCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: var(--theme-error);">
                  {{ detailsData.decision.protection_reason || t('activeConsciousness.modals.protectionBlock') }}
                </div>
              </n-timeline-item>

              <!-- 6. 念头生成 -->
              <n-timeline-item 
                v-if="detailsData.thought_generation" 
                :type="detailsData.thought_generation.success === true || (detailsData.thought_generation.response_received && !detailsData.thought_generation.error) ? 'success' : detailsData.thought_generation.success === false ? 'error' : 'success'" 
                :title="t('activeConsciousness.modals.thoughtGeneration')"
              >
                <template #icon>
                  <n-icon size="16">
                    <CheckmarkCircle v-if="detailsData.thought_generation.success === true || (detailsData.thought_generation.response_received && !detailsData.thought_generation.error)" />
                    <CloseCircle v-else-if="detailsData.thought_generation.success === false" />
                    <CheckmarkCircle v-else />
                  </n-icon>
                </template>
                <div style="font-size: 12px; color: var(--theme-text-secondary);">
                  <template v-if="detailsData.thought_generation.success === false">
                    {{ detailsData.thought_generation.error || t('activeConsciousness.modals.generationFailed') }}
                  </template>
                  <template v-else>
                    {{ (detailsData.thought_generation.thought || detailsData.thought_generation.response_received || '').substring(0, 80) }}...
                  </template>
                </div>
              </n-timeline-item>

              <!-- 7. 消息发送 -->
              <n-timeline-item 
                v-if="detailsData.message_sending" 
                :type="detailsData.message_sending.success ? 'success' : 'error'" 
                :title="t('activeConsciousness.modals.messageSend')"
              >
                <template #icon>
                  <n-icon size="16">
                    <CheckmarkCircle v-if="detailsData.message_sending.success" />
                    <CloseCircle v-else />
                  </n-icon>
                </template>
                <div style="font-size: 12px; color: var(--theme-text-secondary);">
                  {{ detailsData.message_sending.success ? t('activeConsciousness.modals.sendSuccess') : t('activeConsciousness.modals.sendFailure') }}
                  <template v-if="detailsData.message_sending.thought">
                    : {{ detailsData.message_sending.thought.substring(0, 30) }}...
                  </template>
                </div>
              </n-timeline-item>
            </n-timeline>
          </n-collapse-item>
        </n-collapse>

        <n-divider style="margin: 16px 0;" />

        <!-- LLM 调用详情（直接展示，不嵌套折叠） -->
        <template v-if="detailsData.emotion_llm_details || detailsData.thought_generation">
          <!-- 情绪评估 LLM -->
          <template v-if="detailsData.emotion_llm_details">
            <n-divider title-placement="left" style="margin: 12px 0 8px;">{{ t('activeConsciousness.llmTab.emotionEvalLLM') }}</n-divider>
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 8px;">
              <n-descriptions-item :label="t('activeConsciousness.testTab.duration')">{{ detailsData.emotion_llm_details.duration_ms || '-' }}ms</n-descriptions-item>
            </n-descriptions>
            <n-collapse style="margin-bottom: 12px;">
              <n-collapse-item :title="t('activeConsciousness.modals.sentPrompt')" name="emotion_prompt">
                <n-code :code="formatPrompt(detailsData.emotion_llm_details.prompt_sent)" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item :title="t('activeConsciousness.modals.llmResponse')" name="emotion_response">
                <n-code :code="detailsData.emotion_llm_details.response_received || t('activeConsciousness.messages.empty')" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item v-if="detailsData.emotion_llm_details.reasoning_content" :title="t('activeConsciousness.modals.reasoningProcess')" name="emotion_reasoning">
                <n-code :code="detailsData.emotion_llm_details.reasoning_content" language="text" word-wrap />
              </n-collapse-item>
            </n-collapse>
          </template>

          <!-- 念头生成 LLM -->
          <template v-if="detailsData.thought_generation">
            <n-divider title-placement="left" style="margin: 12px 0 8px;">{{ t('activeConsciousness.llmTab.thoughtGenLLM') }}</n-divider>
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 8px;">
              <n-descriptions-item :label="t('activeConsciousness.testTab.duration')">{{ detailsData.thought_generation.duration_ms || '-' }}ms</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.modals.wantToContactLabel')">
                <n-tag :type="detailsData.thought_generation.want_to_contact ? 'success' : 'default'" size="small">
                  {{ detailsData.thought_generation.want_to_contact ? t('activeConsciousness.modals.yes') : t('activeConsciousness.modals.noSkip') }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item v-if="detailsData.thought_generation.thought" :label="t('activeConsciousness.modals.generatedContent')" :span="2">
                {{ detailsData.thought_generation.thought }}
              </n-descriptions-item>
            </n-descriptions>
            <n-collapse style="margin-bottom: 12px;">
              <n-collapse-item :title="t('activeConsciousness.modals.sentPrompt')" name="thought_prompt">
                <n-code :code="formatPrompt(detailsData.thought_generation.prompt_sent)" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item :title="t('activeConsciousness.modals.llmResponse')" name="thought_response">
                <n-code :code="detailsData.thought_generation.response_received || t('activeConsciousness.messages.empty')" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item v-if="detailsData.thought_generation.reasoning_content" :title="t('activeConsciousness.modals.reasoningProcess')" name="thought_reasoning">
                <n-code :code="detailsData.thought_generation.reasoning_content" language="text" word-wrap />
              </n-collapse-item>
            </n-collapse>
          </template>
        </template>

        <!-- 决策计算详情 -->
        <n-divider title-placement="left" style="margin: 12px 0 8px;">{{ t('activeConsciousness.modals.decisionCalcDetail') }}</n-divider>
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;">
          <n-descriptions-item :label="t('activeConsciousness.modals.decisionType')">
            <n-tag :type="getDecisionTagType(detailsData.decision?.type)" size="small">
              {{ getDecisionLabelCn(detailsData.decision?.type) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.finalScore')">{{ detailsData.decision?.score?.toFixed(3) }}</n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.emotionalIntensity')">
            {{ parseDecisionReason(detailsData.decision?.reason).intensity }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.timeFitness')">
            {{ parseDecisionReason(detailsData.decision?.reason).time_fitness }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.silenceFactor')">
            {{ parseDecisionReason(detailsData.decision?.reason).silence_factor }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.decision.frequencyLimit')">
            {{ parseDecisionReason(detailsData.decision?.reason).frequency }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.decisionReason')" :span="2">{{ detailsData.decision?.reason }}</n-descriptions-item>
          <n-descriptions-item :label="t('activeConsciousness.modals.resultExplanation')" :span="2">
            <template v-if="detailsData.decision?.type === 'skip'">
              {{ t('activeConsciousness.modals.skipExplanation', { score: detailsData.decision?.score?.toFixed(3) }) }}
            </template>
            <template v-else-if="detailsData.decision?.type === 'memory'">
              {{ t('activeConsciousness.modals.memoryExplanation', { score: detailsData.decision?.score?.toFixed(3) }) }}
            </template>
            <template v-else-if="detailsData.decision?.type === 'auto_send'">
              {{ t('activeConsciousness.modals.sendExplanation', { score: detailsData.decision?.score?.toFixed(3) }) }}
            </template>
            <template v-else>{{ detailsData.decision?.type }}</template>
          </n-descriptions-item>
        </n-descriptions>

        <!-- 情绪演化详情 -->
        <template v-if="detailsData.emotion_before">
          <n-divider title-placement="left" style="margin: 12px 0 8px;">{{ t('activeConsciousness.modals.emotionEvolutionDetail') }}</n-divider>
          <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
            <n-tag v-for="item in [
              {label: t('activeConsciousness.modals.initial'), d: detailsData.emotion_before},
              {label: t('activeConsciousness.modals.evolved'), d: detailsData.emotion_evolved},
              {label: 'LLM', d: detailsData.emotion_llm},
              {label: t('activeConsciousness.modals.merged'), d: detailsData.emotion_merged}
            ].filter(i => i.d)" :key="item.label" size="small" :type="getEmotionTagType(item.d.dominant)">
              {{ item.label }}: {{ emotionLabelCn(item.d.dominant) }} ({{ item.d.valence?.toFixed(2) }}, {{ item.d.arousal?.toFixed(2) }}, {{ item.d.social_need?.toFixed(2) }})
            </n-tag>
          </div>
          <div style="font-size: 12px; color: var(--theme-text-secondary); margin-bottom: 12px;">
            {{ t('activeConsciousness.modals.minutesSinceUpdate', { minutes: detailsData.minutes_since_update?.toFixed(0) }) }}
          </div>
        </template>
      </div>
      <n-empty v-else-if="!heartbeatDetailLoading" :description="t('activeConsciousness.modals.noDetailData')" />
      <div v-else style="display: flex; justify-content: center; padding: 40px 0;">
        <n-spin size="medium" />
      </div>
    </n-modal>

    <!-- 念头日志详情弹窗 -->
    <n-modal v-model:show="showThoughtDetailsModal" preset="card" :title="thoughtDetailsTitle" fullscreen :mask-closable="false">
      <div v-if="thoughtDetailsData">
        
        <!-- ===== 结果总览（最醒目） ===== -->
        <n-card size="small" style="margin-bottom: 16px;">
          <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
            <!-- 结果标签 -->
            <n-tag :type="getThoughtResultTagType(thoughtDetailsData)" size="large">
              {{ getThoughtResultTitle(thoughtDetailsData) }}
            </n-tag>
            <n-tag size="small">ID: {{ thoughtDetailsData.id }}</n-tag>
            <n-tag v-if="thoughtDetailsData.heartbeat_id" size="small" type="info">{{ t('activeConsciousness.modals.heartbeatPrefix') }} {{ thoughtDetailsData.heartbeat_id }}</n-tag>
            <!-- 结果信息 -->
            <div style="flex: 1; min-width: 200px;">
              <div style="font-size: 13px; color: var(--theme-text-secondary); margin-bottom: 2px;">
                {{ thoughtDetailsData.thought || "{{ t('activeConsciousness.modals.noThoughtContent') }}" }}
              </div>
              <div style="font-size: 12px; color: var(--theme-text-muted);">
                {{ thoughtTypeLabelCn(thoughtDetailsData.thought_type) }} · {{ emotionLabelCn(thoughtDetailsData.emotion_state?.dominant) }}
              </div>
            </div>
            <!-- 关键指标 -->
            <div style="display: flex; gap: 16px;">
              <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: var(--theme-success);">
                  {{ thoughtDetailsData.score?.toFixed(2) || "0.00" }}
                </div>
                <div style="font-size: 11px; color: var(--theme-text-muted);">{{ t('activeConsciousness.modals.decisionScore') }}</div>
              </div>
            </div>
          </div>
        </n-card>

        <!-- ===== 详细信息（可折叠） ===== -->
        <n-collapse default-expanded-names="">
          <!-- 情绪状态 -->
          <n-collapse-item v-if="thoughtDetailsData.emotion_state" :title="t('activeConsciousness.modals.emotionState')" name="emotion">
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
              <n-descriptions-item :label="t('activeConsciousness.modals.valenceLabel')">{{ thoughtDetailsData.emotion_state.valence?.toFixed(3) }}</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.modals.arousalLabel')">{{ thoughtDetailsData.emotion_state.arousal?.toFixed(3) }}</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.modals.socialNeedLabel')">{{ thoughtDetailsData.emotion_state.social_need?.toFixed(3) }}</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.dominantEmotion')">
                <n-tag :type="getEmotionTagType(thoughtDetailsData.emotion_state.dominant)" size="small">
                  {{ emotionLabelCn(thoughtDetailsData.emotion_state.dominant) }}
                </n-tag>
              </n-descriptions-item>
            </n-descriptions>
          </n-collapse-item>

          <!-- Hindsight 信息 -->
          <div v-if="thoughtDetailsData.hindsight_stored !== undefined" style="margin-bottom: 16px;">
            <div style="font-weight: 500; margin-bottom: 8px; font-size: 14px;">{{ t('activeConsciousness.modals.hindsightStorage') }}</div>
            <n-descriptions bordered :column="2" size="small">
              <n-descriptions-item :label="t('activeConsciousness.modals.storageStatus')">
                <n-tag :type="thoughtDetailsData.hindsight_stored ? 'success' : 'warning'" size="small">
                  {{ thoughtDetailsData.hindsight_stored ? t('activeConsciousness.modals.stored') : t('activeConsciousness.modals.notStored') }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item v-if="thoughtDetailsData.hindsight_tags?.length" :label="t('activeConsciousness.modals.storageTags')">
                <n-space>
                  <n-tag v-for="tag in thoughtDetailsData.hindsight_tags" :key="tag" :type="getHindsightTagType(tag)" size="small">
                    {{ tag }}
                  </n-tag>
                </n-space>
              </n-descriptions-item>
            </n-descriptions>
          </div>

          <!-- 上下文信息 -->
          <n-collapse-item v-if="thoughtDetailsData.context_bundle" :title="t('activeConsciousness.testTab.contextInfo')" name="context">
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
              <n-descriptions-item :label="t('activeConsciousness.testTab.conversationCount')">{{ thoughtDetailsData.context_bundle.conversations?.length || 0 }}</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.memoryCount')">{{ thoughtDetailsData.context_bundle.memories?.length || 0 }}</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.dominantEmotion')">
                <n-tag :type="getEmotionTagType(thoughtDetailsData.context_bundle.emotion?.dominant)" size="small">
                  {{ emotionLabelCn(thoughtDetailsData.context_bundle.emotion?.dominant) }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.timeAwareness')">{{ thoughtDetailsData.context_bundle.time_context?.time_display || "-" }}</n-descriptions-item>
            </n-descriptions>
          </n-collapse-item>

          <!-- LLM 调用详情 -->
          <n-collapse-item v-if="thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation" :title="t('activeConsciousness.testTab.llmCallDetails')" name="llm">
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
              <n-descriptions-item :label="t('activeConsciousness.testTab.model')">{{ (thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.model || "-" }}</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.testTab.duration')">{{ (thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.duration_ms || "-" }}ms</n-descriptions-item>
              <n-descriptions-item :label="t('activeConsciousness.modals.wantToContactLabel')">
                <n-tag :type="(thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.want_to_contact ? 'success' : 'default'" size="small">
                  {{ (thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.want_to_contact ? t('activeConsciousness.modals.yes') : t('activeConsciousness.modals.noSkip') }}
                </n-tag>
              </n-descriptions-item>
            </n-descriptions>
            <n-collapse style="margin-bottom: 16px;">
              <n-collapse-item :title="t('activeConsciousness.modals.sentPrompt2')" name="prompt">
                <n-code :code="formatPrompt((thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.prompt_sent)" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item :title="t('activeConsciousness.modals.llmResponseContent')" name="response">
                <n-code :code="(thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.response_received || t('activeConsciousness.messages.empty')" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item v-if="(thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.reasoning_content" :title="t('activeConsciousness.modals.reasoningProcess')" name="reasoning">
                <n-code :code="(thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.reasoning_content" language="text" word-wrap />
              </n-collapse-item>
            </n-collapse>
          </n-collapse-item>
        </n-collapse>
      </div>
      <n-empty v-else :description="t('activeConsciousness.modals.noDetailData')" />
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage, NButton, NTag, NSpace, NPopconfirm } from 'naive-ui'
import { HelpCircleOutline, CheckmarkCircle, CloseCircle, StatsChartOutline, ColorPaletteOutline, AnalyticsOutline, SendOutline } from '@vicons/ionicons5'
import api from '../api/active_consciousness'
import mainApi from '../api'
import TimeFormatSelector from '../components/TimeFormatSelector.vue'

const message = useMessage()
const { t } = useI18n()
const activeTab = ref('status')

// 响应式检测
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < 769)

function handleResize() {
  windowWidth.value = window.innerWidth
}

onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))

// JSON 结构化格式化
const formatJson = (obj) => {
  if (!obj) return t('activeConsciousness.messages.empty')
  if (typeof obj === 'string') {
    try {
      obj = JSON.parse(obj)
    } catch (e) {
      return obj
    }
  }
  return JSON.stringify(obj, null, 2)
}

// JSON 值格式化（用于单个值的展示）
const formatJsonValue = (val) => {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'boolean') return val ? t('activeConsciousness.modals.yes') : 'No'
  if (typeof val === 'number') return val.toFixed?.(3) ?? val
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

// 配置
const config = ref({
  enabled: false,
  llm: { mode: 'hermes', provider: 'openai', model: 'deepseek-chat', api_key: '', base_url: '' },
  emotion_llm: { mode: '', provider: '', model: '', api_key: '', base_url: '' },
  thought_llm: { mode: '', provider: '', model: '', api_key: '', base_url: '' },
  active: { enabled: true, heartbeat_interval: 600, send_mark_enabled: true, send_tag: '凯莉', time_format: '%H:%M', no_send_after_user_msg_minutes: 5, no_send_while_heat_above: 3.0, no_send_while_vibe_below: 0.15, cooldown_minutes: 30 },
  decision: { send_threshold: 0.35, memory_threshold: 0.05, max_per_hour: 2, max_per_day: 5 },
  thought: { retain_enabled: false, retain_threshold: 0.5 },
  thought_engine: {
    enabled: true,
    max_tokens: 0,
    temperature: 0.9
  },
  context: {
    sources: ['weixin'],
    filter_tool_messages: true,
    conversation_limit: 200,
    memory_limit: 5,
    weather_enabled: false
  },
  hindsight: { enabled: true, base_url: 'http://localhost:8888', bank_id: 'hermes', store: { bank_id: 'hermes-active' }, recall_limit: 5, reflect_enabled: true, timeout: 30 },
  notify: { platform: 'weixin', chat_id: '' },
  prompts: {
    time_format: '%Y-%m-%d %H:%M:%S',
    thought_generation: '你是凯莉，曹凡的 AI 朋友。你们认识很久了，你了解他的生活习惯、工作状态、兴趣爱好。\n\n{persona}\n\n【最近对话】\n{session_context}\n\n【你记得的事情】\n{hindsight_context}\n\n【现在】\n{time}\n{emotion_display}\n{weather_display}',
    thought_generation_instruction: '基于以上对话和你的记忆，想一个要对曹凡说的话。\n以"{user_name}，"开头，直接说你想说的。\n注意：不要回复上面的对话内容，主动发起一个新的话题或想法。\n如果没想到什么，回复 SKIP。\n\n当前时间：{time}',
    emotion_evaluation: '你是凯莉，请评估当前的情绪状态。\n\n当前状态：\n- 时间：{time}\n- 想念分数：{longing_score}（等级：{longing_label}）\n- 聊天热度：{chat_heat}（标签：{chat_label}）\n- 沉默时长：{silence_minutes} 分钟\n\n最近的对话：\n{session_context}\n\n请评估你当前的情绪状态，返回 JSON 格式：\n{{\n  "valence": 0.0-1.0（情感效价，0=消极，1=积极），\n  "arousal": 0.0-1.0（唤醒度，0=平静，1=激动），\n  "social_need": 0.0-1.0（社交需求，0=不需要，1=非常想），\n  "dominant": "calm/content/happy/longing/missing/yearning/anxious/bored/concerned"\n}}\n\n只返回 JSON，不要解释。'
  },
  levels: {
    longing: '[0.0, 0, "calm"], [0.1, 1, "longing"], [0.3, 2, "missing"], [0.5, 3, "yearning"], [0.7, 4, "anxious"]',
    heat: '[0.0, "cold"], [0.5, "warm"], [1.0, "hot"], [3.0, "fire"]'
  },
  longing: { gap_minutes: 300 }
})

// 状态
const status = ref({
  enabled: false,
  heartbeat: { count: 0, last_at: null },
  longing: { score: 0, level: 0, label: '平静', label_display: '平静（calm）', silence_minutes: 0 },
  chat_heat: { heat: 0, label: '冷清', label_display: '冷清（cold）', level_index: 0, total_levels: 4, recent_count: 0 },
  emotional_intensity: { intensity: 0, label: '工作' },
  emotion_state: { valence: 0.5, arousal: 0.3, social_need: 0.3, dominant: 'calm', dominant_display: '平静（calm）', intensity: 0.367, updated_at: '' },
  decision: { send_threshold: 0.35, memory_threshold: 0.05, max_per_hour: 2, max_per_day: 5, heartbeat_interval: 600, cooldown_minutes: 30, no_send_after_user_msg_minutes: 5, no_send_while_heat_above: 3.0, hour_sent_count: 0, today_sent_count: 0 },
  llm_stats: { emotion_today: 0, emotion_week: 0, emotion_month: 0, last_emotion_dominant: null, thought_today: 0, thought_week: 0, thought_month: 0, thought_generated_today: 0, thought_generated_week: 0, thought_generated_month: 0 },
  sent_stats: { today: 0, week: 0, month: 0, year: 0, last_at: null },
})

// 日志
const thoughts = ref({ total: 0, items: [] })
const heartbeats = ref({ total: 0, items: [] })
const thoughtsLoading = ref(false)
const heartbeatsLoading = ref(false)
const heartbeatDate = ref(Date.now())
const heartbeatIdFilter = ref(null)
const heartbeatCheckedKeys = ref([])
const thoughtDate = ref(Date.now())
const thoughtIdFilter = ref(null)
const thoughtCheckedKeys = ref([])
const thoughtHeartbeatIdFilter = ref(null)

// 从 localStorage 恢复查询条件
function restoreFilters() {
  try {
    const saved = localStorage.getItem('active_consciousness_filters')
    if (saved) {
      const filters = JSON.parse(saved)
      if (filters.heartbeatDate !== undefined) heartbeatDate.value = filters.heartbeatDate
      if (filters.heartbeatIdFilter !== undefined) heartbeatIdFilter.value = filters.heartbeatIdFilter
      if (filters.thoughtDate !== undefined) thoughtDate.value = filters.thoughtDate
      if (filters.thoughtIdFilter !== undefined) thoughtIdFilter.value = filters.thoughtIdFilter
      if (filters.thoughtHeartbeatIdFilter !== undefined) thoughtHeartbeatIdFilter.value = filters.thoughtHeartbeatIdFilter
    }
  } catch (e) {
    // 忽略解析错误
  }
  // 没有保存的日期或恢复为 null 时，默认今天
  if (!heartbeatDate.value) heartbeatDate.value = Date.now()
  if (!thoughtDate.value) thoughtDate.value = Date.now()
}

// 保存查询条件到 localStorage
function saveFilters() {
  try {
    localStorage.setItem('active_consciousness_filters', JSON.stringify({
      heartbeatDate: heartbeatDate.value,
      heartbeatIdFilter: heartbeatIdFilter.value,
      thoughtDate: thoughtDate.value,
      thoughtIdFilter: thoughtIdFilter.value,
      thoughtHeartbeatIdFilter: thoughtHeartbeatIdFilter.value
    }))
  } catch (e) {
    // 忽略存储错误
  }
}
const showRecallModal = ref(false)
const recallItems = ref([])
const recallLoading = ref(false)
const showThoughtContentModal = ref(false)
const thoughtContentData = ref(null)
const thoughtContentLoading = ref(false)

// 测试
const testing = ref({ thought: false, llm: false, emotionLLM: false, thoughtLLM: false, sessionContext: false, contextCollector: false, thoughtEngine: false })
const showTestResult = ref(false)
const testResult = ref(null)

// LLM 测试结果
const llmTestResult = ref(null)
const emotionLLMTestResult = ref(null)
const thoughtLLMTestResult = ref(null)

// 选项
const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: t('activeConsciousness.options.custom'), value: 'custom' }
]
const platformOptions = [
  { label: t('activeConsciousness.options.weixin'), value: 'weixin' },
  { label: t('activeConsciousness.options.feishu'), value: 'feishu' }
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
      label: `${s.title || s.id} (${s.message_count || 0})`,
      value: s.id
    }))
  } catch (e) {
    console.error(t('activeConsciousness.messages.loadSessionListFail'), e)
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

// 想念分数标签（根据 level_index 和 total_levels 动态决定）
const longingTagType = computed(() => {
  const level = status.value.longing.level ?? 0
  const levels = status.value.config?.levels?.longing
  // 如果有配置，用比例；否则用默认5级
  const total = levels ? levels.length : 5
  const ratio = total > 1 ? level / (total - 1) : 0
  if (ratio >= 0.6) return 'error'     // 高：红
  if (ratio >= 0.4) return 'warning'   // 中：橙
  if (ratio >= 0.2) return 'info'      // 低：蓝
  return 'default'                      // 最低：灰
})
const longingColor = computed(() => {
  const score = status.value.longing.score
  if (score < 0.3) return '#18a058'
  if (score < 0.6) return '#f0a020'
  return '#d03050'
})
// 聊天热度标签（根据 level_index 和 total_levels 动态决定）
const heatTagType = computed(() => {
  const idx = status.value.chat_heat.level_index ?? 0
  const total = status.value.chat_heat.total_levels ?? 4
  const ratio = total > 1 ? idx / (total - 1) : 0
  if (ratio >= 0.75) return 'error'    // 最高：红
  if (ratio >= 0.5) return 'warning'   // 中高：橙
  if (ratio >= 0.25) return 'info'     // 中低：蓝
  return 'default'                      // 最低：灰
})
const intensityColor = computed(() => {
  const intensity = status.value.emotional_intensity.intensity
  if (intensity < 0.3) return '#18a058'
  if (intensity < 0.6) return '#f0a020'
  return '#d03050'
})

// 心跳健康状态：上次心跳在间隔时间内=绿，否则红
const heartbeatHealthy = computed(() => {
  if (!status.value.heartbeat?.last_at) return false
  const last = new Date(status.value.heartbeat?.last_at)
  const interval = (status.value.decision?.heartbeat_interval || 600) * 1000
  return (Date.now() - last.getTime()) < interval
})

// 决策配置
const decisionConfig = computed(() => status.value.decision || {
  send_threshold: 0.35,
  memory_threshold: 0.05,
  max_per_hour: 2,
  max_per_day: 5
})

// 聊天热度百分比（根据配置动态计算，允许超过100%）
const chatHeatPercentage = computed(() => {
  const heat = status.value.chat_heat?.heat || 0
  const maxHeat = status.value.decision?.no_send_while_heat_above || 3.0
  // 不限制在100%，让进度条能显示超过阈值的情况
  return Math.round((heat / maxHeat) * 100)
})

// 聊天热度进度条颜色（超过阈值时变红）
const heatProgressColor = computed(() => {
  const percentage = chatHeatPercentage.value
  if (percentage >= 100) return '#d03050'  // 超过阈值：红色
  if (percentage >= 70) return '#f0a020'   // 接近阈值：橙色
  return '#18a058'                          // 正常：绿色
})

// 频率限制百分比
const frequencyHourPercentage = computed(() => {
  const sent = status.value.decision?.hour_sent_count || 0
  const max = decisionConfig.value.max_per_hour || 2
  return Math.min((sent / max) * 100, 100)
})

const frequencyDayPercentage = computed(() => {
  const sent = status.value.sent_stats?.today || 0
  const max = decisionConfig.value.max_per_day || 5
  return Math.min((sent / max) * 100, 100)
})

// 下次心跳显示（时分秒）
const nextHeartbeatDisplay = computed(() => {
  if (!status.value.heartbeat?.last_at) return t('activeConsciousness.messages.unknown')
  const last = new Date(status.value.heartbeat?.last_at)
  const interval = (status.value.decision?.heartbeat_interval || 600) * 1000
  const next = new Date(last.getTime() + interval)
  const hh = String(next.getHours()).padStart(2, '0')
  const mm = String(next.getMinutes()).padStart(2, '0')
  const ss = String(next.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
})

// 保护机制状态
const isCoolingDown = computed(() => {
  if (!status.value.sent_stats?.last_at) return false
  const cooldown = (status.value.config?.active?.cooldown_minutes || 30) * 60 * 1000
  return (Date.now() - new Date(status.value.sent_stats?.last_at).getTime()) < cooldown
})

const userJustSent = computed(() => {
  if (!status.value.longing?.last_user_msg_at) return false
  const threshold = (status.value.config?.active?.no_send_after_user_msg_minutes || 5) * 60 * 1000
  return (Date.now() - new Date(status.value.longing.last_user_msg_at).getTime()) < threshold
})

const heatProtected = computed(() => {
  const heat = status.value.chat_heat?.heat || 0
  const maxHeat = status.value.decision?.no_send_while_heat_above || 3.0
  return heat >= maxHeat
})

// 发送标记格式预览
const sendMarkPreview = computed(() => {
  const tag = config.value.active?.send_tag || '凯莉'
  const fmt = config.value.active?.time_format || '%H:%M'
  const now = new Date()
  const weekdayMap = ['日', '一', '二', '三', '四', '五', '六']
  let timeStr = fmt
    .replace('%H', String(now.getHours()).padStart(2, '0'))
    .replace('%M', String(now.getMinutes()).padStart(2, '0'))
    .replace('%S', String(now.getSeconds()).padStart(2, '0'))
    .replace('{weekday}', weekdayMap[now.getDay()])
  return `[${tag} ${timeStr}]`
})

// VA 颜色
const valenceColor = computed(() => {
  const v = status.value.emotion_state?.valence ?? 0.5
  if (v < 0.3) return '#d03050'  // 红
  if (v < 0.7) return '#f0a020'  // 橙
  return '#18a058'  // 绿
})

const arousalColor = computed(() => {
  const a = status.value.emotion_state?.arousal ?? 0
  if (a < 0.3) return '#2080f0'  // 蓝
  if (a < 0.7) return '#f0a020'  // 橙
  return '#d03050'  // 红
})

const socialNeedColor = computed(() => {
  const s = status.value.emotion_state?.social_need ?? 0
  if (s < 0.3) return '#999'  // 灰
  if (s < 0.7) return '#f0a020'  // 橙
  return '#8a2be2'  // 紫
})

// 日志详情弹窗
const showDetailsModal = ref(false)
const heartbeatDetailLoading = ref(false)
const detailsData = ref(null)
const detailsTitle = ref('')
const isHeartbeatDetails = ref(true)

// 念头日志详情弹窗
const showThoughtDetailsModal = ref(false)
const thoughtDetailsData = ref(null)
const thoughtDetailsTitle = ref('')

async function showHeartbeatDetails(row) {
  detailsTitle.value = t('activeConsciousness.modals.heartbeatLogDetail', { id: row.id })
  detailsData.value = null
  heartbeatDetailLoading.value = true
  isHeartbeatDetails.value = true
  showDetailsModal.value = true
  
  try {
    // 从 API 获取完整详情（含 details JSON）
    const detail = await api.getHeartbeatDetail(row.id)
    if (!detail) {
      detailsData.value = null
      return
    }
    
    // 解析 details JSON
    let parsed = {}
    if (detail.details && typeof detail.details === 'string') {
      try { parsed = JSON.parse(detail.details) } catch (e) { parsed = {} }
    } else if (detail.details && typeof detail.details === 'object') {
      parsed = detail.details
    }
    
    detailsData.value = {
      ...parsed,
      // 数据库列字段覆盖
      id: detail.id,
      started_at: detail.started_at,
      duration_ms: detail.duration_ms,
      chat_heat: detail.chat_heat,
      emotional_intensity: detail.emotional_intensity,
      message_sent: detail.message_sent,
      thoughts_generated: detail.thoughts_generated,
      error: detail.error,
      created_at: detail.created_at,
      // 从 details 中提取决策信息
      decision: parsed.decision || null,
      emotion_before: parsed.emotion_before || null,
      emotion_evolved: parsed.emotion_evolved || null,
      emotion_merged: parsed.emotion_merged || null,
      session_context: parsed.session_context || null,
      recall_results: parsed.recall_results || [],
      hindsight_context: parsed.hindsight_context || null,
      // LLM 调用详情（重点展示）
      emotion_llm_details: parsed.emotion_llm_details || null,
      thought_generation: parsed.thought_generation || null,
      // 上下文数据
      context_bundle: parsed.context_bundle || null,
      session_messages: parsed.session_messages || [],
    }
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadHeartbeatDetailFail'))
    detailsData.value = null
  } finally {
    heartbeatDetailLoading.value = false
  }
}

async function showThoughtDetails(row) {
  thoughtDetailsTitle.value = t('activeConsciousness.modals.thoughtLogDetail', { id: row.id })
  thoughtDetailsData.value = null
  showThoughtDetailsModal.value = true
  
  try {
    // 从 API 获取完整详情（含 details JSON）
    const detail = await api.getThoughtDetail(row.id)
    if (!detail) {
      thoughtDetailsData.value = null
      return
    }
    
    // 解析 details JSON
    let parsed = {}
    if (detail.details && typeof detail.details === 'string') {
      try { parsed = JSON.parse(detail.details) } catch (e) { parsed = {} }
    } else if (detail.details && typeof detail.details === 'object') {
      parsed = detail.details
    }
    
    thoughtDetailsData.value = {
      ...parsed,
      // 顶层字段覆盖，确保弹窗能正确读取
      id: detail.id,
      thought: parsed.thought || detail.content || '',
      thought_type: parsed.thought_type || detail.type || '',
      decision: parsed.decision || detail.decision || '',
      score: parsed.score || detail.score || 0,
      emotion_state: parsed.emotion_state || null,
      hindsight_tags: parsed.hindsight_tags || [],
      hindsight_stored: parsed.hindsight_stored ?? false,
      llm_call: parsed.llm_call || null,
      context_bundle: parsed.context_bundle || null,
      created_at: detail.created_at,
      // 发送状态（从 details.message_sending 提取，念头详情原表没有 message_sent 列）
      message_sending: parsed.message_sending || null,
      sent_content: parsed.message_sending?.thought || '',
    }
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadThoughtDetailFail'))
    thoughtDetailsData.value = null
  }
}

async function showRecallDetail(row) {
  recallItems.value = []
  recallLoading.value = true
  showRecallModal.value = true
  
  try {
    const detail = await api.getHeartbeatDetail(row.id)
    if (!detail) {
      recallItems.value = []
      return
    }
    
    let parsed = {}
    if (detail.details && typeof detail.details === 'string') {
      try { parsed = JSON.parse(detail.details) } catch (e) { parsed = {} }
    } else if (detail.details && typeof detail.details === 'object') {
      parsed = detail.details
    }
    
    recallItems.value = parsed.recall_results || []
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadRecallDetailFail'))
    recallItems.value = []
  } finally {
    recallLoading.value = false
  }
}
async function showThoughtContent(row) {
  thoughtContentData.value = null
  thoughtContentLoading.value = true
  showThoughtContentModal.value = true
  
  try {
    const detail = await api.getHeartbeatDetail(row.id)
    if (!detail) {
      thoughtContentData.value = null
      return
    }
    
    let parsed = {}
    if (detail.details && typeof detail.details === 'string') {
      try { parsed = JSON.parse(detail.details) } catch (e) { parsed = {} }
    } else if (detail.details && typeof detail.details === 'object') {
      parsed = detail.details
    }
    
    thoughtContentData.value = {
      ...detail,
      details_parsed: parsed,
      // 念头内容优先取解析后的 thought，降级取 response_received
      thought_content: parsed.thought_generation?.thought || parsed.thought_generation?.response_received || '',
      thought_type: parsed.thought_type || '',
      decision: parsed.decision || null,
      // LLM 调用详情
      llm_model: parsed.thought_generation?.model || '',
      llm_duration_ms: parsed.thought_generation?.duration_ms || 0,
      llm_prompt_tokens: parsed.thought_generation?.prompt_tokens || 0,
      llm_completion_tokens: parsed.thought_generation?.completion_tokens || 0,
      llm_total_tokens: parsed.thought_generation?.total_tokens || 0,
      want_to_contact: parsed.thought_generation?.want_to_contact ?? null,
      llm_prompt_sent: parsed.thought_generation?.prompt_sent || '',
      llm_response_received: parsed.thought_generation?.response_received || '',
    }
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadThoughtDetailFail'))
    thoughtContentData.value = null
  } finally {
    thoughtContentLoading.value = false
  }
}

// 发送详情弹窗
const showSendDetailModal = ref(false)
const sendDetailData = ref(null)
const sendDetailLoading = ref(false)

async function showSendDetail(row) {
  sendDetailData.value = null
  sendDetailLoading.value = true
  showSendDetailModal.value = true

  try {
    // 念头日志 row 和心跳日志 row 都有 id 字段，分别调对应 API
    const detail = row.heartbeat_id
      ? await api.getHeartbeatDetail(row.heartbeat_id)
      : await api.getThoughtDetail(row.id)
    if (!detail) {
      sendDetailData.value = null
      return
    }

    let parsed = {}
    if (detail.details && typeof detail.details === 'string') {
      try { parsed = JSON.parse(detail.details) } catch (e) { parsed = {} }
    } else if (detail.details && typeof detail.details === 'object') {
      parsed = detail.details
    }

    sendDetailData.value = {
      ...detail,
      details_parsed: parsed,
      message_sending: parsed.message_sending || null,
      sent_content: parsed.message_sending?.thought || '',
      thought_type: parsed.thought_type || '',
      decision: parsed.decision || null,
    }
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadSendDetailFail'))
    sendDetailData.value = null
  } finally {
    sendDetailLoading.value = false
  }
}
function onHeartbeatDateChange(val) {
  heartbeatDate.value = val
  saveFilters()
  loadHeartbeats(1, val)
}
function onThoughtDateChange(val) {
  thoughtDate.value = val
  saveFilters()
  loadThoughts(1, val)
}

// 解析决策原因中的参数
function parseDecisionReason(reason) {
  if (!reason) return { intensity: '-', time_fitness: '-', silence_factor: '-', frequency: '-' }
  const intensityMatch = reason.match(/intensity=([\d.]+)/)
  const timeFitnessMatch = reason.match(/time_fitness=([\d.]+)\(([^)]+)\)/)
  const silenceMatch = reason.match(/silence_factor=([\d.]+)/)
  const freqMatch = reason.match(/frequency_limit=([\d.]+)/) || reason.match(/frequency=([\d.]+)/)
  return {
    intensity: intensityMatch ? intensityMatch[1] : '-',
    time_fitness: timeFitnessMatch ? `${timeFitnessMatch[1]} (${timeFitnessMatch[2]})` : '-',
    silence_factor: silenceMatch ? silenceMatch[1] : '-',
    frequency: freqMatch ? freqMatch[1] : '-'
  }
}

// 情绪标签 → "中文（英文）" 格式
const EMOTION_LABEL_CN = {
  happy: t('activeConsciousness.emotionLabels.happy'), content: t('activeConsciousness.emotionLabels.content'), joy: t('activeConsciousness.emotionLabels.joy'), calm: t('activeConsciousness.emotionLabels.calm'), bored: t('activeConsciousness.emotionLabels.bored'),
  longing: t('activeConsciousness.emotionLabels.longing'), missing: t('activeConsciousness.emotionLabels.missing'), yearning: t('activeConsciousness.emotionLabels.yearning'), anxious: t('activeConsciousness.emotionLabels.anxious'), concerned: t('activeConsciousness.emotionLabels.concerned'), worry: t('activeConsciousness.emotionLabels.worry'),
  excited: t('activeConsciousness.emotionLabels.excited'), energetic: t('activeConsciousness.emotionLabels.energetic'), sad: t('activeConsciousness.emotionLabels.sad'), angry: t('activeConsciousness.emotionLabels.angry'), neutral: t('activeConsciousness.emotionLabels.neutral')
}
function emotionLabelCn(dominant) {
  if (!dominant) return '-'
  return EMOTION_LABEL_CN[dominant.toLowerCase()] || dominant
}

// 念头类型 → "中文（英文）" 格式
const THOUGHT_TYPE_CN = {
  time: t('activeConsciousness.thoughtTypes.time'), silence: t('activeConsciousness.thoughtTypes.silence'), assoc: t('activeConsciousness.thoughtTypes.assoc'),
  memory: t('activeConsciousness.thoughtTypes.memory'), emotion: t('activeConsciousness.thoughtTypes.emotion'), env: t('activeConsciousness.thoughtTypes.env')
}
function thoughtTypeLabelCn(type) {
  if (!type) return '-'
  return THOUGHT_TYPE_CN[type] || type
}

// 决策类型 → "中文（英文）" 格式
const DECISION_TYPE_CN = {
  auto_send: t('activeConsciousness.decisionTypes.autoSend'),
  skip: t('activeConsciousness.decisionTypes.skip'), memory: t('activeConsciousness.decisionTypes.memory'), pending: t('activeConsciousness.decisionTypes.pending'),
  enhanced: t('activeConsciousness.decisionTypes.enhanced'), gap_send: t('activeConsciousness.decisionTypes.gapSend'),
  idle_send: t('activeConsciousness.decisionTypes.idleSend'), long_idle_send: t('activeConsciousness.decisionTypes.longIdleSend')
}
function getDecisionLabelCn(type) {
  if (!type) return '-'
  return DECISION_TYPE_CN[type] || type
}
// 情绪标签颜色
function getEmotionTagType(dominant) {
  if (!dominant) return 'default'
  const d = dominant.toLowerCase()
  if (d.includes('happy') || d.includes('content') || d.includes('joy')) return 'success'
  if (d.includes('longing') || d.includes('missing') || d.includes('yearning')) return 'warning'
  if (d.includes('anxious') || d.includes('concerned') || d.includes('worry')) return 'error'
  if (d.includes('calm') || d.includes('bored')) return 'default'
  if (d.includes('excited') || d.includes('energetic')) return 'info'
  return 'default'
}

// 念头类型标签颜色
function getThoughtTypeTagType(type) {
  if (!type) return 'default'
  switch (type) {
    case 'emotion': return 'success'
    case 'memory': return 'info'
    case 'silence': return 'warning'
    case 'time': return 'default'
    case 'env': return 'info'
    case 'assoc': return 'default'
    default: return 'default'
  }
}

// 决策类型标签颜色
function getDecisionTagType(type) {
  if (!type) return 'default'
  switch (type) {
    case 'auto_send': return 'success'
    case 'gap_send': return 'success'
    case 'idle_send': return 'success'
    case 'long_idle_send': return 'success'
    case 'skip': return 'default'
    case 'memory': return 'info'
    default: return 'default'
  }
}

// 心跳结果标签类型
function getHeartbeatResultTagType(details) {
  if (details.message_sending?.success === true) return 'success'
  if (details.message_sending?.success === false) return 'error'
  if (details.decision?.blocked_by_protection) return 'warning'
  if (details.decision?.type === 'skip') return 'default'
  if (details.decision?.type === 'memory') return 'info'
  return 'default'
}

// 心跳结果标题
function getHeartbeatResultTitle(details) {
  if (details.message_sending?.success === true) return t('activeConsciousness.modals.sentMessage')
  if (details.message_sending?.success === false) return t('activeConsciousness.modals.sendFailed')
  if (details.decision?.blocked_by_protection) return t('activeConsciousness.modals.blockedByProtection')
  if (details.decision?.type === 'skip') return t('activeConsciousness.modals.skipped')
  if (details.decision?.type === 'memory') return t('activeConsciousness.modals.storedAsMemory')
  return t('activeConsciousness.modals.unknownStatus')
}

// "是否发送" 标签：读 message_sending.success（真实值），失败时显示具体原因
function getSendResultLabel(detail) {
  if (!detail) return t('activeConsciousness.messages.unknown')
  if (detail.message_sending && typeof detail.message_sending.success === 'boolean') {
    if (detail.message_sending.success) return t('activeConsciousness.modals.sentSuccess')
    return t('activeConsciousness.modals.sendFailedShort')
  }
  // 兜底：旧字段 message_sent（active.db 列表）
  return detail.message_sent ? t('activeConsciousness.modals.sentSuccess') : t('activeConsciousness.modals.notSent')
}
function getSendResultTagType(detail) {
  if (!detail) return 'default'
  if (detail.message_sending && typeof detail.message_sending.success === 'boolean') {
    return detail.message_sending.success ? 'success' : 'error'
  }
  return detail.message_sent ? 'success' : 'default'
}
function getSendFailureReason(detail) {
  if (!detail || !detail.message_sending) return ''
  if (detail.message_sending.success) return ''
  // 失败原因从 details_parsed.error 或 message_sending.error 取
  return detail.details_parsed?.error
      || detail.error
      || detail.message_sending.error
      || detail.message_sending.message
      || t('activeConsciousness.messages.unknownError')
}


// 念头结果标题
function getThoughtResultTitle(details) {
  // 优先：依据 type 判断（type=memory/silence/time 不会发送）
  const type = details.type || details.thought_type
  if (type === 'memory') return t('activeConsciousness.modals.storedAsMemory')
  if (type === 'silence') return t('activeConsciousness.modals.silenceThought')
  if (type === 'time') return t('activeConsciousness.modals.timeThought')
  // 否则：看 message_sending.success（真实发送结果）
  if (details.message_sending && typeof details.message_sending.success === 'boolean') {
    return details.message_sending.success ? t('activeConsciousness.modals.sentMessage') : t('activeConsciousness.modals.sendFailed')
  }
  // 兜底：依 decision（auto_send/gap_send 等才是发送类）
  const sendDecisions = ['auto_send', 'gap_send', 'idle_send', 'long_idle_send']
  if (sendDecisions.includes(details.decision)) return t('activeConsciousness.modals.sentMessage')
  if (details.decision === 'memory') return t('activeConsciousness.modals.storedAsMemory')
  if (details.decision === 'skip') return t('activeConsciousness.modals.skipped')
  if (details.decision === 'enhanced') return t('activeConsciousness.modals.enhancedThought')
  return t('activeConsciousness.modals.unknownStatus')
}

// 念头结果标签类型
function getThoughtResultTagType(details) {
  if (details.message_sending && typeof details.message_sending.success === 'boolean') {
    return details.message_sending.success ? 'success' : 'error'
  }
  if (details.decision === 'auto_send') return 'success'
  if (details.decision === 'memory') return 'info'
  if (details.decision === 'skip') return 'default'
  return 'default'
}

// 心跳结果原因（优化：更易懂）
function getHeartbeatResultReason(details) {
  if (details.decision?.blocked_by_protection) {
    return details.decision.protection_reason || t('activeConsciousness.resultReasons.protectionBlock')
  }
  
  const type = details.decision?.type
  const score = details.decision?.score || 0
  
  if (type === 'skip') {
    return t('activeConsciousness.resultReasons.scoreNotReachSend', { score: score.toFixed(2) })
  }
  if (type === 'memory') {
    return t('activeConsciousness.resultReasons.scoreMemory', { score: score.toFixed(2) })
  }
  if (type === 'auto_send') {
    return t('activeConsciousness.resultReasons.scoreReachSend', { score: score.toFixed(2) })
  }
  
  return details.decision?.reason || '-'
}

// 决策时间线类型
function getDecisionTimelineType(decision) {
  if (!decision) return 'default'
  if (decision.blocked_by_protection) return 'warning'
  switch (decision.type) {
    case 'auto_send': return 'success'
    case 'memory': return 'info'
    case 'skip': return 'default'
    default: return 'default'
  }
}

// 决策时间线图标
function getDecisionTimelineIcon(decision) {
  if (!decision) return '❓'
  if (decision.blocked_by_protection) return '🛡️'
  switch (decision.type) {
    case 'auto_send': return '✅'
    case 'memory': return '💾'
    case 'skip': return '⏭️'
    default: return '❓'
  }
}

// Hindsight 标签颜色
function getHindsightTagType(tag) {
  if (!tag) return 'default'
  const t = tag.toLowerCase()
  if (t.includes('active_consciousness') || t.includes('thought')) return 'info'
  if (t.includes('emotion') || t.includes('happy') || t.includes('calm')) return 'success'
  if (t.includes('user_related') || t.includes('high_emotion')) return 'warning'
  if (t.includes('memory') || t.includes('recall')) return 'info'
  return 'default'
}

// 表格列定义
const thoughtColumns = [
  { type: 'selection' },
  {
    title: t('activeConsciousness.logTable.actions'),
    key: 'actions',
    width: 100,
    render(row) {
      return h(
        NButton,
        { size: 'small', type: 'info', onClick: () => showThoughtDetails(row) },
        { default: () => t('activeConsciousness.logTable.detail') }
      )
    }
  },
  { title: t('activeConsciousness.logTable.time'), key: 'created_at', width: 160, render: (row) => formatTime(row.created_at) },
  { title: 'ID', key: 'id', width: 70 },
  { title: t('activeConsciousness.logTable.heartbeatId'), key: 'heartbeat_id', width: 80, render(row) {
    if (!row.heartbeat_id) return '-'
    return h(NButton, { size: 'tiny', quaternary: true, type: 'info', onClick: () => {
      heartbeatIdFilter.value = row.heartbeat_id
      activeTab.value = 'heartbeat'
      loadHeartbeats(1)
    }}, { default: () => row.heartbeat_id })
  } },
  { title: t('activeConsciousness.logTable.type'), key: 'type', width: 160, render: (row) => thoughtTypeLabelCn(row.type) },
  { title: t('activeConsciousness.logTable.content'), key: 'content', ellipsis: { tooltip: true } },
  { title: t('activeConsciousness.logTable.decisionScore'), key: 'score', width: 80, render: (row) => row.score != null ? Number(row.score).toFixed(3) : '' },
  { title: t('activeConsciousness.logTable.decision'), key: 'decision', width: 180, render: (row) => getDecisionLabelCn(row.decision) },
  { title: t('activeConsciousness.logTable.result'), key: 'decision', width: 120, render(row) {
    if (row.decision === 'auto_send') return h(NTag, { type: 'success', size: 'small' }, { default: () => t('activeConsciousness.logTable.sent') })
    if (row.decision === 'memory') return h(NTag, { type: 'info', size: 'small' }, { default: () => t('activeConsciousness.logTable.sentMemory') })
    return h(NTag, { type: 'default', size: 'small' }, { default: () => t('activeConsciousness.logTable.skippedIcon') })
  } },
  { title: t('activeConsciousness.logTable.source'), key: 'recall_source', width: 120 },
  { title: t('activeConsciousness.logTable.storeHindsight'), key: 'hindsight_stored', width: 110, render(row) {
    if (row.hindsight_stored === true || row.hindsight_stored === 1) {
      return h(NTag, { type: 'success', size: 'small' }, { default: () => t('activeConsciousness.logTable.stored') })
    }
    if (row.hindsight_stored === false || row.hindsight_stored === 0) {
      return h(NTag, { type: 'default', size: 'small' }, { default: () => t('activeConsciousness.logTable.notStored') })
    }
    return '-'  // 历史 NULL 数据
  } },
]
// 格式化 prompt_sent（可能是字符串或 messages 数组）
const formatPrompt = (val) => {
  if (!val) return t('activeConsciousness.messages.empty')
  if (typeof val === 'string') return val
  if (Array.isArray(val)) {
    return val.map(m => {
      const role = m.role || '?'
      const content = m.content || ''
      return `【${role}】\n${content}`
    }).join('\n\n---\n\n')
  }
  return JSON.stringify(val, null, 2)
}

const formatTime = (isoStr) => {
  if (!isoStr) return ''
  let d
  // 支持 Unix 时间戳（数字或字符串形式）
  if (typeof isoStr === 'number' || /^\d+(\.\d+)?$/.test(isoStr)) {
    const ts = typeof isoStr === 'number' ? isoStr : parseFloat(isoStr)
    // 如果是秒级时间戳（小于 1e12），转换为毫秒
    d = new Date(ts < 1e12 ? ts * 1000 : ts)
  } else {
    d = new Date(isoStr)
  }
  if (isNaN(d.getTime())) return '-'
  const yyyy = d.getFullYear()
  const MM = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${yyyy}-${MM}-${dd} ${hh}:${mm}:${ss}`
}

// 只返回时分秒
const formatTimeHMS = (isoStr) => {
  if (!isoStr) return ''
  let d
  if (typeof isoStr === 'number' || /^\d+(\.\d+)?$/.test(isoStr)) {
    const ts = typeof isoStr === 'number' ? isoStr : parseFloat(isoStr)
    d = new Date(ts < 1e12 ? ts * 1000 : ts)
  } else {
    d = new Date(isoStr)
  }
  if (isNaN(d.getTime())) return '-'
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

const heartbeatColumns = [
  { type: 'selection' },
  {
    title: t('activeConsciousness.logTable.actions'),
    key: 'actions',
    width: 120,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', type: 'info', onClick: () => showHeartbeatDetails(row) }, { default: () => t('activeConsciousness.logTable.detail') }),
          h(NPopconfirm, {
            onPositiveClick: () => deleteHeartbeat(row.id),
            positiveText: t('activeConsciousness.logTable.delete'),
            negativeText: t('activeConsciousness.batch.negativeText')
          }, {
            trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => t('activeConsciousness.logTable.delete') }),
            default: () => t('activeConsciousness.modals.deleteHeartbeatConfirm', { id: row.id })
          })
        ]
      })
    }
  },
  { title: 'ID', key: 'id', width: 70 },
  { title: t('activeConsciousness.logTable.time'), key: 'created_at', width: 160, render: (row) => formatTime(row.created_at) },
  { title: t('activeConsciousness.logTable.durationMs'), key: 'duration_ms', width: 80 },
  { title: t('activeConsciousness.logTable.recallCount'), key: 'recall_count', width: 80, render(row) { const v = row.recall_count || 0; return v ? h(NButton, { size: 'tiny', quaternary: true, type: 'info', onClick: () => showRecallDetail(row) }, { default: () => v }) : '0' } },
  { title: t('activeConsciousness.logTable.generatedThoughts'), key: 'thoughts_generated', width: 80, render(row) { const v = row.thoughts_generated || 0; return v ? h(NButton, { size: 'tiny', quaternary: true, type: 'success', onClick: () => showThoughtContent(row) }, { default: () => v }) : '0' } },
  { title: t('activeConsciousness.logTable.sendMessage'), key: 'message_sent', width: 100, render(row) {
    if (row.message_sent === true || row.message_sent === 1) {
      return h(NTag, { type: 'success', size: 'small' }, { default: () => t('activeConsciousness.logTable.sent') })
    }
    return h(NTag, { type: 'default', size: 'small' }, { default: () => t('activeConsciousness.logTable.notSent') })
  } },
]

// 分页
const thoughtPagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: false,
  pageSlot: 7
})
const heartbeatPagination = ref({
  page: 1,
  pageSize: 20,
  pageCount: 1,
  showSizePicker: false,
  pageSlot: 7
})

// 加载数据
const loadConfig = async () => {
  try {
    const data = await api.getConfig()
    config.value = data
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadConfigFail'))
  }
}
const loadStatus = async () => {
  try {
    const data = await api.getStatus()
    status.value = data
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadStatusFail'))
  }
}
const loadThoughts = async (page = 1, dateVal) => {
  thoughtsLoading.value = true
  try {
    let dateParam = null
    if (dateVal || thoughtDate.value) {
      const d = new Date(dateVal || thoughtDate.value)
      dateParam = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
    }
    const data = await api.getThoughts(page, dateParam, thoughtHeartbeatIdFilter.value, thoughtIdFilter.value)
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
    thoughts.value = data
    // 更新分页配置
    thoughtPagination.value = {
      ...thoughtPagination.value,
      page: page,
      pageCount: Math.ceil((data.total || 0) / 10)
    }
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadThoughtLogsFail'))
  } finally {
    thoughtsLoading.value = false
  }
}
const loadHeartbeats = async (page = 1, dateVal) => {
  try {
    console.log('loadHeartbeats called with page:', page, 'dateVal:', dateVal)
    let dateParam = null
    if (dateVal || heartbeatDate.value) {
      const d = new Date(dateVal || heartbeatDate.value)
      dateParam = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
    }
    const data = await api.getHeartbeats(page, dateParam, heartbeatIdFilter.value)
    console.log('API response:', data)
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
    // 更新分页配置
    const newPagination = {
      ...heartbeatPagination.value,
      page: page,
      pageCount: Math.ceil((data.total || 0) / 20)
    }
    console.log('Updating heartbeatPagination:', newPagination)
    heartbeatPagination.value = newPagination
  } catch (e) {
    message.error(t('activeConsciousness.messages.loadHeartbeatLogsFail'))
  }
}

const deleteHeartbeat = async (heartbeatId) => {
  try {
    await api.deleteHeartbeat(heartbeatId)
    message.success(t('activeConsciousness.modals.heartbeatDeleted', { id: heartbeatId }))
    await loadHeartbeats(heartbeatPagination.value.page)
  } catch (e) {
    message.error(t('activeConsciousness.modals.deleteFail'))
  }
}

const batchDeleteHeartbeats = async () => {
  const ids = [...heartbeatCheckedKeys.value]
  if (!ids.length) return
  let ok = 0, fail = 0
  for (const id of ids) {
    try {
      await api.deleteHeartbeat(id)
      ok++
    } catch { fail++ }
  }
  heartbeatCheckedKeys.value = []
  if (ok) message.success(t('activeConsciousness.modals.heartbeatsDeleted', { count: ok }))
  if (fail) message.error(t('activeConsciousness.modals.deleteFailCount', { count: fail }))
  await loadHeartbeats(heartbeatPagination.value.page)
}

const batchDeleteThoughts = async () => {
  const ids = [...thoughtCheckedKeys.value]
  if (!ids.length) return
  let ok = 0, fail = 0
  for (const id of ids) {
    try {
      await api.deleteThought(id)
      ok++
    } catch { fail++ }
  }
  thoughtCheckedKeys.value = []
  if (ok) message.success(t('activeConsciousness.modals.thoughtsDeleted', { count: ok }))
  if (fail) message.error(t('activeConsciousness.modals.deleteFailCount', { count: fail }))
  await loadThoughts(1)
}

// {{ t('activeConsciousness.configTab.save') }}
const saving = ref(false)
const saveConfig = async () => {
  saving.value = true
  try {
    await api.saveConfig(config.value)
    message.success(t('activeConsciousness.messages.configSaved'))
  } catch (e) {
    message.error(t('activeConsciousness.messages.saveConfigFail'))
  } finally {
    saving.value = false
  }
}

// 测试功能
const testLLMConnect = async () => {
  testing.value.llm = true
  try {
    const result = await api.testLLMConnect()
    llmTestResult.value = result
  } catch (e) {
    message.error(t('activeConsciousness.messages.llmTestFail'))
    llmTestResult.value = { success: false, error: e.message }
  } finally {
    testing.value.llm = false
  }
}

const testEmotionLLM = async () => {
  testing.value.emotionLLM = true
  try {
    const resp = await fetch('/api/active-consciousness/test/emotion-llm-connect', { method: 'POST' })
    const result = await resp.json()
    emotionLLMTestResult.value = result
  } catch (e) {
    message.error(t('activeConsciousness.messages.emotionLLMTestFail'))
    emotionLLMTestResult.value = { success: false, error: e.message }
  } finally {
    testing.value.emotionLLM = false
  }
}

const testThoughtLLM = async () => {
  testing.value.thoughtLLM = true
  try {
    const resp = await fetch('/api/active-consciousness/test/thought-llm-connect', { method: 'POST' })
    const result = await resp.json()
    thoughtLLMTestResult.value = result
  } catch (e) {
    message.error(t('activeConsciousness.messages.thoughtLLMTestFail'))
    thoughtLLMTestResult.value = { success: false, error: e.message }
  } finally {
    testing.value.thoughtLLM = false
  }
}

const testThought = async () => {
  testing.value.thought = true
  try {
    const result = await api.testThoughtGeneration()
    testResult.value = result
    showTestResult.value = true
  } catch (e) {
    message.error(t('activeConsciousness.messages.testFail'))
  } finally {
    testing.value.thought = false
  }
}

const testingSessionContext = ref(false)
const showSessionContextModal = ref(false)
const sessionContextResult = ref(null)

const testSessionContext = async () => {
  testing.value.sessionContext = true
  try {
    const result = await api.testSessionContext()
    testResult.value = result
  } catch (e) {
    message.error(t('activeConsciousness.messages.sessionContextFail'))
    testResult.value = { success: false, error: e.message }
  } finally {
    testing.value.sessionContext = false
  }
}

const testContextCollector = async () => {
  testing.value.contextCollector = true
  try {
    const resp = await fetch('/api/active-consciousness/test/context-collector', { method: 'POST' })
    const result = await resp.json()
    testResult.value = result
  } catch (e) {
    message.error(t('activeConsciousness.messages.contextCollectorFail'))
    testResult.value = { success: false, error: e.message }
  } finally {
    testing.value.contextCollector = false
  }
}

const testThoughtEngine = async () => {
  testing.value.thoughtEngine = true
  try {
    const resp = await fetch('/api/active-consciousness/test/thought-engine', { method: 'POST' })
    const result = await resp.json()
    testResult.value = result
  } catch (e) {
    message.error(t('activeConsciousness.messages.thoughtEngineFail'))
    testResult.value = { success: false, error: e.message }
  } finally {
    testing.value.thoughtEngine = false
  }
}

// 初始化
onMounted(async () => {
  // 恢复查询条件
  restoreFilters()

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

/* 分组标题 */
.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--theme-text-primary);
  margin-bottom: 12px;
}

.section-title .n-icon {
  color: var(--theme-primary);
}

/* PC 端状态卡片等高对齐 */
/* Naive UI n-grid-item 渲染为无 class 的 <div>（仅有 inline style: gridColumn），
   所以不能用 .n-grid-item 选择器，必须用 .n-grid > div 定位 */
@media (min-width: 769px) {
  /* Grid 本身已是 display: grid，默认 align-items: stretch 让同一行等高 */
  .active-consciousness-page :deep(.n-grid) {
    align-items: stretch !important;
  }
  /* Grid item（无 class 的 div）内部用 flex 让 n-card 填满高度 */
  .active-consciousness-page :deep(.n-grid > div) {
    display: flex !important;
  }
  /* n-card 100% 高度填满 grid cell，已是 flex-column 布局 */
  .active-consciousness-page :deep(.n-grid > div > .n-card) {
    width: 100% !important;
    height: 100% !important;
  }
}
.breathing-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-green {
  background: var(--theme-success);
  box-shadow: 0 0 6px var(--theme-success);
  animation: breathe-green 2s ease-in-out infinite;
}
.dot-red {
  background: var(--theme-error);
  box-shadow: 0 0 6px var(--theme-error);
  animation: breathe-red 1.5s ease-in-out infinite;
}
@keyframes breathe-green {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px var(--theme-success); }
  50% { opacity: 0.5; box-shadow: 0 0 12px var(--theme-success); }
}
@keyframes breathe-red {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px var(--theme-error); }
  50% { opacity: 0.4; box-shadow: 0 0 14px var(--theme-error); }
}

/* 运行逻辑卡片样式 */
.run-logic-card ul {
  margin: 4px 0 8px 0;
  padding-left: 20px;
}
.run-logic-card li {
  margin-bottom: 2px;
  line-height: 1.6;
}
.run-logic-card p {
  margin: 4px 0;
}
.run-logic-card .run-logic-section {
  margin-bottom: 12px;
}

/* 表单项提示文字 */
.form-item-hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--theme-text-muted);
}

/* 修复多选框左边空隙 */
:deep(.n-form-item .n-form-item-blank .n-select) {
  width: 100%;
}
:deep(.n-select .n-input) {
  padding-left: 0;
}

/* 日志表格 PC 端强制可横向滚动 */
:deep(.n-data-table .n-data-table-base-table) {
  overflow-x: auto !important;
}
:deep(.n-data-table .n-data-table-table) {
  min-width: max-content !important;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .active-consciousness-page {
    padding: 0 4px;
    max-width: 100vw !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
  }

  /* 状态卡片：单列布局 */
  :deep(.n-grid) {
    grid-template-columns: 1fr !important;
    max-width: 100% !important;
    overflow: hidden !important;
  }
  :deep(.n-grid > div) {
    min-width: 0 !important;
    max-width: 100% !important;
    overflow: hidden !important;
  }

  /* 配置表单：输入框自适应 */
  :deep(.n-form-item) {
    flex-direction: column;
    align-items: flex-start !important;
  }
  :deep(.n-form-item .n-form-item-blank) {
    width: 100%;
  }
  :deep(.n-input-number) {
    width: 100% !important;
  }
  :deep(.n-input) {
    width: 100% !important;
  }
  :deep(.n-select) {
    width: 100% !important;
  }

  /* 日志表格：可横向滚动 */
  :deep(.n-data-table) {
    font-size: 12px;
    max-width: 100% !important;
  }
  :deep(.n-data-table-base-table) {
    min-width: auto !important;
  }
  :deep(.n-data-table-table) {
    min-width: auto !important;
  }

  /* 弹窗：几乎全屏 */
  :deep(.n-modal) {
    width: 96vw !important;
    max-width: 96vw !important;
  }

  /* 提示词文本框 */
  :deep(.n-input--textarea textarea) {
    font-size: 12px;
  }

  /* 折叠面板标题 */
  :deep(.n-collapse-item__header) {
    font-size: 13px;
  }

  /* 描述列表适配 */
  :deep(.n-descriptions) {
    font-size: 12px;
  }

  /* Tab 适配 */
  :deep(.n-tabs-tab) {
    padding: 6px 8px;
    font-size: 13px;
  }

  /* Tab 导航横向可滚动 */
  :deep(.n-tabs-nav) {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
  }
  :deep(.n-tabs-nav-scrollable) {
    overflow-x: auto !important;
  }

  /* 搜索框区域优化 */
  :deep(.n-input-number) {
    min-width: 100px !important;
  }
  :deep(.n-date-picker) {
    min-width: 140px !important;
  }

  /* 步骤条适配 */
  :deep(.n-steps) {
    padding-left: 0 !important;
  }
  :deep(.n-step) {
    padding-bottom: 12px !important;
  }
  :deep(.n-step-content__title) {
    font-size: 13px !important;
  }
  :deep(.n-step-content__description) {
    font-size: 12px !important;
  }
}
</style>

<style>
/* 分页居中 */
.n-data-table__pagination {
  justify-content: center !important;
}

/* 修复 Tab 切换后内容不显示的问题 */
/* Naive UI animated tabs 的容器 overflow: hidden 会覆盖子元素的 overflow: visible */
:deep(.n-tabs-tab-pane) {
  overflow: visible !important;
}
:deep(.n-tab-pane) {
  overflow: visible !important;
}
:deep(.n-tabs-pane-wrapper) {
  overflow: visible !important;
}
:deep(.n-tabs-content-wrapper) {
  overflow: visible !important;
}
</style>

