<template>
  <div class="active-consciousness-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 状态 -->
      <n-tab-pane name="status" tab="状态">
        <n-grid :cols="2" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-card title="心跳状态">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span :class="['breathing-dot', heartbeatHealthy ? 'dot-green' : 'dot-red']"></span>
                <n-statistic label="今日心跳次数" :value="status.heartbeat_count" />
              </div>
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
              <n-progress :percentage="Number((status.longing.score * 100).toFixed(1))" :color="longingColor" style="margin-top: 8px" />
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

      <!-- Tab 2: 日志 -->
      <n-tab-pane name="logs" tab="日志" style="overflow: visible;">
        <n-tabs type="line" animated style="overflow: visible;">
          <n-tab-pane name="heartbeats" tab="心跳日志" style="overflow: visible;">
            <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px;">
              <n-date-picker v-model:value="heartbeatDate" type="date" clearable
                @update:value="onHeartbeatDateChange" style="width: 160px" />
              <n-button size="small" @click="heartbeatDate = Date.now(); loadHeartbeats(1)">今天</n-button>
              <n-button size="small" quaternary @click="heartbeatDate = null; loadHeartbeats(1)">全部</n-button>
            </div>
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
              <n-data-table :columns="heartbeatColumns" :data="heartbeats.items" :pagination="heartbeatPagination" @update:page="loadHeartbeats" :scroll-x="960" />
            </div>
          </n-tab-pane>
          <n-tab-pane name="thoughts" tab="念头日志" style="overflow: visible;">
            <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px;">
              <n-date-picker v-model:value="thoughtDate" type="date" clearable
                @update:value="onThoughtDateChange" style="width: 160px" />
              <n-button size="small" @click="thoughtDate = Date.now(); loadThoughts(1)">今天</n-button>
              <n-button size="small" quaternary @click="thoughtDate = null; loadThoughts(1)">全部</n-button>
            </div>
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
              <n-data-table :columns="thoughtColumns" :data="thoughts.items" :pagination="thoughtPagination" @update:page="loadThoughts" :scroll-x="860" />
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-tab-pane>

      <!-- Tab 3: 配置 -->
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

          <!-- 增强念头生成配置 -->
          <n-divider>🧠 增强念头生成</n-divider>

          <!-- 总开关 -->
          <n-form-item label="启用增强念头生成">
            <n-switch v-model:value="config.thought_enhanced.enabled" />
          </n-form-item>

          <template v-if="config.thought_enhanced.enabled">
            <!-- 时间范围配置 -->
            <n-divider>时间范围配置</n-divider>

            <n-form-item label="低唤醒度阈值（使用 15 天）">
              <n-input-number
                v-model:value="config.thought_enhanced.arousal_low_threshold"
                :min="0" :max="1" :step="0.1"
              />
            </n-form-item>

            <n-form-item label="高唤醒度阈值（使用 1 天）">
              <n-input-number
                v-model:value="config.thought_enhanced.arousal_high_threshold"
                :min="0" :max="1" :step="0.1"
              />
            </n-form-item>

            <n-form-item label="15 天生成念头数">
              <n-input-number
                v-model:value="config.thought_enhanced.count_15d"
                :min="1" :max="5"
              />
            </n-form-item>

            <n-form-item label="7 天生成念头数">
              <n-input-number
                v-model:value="config.thought_enhanced.count_7d"
                :min="1" :max="5"
              />
            </n-form-item>

            <n-form-item label="3 天生成念头数">
              <n-input-number
                v-model:value="config.thought_enhanced.count_3d"
                :min="1" :max="5"
              />
            </n-form-item>

            <n-form-item label="1 天生成念头数">
              <n-input-number
                v-model:value="config.thought_enhanced.count_1d"
                :min="1" :max="5"
              />
            </n-form-item>

            <!-- LLM 配置 -->
            <n-divider>LLM 思考配置</n-divider>

            <n-form-item label="Temperature（随机性）">
              <n-input-number
                v-model:value="config.thought_enhanced.temperature"
                :min="0" :max="2" :step="0.1"
              />
            </n-form-item>

            <n-form-item label="最大 Token 数">
              <n-input-number
                v-model:value="config.thought_enhanced.max_tokens"
                :min="100" :max="2000" :step="100"
              />
            </n-form-item>

            <!-- 旧念头召回配置 -->
            <n-divider>旧念头召回配置</n-divider>

            <n-form-item label="召回旧念头数量">
              <n-input-number
                v-model:value="config.thought_enhanced.recall_old_thoughts_limit"
                :min="1" :max="50" :step="1"
              />
            </n-form-item>

            <!-- 存储配置 -->
            <n-divider>存储配置</n-divider>

            <n-form-item label="存入 Hindsight 阈值">
              <n-input-number
                v-model:value="config.thought_enhanced.retain_threshold"
                :min="0" :max="1" :step="0.1"
              />
            </n-form-item>

            <n-form-item label="天气念头存入 Hindsight">
              <n-switch v-model:value="config.thought_enhanced.retain_on_weather" />
            </n-form-item>
          </template>

          <!-- 天气配置（共享） -->
          <n-divider>🌤️ 天气配置（共享）</n-divider>

          <n-form-item label="启用天气">
            <n-switch v-model:value="config.weather.enabled" />
          </n-form-item>

          <template v-if="config.weather.enabled">
            <n-form-item label="高德 API Key">
              <n-input
                v-model:value="config.weather.amap_key"
                placeholder="输入高德开放平台 Key"
                type="password"
                show-password-on="mousedown"
              />
            </n-form-item>

            <n-form-item label="城市编码">
              <n-input
                v-model:value="config.weather.adcode"
                placeholder="如：370100（济南）"
              />
              <span style="margin-left: 8px; font-size: 12px; color: #999;">
                高德城市编码，可在高德开放平台查询
              </span>
            </n-form-item>

            <n-form-item label="缓存时长（秒）">
              <n-input-number
                v-model:value="config.weather.cache_ttl"
                :min="60" :max="86400" :step="60"
              />
            </n-form-item>

            <n-form-item label="温度变化阈值（°C）">
              <n-input-number
                v-model:value="config.weather.temp_change_threshold"
                :min="1" :max="20" :step="1"
              />
            </n-form-item>

            <n-form-item label="天气触发念头">
              <n-switch v-model:value="config.thought_enhanced.weather_trigger_enabled" />
              <span style="margin-left: 8px; font-size: 12px; color: #999;">
                天气变化时自动生成相关念头
              </span>
            </n-form-item>
          </template>

          <n-divider>念头存储</n-divider>
          <n-form-item label="存入 Hindsight">
            <n-switch v-model:value="config.thought.retain_enabled" />
            <span style="margin-left: 8px; font-size: 12px; color: #999;">开启后念头会写入长期记忆库（当前质量低建议关闭）</span>
          </n-form-item>

          <n-button type="primary" @click="saveConfig" :loading="saving" style="margin-top: 16px">
            保存配置
          </n-button>
        </n-card>
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

    <!-- 召回内容弹窗 -->
    <n-modal v-model:show="showRecallModal" preset="card" title="召回内容" style="width: 90vw; max-width: 900px">
      <n-list bordered v-if="recallItems.length">
        <n-list-item v-for="(item, idx) in recallItems" :key="idx">
          <div style="font-size: 13px; white-space: pre-wrap;">{{ item.content || item.text || JSON.stringify(item) }}</div>
        </n-list-item>
      </n-list>
      <n-empty v-else description="无召回内容" />
    </n-modal>

    <!-- 念头内容弹窗 -->
    <n-modal v-model:show="showThoughtContentModal" preset="card" title="念头内容" style="width: 90vw; max-width: 900px">
      <template v-if="thoughtContentData">
        <n-descriptions :column="1" label-placement="left" bordered size="small">
          <n-descriptions-item label="心跳ID">{{ thoughtContentData.heartbeat_id }}</n-descriptions-item>
          <n-descriptions-item label="生成数量">{{ thoughtContentData.thoughts_generated }}</n-descriptions-item>
          <n-descriptions-item label="念头内容" v-if="thoughtContentData.details_parsed?.thought_generation?.thought">
            {{ thoughtContentData.details_parsed.thought_generation.thought }}
          </n-descriptions-item>
          <n-descriptions-item label="念头类型" v-if="thoughtContentData.details_parsed?.thought_type">
            {{ thoughtContentData.details_parsed.thought_type }}
          </n-descriptions-item>
        </n-descriptions>
      </template>
      <n-empty v-else description="无念头内容" />
    </n-modal>

    <!-- 心跳日志详情弹窗 -->
    <n-modal v-model:show="showDetailsModal" preset="card" :title="detailsTitle" fullscreen :mask-closable="false">
      <div v-if="detailsData">
        <!-- 情绪演化流程 -->
        <template v-if="isHeartbeatDetails">
          <n-divider title-placement="left">情绪演化</n-divider>
          <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
            <n-tag v-for="item in [
              {label: '初始', d: detailsData.emotion_before},
              {label: '演化', d: detailsData.emotion_evolved},
              {label: 'LLM', d: detailsData.emotion_llm},
              {label: '合并', d: detailsData.emotion_merged}
            ].filter(i => i.d)" :key="item.label" size="small" :type="getEmotionTagType(item.d.dominant)">
              {{ item.label }}: {{ emotionLabelCn(item.d.dominant) }} ({{ item.d.valence?.toFixed(2) }}, {{ item.d.arousal?.toFixed(2) }}, {{ item.d.social_need?.toFixed(2) }})
            </n-tag>
          </div>
          <div style="font-size: 12px; color: #666; margin-bottom: 16px;">
            距上次 {{ detailsData.minutes_since_update?.toFixed(0) }}分钟 | 合并权重：演化40% + LLM60%
          </div>
        </template>

        <!-- 决策计算 -->
        <template v-if="detailsData.decision">
          <n-divider title-placement="left">决策计算</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="公式" :span="2">score = intensity × time_fitness × silence × freq</n-descriptions-item>
            <n-descriptions-item label="决策类型">
              <n-tag :type="getDecisionTagType(detailsData.decision.type)" size="small">
                {{ getDecisionLabelCn(detailsData.decision.type) }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="最终分数">{{ detailsData.decision.score?.toFixed(3) }} → {{ getDecisionLabelCn(detailsData.decision.type) }}</n-descriptions-item>
            <n-descriptions-item label="情绪强度">
              {{ parseDecisionReason(detailsData.decision.reason).intensity }}
              <n-tag size="tiny" type="info" style="margin-left: 4px">情绪越强分越高</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="时间适宜性">
              {{ parseDecisionReason(detailsData.decision.reason).time_fitness }}
              <n-tag size="tiny" type="warning" style="margin-left: 4px">工作时间降权</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="沉默因子">
              {{ parseDecisionReason(detailsData.decision.reason).silence_factor }}
              <n-tag size="tiny" type="default" style="margin-left: 4px">越久没聊天分越高</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="频率限制">
              {{ parseDecisionReason(detailsData.decision.reason).frequency }}
              <n-tag size="tiny" type="error" style="margin-left: 4px">超频归零</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="决策原因" :span="2">{{ detailsData.decision.reason }}</n-descriptions-item>
          </n-descriptions>
          <n-descriptions v-if="detailsData.time_fitness" bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="时间适宜性">{{ detailsData.time_fitness.score?.toFixed(3) }} ({{ detailsData.time_fitness.label }})</n-descriptions-item>
          </n-descriptions>
        </template>

        <!-- 召回详情 -->
        <template v-if="detailsData.recall_results?.length">
          <n-divider title-placement="left">Hindsight 召回</n-divider>
          <n-list bordered size="small" style="margin-bottom: 16px">
            <n-list-item v-for="(item, idx) in detailsData.recall_results" :key="idx">
              <div style="font-size: 13px;">{{ item.content || item.text || JSON.stringify(item) }}</div>
            </n-list-item>
          </n-list>
        </template>

        <!-- 念头生成 -->
        <template v-if="detailsData.thought_generation || detailsData.thought_type">
          <n-divider title-placement="left">念头生成</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="念头类型">
              <n-tag :type="getThoughtTypeTagType(detailsData.thought_type)" size="small">
                {{ detailsData.thought_type || '未知' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="生成状态">
              <n-tag :type="detailsData.thought_generation?.success ? 'success' : 'error'" size="small">
                {{ detailsData.thought_generation?.success ? '成功' : '失败' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item v-if="detailsData.thought_generation?.thought" label="生成内容" :span="2">
              {{ detailsData.thought_generation.thought }}
            </n-descriptions-item>
            <n-descriptions-item v-if="detailsData.thought_generation?.hindsight_stored !== undefined" label="Hindsight">
              <n-tag :type="detailsData.thought_generation.hindsight_stored ? 'success' : 'default'" size="small">
                {{ detailsData.thought_generation.hindsight_stored ? '已存储' : '未存储' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item v-if="detailsData.thought_generation?.model" label="LLM 模型">
              {{ detailsData.thought_generation.model }}
            </n-descriptions-item>
            <n-descriptions-item v-if="detailsData.thought_generation?.duration_ms" label="LLM 耗时">
              {{ detailsData.thought_generation.duration_ms }}ms
            </n-descriptions-item>
            <n-descriptions-item v-if="detailsData.thought_generation?.error" label="错误" :span="2">
              <span style="color: #d03050;">{{ detailsData.thought_generation.error }}</span>
            </n-descriptions-item>
          </n-descriptions>
        </template>

        <!-- 消息发送 -->
        <template v-if="detailsData.message_sending">
          <n-divider title-placement="left">消息发送</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="发送状态">
              <n-tag :type="detailsData.message_sending.success ? 'success' : 'error'" size="small">
                {{ detailsData.message_sending.success ? '成功' : '失败' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item v-if="detailsData.message_sending.thought_type" label="念头类型">
              <n-tag :type="getThoughtTypeTagType(detailsData.message_sending.thought_type)" size="small">
                {{ detailsData.message_sending.thought_type }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item v-if="detailsData.message_sending.thought" label="发送内容" :span="2">
              {{ detailsData.message_sending.thought }}
            </n-descriptions-item>
          </n-descriptions>
        </template>

        <!-- 延迟队列重评估 -->
        <template v-if="detailsData.delay_reeval">
          <n-divider title-placement="left">延迟队列重评估</n-divider>
          <n-descriptions bordered :column="3" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="发送">{{ detailsData.delay_reeval.sent }}</n-descriptions-item>
            <n-descriptions-item label="丢弃">{{ detailsData.delay_reeval.discarded }}</n-descriptions-item>
            <n-descriptions-item label="保持">{{ detailsData.delay_reeval.kept }}</n-descriptions-item>
          </n-descriptions>
        </template>

        <!-- 情绪评估 LLM 调用 -->
        <template v-if="detailsData.emotional_evaluation">
          <n-divider title-placement="left">情绪评估 LLM 调用</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="模型">{{ detailsData.emotional_evaluation.model }}</n-descriptions-item>
            <n-descriptions-item label="模式">{{ detailsData.emotional_evaluation.mode }}</n-descriptions-item>
            <n-descriptions-item label="耗时">{{ detailsData.emotional_evaluation.duration_ms }}ms</n-descriptions-item>
            <n-descriptions-item label="返回值">{{ detailsData.emotional_evaluation.response }}</n-descriptions-item>
            <n-descriptions-item label="规则分数">{{ detailsData.emotional_evaluation.rule_score?.toFixed(3) }}</n-descriptions-item>
            <n-descriptions-item label="LLM 分数">{{ detailsData.emotional_evaluation.llm_score?.toFixed(3) }}</n-descriptions-item>
            <n-descriptions-item label="最终分数">{{ detailsData.emotional_evaluation.final_score?.toFixed(3) }}</n-descriptions-item>
            <n-descriptions-item v-if="detailsData.emotional_evaluation.matched_keywords?.length" label="匹配关键词" :span="2">
              <n-space>
                <n-tag v-for="kw in detailsData.emotional_evaluation.matched_keywords" :key="kw" size="small">{{ kw }}</n-tag>
              </n-space>
            </n-descriptions-item>
            <n-descriptions-item v-if="detailsData.emotional_evaluation.error" label="错误" :span="2">
              <span style="color: #d03050;">{{ detailsData.emotional_evaluation.error }}</span>
            </n-descriptions-item>
          </n-descriptions>
          <n-collapse style="margin-bottom: 16px">
            <n-collapse-item title="Prompt 预览" name="prompt" v-if="detailsData.emotional_evaluation.prompt_preview">
              <n-code :code="detailsData.emotional_evaluation.prompt_preview" language="text" />
            </n-collapse-item>
          </n-collapse>
        </template>

        <!-- 原始JSON -->
        <n-collapse>
          <n-collapse-item title="原始 JSON 数据" name="raw">
            <n-code :code="JSON.stringify(detailsData, null, 2)" language="json" />
          </n-collapse-item>
        </n-collapse>
      </div>
      <n-empty v-else description="暂无详情数据" />
    </n-modal>

    <!-- 念头日志详情弹窗 -->
    <n-modal v-model:show="showThoughtDetailsModal" preset="card" :title="thoughtDetailsTitle" fullscreen :mask-closable="false">
      <div v-if="thoughtDetailsData">
        <!-- 念头信息 -->
        <n-divider title-placement="left">念头信息</n-divider>
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
          <n-descriptions-item label="念头类型">
            <n-tag :type="getThoughtTypeTagType(thoughtDetailsData.thought_type)" size="small">
              {{ thoughtDetailsData.thought_type || '未知' }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="决策类型">
            <n-tag :type="getDecisionTagType(thoughtDetailsData.decision)" size="small">
              {{ thoughtDetailsData.decision || '未知' }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="决策分数">{{ thoughtDetailsData.score?.toFixed(3) }}</n-descriptions-item>
          <n-descriptions-item v-if="thoughtDetailsData.thought" label="念头内容" :span="2">
            {{ thoughtDetailsData.thought }}
          </n-descriptions-item>
        </n-descriptions>

        <!-- 情绪状态 -->
        <template v-if="thoughtDetailsData.emotion_state">
          <n-divider title-placement="left">情绪状态</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="valence">{{ thoughtDetailsData.emotion_state.valence?.toFixed(3) }}</n-descriptions-item>
            <n-descriptions-item label="arousal">{{ thoughtDetailsData.emotion_state.arousal?.toFixed(3) }}</n-descriptions-item>
            <n-descriptions-item label="social_need">{{ thoughtDetailsData.emotion_state.social_need?.toFixed(3) }}</n-descriptions-item>
            <n-descriptions-item label="dominant">
              <n-tag :type="getEmotionTagType(thoughtDetailsData.emotion_state.dominant)" size="small">
                {{ thoughtDetailsData.emotion_state.dominant }}
              </n-tag>
            </n-descriptions-item>
          </n-descriptions>
        </template>

        <!-- Hindsight 信息 -->
        <template v-if="thoughtDetailsData.hindsight_stored !== undefined || thoughtDetailsData.hindsight_tags">
          <n-divider title-placement="left">Hindsight</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="存储状态">
              <n-tag :type="thoughtDetailsData.hindsight_stored ? 'success' : 'warning'" size="small">
                {{ thoughtDetailsData.hindsight_stored ? '已存储' : '未存储' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item v-if="thoughtDetailsData.hindsight_tags?.length" label="存储标签">
              <n-space>
                <n-tag v-for="tag in thoughtDetailsData.hindsight_tags" :key="tag" :type="getHindsightTagType(tag)" size="small">
                  {{ tag }}
                </n-tag>
              </n-space>
            </n-descriptions-item>
          </n-descriptions>
        </template>

        <!-- LLM 调用 -->
        <template v-if="thoughtDetailsData.llm_call">
          <n-divider title-placement="left">LLM 调用</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="模型">{{ thoughtDetailsData.llm_call.model }}</n-descriptions-item>
            <n-descriptions-item label="耗时">{{ thoughtDetailsData.llm_call.duration_ms }}ms</n-descriptions-item>
          </n-descriptions>
        </template>

        <!-- 原始JSON -->
        <n-collapse>
          <n-collapse-item title="原始 JSON 数据" name="raw">
            <n-code :code="JSON.stringify(thoughtDetailsData, null, 2)" language="json" />
          </n-collapse-item>
        </n-collapse>
      </div>
      <n-empty v-else description="暂无详情数据" />
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { useMessage, NButton } from 'naive-ui'
import api from '../api/active_consciousness'
import mainApi from '../api'

const message = useMessage()
const activeTab = ref('status')

// 配置
const config = ref({
  enabled: false,
  llm: { mode: 'hermes', provider: 'openai', model: 'deepseek-chat', api_key: '', base_url: '' },
  active: { enabled: true, heartbeat_interval: 600, send_tag: '[凯莉主动发送]', time_format: '%H:%M', no_send_after_user_msg_minutes: 10, no_send_while_heat_above: 0.5, no_send_while_vibe_below: 0.3 },
  session: { sources: ['weixin'], time_range_hours: 24, max_messages_per_session: 15, filter_tool_messages: true },
  decision: { send_threshold: 0.6, delay_threshold: 0.3, memory_threshold: 0.1, max_per_hour: 2, max_per_day: 5 },
  thought: { retain_enabled: false, retain_threshold: 0.5 },
  thought_enhanced: {
    enabled: true,
    arousal_low_threshold: 0.3,
    arousal_high_threshold: 0.7,
    count_15d: 3,
    count_7d: 2,
    count_3d: 2,
    count_1d: 1,
    temperature: 0.9,
    max_tokens: 500,
    weather_trigger_enabled: true,
    recall_old_thoughts_limit: 10,
    retain_threshold: 0.5,
    retain_on_weather: true
  },
  weather: {
    enabled: false,
    amap_key: '',
    adcode: '370100',
    cache_ttl: 3600,
    temp_change_threshold: 5.0
  },
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
const heartbeatDate = ref(Date.now())
const thoughtDate = ref(Date.now())
const showRecallModal = ref(false)
const recallItems = ref([])
const showThoughtContentModal = ref(false)
const thoughtContentData = ref(null)

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

// 心跳健康状态：上次心跳在5分钟内=绿，否则红
const heartbeatHealthy = computed(() => {
  if (!status.value.last_heartbeat_at) return false
  const last = new Date(status.value.last_heartbeat_at)
  return (Date.now() - last.getTime()) < 5 * 60 * 1000
})

// 日志详情弹窗
const showDetailsModal = ref(false)
const detailsData = ref(null)
const detailsTitle = ref('')
const isHeartbeatDetails = ref(true)

// 念头日志详情弹窗
const showThoughtDetailsModal = ref(false)
const thoughtDetailsData = ref(null)
const thoughtDetailsTitle = ref('')

function showHeartbeatDetails(row) {
  detailsTitle.value = `心跳日志 #${row.id} 详情`
  detailsData.value = row.details_parsed || null
  isHeartbeatDetails.value = true
  showDetailsModal.value = true
}

function showThoughtDetails(row) {
  thoughtDetailsTitle.value = `念头日志 #${row.id} 详情`
  thoughtDetailsData.value = row.details_parsed || null
  showThoughtDetailsModal.value = true
}

function showRecallDetail(row) {
  recallItems.value = row.details_parsed?.recall_results || []
  showRecallModal.value = true
}
function showThoughtContent(row) {
  thoughtContentData.value = row
  showThoughtContentModal.value = true
}
function onHeartbeatDateChange(val) {
  heartbeatDate.value = val
  loadHeartbeats(1, val)
}
function onThoughtDateChange(val) {
  thoughtDate.value = val
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

const EMOTION_LABEL_CN = {
  happy: '开心', content: '满足', joy: '喜悦', calm: '平静', bored: '无聊',
  longing: '想念', missing: '思念', yearning: '渴望', anxious: '焦虑', concerned: '担忧', worry: '忧虑',
  excited: '兴奋', energetic: '有活力', sad: '悲伤', angry: '生气', neutral: '平静'
}
function emotionLabelCn(dominant) {
  if (!dominant) return '-'
  return EMOTION_LABEL_CN[dominant.toLowerCase()] || dominant
}
function getDecisionLabelCn(type) {
  if (!type) return '-'
  const map = { auto_send: '立即发送', delay_send: '延迟发送', skip: '跳过', memory: '存为记忆' }
  return map[type] || type
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
    case 'delay_send': return 'warning'
    case 'skip': return 'default'
    case 'memory': return 'info'
    default: return 'default'
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
  { title: '时间', key: 'created_at', width: 160, render: (row) => formatTime(row.created_at) },
  { title: '类型', key: 'type', width: 80 },
  { title: '内容', key: 'content', ellipsis: { tooltip: true } },
  { title: '强度', key: 'intensity', width: 80, render: (row) => row.intensity != null ? Number(row.intensity).toFixed(2) : '' },
  { title: '决策', key: 'decision', width: 80 },
  { title: '来源', key: 'recall_source', width: 100 },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render(row) {
      return h(
        NButton,
        { size: 'small', type: 'info', onClick: () => showThoughtDetails(row) },
        { default: () => '详情' }
      )
    }
  }
]
const formatTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const yyyy = d.getFullYear()
  const MM = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${yyyy}-${MM}-${dd} ${hh}:${mm}:${ss}`
}

const heartbeatColumns = [
  { title: '时间', key: 'created_at', width: 160, render: (row) => formatTime(row.created_at) },
  { title: '耗时(ms)', key: 'duration_ms', width: 80 },
  { title: '召回数量', key: 'recall_count', width: 80, render(row) { const v = row.recall_count || 0; return v ? h(NButton, { size: 'tiny', quaternary: true, type: 'info', onClick: () => showRecallDetail(row) }, { default: () => v }) : '0' } },
  { title: '生成念头', key: 'thoughts_generated', width: 80, render(row) { const v = row.thoughts_generated || 0; return v ? h(NButton, { size: 'tiny', quaternary: true, type: 'success', onClick: () => showThoughtContent(row) }, { default: () => v }) : '0' } },
  { title: '发送消息', key: 'message_sent', width: 80, render(row) { const v = row.message_sent; return v ? h(NButton, { size: 'tiny', quaternary: true, type: 'warning', onClick: () => showThoughtContent(row) }, { default: () => '是' }) : '否' } },
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
const thoughtPagination = ref({ page: 1, pageSize: 10, pageCount: 1 })
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
const loadThoughts = async (page = 1, dateVal) => {
  try {
    let dateParam = null
    if (dateVal || thoughtDate.value) {
      const d = new Date(dateVal || thoughtDate.value)
      dateParam = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
    }
    const data = await api.getThoughts(page, dateParam)
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
    thoughtPagination.value.page = page
    thoughtPagination.value.pageCount = Math.ceil(data.total / 10)
  } catch (e) {
    message.error('加载念头日志失败')
  }
}
const loadHeartbeats = async (page = 1, dateVal) => {
  try {
    let dateParam = null
    if (dateVal || heartbeatDate.value) {
      const d = new Date(dateVal || heartbeatDate.value)
      dateParam = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
    }
    const data = await api.getHeartbeats(page, dateParam)
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
.breathing-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-green {
  background: #18a058;
  box-shadow: 0 0 6px #18a058;
  animation: breathe-green 2s ease-in-out infinite;
}
.dot-red {
  background: #d03050;
  box-shadow: 0 0 6px #d03050;
  animation: breathe-red 1.5s ease-in-out infinite;
}
@keyframes breathe-green {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px #18a058; }
  50% { opacity: 0.5; box-shadow: 0 0 12px #18a058; }
}
@keyframes breathe-red {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px #d03050; }
  50% { opacity: 0.4; box-shadow: 0 0 14px #d03050; }
}
</style>

<style>
/* 分页居中 */
.n-data-table__pagination {
  justify-content: center !important;
}
</style>

