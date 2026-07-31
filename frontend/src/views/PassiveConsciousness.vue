<template>
  <div class="passive-consciousness-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 配置 -->
      <n-tab-pane name="config" :tab="t('passiveConsciousness.tabs.config')">
        <n-card :title="'💡 ' + t('passiveConsciousness.config.title')" style="margin-bottom: 16px">
          <!-- 总开关 -->
          <n-form-item :label="t('passiveConsciousness.config.enable')">
            <n-switch v-model:value="config.enabled" />
          </n-form-item>

          <template v-if="config.enabled">
            <!-- LLM 配置 -->
            <n-divider>{{ t('passiveConsciousness.config.llm.title') }}</n-divider>
            <n-form-item :label="t('passiveConsciousness.config.llm.mode')">
              <n-radio-group v-model:value="config.llm.mode">
                <n-radio value="hermes">{{ t('passiveConsciousness.config.llm.hermesMode') }}</n-radio>
                <n-radio value="custom">{{ t('passiveConsciousness.config.llm.customMode') }}</n-radio>
              </n-radio-group>
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.llm.provider')" v-if="config.llm.mode === 'custom'">
              <n-select v-model:value="config.llm.provider" :options="providerOptions" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.llm.model')" v-if="config.llm.mode === 'custom'">
              <n-input v-model:value="config.llm.model" placeholder="deepseek-chat" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.llm.apiKey')" v-if="config.llm.mode === 'custom'">
              <n-input v-model:value="config.llm.api_key" :placeholder="t('passiveConsciousness.config.llm.apiKeyPlaceholder')" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.llm.baseUrl')" v-if="config.llm.mode === 'custom'">
              <n-input v-model:value="config.llm.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>

            <!-- 被动意识配置 -->
            <n-divider>{{ t('passiveConsciousness.config.injection.title') }}</n-divider>
            <n-form-item :label="t('passiveConsciousness.config.injection.enable')">
              <n-switch v-model:value="config.passive.enabled" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.injection.emotion')">
              <n-switch v-model:value="config.passive.inject_emotion" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.injection.heat')">
              <n-switch v-model:value="config.passive.inject_heat" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.injection.memory')">
              <n-switch v-model:value="config.passive.inject_memory" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.injection.thought')">
              <n-switch v-model:value="config.passive.inject_thought" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.injection.tag')">
              <n-input v-model:value="config.passive.inject_tag" placeholder="[CONSCIOUSNESS_CONTEXT]" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.injection.timeFormat')">
              <n-input v-model:value="config.passive.time_format" placeholder="%H:%M" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.injection.thoughtMaxChars')">
              <n-input-number v-model:value="config.passive.thought_max_chars" :min="50" :max="500" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.injection.vibeMaxChars')">
              <n-input-number v-model:value="config.passive.vibe_max_chars" :min="20" :max="200" />
            </n-form-item>

            <!-- 平台过滤 -->
            <n-divider>{{ t('passiveConsciousness.config.platforms.title') }}</n-divider>
            <n-form-item :label="t('passiveConsciousness.config.platforms.enable')">
              <n-switch v-model:value="config.platforms.enabled" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.platforms.enabledPlatforms')" v-if="config.platforms.enabled">
              <n-select
                v-model:value="config.platforms.whitelist"
                multiple
                :options="platformFilterOptions"
                :placeholder="t('passiveConsciousness.config.platforms.selectPlaceholder')"
              />
              <n-text v-if="config.platforms.enabled && config.platforms.whitelist.length === 0" type="error" style="font-size: 12px; margin-top: 4px;">
                {{ t('passiveConsciousness.config.platforms.minSelectError') }}
              </n-text>
            </n-form-item>

            <!-- Session 来源配置 -->
            <n-divider>{{ t('passiveConsciousness.config.session.title') }}</n-divider>
            <n-form-item :label="t('passiveConsciousness.config.session.sourcePlatform')">
              <n-select v-model:value="config.session.sources" multiple :options="sessionSourceOptions" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.session.timeRange')">
              <n-input-number v-model:value="config.session.time_range_hours" :min="1" :max="168" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.session.maxMessages')">
              <n-input-number v-model:value="config.session.max_messages_per_session" :min="5" :max="100" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.session.filterTool')">
              <n-switch v-model:value="config.session.filter_tool_messages" />
            </n-form-item>

            <!-- Hindsight -->
            <n-divider>{{ t('passiveConsciousness.config.hindsight.title') }}</n-divider>
            <n-form-item :label="t('passiveConsciousness.config.hindsight.enable')">
              <n-switch v-model:value="config.hindsight.enabled" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.hindsight.recallLimit')">
              <n-input-number v-model:value="config.hindsight.recall_limit" :min="1" :max="20" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.config.hindsight.reflectEnable')">
              <n-switch v-model:value="config.hindsight.reflect_enabled" />
            </n-form-item>

            <!-- 模板配置 -->
            <n-divider>{{ t('passiveConsciousness.config.templates.title') }}</n-divider>
            <n-form-item :label="t('passiveConsciousness.config.templates.current')">
              <n-select
                v-model:value="config.templates.active_id"
                :options="templateOptions"
                :placeholder="t('passiveConsciousness.config.templates.selectPlaceholder')"
              />
            </n-form-item>
            <n-space>
              <n-button @click="openTemplateEditor()" size="small">
                {{ t('passiveConsciousness.config.templates.create') }}
              </n-button>
              <n-button @click="openTemplateEditor(config.templates.active_id)" size="small" :disabled="!config.templates.active_id">
                {{ t('passiveConsciousness.config.templates.editCurrent') }}
              </n-button>
            </n-space>
          </template>

          <n-button type="primary" @click="saveConfig" :loading="saving" style="margin-top: 16px">
            {{ t('passiveConsciousness.config.save') }}
          </n-button>
        </n-card>
      </n-tab-pane>

      <!-- Tab 2: 状态 -->
      <n-tab-pane name="status" :tab="t('passiveConsciousness.tabs.status')">
        <n-grid :cols="3" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-card :title="t('passiveConsciousness.status.longing')">
              <n-statistic :value="status.longing.score" :precision="3">
                <template #suffix>
                  <n-tag :type="longingTagType" size="small">{{ status.longing.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="status.longing.score * 100" :color="longingColor" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card :title="t('passiveConsciousness.status.chatHeat')">
              <n-statistic :value="status.chat_heat.heat" :precision="2">
                <template #suffix>
                  <n-tag :type="heatTagType" size="small">{{ status.chat_heat.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="Math.min(status.chat_heat.heat * 20, 100)" :color="heatColor" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card :title="t('passiveConsciousness.status.emotion')">
              <n-statistic :value="status.emotional_intensity.intensity" :precision="3">
                <template #suffix>
                  <n-tag size="small">{{ status.emotional_intensity.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="status.emotional_intensity.intensity * 100" :color="intensityColor" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card :title="'🌤 ' + t('passiveConsciousness.status.weather')">
              <template v-if="status.weather">
                <n-statistic :value="status.weather.temperature" :suffix="'°C'">
                  <template #prefix>
                    <n-tag size="small">{{ status.weather.weather }}</n-tag>
                  </template>
                </n-statistic>
                <n-space vertical size="small" style="margin-top: 8px">
                  <n-text>💨 {{ status.weather.wind_dir }}</n-text>
                  <n-text>💧 {{ t('passiveConsciousness.status.humidity') }} {{ status.weather.humidity }}%</n-text>
                  <n-text>📍 {{ status.weather.city }}</n-text>
                </n-space>
              </template>
              <n-text v-else type="secondary">{{ t('passiveConsciousness.status.weatherDisabled') }}</n-text>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-tab-pane>

      <!-- Tab 3: 聊天记录 -->
      <n-tab-pane name="chat" :tab="t('passiveConsciousness.tabs.chat')">
        <n-list bordered>
          <n-list-item v-for="msg in chats.items" :key="msg.id">
            <div :class="['chat-msg', msg.role === 'user' ? 'user-msg' : 'assistant-msg']">
              <div class="msg-header">
                <n-tag :type="msg.role === 'user' ? 'info' : 'warning'" size="small">
                  {{ msg.role === 'user' ? globalConfig.user_name : globalConfig.assistant_name }}
                </n-tag>
                <span class="msg-time">{{ msg.timestamp }}</span>
              </div>
              <div class="msg-content">{{ msg.content }}</div>
            </div>
          </n-list-item>
        </n-list>
      </n-tab-pane>

      <!-- Tab 4: 测试 -->
      <n-tab-pane name="test" :tab="t('passiveConsciousness.tabs.test')">
        <!-- 一键全量测试 -->
        <n-card :title="'🚀 ' + t('passiveConsciousness.test.fullTest')" style="margin-bottom: 16px">
          <n-space vertical>
            <n-button
              type="primary"
              size="large"
              @click="runFullTest"
              :loading="testing.full"
              block
            >
              {{ t('passiveConsciousness.test.runFullTest') }}
            </n-button>
            <template v-if="fullTestResult">
              <n-alert
                :type="fullTestResult.failed === 0 ? 'success' : 'warning'"
                :title="t('passiveConsciousness.test.testComplete', { success: fullTestResult.success, total: fullTestResult.total })"
                style="margin-top: 8px"
              >
                <template v-if="fullTestResult.failed > 0">
                  {{ t('passiveConsciousness.test.failedItems') }}
                  <template v-for="(val, key) in fullTestResult.results" :key="key">
                    <n-tag v-if="!val?.success && !val?.steps" type="error" size="small" style="margin: 2px">
                      {{ key }}
                    </n-tag>
                  </template>
                </template>
              </n-alert>
            </template>
          </n-space>
        </n-card>

        <!-- 单项测试卡片 -->
        <n-grid :cols="2" :x-gap="12" :y-gap="12">
          <!-- 💕 想念分数 -->
          <n-grid-item>
            <n-card :title="'💕 ' + t('passiveConsciousness.test.longing')" size="small">
              <n-button @click="runTest('longing')" :loading="testing.longing" size="small" style="margin-bottom: 12px">
                {{ t('passiveConsciousness.test.test') }}
              </n-button>
              <n-alert v-if="testResults.longing?.error" type="error" style="margin-bottom: 8px">
                {{ testResults.longing.error }}
              </n-alert>
              <n-descriptions v-if="testResults.longing?.data" :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.score')">{{ testResults.longing.data.score }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.level')">{{ testResults.longing.data.level }} ({{ testResults.longing.data.label }})</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.gapMinutes')">{{ testResults.longing.data.gap_minutes }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.recentMsg')">{{ testResults.longing.data.last_user_msg_at || t('passiveConsciousness.test.labels.none') }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-grid-item>

          <!-- 🔥 聊天热度 -->
          <n-grid-item>
            <n-card :title="'🔥 ' + t('passiveConsciousness.test.chatHeat')" size="small">
              <n-button @click="runTest('chatHeat')" :loading="testing.chatHeat" size="small" style="margin-bottom: 12px">
                {{ t('passiveConsciousness.test.test') }}
              </n-button>
              <n-alert v-if="testResults.chatHeat?.error" type="error" style="margin-bottom: 8px">
                {{ testResults.chatHeat.error }}
              </n-alert>
              <n-descriptions v-if="testResults.chatHeat?.data" :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.heat')">{{ testResults.chatHeat.data.heat }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.level')">{{ testResults.chatHeat.data.label }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.recentCount')">{{ testResults.chatHeat.data.recent_count }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.recentMsg')">{{ testResults.chatHeat.data.recent_msg_at || t('passiveConsciousness.test.labels.none') }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-grid-item>

          <!-- 🎭 情绪值 -->
          <n-grid-item>
            <n-card :title="'🎭 ' + t('passiveConsciousness.test.emotionalIntensity')" size="small">
              <n-button @click="runTest('emotionalIntensity')" :loading="testing.emotionalIntensity" size="small" style="margin-bottom: 12px">
                {{ t('passiveConsciousness.test.test') }}
              </n-button>
              <n-alert v-if="testResults.emotionalIntensity?.error" type="error" style="margin-bottom: 8px">
                {{ testResults.emotionalIntensity.error }}
              </n-alert>
              <n-descriptions v-if="testResults.emotionalIntensity?.data" :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.intensity')">{{ testResults.emotionalIntensity.data.intensity }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.tag')">{{ testResults.emotionalIntensity.data.label }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.rawValue')">{{ testResults.emotionalIntensity.data.raw_value || t('passiveConsciousness.test.labels.unset') }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-grid-item>

          <!-- 🌤 天气感知 -->
          <n-grid-item>
            <n-card :title="'🌤 ' + t('passiveConsciousness.test.weather')" size="small">
              <n-space style="margin-bottom: 12px">
                <n-button @click="runTest('weather')" :loading="testing.weather" size="small">
                  {{ t('passiveConsciousness.test.test') }}
                </n-button>
                <n-button @click="clearWeatherCache" size="small" secondary>
                  {{ t('passiveConsciousness.test.clearCache') }}
                </n-button>
              </n-space>
              <n-alert v-if="testResults.weather?.error" type="error" style="margin-bottom: 8px">
                {{ testResults.weather.error }}
              </n-alert>
              <n-descriptions v-if="testResults.weather?.data" :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.city')">{{ testResults.weather.data.city }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.weather')">{{ testResults.weather.data.weather }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.temperature')">{{ testResults.weather.data.temperature }}°C</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.humidity')">{{ testResults.weather.data.humidity }}%</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.windDir')">{{ testResults.weather.data.winddirection }}</n-descriptions-item>
                <n-descriptions-item :label="t('passiveConsciousness.test.labels.updateTime')">{{ testResults.weather.data.reporttime }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-grid-item>

          <!-- 📖 Hindsight 记忆 -->
          <n-grid-item>
            <n-card :title="'📖 ' + t('passiveConsciousness.test.hindsight')" size="small">
              <n-space style="margin-bottom: 12px">
                <n-button @click="runTest('hindsightRecall')" :loading="testing.hindsightRecall" size="small">
                  {{ t('passiveConsciousness.test.recallTest') }}
                </n-button>
                <n-button @click="runTest('hindsightReflect')" :loading="testing.hindsightReflect" size="small">
                  {{ t('passiveConsciousness.test.reflectTest') }}
                </n-button>
              </n-space>
              <n-alert v-if="testResults.hindsightRecall?.error" type="error" style="margin-bottom: 8px">
                Recall: {{ testResults.hindsightRecall.error }}
              </n-alert>
              <n-alert v-if="testResults.hindsightReflect?.error" type="error" style="margin-bottom: 8px">
                Reflect: {{ testResults.hindsightReflect.error }}
              </n-alert>
              <template v-if="testResults.hindsightRecall?.data">
                <n-descriptions :column="1" label-placement="left" bordered size="small" style="margin-bottom: 8px">
                  <n-descriptions-item :label="t('passiveConsciousness.test.labels.recallCount')">{{ testResults.hindsightRecall.data.count }}</n-descriptions-item>
                </n-descriptions>
                <n-list bordered size="small" v-if="testResults.hindsightRecall.data.results?.length">
                  <n-list-item v-for="(r, i) in testResults.hindsightRecall.data.results" :key="i">
                    <n-tag size="small" :type="r.type === 'episodic' ? 'info' : 'success'" style="margin-right: 8px">
                      {{ r.type }}
                    </n-tag>
                    {{ r.text?.substring(0, 150) }}{{ r.text?.length > 150 ? '...' : '' }}
                  </n-list-item>
                </n-list>
              </template>
              <template v-if="testResults.hindsightReflect?.data">
                <n-card :title="'Reflect ' + t('passiveConsciousness.templateEditor.previewResult')" size="small" style="margin-top: 8px">
                  <n-text>{{ testResults.hindsightReflect.data.reflection }}</n-text>
                </n-card>
              </template>
            </n-card>
          </n-grid-item>

          <!-- 📋 完整上下文预览 -->
          <n-grid-item :span="2">
            <n-card :title="'📋 ' + t('passiveConsciousness.test.contextPreview')" size="small">
              <n-button
                type="primary"
                @click="runContextTest"
                :loading="testing.context"
                style="margin-bottom: 12px"
              >
                {{ t('passiveConsciousness.test.simulateFlow') }}
              </n-button>

              <template v-if="contextResult">
                <!-- 步骤状态 -->
                <n-card :title="t('passiveConsciousness.test.steps')" size="small" style="margin-bottom: 12px">
                  <n-list bordered size="small">
                    <n-list-item v-for="(step, i) in contextResult.steps" :key="i">
                      <n-space align="center">
                        <n-tag :type="step.ok ? 'success' : 'error'" size="small">
                          {{ step.ok ? '✓' : '✗' }}
                        </n-tag>
                        <n-text>{{ step.name }}</n-text>
                        <n-text v-if="step.error" type="error" style="font-size: 12px">
                          {{ step.error }}
                        </n-text>
                      </n-space>
                    </n-list-item>
                  </n-list>
                </n-card>

                <!-- 错误列表 -->
                <n-alert
                  v-if="contextResult.errors?.length"
                  type="warning"
                  :title="t('passiveConsciousness.test.partialFail')"
                  style="margin-bottom: 12px"
                >
                  <n-list size="small">
                    <n-list-item v-for="(err, i) in contextResult.errors" :key="i">
                      <n-text type="error">{{ err }}</n-text>
                    </n-list-item>
                  </n-list>
                </n-alert>

                <!-- 最终上下文 -->
                <n-card :title="t('passiveConsciousness.test.injectedContext')" size="small">
                  <n-code
                    :code="contextResult.context || t('passiveConsciousness.test.empty')"
                    language="text"
                    word-wrap
                  />
                </n-card>
              </template>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-tab-pane>
    </n-tabs>

    <!-- 模板编辑器弹窗 -->
    <n-modal v-model:show="showTemplateEditor" preset="card" :title="t('passiveConsciousness.templateEditor.title')" style="width: 90vw; max-width: 1200px;">
      <n-grid :cols="2" :x-gap="16">
        <!-- 左侧：编辑器 -->
        <n-grid-item>
          <n-card :title="t('passiveConsciousness.templateEditor.content')" size="small">
            <n-form-item :label="t('passiveConsciousness.templateEditor.id')" v-if="templateEditor.isNew">
              <n-input v-model:value="templateEditor.id" placeholder="my-template" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.templateEditor.name')">
              <n-input v-model:value="templateEditor.name" :placeholder="t('passiveConsciousness.templateEditor.name')" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.templateEditor.description')">
              <n-input v-model:value="templateEditor.description" :placeholder="t('passiveConsciousness.templateEditor.description')" />
            </n-form-item>
            <n-form-item :label="t('passiveConsciousness.templateEditor.contentEditor')">
              <n-input
                v-model:value="templateEditor.content"
                type="textarea"
                :rows="16"
                :placeholder="t('passiveConsciousness.templateEditor.contentPlaceholder')"
                style="font-family: monospace"
              />
            </n-form-item>
            <n-space>
              <n-button type="primary" @click="saveTemplate" :loading="templateEditor.saving">
                {{ t('passiveConsciousness.templateEditor.save') }}
              </n-button>
              <n-button @click="previewTemplate" :loading="templateEditor.previewing">
                {{ t('passiveConsciousness.templateEditor.preview') }}
              </n-button>
              <n-button
                type="error"
                @click="deleteTemplate"
                :loading="templateEditor.deleting"
                v-if="!templateEditor.isNew && templateEditor.id !== 'default'"
              >
                {{ t('passiveConsciousness.templateEditor.delete') }}
              </n-button>
            </n-space>
          </n-card>
        </n-grid-item>

        <!-- 右侧：预览 + 变量参考 -->
        <n-grid-item>
          <n-card :title="t('passiveConsciousness.templateEditor.previewResult')" size="small" style="margin-bottom: 16px">
            <n-code
              :code="templateEditor.preview || t('passiveConsciousness.templateEditor.previewPlaceholder')"
              language="text"
              word-wrap
            />
          </n-card>
          <n-card :title="t('passiveConsciousness.templateEditor.variables')" size="small">
            <n-list bordered size="small">
              <n-list-item v-for="v in templateVariables" :key="v.name">
                <n-space align="center">
                  <n-tag size="small" type="info">{{ v.name }}</n-tag>
                  <n-text depth="3" style="font-size: 12px">{{ v.type }}</n-text>
                  <n-text>{{ v.description }}</n-text>
                </n-space>
              </n-list-item>
            </n-list>
          </n-card>
        </n-grid-item>
      </n-grid>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useConfig } from '../composables/useConfig'
import api from '../api/passive_consciousness'

const message = useMessage()
const { t } = useI18n()
const { config: globalConfig } = useConfig()
const activeTab = ref('config')

// 配置
const config = ref({
  enabled: false,
  llm: { mode: 'hermes', provider: 'openai', model: 'deepseek-chat', api_key: '', base_url: '' },
  passive: { enabled: true, inject_emotion: true, inject_heat: true, inject_memory: true, inject_thought: true, thought_max_chars: 200, vibe_max_chars: 50, inject_tag: '[CONSCIOUSNESS_CONTEXT]', time_format: '%H:%M' },
  session: { sources: ['weixin'], time_range_hours: 24, max_messages_per_session: 15, filter_tool_messages: true },
  hindsight: { enabled: true, recall_limit: 5, reflect_enabled: true },
  platforms: { enabled: false, whitelist: ['weixin'] },
  templates: { list: [], active_id: 'default' }
})

// 状态
const status = ref({
  enabled: false,
  longing: { score: 0, level: 0, label: 'calm', last_user_msg_at: null, last_self_msg_at: null },
  chat_heat: { heat: 0, label: 'cold', recent_count: 0, recent_hours: 0, recent_user_msg_at: null },
  emotional_intensity: { intensity: 0, label: '' },
  weather: null
})

// 聊天记录
const chats = ref({ total: 0, items: [] })

// 选项
const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '自定义', value: 'custom' }
]
// 平台过滤选项 - 从 API 获取
const platformFilterOptions = ref([])
// Session 来源选项 - 从 API 获取
const sessionSourceOptions = ref([])

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

// 加载数据
const loadConfig = async () => {
  try {
    const data = await api.getConfig()
    config.value = data
  } catch (e) {
    message.error(t('passiveConsciousness.messages.loadConfigFail'))
  }
}
const loadStatus = async () => {
  try {
    const data = await api.getStatus()
    status.value = data
  } catch (e) {
    message.error(t('passiveConsciousness.messages.loadStatusFail'))
  }
}
const loadChats = async () => {
  try {
    const data = await api.getChats()
    chats.value = data
  } catch (e) {
    message.error(t('passiveConsciousness.messages.loadChatsFail'))
  }
}

// 加载可用平台列表
const loadPlatforms = async () => {
  try {
    const resp = await api.getAvailablePlatforms()
    if (resp.success && resp.data) {
      const options = resp.data.map(p => ({ label: p.name, value: p.id }))
      platformFilterOptions.value = options
      sessionSourceOptions.value = options
    }
  } catch (e) {
    console.error(t('passiveConsciousness.messages.loadPlatformsFail') + ':', e)
    // 使用默认值
    const defaultOptions = [
      { label: '微信', value: 'weixin' },
      { label: '飞书', value: 'feishu' },
      { label: 'Telegram', value: 'telegram' },
      { label: 'Discord', value: 'discord' },
      { label: 'Slack', value: 'slack' },
      { label: '自定义', value: 'custom' }
    ]
    platformFilterOptions.value = defaultOptions
    sessionSourceOptions.value = defaultOptions
  }
}

// 保存配置
const saving = ref(false)
const saveConfig = async () => {
  // 验证：如果启用了平台过滤但没有选择任何平台，则提示错误
  if (config.value.platforms.enabled && config.value.platforms.whitelist.length === 0) {
    message.error(t('passiveConsciousness.messages.platformMinError'))
    return
  }

  saving.value = true
  try {
    await api.saveConfig(config.value)
    message.success(t('passiveConsciousness.messages.configSaved'))
  } catch (e) {
    message.error(t('passiveConsciousness.messages.saveConfigFail'))
  } finally {
    saving.value = false
  }
}

// ============ 测试相关 ============

// 测试 loading 状态
const testing = ref({
  full: false,
  longing: false,
  chatHeat: false,
  emotionalIntensity: false,
  weather: false,
  hindsightRecall: false,
  hindsightReflect: false,
  context: false,
})

// 测试结果
const testResults = ref({
  longing: null,
  chatHeat: null,
  emotionalIntensity: null,
  weather: null,
  hindsightRecall: null,
  hindsightReflect: null,
})

// 全量测试结果
const fullTestResult = ref(null)

// 上下文测试结果
const contextResult = ref(null)

// ============ 模板相关 ============

// 模板列表
const templates = ref([])

// 模板选项（用于下拉框）
const templateOptions = computed(() => {
  return templates.value.map(tmpl => ({
    label: tmpl.name + (tmpl.is_default ? ' ' + t('passiveConsciousness.defaultLabel') : ''),
    value: tmpl.id
  }))
})

// 模板编辑器状态
const showTemplateEditor = ref(false)
const templateEditor = ref({
  isNew: false,
  id: '',
  name: '',
  description: '',
  content: '',
  preview: '',
  saving: false,
  previewing: false,
  deleting: false
})

// 模板变量列表
const templateVariables = ref([])

// 单项测试 API 映射
const testApiMap = {
  longing: () => api.testLonging(),
  chatHeat: () => api.testChatHeat(),
  emotionalIntensity: () => api.testEmotionalIntensity(),
  weather: () => api.testWeather(),
  hindsightRecall: () => api.testHindsightRecall(),
  hindsightReflect: () => api.testHindsightReflect(),
}

// 测试名称映射
const testNameMap = {
  longing: () => t('passiveConsciousness.test.longing'),
  chatHeat: () => t('passiveConsciousness.test.chatHeat'),
  emotionalIntensity: () => t('passiveConsciousness.test.emotionalIntensity'),
  weather: () => t('passiveConsciousness.test.weather'),
  hindsightRecall: () => t('passiveConsciousness.test.hindsight'),
  hindsightReflect: () => t('passiveConsciousness.test.hindsight'),
}

// 运行单项测试
const runTest = async (name) => {
  testing.value[name] = true
  const displayName = testNameMap[name]?.() || name
  try {
    const resp = await testApiMap[name]()
    testResults.value[name] = resp
    if (resp?.success) {
      message.success(displayName + ' ' + t('passiveConsciousness.messages.testSuccess'))
    } else {
      message.warning(displayName + ' ' + t('passiveConsciousness.messages.testReturned') + ': ' + (resp?.error || t('passiveConsciousness.messages.unknown')))
    }
  } catch (e) {
    testResults.value[name] = { success: false, error: e.message || String(e) }
    message.error(displayName + ' ' + t('passiveConsciousness.messages.testFailed') + ': ' + e.message)
  } finally {
    testing.value[name] = false
  }
}

// 清除天气缓存
const clearWeatherCache = async () => {
  try {
    await api.clearWeatherCache()
    message.success(t('passiveConsciousness.messages.weatherCacheCleared'))
  } catch (e) {
    message.error(t('passiveConsciousness.messages.clearCacheFail') + ': ' + e.message)
  }
}

// 运行全量测试
const runFullTest = async () => {
  testing.value.full = true
  try {
    const resp = await api.testFull()
    fullTestResult.value = resp
    if (resp?.failed === 0) {
      message.success(t('passiveConsciousness.messages.fullTestPassed', { success: resp.success, total: resp.total }))
    } else {
      message.warning(t('passiveConsciousness.messages.fullTestResult', { success: resp?.success, total: resp?.total }))
    }
  } catch (e) {
    message.error(t('passiveConsciousness.messages.fullTestFailed') + ': ' + e.message)
  } finally {
    testing.value.full = false
  }
}

// 运行上下文测试
const runContextTest = async () => {
  testing.value.context = true
  try {
    const resp = await api.testContext()
    contextResult.value = resp
    const okCount = resp?.steps?.filter(s => s.ok).length || 0
    const totalSteps = resp?.steps?.length || 0
    if (resp?.errors?.length === 0) {
      message.success(t('passiveConsciousness.messages.contextComplete', { ok: okCount, total: totalSteps }))
    } else {
      message.warning(t('passiveConsciousness.messages.contextPartial', { ok: okCount, total: totalSteps, errors: resp?.errors?.length }))
    }
  } catch (e) {
    message.error(t('passiveConsciousness.messages.contextTestFailed') + ': ' + e.message)
  } finally {
    testing.value.context = false
  }
}

// ============ 模板方法 ============

// 加载模板列表
const loadTemplates = async () => {
  try {
    const resp = await api.getTemplates()
    if (resp.success && resp.data) {
      templates.value = resp.data
    }
  } catch (e) {
    console.error(t('passiveConsciousness.messages.loadTemplateListFail') + ':', e)
  }
}

// 加载模板变量列表
const loadTemplateVariables = async () => {
  try {
    const resp = await api.getTemplateVariables()
    if (resp.success && resp.data) {
      templateVariables.value = resp.data
    }
  } catch (e) {
    console.error(t('passiveConsciousness.messages.loadTemplateVarsFail') + ':', e)
  }
}

// 打开模板编辑器
const openTemplateEditor = async (templateId) => {
  if (templateId) {
    // 编辑现有模板
    try {
      const resp = await api.getTemplate(templateId)
      if (resp.success && resp.data) {
        templateEditor.value = {
          isNew: false,
          id: resp.data.id,
          name: resp.data.name,
          description: resp.data.description || '',
          content: resp.data.content,
          preview: '',
          saving: false,
          previewing: false,
          deleting: false
        }
      }
    } catch (e) {
      message.error(t('passiveConsciousness.messages.loadTemplateFail') + ': ' + e.message)
      return
    }
  } else {
    // 新建模板
    templateEditor.value = {
      isNew: true,
      id: '',
      name: '',
      description: '',
      content: '',
      preview: '',
      saving: false,
      previewing: false,
      deleting: false
    }
  }
  showTemplateEditor.value = true
}

// 预览模板
const previewTemplate = async () => {
  templateEditor.value.previewing = true
  try {
    if (templateEditor.value.isNew) {
      // 新模板直接用内容预览
      const resp = await api.previewTemplate('default', {})
      // 对于新模板，我们先保存再预览，或者直接用 mock 渲染
      // 简单处理：提示用户先保存
      message.info(t('passiveConsciousness.messages.saveTemplateFirst'))
      return
    }
    const resp = await api.previewTemplate(templateEditor.value.id)
    if (resp.success && resp.data) {
      templateEditor.value.preview = resp.data.preview
    }
  } catch (e) {
    message.error(t('passiveConsciousness.messages.previewFail') + ': ' + e.message)
  } finally {
    templateEditor.value.previewing = false
  }
}

// 保存模板
const saveTemplate = async () => {
  // 验证
  if (!templateEditor.value.name) {
    message.error(t('passiveConsciousness.messages.enterTemplateName'))
    return
  }
  if (!templateEditor.value.content) {
    message.error(t('passiveConsciousness.messages.enterTemplateContent'))
    return
  }
  if (templateEditor.value.isNew && !templateEditor.value.id) {
    message.error(t('passiveConsciousness.messages.enterTemplateId'))
    return
  }

  templateEditor.value.saving = true
  try {
    const templateData = {
      name: templateEditor.value.name,
      description: templateEditor.value.description,
      content: templateEditor.value.content
    }

    if (templateEditor.value.isNew) {
      templateData.id = templateEditor.value.id
      await api.createTemplate(templateData)
      message.success(t('passiveConsciousness.messages.templateCreated'))
    } else {
      await api.updateTemplate(templateEditor.value.id, templateData)
      message.success(t('passiveConsciousness.messages.templateUpdated'))
    }

    // 重新加载模板列表
    await loadTemplates()
    showTemplateEditor.value = false
  } catch (e) {
    message.error(t('passiveConsciousness.messages.saveFail') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    templateEditor.value.saving = false
  }
}

// 删除模板
const deleteTemplate = async () => {
  if (templateEditor.value.id === 'default') {
    message.error(t('passiveConsciousness.messages.cannotDeleteDefault'))
    return
  }

  templateEditor.value.deleting = true
  try {
    await api.deleteTemplate(templateEditor.value.id)
    message.success(t('passiveConsciousness.messages.templateDeleted'))
    await loadTemplates()
    showTemplateEditor.value = false
  } catch (e) {
    message.error(t('passiveConsciousness.messages.deleteFail') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    templateEditor.value.deleting = false
  }
}

// 初始化
onMounted(async () => {
  await Promise.all([
    loadConfig(),
    loadStatus(),
    loadChats(),
    loadPlatforms(),
    loadTemplates(),
    loadTemplateVariables()
  ])
})
</script>

<style scoped>
.passive-consciousness-page {
  padding: 0;
}

.chat-msg {
  padding: 12px;
  border-radius: 8px;
  margin: 8px 0;
}

.user-msg {
  background: var(--theme-user-msg-bg);
  margin-left: 20%;
}

.assistant-msg {
  background: var(--theme-assistant-msg-bg);
  margin-right: 20%;
}

.msg-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.msg-time {
  font-size: 12px;
  color: var(--theme-text-secondary);
}

.msg-content {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
