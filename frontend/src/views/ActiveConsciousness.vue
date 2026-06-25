<template>
  <div class="active-consciousness-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 状态 -->
      <n-tab-pane name="status" tab="状态">
        <!-- 第1行：核心状态（4个卡片） -->
        <n-grid :cols="4" :x-gap="12" :y-gap="12">
          <n-grid-item>
            <n-card size="small">
              <template #header>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span :class="['breathing-dot', heartbeatHealthy ? 'dot-green' : 'dot-red']"></span>
                  <span>心跳状态</span>
                </div>
              </template>
              <n-statistic label="今日心跳" :value="status.heartbeat_count" />
              <div style="margin-top: 4px; font-size: 11px; color: #999;">
                上次：{{ formatTime(status.last_heartbeat_at) || '无' }}
              </div>
              <div style="margin-top: 4px; font-size: 11px; color: #666;">
                下次：{{ nextHeartbeatDisplay }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="想念分数">
              <n-statistic :value="status.longing.score" :precision="3">
                <template #suffix>
                  <n-tag :type="longingTagType" size="small">{{ status.longing.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="Number((status.longing.score * 100).toFixed(1))" :color="longingColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
              <div style="margin-top: 4px; font-size: 11px; color: #999;">
                沉默：{{ status.longing.silence_minutes ? Math.round(status.longing.silence_minutes) + '分钟' : '-' }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="聊天热度">
              <n-statistic :value="status.chat_heat.heat" :precision="2">
                <template #suffix>
                  <n-tag :type="heatTagType" size="small">{{ status.chat_heat.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="chatHeatPercentage" :color="heatProgressColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
              <div style="margin-top: 4px; font-size: 11px; color: #999;">
                近1小时：{{ status.chat_heat.recent_count || 0 }} 条
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="情绪强度">
              <n-statistic :value="status.emotional_intensity.intensity" :precision="3">
                <template #suffix>
                  <n-tag size="small">{{ status.emotional_intensity.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="status.emotional_intensity.intensity * 100" :color="intensityColor" :show-indicator="false" :height="8" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>
        </n-grid>

        <!-- 第2行：VA模型 + 决策配置 -->
        <n-grid :cols="2" :x-gap="12" :y-gap="12" style="margin-top: 12px;">
          <n-grid-item>
            <n-card size="small" title="情绪状态（VA 模型）">
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 13px; color: #666;">效价（Valence）</span>
                    <span style="font-weight: 600;">{{ status.emotion_state?.valence ?? '-' }}</span>
                  </div>
                  <n-progress :percentage="(status.emotion_state?.valence ?? 0) * 100" :show-indicator="false" :height="8"
                    :color="valenceColor" />
                </div>
                <div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 13px; color: #666;">唤醒度（Arousal）</span>
                    <span style="font-weight: 600;">{{ status.emotion_state?.arousal ?? '-' }}</span>
                  </div>
                  <n-progress :percentage="(status.emotion_state?.arousal ?? 0) * 100" :show-indicator="false" :height="8"
                    :color="arousalColor" />
                </div>
                <div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 13px; color: #666;">社交需求</span>
                    <span style="font-weight: 600;">{{ status.emotion_state?.social_need ?? '-' }}</span>
                  </div>
                  <n-progress :percentage="(status.emotion_state?.social_need ?? 0) * 100" :show-indicator="false" :height="8"
                    :color="socialNeedColor" />
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                  <span style="font-size: 13px; color: #666;">主导情绪</span>
                  <n-tag :type="getEmotionTagType(status.emotion_state?.dominant)" size="small">
                    {{ emotionLabelCn(status.emotion_state?.dominant) }}
                  </n-tag>
                </div>
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="决策配置与阈值">
              <div style="display: flex; flex-direction: column; gap: 12px;">
                <div>
                  <div style="font-size: 13px; color: #666; margin-bottom: 8px;">决策阈值</div>
                  <div style="display: flex; gap: 12px;">
                    <div style="flex: 1; text-align: center;">
                      <div style="font-size: 18px; font-weight: bold; color: #18a058;">{{ decisionConfig.send_threshold }}</div>
                      <div style="font-size: 11px; color: #999;">发送</div>
                    </div>
                    <div style="flex: 1; text-align: center;">
                      <div style="font-size: 18px; font-weight: bold; color: #d03050;">{{ decisionConfig.memory_threshold }}</div>
                      <div style="font-size: 11px; color: #999;">记忆</div>
                    </div>
                  </div>
                </div>
                <n-divider style="margin: 0;" />
                <div>
                  <div style="font-size: 13px; color: #666; margin-bottom: 8px;">频率限制</div>
                  <div style="display: flex; gap: 12px;">
                    <div style="flex: 1;">
                      <div style="display: flex; justify-content: space-between;">
                        <span style="font-size: 12px;">本小时</span>
                        <span style="font-weight: 600;">{{ status.hour_sent_count }}/{{ decisionConfig.max_per_hour }}</span>
                      </div>
                      <n-progress :percentage="frequencyHourPercentage" :show-indicator="false" :height="4"
                        :color="frequencyHourPercentage >= 100 ? '#d03050' : '#18a058'" />
                    </div>
                    <div style="flex: 1;">
                      <div style="display: flex; justify-content: space-between;">
                        <span style="font-size: 12px;">今日</span>
                        <span style="font-weight: 600;">{{ status.today_sent_count }}/{{ decisionConfig.max_per_day }}</span>
                      </div>
                      <n-progress :percentage="frequencyDayPercentage" :show-indicator="false" :height="4"
                        :color="frequencyDayPercentage >= 100 ? '#d03050' : '#18a058'" />
                    </div>
                  </div>
                </div>
                <n-divider style="margin: 0;" />
                <div>
                  <div style="font-size: 13px; color: #666; margin-bottom: 8px;">保护机制</div>
                  <div style="display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; justify-content: space-between;">
                      <span style="font-size: 12px;">冷却时间</span>
                      <n-tag :type="isCoolingDown ? 'warning' : 'success'" size="small">
                        {{ isCoolingDown ? '冷却中' : '正常' }}
                      </n-tag>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                      <span style="font-size: 12px;">用户刚发消息</span>
                      <n-tag :type="userJustSent ? 'warning' : 'success'" size="small">
                        {{ userJustSent ? '等待中' : '正常' }}
                      </n-tag>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                      <span style="font-size: 12px;">热度保护</span>
                      <n-tag :type="heatProtected ? 'warning' : 'success'" size="small">
                        {{ heatProtected ? '已触发' : '正常' }}
                      </n-tag>
                    </div>
                  </div>
                </div>
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>

        <!-- 第3行：发送统计 -->
        <n-grid :cols="3" :x-gap="12" :y-gap="12" style="margin-top: 12px;">
          <n-grid-item>
            <n-card size="small" title="发送统计">
              <div style="display: flex; justify-content: space-around;">
                <div style="text-align: center;">
                  <div style="font-size: 20px; font-weight: 600; color: #333;">{{ status.today_sent_count }}</div>
                  <div style="font-size: 11px; color: #999; margin-top: 2px;">今日</div>
                </div>
                <div style="text-align: center;">
                  <div style="font-size: 20px; font-weight: 600; color: #333;">{{ status.hour_sent_count }}</div>
                  <div style="font-size: 11px; color: #999; margin-top: 2px;">本小时</div>
                </div>
                <div style="text-align: center;">
                  <div style="font-size: 14px; font-weight: 600; color: #333;">{{ formatTime(status.last_sent_at) || '-' }}</div>
                  <div style="font-size: 11px; color: #999; margin-top: 2px;">上次发送</div>
                </div>
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="用户消息">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">最后消息</span>
                  <span style="font-size: 12px;">{{ formatTime(status.longing.last_user_msg_at) || '-' }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">最后回复</span>
                  <span style="font-size: 12px;">{{ formatTime(status.longing.last_self_msg_at) || '-' }}</span>
                </div>
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>

        <!-- LLM 调用统计 -->
        <n-grid :cols="3" :x-gap="12" :y-gap="12" style="margin-top: 12px;">
          <n-grid-item>
            <n-card size="small" title="🎭 情绪 LLM">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">今天</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.emotion_today ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">本周</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.emotion_week ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">本月</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.emotion_month ?? 0 }}</span>
                </div>
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="💭 念头 LLM">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">今天</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.thought_today ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">本周</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.thought_week ?? 0 }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">本月</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ status.llm_stats?.thought_month ?? 0 }}</span>
                </div>
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card size="small" title="📊 总 LLM 调用">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">今天</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ (status.llm_stats?.emotion_today ?? 0) + (status.llm_stats?.thought_today ?? 0) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">本周</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ (status.llm_stats?.emotion_week ?? 0) + (status.llm_stats?.thought_week ?? 0) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="font-size: 12px; color: #666;">本月</span>
                  <span style="font-size: 14px; font-weight: bold;">{{ (status.llm_stats?.emotion_month ?? 0) + (status.llm_stats?.thought_month ?? 0) }}</span>
                </div>
              </div>
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
              <n-input-number v-model:value="heartbeatIdFilter" placeholder="心跳ID" clearable
                :show-button="false" style="width: 120px"
                @update:value="() => loadHeartbeats(1)" />
              <n-button size="small" @click="heartbeatDate = Date.now(); heartbeatIdFilter = null; loadHeartbeats(1)">今天</n-button>
              <n-button size="small" quaternary @click="heartbeatDate = null; heartbeatIdFilter = null; loadHeartbeats(1)">全部</n-button>
            </div>
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
              <n-data-table :columns="heartbeatColumns" :data="heartbeats.items" :pagination="heartbeatPagination" @update:page="loadHeartbeats" :scroll-x="1030" remote />
            </div>
          </n-tab-pane>
          <n-tab-pane name="thoughts" tab="念头日志" style="overflow: visible;">
            <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
              <n-date-picker v-model:value="thoughtDate" type="date" clearable
                @update:value="onThoughtDateChange" style="width: 160px" />
              <n-input-number v-model:value="thoughtIdFilter" placeholder="念头ID" clearable
                :show-button="false" style="width: 120px"
                @update:value="() => loadThoughts(1)" />
              <n-input-number v-model:value="thoughtHeartbeatIdFilter" placeholder="心跳ID" clearable
                :show-button="false" style="width: 120px"
                @update:value="() => loadThoughts(1)" />
              <n-button size="small" @click="thoughtDate = Date.now(); thoughtIdFilter = null; thoughtHeartbeatIdFilter = null; loadThoughts(1)">今天</n-button>
              <n-button size="small" quaternary @click="thoughtDate = null; thoughtIdFilter = null; thoughtHeartbeatIdFilter = null; loadThoughts(1)">全部</n-button>
            </div>
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
              <n-data-table :columns="thoughtColumns" :data="thoughts.items" :pagination="thoughtPagination" @update:page="loadThoughts" :scroll-x="1250" remote :loading="thoughtsLoading" />
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
            <!-- 基础设置 -->
            <n-divider>基础设置</n-divider>
            <n-form-item label="启用心跳">
              <n-switch v-model:value="config.active.enabled" />
            </n-form-item>
            <n-form-item label="心跳间隔（秒）">
              <n-input-number v-model:value="config.active.heartbeat_interval" :min="60" :max="3600" />
            </n-form-item>
            <n-form-item label="发送标记">
              <n-input v-model:value="config.active.send_tag" placeholder="凯莉" />
              <span class="form-item-hint">最终格式：[凯莉 20:16 星期五]</span>
            </n-form-item>
            <n-form-item label="时间格式">
              <n-input v-model:value="config.active.time_format" placeholder="%H:%M" />
              <span class="form-item-hint">strftime 格式，支持 {weekday} 占位符。例：%H:%M 星期{weekday}</span>
            </n-form-item>

            <!-- 决策阈值 -->
            <n-divider>决策阈值</n-divider>
            <n-form-item label="立即发送阈值">
              <n-input-number v-model:value="config.decision.send_threshold" :min="0" :max="1" :step="0.1" />
            </n-form-item>
            <n-form-item label="存为记忆阈值">
              <n-input-number v-model:value="config.decision.memory_threshold" :min="0" :max="1" :step="0.1" />
            </n-form-item>
            <n-form-item label="每小时最大消息">
              <n-input-number v-model:value="config.decision.max_per_hour" :min="1" :max="1000" />
            </n-form-item>
            <n-form-item label="每日最大消息">
              <n-input-number v-model:value="config.decision.max_per_day" :min="1" :max="1000" />
            </n-form-item>

            <!-- 发送保护 -->
            <n-divider>发送保护</n-divider>
            <n-form-item label="禁止窗口（用户消息后分钟）">
              <n-input-number v-model:value="config.active.no_send_after_user_msg_minutes" :min="1" :max="60" />
            </n-form-item>
            <n-form-item label="热度阈值（高于此不发送）">
              <n-input-number v-model:value="config.active.no_send_while_heat_above" :min="0" :max="1000" :step="0.1" />
            </n-form-item>
            <n-form-item label="情绪阈值（低于此不发送）">
              <n-input-number v-model:value="config.active.no_send_while_vibe_below" :min="0" :max="1" :step="0.1" />
            </n-form-item>

            <!-- 念头存储 -->
            <n-divider>念头存储</n-divider>
            <n-form-item label="存入 Hindsight">
              <n-switch v-model:value="config.thought.retain_enabled" />
              <span style="margin-left: 8px; font-size: 12px; color: #999;">开启后念头会写入长期记忆库</span>
            </n-form-item>
            <n-form-item label="Bank ID">
              <n-input v-model:value="config.hindsight.store.bank_id" placeholder="hermes-active" />
              <span style="margin-left: 8px; font-size: 12px; color: #999;">Hindsight 存储 Bank ID，用于区分不同来源的记忆</span>
            </n-form-item>

            <!-- 上下文收集配置 -->
            <n-divider>📦 上下文收集</n-divider>
            <n-form-item label="来源平台">
              <n-select v-model:value="config.context.sources" multiple :options="platformOptions" />
              <span class="form-item-hint">选择要收集对话的平台（可多选）</span>
            </n-form-item>
            <n-form-item label="过滤 Tool 消息">
              <n-switch v-model:value="config.context.filter_tool_messages" />
              <span class="form-item-hint">开启后不包含工具调用消息，只保留用户和助手对话</span>
            </n-form-item>
            <n-form-item label="获取最近消息条数">
              <n-input-number v-model:value="config.context.conversation_limit" :min="10" :max="1000" :step="10" />
              <span class="form-item-hint">跨 session 获取最近 N 条消息作为上下文（默认 200）</span>
            </n-form-item>
            <n-form-item label="记忆召回数量">
              <n-input-number v-model:value="config.context.memory_limit" :min="1" :max="10" />
              <span class="form-item-hint">从 Hindsight 长期记忆中召回多少条相关记忆</span>
            </n-form-item>
            <n-form-item label="启用天气感知">
              <n-switch v-model:value="config.context.weather_enabled" />
              <span class="form-item-hint">收集天气信息作为上下文（需在「配置管理」页面配置天气 API）</span>
            </n-form-item>

            <!-- 想念分数配置 -->
            <n-divider>想念分数配置</n-divider>
            <n-form-item label="计算基准（分钟）">
              <n-input-number v-model:value="config.longing.gap_minutes" :min="60" :max="1440" :step="30" />
              <span style="margin-left: 8px; font-size: 12px; color: #999;">
                沉默分钟数 / 此值 = 想念分数（最大1.0）。默认300分钟（5小时）达到最大值
              </span>
            </n-form-item>

            <!-- 等级配置 -->
            <n-divider>等级配置</n-divider>
            <n-form-item label="想念等级阈值">
              <n-input v-model:value="config.levels.longing" type="textarea" :rows="3" placeholder='[0.0, 0, "calm"], [0.1, 1, "longing"], ...' />
              <span style="margin-left: 8px; font-size: 12px; color: #999;">
                格式：[阈值, 等级, 标签]，逗号分隔
              </span>
            </n-form-item>
            <n-form-item label="聊天热度等级">
              <n-input v-model:value="config.levels.heat" type="textarea" :rows="2" placeholder='[0.0, "cold"], [0.5, "warm"], ...' />
              <span style="margin-left: 8px; font-size: 12px; color: #999;">
                格式：[阈值, 标签]，逗号分隔
              </span>
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
          </template>

          <n-button type="primary" @click="saveConfig" :loading="saving" style="margin-top: 16px">
            保存配置
          </n-button>
        </n-card>
      </n-tab-pane>

      <!-- Tab: LLM -->
      <n-tab-pane name="llm" tab="LLM">
        <!-- 通用 LLM（默认/回退） -->
        <n-card title="通用 LLM（默认/回退）" size="small" style="margin-bottom: 16px">
          <n-form-item label="LLM 模式">
            <n-radio-group v-model:value="config.llm.mode">
              <n-radio value="hermes">使用 Hermes LLM</n-radio>
              <n-radio value="custom">自定义 LLM</n-radio>
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
              <n-input v-model:value="config.llm.api_key" placeholder="输入 API Key" />
            </n-form-item>
            <n-form-item label="Base URL">
              <n-input v-model:value="config.llm.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>
          </template>
          <n-button type="primary" @click="testLLMConnect" :loading="testing.llm" size="small" style="margin-top: 8px">
            测试连通性
          </n-button>
          <n-alert v-if="llmTestResult" :type="llmTestResult.success ? 'success' : 'error'" style="margin-top: 8px" closable @close="llmTestResult = null">
            {{ llmTestResult.success ? 'LLM 连通成功' : 'LLM 连通失败: ' + (llmTestResult.error || '') }}
          </n-alert>
        </n-card>

        <!-- 🎭 情绪评估 LLM -->
        <n-card title="🎭 情绪评估 LLM" size="small" style="margin-bottom: 16px">
          <n-form-item label="LLM 模式">
            <n-radio-group v-model:value="config.emotion_llm.mode">
              <n-radio value="">跟随通用 LLM</n-radio>
              <n-radio value="hermes">使用 Hermes LLM</n-radio>
              <n-radio value="custom">自定义 LLM</n-radio>
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
              <n-input v-model:value="config.emotion_llm.api_key" placeholder="输入 API Key" />
            </n-form-item>
            <n-form-item label="Base URL">
              <n-input v-model:value="config.emotion_llm.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>
          </template>
          <n-form-item label="情绪评估提示词">
            <n-input v-model:value="config.prompts.emotion_evaluation" type="textarea" :rows="6" placeholder="输入情绪评估提示词模板" />
          </n-form-item>
          <div style="font-size: 11px; color: #999; margin-bottom: 8px;">
            可用变量：{time} {longing_score} {longing_label} {chat_heat} {chat_label} {silence_minutes} {context}
          </div>
          <n-button type="primary" @click="testEmotionLLM" :loading="testing.emotionLLM" size="small">
            测试情绪评估 LLM
          </n-button>
          <n-alert v-if="emotionLLMTestResult" :type="emotionLLMTestResult.success ? 'success' : 'error'" style="margin-top: 8px" closable @close="emotionLLMTestResult = null">
            <template v-if="emotionLLMTestResult.success">
              情绪评估 LLM 测试成功
              <div v-if="emotionLLMTestResult.data" style="font-size: 12px; margin-top: 4px;">
                模型: {{ emotionLLMTestResult.data.model || '-' }} | 耗时: {{ emotionLLMTestResult.data.duration_ms || '-' }}ms
              </div>
            </template>
            <template v-else>
              情绪评估 LLM 测试失败: {{ emotionLLMTestResult.error || '' }}
            </template>
          </n-alert>
        </n-card>

        <!-- 💭 念头生成 LLM -->
        <n-card title="💭 念头生成 LLM" size="small" style="margin-bottom: 16px">
          <n-form-item label="启用 ThoughtEngine">
            <n-switch v-model:value="config.thought_engine.enabled" />
            <span class="form-item-hint">统一念头生成器：收集上下文 → 构建提示词 → LLM 生成 → 解析结果</span>
          </n-form-item>
          <template v-if="config.thought_engine.enabled">
            <n-form-item label="最大 Token 数">
              <n-input-number v-model:value="config.thought_engine.max_tokens" :min="0" :max="2000" />
              <span class="form-item-hint">0 = 不限制（推荐 sensenova 设 1000+，deepseek 可设 0）</span>
            </n-form-item>
            <n-form-item label="Temperature">
              <n-input-number v-model:value="config.thought_engine.temperature" :min="0" :max="2" :step="0.1" />
              <span class="form-item-hint">推荐 0.7-1.0</span>
            </n-form-item>
          </template>
          <n-form-item label="LLM 模式">
            <n-radio-group v-model:value="config.thought_llm.mode">
              <n-radio value="">跟随通用 LLM</n-radio>
              <n-radio value="hermes">使用 Hermes LLM</n-radio>
              <n-radio value="custom">自定义 LLM</n-radio>
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
              <n-input v-model:value="config.thought_llm.api_key" placeholder="输入 API Key" />
            </n-form-item>
            <n-form-item label="Base URL">
              <n-input v-model:value="config.thought_llm.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>
          </template>
          <n-form-item label="念头生成 System 提示词">
            <n-input v-model:value="config.prompts.thought_generation" type="textarea" :rows="6" placeholder="输入念头生成 System 提示词（人设 + 对话 + 记忆 + 环境）" />
          </n-form-item>
          <div style="font-size: 11px; color: #999; margin-bottom: 8px;">
            可用变量：{persona} {session_context} {hindsight_context} {time} {emotion_display} {weather_display}
          </div>
          <n-form-item label="念头生成 User 指令">
            <n-input v-model:value="config.prompts.thought_generation_instruction" type="textarea" :rows="4" placeholder="输入念头生成 User 指令（任务指令 + output priming）" />
          </n-form-item>
          <div style="font-size: 11px; color: #999; margin-bottom: 8px;">
            这是发给 LLM 的最后一条消息，控制 LLM 的行为模式。建议包含 output priming（如"以XXX开头"）和反复读指令。
          </div>
          <n-button type="primary" @click="testThoughtLLM" :loading="testing.thoughtLLM" size="small">
            测试念头生成 LLM
          </n-button>
          <n-alert v-if="thoughtLLMTestResult" :type="thoughtLLMTestResult.success ? 'success' : 'error'" style="margin-top: 8px" closable @close="thoughtLLMTestResult = null">
            <template v-if="thoughtLLMTestResult.success">
              念头生成 LLM 测试成功
              <div v-if="thoughtLLMTestResult.data" style="font-size: 12px; margin-top: 4px;">
                模型: {{ thoughtLLMTestResult.data.model || '-' }} | 耗时: {{ thoughtLLMTestResult.data.duration_ms || '-' }}ms
              </div>
            </template>
            <template v-else>
              念头生成 LLM 测试失败: {{ thoughtLLMTestResult.error || '' }}
            </template>
          </n-alert>
        </n-card>
        
        <!-- 保存按钮 -->
        <div style="text-align: center; padding: 16px 0;">
          <n-button type="primary" @click="saveConfig" :loading="saving" size="large">
            保存 LLM 配置
          </n-button>
        </div>
      </n-tab-pane>

      <!-- Tab: 运行逻辑 -->
      <n-tab-pane name="logic" tab="运行逻辑">
        <n-card title="主动意识运行逻辑" size="small" class="run-logic-card">
          <n-steps vertical :current="10" size="small">
            <n-step title="1. 心跳触发">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                APScheduler 定时触发，默认间隔 300 秒（5 分钟）。检查主动意识是否启用、是否在活跃时间窗口内。
              </div>
            </n-step>
            <n-step title="2. 情绪演化">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                VA 模型自然演化：Arousal 每小时衰减 0.02、Social Need 每小时增长 0.01、Valence 每小时向 0.5 回归 10%。根据距上次更新的时间间隔自动计算。
              </div>
            </n-step>
            <n-step title="3. LLM 情绪评估">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                LLM 根据最近对话评估情绪状态，返回 VA 值和主导情绪。通过置信度计算动态合并 LLM 与演化结果（高信任: 演化30%+LLM70%，低信任: 演化70%+LLM30%）。
              </div>
            </n-step>
            <n-step title="4. 上下文收集 + Hindsight 记忆召回">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                ContextCollector 跨 Session 获取最近 N 条消息（默认 200 条，彻底过滤 Tool 消息），同时调用 Hindsight Recall 检索相关记忆。收集的信息包括：对话历史、情绪状态、时间感知、天气信息、用户习惯。
              </div>
            </n-step>
            <n-step title="5. 决策矩阵评分">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                score = intensity × time_fitness × silence_factor × frequency_limit。综合情绪强度（social_need×0.5 + arousal×0.3 + valence×0.2）、时间适宜性、沉默时长和频率限制。根据 score 与阈值比较得出决策：auto_send（≥send_threshold）、memory（≥memory_threshold）、skip（&lt;memory_threshold）。skip 不调 LLM，省 token。
              </div>
            </n-step>
            <n-step title="6. 发送保护检查">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                检查：用户消息后 5 分钟等待期、聊天热度 > 3.0、情绪强度 < 0.15、冷却期 30 分钟、每小时最多 2 条 / 每天最多 5 条。任一不通过则拦截实际发送（但保留决策分数）。
              </div>
            </n-step>
            <n-step title="7. 念头生成（LLM）">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                仅当决策为 auto_send 或 memory 时调用 LLM 生成念头。ThoughtEngine 使用 system/user 消息分离结构：system 放人设+对话+记忆+环境，user 放任务指令（含 output priming）。LLM 可输出 SKIP 表示不想联系用户。决策为 skip 时跳过此步，不消耗 token。max_tokens=0 时不限制输出长度。
              </div>
            </n-step>
            <n-step title="8. 执行动作">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                auto_send：发送消息到目标平台。memory：存为记忆不发送。发送或存记忆时同步写入 Hindsight 长期记忆。
              </div>
            </n-step>
            <n-step title="9. 想念分数计算">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                longing_score = min(沉默分钟/gap_minutes, 1.0) × decay_factor。用户每回复 1 条消息衰减 10%，最少保留 10%。等级：平静→思念→想念→渴望→焦虑。
              </div>
            </n-step>
            <n-step title="10. 情绪状态持久化">
              <div style="font-size: 13px; color: #666; line-height: 1.6;">
                保存更新后的情绪状态（VA 值 + 主导情绪 + 更新时间），写入心跳日志（含决策详情、耗时、LLM 调用记录），供前端展示和下次心跳演化使用。
              </div>
            </n-step>
          </n-steps>

          <!-- 参考信息折叠区 -->
          <n-collapse style="margin-top: 16px;">
            <n-collapse-item title="📖 术语总览" name="overview">
              <div style="font-size: 13px; line-height: 1.8;">
                <p><strong>VA 模型</strong>（情绪三维度）：</p>
                <ul>
                  <li><strong>Valence（效价）</strong>：情绪的正负性，0=消极，1=积极，0.5=中性</li>
                  <li><strong>Arousal（唤醒度）</strong>：情绪的激活程度，0=平静，1=激动</li>
                  <li><strong>Social Need（社交需求）</strong>：想要社交/聊天的程度，0=不需要，1=非常想</li>
                </ul>
                <p><strong>核心指标</strong>：</p>
                <ul>
                  <li><strong>想念分数</strong>（longing_score）：基于沉默时长和回复频率，0-1</li>
                  <li><strong>聊天热度</strong>（chat_heat）：近1小时用户消息数</li>
                  <li><strong>情绪强度</strong>（intensity）：social_need×0.5 + arousal×0.3 + valence×0.2</li>
                  <li><strong>决策分数</strong>（score）：intensity × time_fitness × silence_factor × frequency_limit</li>
                </ul>
              </div>
            </n-collapse-item>

            <n-collapse-item title="📊 决策阈值详情" name="decision_detail">
              <div style="font-size: 13px; line-height: 1.8;">
                <p><strong>intensity（情绪强度）</strong>：social_need × 0.5 + arousal × 0.3 + valence × 0.2，最低 0.2</p>
                <p><strong>time_fitness（时间适宜性）</strong>：</p>
                <ul>
                  <li>7:00-9:00 早安窗口: 1.0 | 9:00-12:00 工作: 0.8 | 12:00-14:00 午休: 0.9</li>
                  <li>14:00-18:00 工作: 0.7 | 18:00-22:00 下班: 1.0 | 22:00-23:30 睡前: 0.8 | 23:30-7:00 深夜: 0.3</li>
                </ul>
                <p><strong>silence_factor（沉默因子）</strong>：</p>
                <ul>
                  <li>&lt;30分钟: 0.6 | 30-60分钟: 0.75 | 1-3小时: 0.85 | 3-6小时: 0.95 | &gt;6小时: 1.0</li>
                </ul>
                <p><strong>frequency_limit</strong>：未超频 1.0，超频 0.0</p>
                <p><strong>决策阈值</strong>：≥0.35 auto_send | ≥0.05 memory | &lt;0.05 skip</p>
              </div>
            </n-collapse-item>

            <n-collapse-item title="🛡️ 保护规则" name="protection">
              <div style="font-size: 13px; line-height: 1.8;">
                <ul>
                  <li><strong>用户消息后等待期</strong>：用户发消息后 5 分钟内不发送</li>
                  <li><strong>聊天热度</strong>：热度 > 3.0 时不发送</li>
                  <li><strong>情绪强度</strong>：强度 < 0.15 时不发送</li>
                  <li><strong>冷却期</strong>：上次发送后 30 分钟内不发送</li>
                  <li><strong>频率限制</strong>：每小时最多 2 条，每天最多 5 条</li>
                </ul>
              </div>
            </n-collapse-item>

            <n-collapse-item title="📈 聊天热度等级" name="heat">
              <div style="font-size: 13px; line-height: 1.8;">
                <p><strong>公式</strong>：chat_heat = 近1小时用户消息数 / 1小时</p>
                <ul>
                  <li>0.0-0.5：cold（冷清）</li>
                  <li>0.5-1.0：warm（温暖）</li>
                  <li>1.0-3.0：hot（热烈）</li>
                  <li>> 3.0：fire（火热）</li>
                </ul>
              </div>
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </n-tab-pane>

      <!-- Tab: 测试 -->
      <n-tab-pane name="test" tab="测试">

        <!-- 测试按钮组 -->
        <n-card title="节点测试" size="small" style="margin-bottom: 16px">
          <n-space vertical>
            <n-grid :cols="2" :x-gap="12" :y-gap="12">
              <n-grid-item>
                <n-button block @click="testLLMConnect" :loading="testing.llm">
                  ① LLM 连通性测试
                </n-button>
                <div style="font-size: 11px; color: #999; margin-top: 4px;">测试 LLM 服务是否可连接</div>
              </n-grid-item>
              <n-grid-item>
                <n-button block @click="testSessionContext" :loading="testing.sessionContext">
                  ② Session 上下文测试
                </n-button>
                <div style="font-size: 11px; color: #999; margin-top: 4px;">测试从 state.db 读取最近对话</div>
              </n-grid-item>
              <n-grid-item>
                <n-button block @click="testContextCollector" :loading="testing.contextCollector">
                  ③ ContextCollector 测试
                </n-button>
                <div style="font-size: 11px; color: #999; margin-top: 4px;">测试完整上下文收集（对话+记忆+情绪+时间+天气）</div>
              </n-grid-item>
              <n-grid-item>
                <n-button block type="primary" @click="testThoughtEngine" :loading="testing.thoughtEngine">
                  ④ ThoughtEngine 完整测试
                </n-button>
                <div style="font-size: 11px; color: #999; margin-top: 4px;">测试完整流程：上下文收集 → LLM 生成 → SKIP 判断</div>
              </n-grid-item>
            </n-grid>
          </n-space>
        </n-card>


        <!-- 测试结果展示 -->
        <n-card v-if="testResult" title="测试结果" size="small">
          <template #header-extra>
            <n-button text @click="testResult = null">清空</n-button>
          </template>
          
          <!-- 状态标签 -->
          <n-space style="margin-bottom: 12px;">
            <n-tag :type="testResult.success ? 'success' : 'error'" size="small">
              {{ testResult.success ? '成功' : '失败' }}
            </n-tag>
            <n-tag v-if="testResult.data?.want_to_contact !== undefined" 
                   :type="testResult.data.want_to_contact ? 'success' : 'warning'" size="small">
              {{ testResult.data.want_to_contact ? '想联系用户' : 'SKIP（不想联系）' }}
            </n-tag>
          </n-space>

          <!-- ThoughtEngine 结果 -->
          <template v-if="testResult.data?.thought">
            <n-divider title-placement="left">💭 生成的念头</n-divider>
            <n-card size="small" style="margin-bottom: 12px;">
              <div style="font-size: 14px; white-space: pre-wrap;">{{ testResult.data.thought }}</div>
            </n-card>
          </template>

          <!-- 上下文信息 -->
          <template v-if="testResult.data?.context_bundle || testResult.data?.conversations_count !== undefined">
            <n-divider title-placement="left">📦 上下文信息</n-divider>
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;">
              <n-descriptions-item label="对话条数">
                {{ testResult.data.context_bundle?.conversations_count || testResult.data.conversations_count || 0 }}
              </n-descriptions-item>
              <n-descriptions-item label="记忆条数">
                {{ testResult.data.context_bundle?.memories_count || testResult.data.memories_count || 0 }}
              </n-descriptions-item>
              <n-descriptions-item label="主导情绪">
                {{ testResult.data.context_bundle?.emotion?.dominant || testResult.data.emotion?.dominant || '-' }}
              </n-descriptions-item>
              <n-descriptions-item label="时间感知">
                {{ testResult.data.context_bundle?.time_context?.time_display || testResult.data.time_context?.time_display || '-' }}
              </n-descriptions-item>
            </n-descriptions>
          </template>

          <!-- LLM 调用详情 -->
          <template v-if="testResult.data?.llm_details">
            <n-divider title-placement="left">🤖 LLM 调用详情</n-divider>
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;">
              <n-descriptions-item label="模型">{{ testResult.data.llm_details.model || '-' }}</n-descriptions-item>
              <n-descriptions-item label="耗时">{{ testResult.data.llm_details.duration_ms || '-' }}ms</n-descriptions-item>
              <n-descriptions-item label="Prompt Tokens">{{ testResult.data.llm_details.prompt_tokens ?? '-' }}</n-descriptions-item>
              <n-descriptions-item label="Completion Tokens">{{ testResult.data.llm_details.completion_tokens ?? '-' }}</n-descriptions-item>
              <n-descriptions-item v-if="testResult.data.llm_details.error" label="错误" :span="2">
                <span style="color: #d03050;">{{ testResult.data.llm_details.error }}</span>
              </n-descriptions-item>
            </n-descriptions>
          </template>

          <!-- 错误信息 -->
          <template v-if="testResult.error">
            <n-divider title-placement="left">❌ 错误信息</n-divider>
            <n-alert type="error" style="margin-bottom: 12px;">
              {{ testResult.error }}
            </n-alert>
            <n-collapse v-if="testResult.traceback">
              <n-collapse-item title="堆栈跟踪" name="traceback">
                <n-code :code="testResult.traceback" language="text" word-wrap />
              </n-collapse-item>
            </n-collapse>
          </template>

          <!-- 完整 JSON -->
          <n-collapse>
            <n-collapse-item title="完整 JSON 数据" name="json">
              <n-code :code="formatJson(testResult)" language="json" word-wrap />
            </n-collapse-item>
          </n-collapse>
        </n-card>


      </n-tab-pane>
    </n-tabs>

    <!-- 上下文测试结果弹窗 -->
    <n-modal v-model:show="showSessionContextModal" preset="card" title="上下文测试结果" style="width: 90vw; max-width: 900px">
      <template v-if="sessionContextResult">
        <n-descriptions :column="2" label-placement="left" bordered size="small" style="margin-bottom: 12px">
          <n-descriptions-item label="对话数量">
            {{ sessionContextResult.data?.conversations_count ?? '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="记忆数量">
            {{ sessionContextResult.data?.memories_count ?? '-' }}
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
          <div style="font-size: 13px; white-space: pre-wrap;">{{ item.content || item.text || formatJson(item) }}</div>
        </n-list-item>
      </n-list>
      <n-empty v-else-if="!recallLoading" description="无召回内容" />
      <div v-else style="display: flex; justify-content: center; padding: 40px 0;">
        <n-spin size="medium" />
      </div>
    </n-modal>

    <!-- 念头内容弹窗（生成念头列点击） -->
    <n-modal v-model:show="showThoughtContentModal" preset="card" title="念头详情" style="width: 90vw; max-width: 900px">
      <template v-if="thoughtContentData">
        <!-- 念头内容（最醒目） -->
        <n-card size="small" style="margin-bottom: 12px;">
          <div style="white-space: pre-wrap; font-size: 14px; line-height: 1.6;">{{ thoughtContentData.thought_content || '无念头内容' }}</div>
        </n-card>
        <!-- 基本信息 -->
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;" :label-style="{ width: '100px' }">
          <n-descriptions-item label="决策类型" v-if="thoughtContentData.decision?.type">
            <n-tag :type="getDecisionTagType(thoughtContentData.decision.type)" size="small">
              {{ getDecisionLabelCn(thoughtContentData.decision.type) }}
            </n-tag>
            <span v-if="thoughtContentData.decision.score" style="margin-left: 8px; font-size: 12px; color: #999;">
              分数: {{ thoughtContentData.decision.score?.toFixed(3) }}
            </span>
          </n-descriptions-item>
          <n-descriptions-item label="念头类型" v-if="thoughtContentData.thought_type">
            {{ thoughtTypeLabelCn(thoughtContentData.thought_type) }}
          </n-descriptions-item>
          <n-descriptions-item label="想联系用户" v-if="thoughtContentData.want_to_contact !== null">
            <n-tag :type="thoughtContentData.want_to_contact ? 'success' : 'default'" size="small">
              {{ thoughtContentData.want_to_contact ? '是' : '否 (SKIP)' }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="心跳ID">{{ thoughtContentData.id }}</n-descriptions-item>
        </n-descriptions>
        <!-- LLM 信息 -->
        <n-divider title-placement="left" style="margin: 12px 0 8px;">LLM 调用</n-divider>
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;" :label-style="{ width: '100px' }">
          <n-descriptions-item label="耗时" v-if="thoughtContentData.llm_duration_ms">
            {{ thoughtContentData.llm_duration_ms }}ms
          </n-descriptions-item>
          <n-descriptions-item label="总Token" v-if="thoughtContentData.llm_total_tokens">
            {{ thoughtContentData.llm_total_tokens }}（输入 {{ thoughtContentData.llm_prompt_tokens }} / 输出 {{ thoughtContentData.llm_completion_tokens }}）
          </n-descriptions-item>
        </n-descriptions>
        <!-- Prompt 和 LLM 返回（默认折叠） -->
        <n-collapse style="margin-bottom: 12px;">
          <n-collapse-item title="发送的 Prompt" name="prompt">
            <n-code :code="formatPrompt(thoughtContentData.llm_prompt_sent)" language="text" word-wrap />
          </n-collapse-item>
          <n-collapse-item title="LLM 原始返回" name="response">
            <n-code :code="thoughtContentData.llm_response_received || '无'" language="text" word-wrap />
          </n-collapse-item>
        </n-collapse>
      </template>
      <n-empty v-else-if="!thoughtContentLoading" description="无念头内容" />
      <div v-else style="display: flex; justify-content: center; padding: 40px 0;">
        <n-spin size="medium" />
      </div>
    </n-modal>

    <!-- 发送详情弹窗（发送消息列点击） -->
    <n-modal v-model:show="showSendDetailModal" preset="card" title="发送详情" style="width: 90vw; max-width: 900px">
      <template v-if="sendDetailData">
        <n-descriptions :column="1" label-placement="left" bordered size="small" :label-style="{ width: '100px' }">
          <n-descriptions-item label="心跳ID">{{ sendDetailData.id }}</n-descriptions-item>
          <n-descriptions-item label="是否发送">
            <n-tag :type="getSendResultTagType(sendDetailData)" size="small">
              {{ getSendResultLabel(sendDetailData) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="失败原因" v-if="getSendResultTagType(sendDetailData) === 'error'">
            <pre style="white-space: pre-wrap; color: #d03050; font-size: 12px; margin: 0;">{{ getSendFailureReason(sendDetailData) }}</pre>
          </n-descriptions-item>
          <n-descriptions-item label="发送状态" v-if="sendDetailData.message_sending">
            <n-tag :type="sendDetailData.message_sending.success ? 'success' : 'error'" size="small">
              {{ sendDetailData.message_sending.success ? '发送成功' : '发送失败' }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="发送内容" v-if="sendDetailData.sent_content">
            <div style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">{{ sendDetailData.sent_content }}</div>
          </n-descriptions-item>
          <n-descriptions-item label="念头类型" v-if="sendDetailData.thought_type">
            {{ thoughtTypeLabelCn(sendDetailData.thought_type) }}
          </n-descriptions-item>
          <n-descriptions-item label="决策类型" v-if="sendDetailData.decision?.type">
            <n-tag :type="getDecisionTagType(sendDetailData.decision.type)" size="small">
              {{ sendDetailData.decision.type }}
            </n-tag>
          </n-descriptions-item>
        </n-descriptions>
      </template>
      <n-empty v-else-if="!sendDetailLoading" description="无发送详情" />
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
              <div style="font-size: 13px; color: #666; margin-bottom: 2px;">
                {{ getHeartbeatResultReason(detailsData) }}
              </div>
              <div style="font-size: 12px; color: #999;">
                {{ detailsData.duration_ms ? `耗时 ${detailsData.duration_ms}ms` : '' }}
              </div>
            </div>
            <!-- 关键指标 -->
            <div style="display: flex; gap: 16px;">
              <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #18a058;">
                  {{ detailsData.decision?.score?.toFixed(2) || '0.00' }}
                </div>
                <div style="font-size: 11px; color: #999;">决策分数</div>
              </div>
              <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #2080f0;">
                  {{ detailsData.chat_heat?.toFixed(1) || '0.0' }}
                </div>
                <div style="font-size: 11px; color: #999;">聊天热度</div>
              </div>
              <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #f0a020;">
                  {{ detailsData.emotional_intensity?.toFixed(2) || '0.00' }}
                </div>
                <div style="font-size: 11px; color: #999;">情绪强度</div>
              </div>
            </div>
          </div>
        </n-card>


        <!-- ===== 执行流程（可折叠） ===== -->
        <n-collapse default-expanded-names="">
          <n-collapse-item title="执行流程" name="timeline">
            <n-timeline>
              <!-- 1. 心跳触发 -->
              <n-timeline-item type="success" title="心跳触发">
                <template #icon>
                  <n-icon size="16"><CheckmarkCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: #666;">
                  {{ detailsData.started_at || '-' }}
                </div>
              </n-timeline-item>

              <!-- 2. 情绪演化 -->
              <n-timeline-item v-if="detailsData.emotion_before" type="success" title="情绪演化">
                <template #icon>
                  <n-icon size="16"><CheckmarkCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: #666;">
                  距上次 {{ detailsData.minutes_since_update?.toFixed(0) || '0' }} 分钟
                  <n-tag size="tiny" :type="getEmotionTagType(detailsData.emotion_merged?.dominant)">
                    {{ emotionLabelCn(detailsData.emotion_merged?.dominant) }}
                  </n-tag>
                </div>
              </n-timeline-item>

              <!-- 3. 上下文收集 -->
              <n-timeline-item v-if="detailsData.session_context !== undefined" type="success" title="上下文收集">
                <template #icon>
                  <n-icon size="16"><CheckmarkCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: #666;">
                  对话 {{ detailsData.session_context ? '✓' : '✗' }}
                  | 记忆 {{ detailsData.recall_results?.length || 0 }} 条
                  | Hindsight {{ detailsData.hindsight_context ? '✓' : '✗' }}
                </div>
              </n-timeline-item>

              <!-- 4. 决策计算 -->
              <n-timeline-item v-if="detailsData.decision" :type="getDecisionTimelineType(detailsData.decision)" title="决策计算">
                <template #icon>
                  <n-icon size="16"><CheckmarkCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: #666;">
                  分数 {{ detailsData.decision.score?.toFixed(3) || '0.000' }}
                  → <n-tag size="tiny" :type="getDecisionTagType(detailsData.decision.type)">
                    {{ getDecisionLabelCn(detailsData.decision.type) }}
                  </n-tag>
                </div>
              </n-timeline-item>

              <!-- 5. 发送保护 -->
              <n-timeline-item 
                v-if="detailsData.decision?.blocked_by_protection" 
                type="error" 
                title="发送保护拦截"
              >
                <template #icon>
                  <n-icon size="16"><CloseCircle /></n-icon>
                </template>
                <div style="font-size: 12px; color: #d03050;">
                  {{ detailsData.decision.protection_reason || '保护机制拦截' }}
                </div>
              </n-timeline-item>

              <!-- 6. 念头生成 -->
              <n-timeline-item 
                v-if="detailsData.thought_generation" 
                :type="detailsData.thought_generation.success === true || (detailsData.thought_generation.response_received && !detailsData.thought_generation.error) ? 'success' : detailsData.thought_generation.success === false ? 'error' : 'success'" 
                title="念头生成"
              >
                <template #icon>
                  <n-icon size="16">
                    <CheckmarkCircle v-if="detailsData.thought_generation.success === true || (detailsData.thought_generation.response_received && !detailsData.thought_generation.error)" />
                    <CloseCircle v-else-if="detailsData.thought_generation.success === false" />
                    <CheckmarkCircle v-else />
                  </n-icon>
                </template>
                <div style="font-size: 12px; color: #666;">
                  <template v-if="detailsData.thought_generation.success === false">
                    {{ detailsData.thought_generation.error || '生成失败' }}
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
                title="消息发送"
              >
                <template #icon>
                  <n-icon size="16">
                    <CheckmarkCircle v-if="detailsData.message_sending.success" />
                    <CloseCircle v-else />
                  </n-icon>
                </template>
                <div style="font-size: 12px; color: #666;">
                  {{ detailsData.message_sending.success ? '发送成功' : '发送失败' }}
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
            <n-divider title-placement="left" style="margin: 12px 0 8px;">情绪评估 LLM</n-divider>
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 8px;">
              <n-descriptions-item label="耗时">{{ detailsData.emotion_llm_details.duration_ms || '-' }}ms</n-descriptions-item>
            </n-descriptions>
            <n-collapse style="margin-bottom: 12px;">
              <n-collapse-item title="发送的 Prompt" name="emotion_prompt">
                <n-code :code="formatPrompt(detailsData.emotion_llm_details.prompt_sent)" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item title="LLM 返回" name="emotion_response">
                <n-code :code="detailsData.emotion_llm_details.response_received || '无'" language="text" word-wrap />
              </n-collapse-item>
            </n-collapse>
          </template>

          <!-- 念头生成 LLM -->
          <template v-if="detailsData.thought_generation">
            <n-divider title-placement="left" style="margin: 12px 0 8px;">念头生成 LLM</n-divider>
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 8px;">
              <n-descriptions-item label="耗时">{{ detailsData.thought_generation.duration_ms || '-' }}ms</n-descriptions-item>
              <n-descriptions-item label="想联系用户">
                <n-tag :type="detailsData.thought_generation.want_to_contact ? 'success' : 'default'" size="small">
                  {{ detailsData.thought_generation.want_to_contact ? '是' : '否 (SKIP)' }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item v-if="detailsData.thought_generation.thought" label="生成内容" :span="2">
                {{ detailsData.thought_generation.thought }}
              </n-descriptions-item>
            </n-descriptions>
            <n-collapse style="margin-bottom: 12px;">
              <n-collapse-item title="发送的 Prompt" name="thought_prompt">
                <n-code :code="formatPrompt(detailsData.thought_generation.prompt_sent)" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item title="LLM 返回" name="thought_response">
                <n-code :code="detailsData.thought_generation.response_received || '无'" language="text" word-wrap />
              </n-collapse-item>
            </n-collapse>
          </template>
        </template>

        <!-- 决策计算详情 -->
        <n-divider title-placement="left" style="margin: 12px 0 8px;">决策计算详情</n-divider>
        <n-descriptions bordered :column="2" size="small" style="margin-bottom: 12px;">
          <n-descriptions-item label="决策类型">
            <n-tag :type="getDecisionTagType(detailsData.decision?.type)" size="small">
              {{ getDecisionLabelCn(detailsData.decision?.type) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="最终分数">{{ detailsData.decision?.score?.toFixed(3) }}</n-descriptions-item>
          <n-descriptions-item label="情绪强度">
            {{ parseDecisionReason(detailsData.decision?.reason).intensity }}
          </n-descriptions-item>
          <n-descriptions-item label="时间适宜性">
            {{ parseDecisionReason(detailsData.decision?.reason).time_fitness }}
          </n-descriptions-item>
          <n-descriptions-item label="沉默因子">
            {{ parseDecisionReason(detailsData.decision?.reason).silence_factor }}
          </n-descriptions-item>
          <n-descriptions-item label="频率限制">
            {{ parseDecisionReason(detailsData.decision?.reason).frequency }}
          </n-descriptions-item>
          <n-descriptions-item label="决策原因" :span="2">{{ detailsData.decision?.reason }}</n-descriptions-item>
          <n-descriptions-item label="结果说明" :span="2">
            <template v-if="detailsData.decision?.type === 'skip'">
              分数 {{ detailsData.decision?.score?.toFixed(3) }} 未达记忆阈值，跳过本轮（不调用 LLM）
            </template>
            <template v-else-if="detailsData.decision?.type === 'memory'">
              分数 {{ detailsData.decision?.score?.toFixed(3) }} 达到记忆阈值，生成念头存入记忆
            </template>
            <template v-else-if="detailsData.decision?.type === 'auto_send'">
              分数 {{ detailsData.decision?.score?.toFixed(3) }} 达到发送阈值，生成念头并发送
            </template>
            <template v-else>{{ detailsData.decision?.type }}</template>
          </n-descriptions-item>
        </n-descriptions>

        <!-- 情绪演化详情 -->
        <template v-if="detailsData.emotion_before">
          <n-divider title-placement="left" style="margin: 12px 0 8px;">情绪演化详情</n-divider>
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
          <div style="font-size: 12px; color: #666; margin-bottom: 12px;">
            距上次 {{ detailsData.minutes_since_update?.toFixed(0) }}分钟
          </div>
        </template>
      </div>
      <n-empty v-else-if="!heartbeatDetailLoading" description="暂无详情数据" />
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
            <n-tag v-if="thoughtDetailsData.heartbeat_id" size="small" type="info">心跳: {{ thoughtDetailsData.heartbeat_id }}</n-tag>
            <!-- 结果信息 -->
            <div style="flex: 1; min-width: 200px;">
              <div style="font-size: 13px; color: #666; margin-bottom: 2px;">
                {{ thoughtDetailsData.thought || "无念头内容" }}
              </div>
              <div style="font-size: 12px; color: #999;">
                {{ thoughtTypeLabelCn(thoughtDetailsData.thought_type) }} · {{ emotionLabelCn(thoughtDetailsData.emotion_state?.dominant) }}
              </div>
            </div>
            <!-- 关键指标 -->
            <div style="display: flex; gap: 16px;">
              <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #18a058;">
                  {{ thoughtDetailsData.score?.toFixed(2) || "0.00" }}
                </div>
                <div style="font-size: 11px; color: #999;">决策分数</div>
              </div>
            </div>
          </div>
        </n-card>

        <!-- ===== 详细信息（可折叠） ===== -->
        <n-collapse default-expanded-names="">
          <!-- 情绪状态 -->
          <n-collapse-item v-if="thoughtDetailsData.emotion_state" title="情绪状态" name="emotion">
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
              <n-descriptions-item label="效价">{{ thoughtDetailsData.emotion_state.valence?.toFixed(3) }}</n-descriptions-item>
              <n-descriptions-item label="唤醒度">{{ thoughtDetailsData.emotion_state.arousal?.toFixed(3) }}</n-descriptions-item>
              <n-descriptions-item label="社交需求">{{ thoughtDetailsData.emotion_state.social_need?.toFixed(3) }}</n-descriptions-item>
              <n-descriptions-item label="主导情绪">
                <n-tag :type="getEmotionTagType(thoughtDetailsData.emotion_state.dominant)" size="small">
                  {{ emotionLabelCn(thoughtDetailsData.emotion_state.dominant) }}
                </n-tag>
              </n-descriptions-item>
            </n-descriptions>
          </n-collapse-item>

          <!-- Hindsight 信息 -->
          <div v-if="thoughtDetailsData.hindsight_stored !== undefined" style="margin-bottom: 16px;">
            <div style="font-weight: 500; margin-bottom: 8px; font-size: 14px;">Hindsight 存储</div>
            <n-descriptions bordered :column="2" size="small">
              <n-descriptions-item label="存储状态">
                <n-tag :type="thoughtDetailsData.hindsight_stored ? 'success' : 'warning'" size="small">
                  {{ thoughtDetailsData.hindsight_stored ? "已存储" : "未存储" }}
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
          </div>

          <!-- 上下文信息 -->
          <n-collapse-item v-if="thoughtDetailsData.context_bundle" title="上下文信息" name="context">
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
              <n-descriptions-item label="对话条数">{{ thoughtDetailsData.context_bundle.conversations?.length || 0 }}</n-descriptions-item>
              <n-descriptions-item label="记忆条数">{{ thoughtDetailsData.context_bundle.memories?.length || 0 }}</n-descriptions-item>
              <n-descriptions-item label="主导情绪">
                <n-tag :type="getEmotionTagType(thoughtDetailsData.context_bundle.emotion?.dominant)" size="small">
                  {{ emotionLabelCn(thoughtDetailsData.context_bundle.emotion?.dominant) }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="时间感知">{{ thoughtDetailsData.context_bundle.time_context?.time_display || "-" }}</n-descriptions-item>
            </n-descriptions>
          </n-collapse-item>

          <!-- LLM 调用详情 -->
          <n-collapse-item v-if="thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation" title="LLM 调用详情" name="llm">
            <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
              <n-descriptions-item label="模型">{{ (thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.model || "-" }}</n-descriptions-item>
              <n-descriptions-item label="耗时">{{ (thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.duration_ms || "-" }}ms</n-descriptions-item>
              <n-descriptions-item label="想联系用户">
                <n-tag :type="(thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.want_to_contact ? 'success' : 'default'" size="small">
                  {{ (thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.want_to_contact ? "是" : "否 (SKIP)" }}
                </n-tag>
              </n-descriptions-item>
            </n-descriptions>
            <n-collapse style="margin-bottom: 16px;">
              <n-collapse-item title="发送的提示词" name="prompt">
                <n-code :code="formatPrompt((thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.prompt_sent)" language="text" word-wrap />
              </n-collapse-item>
              <n-collapse-item title="LLM 返回内容" name="response">
                <n-code :code="(thoughtDetailsData.llm_call || thoughtDetailsData.thought_generation)?.response_received || '无'" language="text" word-wrap />
              </n-collapse-item>
            </n-collapse>
          </n-collapse-item>
        </n-collapse>
      </div>
      <n-empty v-else description="暂无详情数据" />
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { useMessage, NButton, NTag } from 'naive-ui'
import { HelpCircleOutline, CheckmarkCircle, CloseCircle } from '@vicons/ionicons5'
import api from '../api/active_consciousness'
import mainApi from '../api'

const message = useMessage()
const activeTab = ref('status')

// JSON 结构化格式化
const formatJson = (obj) => {
  if (!obj) return '（空）'
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
  if (typeof val === 'boolean') return val ? '是' : '否'
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
  active: { enabled: true, heartbeat_interval: 600, send_tag: '凯莉', time_format: '%H:%M', no_send_after_user_msg_minutes: 5, no_send_while_heat_above: 3.0, no_send_while_vibe_below: 0.15, cooldown_minutes: 30 },
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
    thought_generation: '你是凯莉，曹凡的 AI 朋友。你们认识很久了，你了解他的生活习惯、工作状态、兴趣爱好。\n\n{persona}\n\n【最近对话】\n{session_context}\n\n【你记得的事情】\n{hindsight_context}\n\n【现在】\n{time}\n{emotion_display}\n{weather_display}',
    thought_generation_instruction: '基于以上对话和你的记忆，想一个要对曹凡说的话。\n以"曹凡，"开头，直接说你想说的。\n注意：不要回复上面的对话内容，主动发起一个新的话题或想法。\n如果没想到什么，回复 SKIP。',
    emotion_evaluation: '你是凯莉，请评估当前的情绪状态。\n\n当前状态：\n- 时间：{time}\n- 想念分数：{longing_score}（等级：{longing_label}）\n- 聊天热度：{chat_heat}（标签：{chat_label}）\n- 沉默时长：{silence_minutes} 分钟\n\n最近的对话：\n{context}\n\n请评估你当前的情绪状态，返回 JSON 格式：\n{{\n  "valence": 0.0-1.0（情感效价，0=消极，1=积极），\n  "arousal": 0.0-1.0（唤醒度，0=平静，1=激动），\n  "social_need": 0.0-1.0（社交需求，0=不需要，1=非常想），\n  "dominant": "calm/content/happy/longing/missing/yearning/anxious/bored/concerned"\n}}\n\n只返回 JSON，不要解释。'
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
  heartbeat_count: 0,
  last_heartbeat_at: null,
  longing: { score: 0, level: 0, label: '平静', label_display: '平静（calm）', last_user_msg_at: null, last_self_msg_at: null, silence_minutes: 0 },
  chat_heat: { heat: 0, label: '冷清', label_display: '冷清（cold）', recent_count: 0, recent_hours: 0, recent_user_msg_at: null },
  emotional_intensity: { intensity: 0, label: '工作' },
  emotion_state: { valence: 0.5, arousal: 0.3, social_need: 0.3, dominant: 'calm', dominant_display: '平静（calm）', intensity: 0.367, updated_at: '' },
  today_sent_count: 0,
  hour_sent_count: 0,
  last_sent_at: null,
})

// 日志
const thoughts = ref({ total: 0, items: [] })
const heartbeats = ref({ total: 0, items: [] })
const thoughtsLoading = ref(false)
const heartbeatsLoading = ref(false)
const heartbeatDate = ref(Date.now())
const heartbeatIdFilter = ref(null)
const thoughtDate = ref(Date.now())
const thoughtIdFilter = ref(null)
const thoughtHeartbeatIdFilter = ref(null)
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

// 心跳健康状态：上次心跳在5分钟内=绿，否则红
const heartbeatHealthy = computed(() => {
  if (!status.value.last_heartbeat_at) return false
  const last = new Date(status.value.last_heartbeat_at)
  return (Date.now() - last.getTime()) < 5 * 60 * 1000
})

// 决策配置
const decisionConfig = computed(() => status.value.config?.decision || {
  send_threshold: 0.35,
  memory_threshold: 0.05,
  max_per_hour: 2,
  max_per_day: 5
})

// 聊天热度百分比（根据配置动态计算，允许超过100%）
const chatHeatPercentage = computed(() => {
  const heat = status.value.chat_heat?.heat || 0
  const maxHeat = status.value.config?.active?.no_send_while_heat_above || 3.0
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
  const sent = status.value.hour_sent_count || 0
  const max = decisionConfig.value.max_per_hour || 2
  return Math.min((sent / max) * 100, 100)
})

const frequencyDayPercentage = computed(() => {
  const sent = status.value.today_sent_count || 0
  const max = decisionConfig.value.max_per_day || 5
  return Math.min((sent / max) * 100, 100)
})

// 下次心跳显示
const nextHeartbeatDisplay = computed(() => {
  if (!status.value.last_heartbeat_at) return '未知'
  const last = new Date(status.value.last_heartbeat_at)
  const interval = (status.value.config?.active?.heartbeat_interval || 600) * 1000
  const next = new Date(last.getTime() + interval)
  const diff = next.getTime() - Date.now()
  if (diff <= 0) return '即将触发'
  const minutes = Math.floor(diff / 60000)
  const seconds = Math.floor((diff % 60000) / 1000)
  return `${minutes}分${seconds}秒`
})

// 保护机制状态
const isCoolingDown = computed(() => {
  if (!status.value.last_sent_at) return false
  const cooldown = (status.value.config?.active?.cooldown_minutes || 30) * 60 * 1000
  return (Date.now() - new Date(status.value.last_sent_at).getTime()) < cooldown
})

const userJustSent = computed(() => {
  if (!status.value.longing?.last_user_msg_at) return false
  const threshold = (status.value.config?.active?.no_send_after_user_msg_minutes || 5) * 60 * 1000
  return (Date.now() - new Date(status.value.longing.last_user_msg_at).getTime()) < threshold
})

const heatProtected = computed(() => {
  const heat = status.value.chat_heat?.heat || 0
  const maxHeat = status.value.config?.active?.no_send_while_heat_above || 3.0
  return heat >= maxHeat
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
  detailsTitle.value = `心跳日志 #${row.id} 详情`
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
    message.error('加载心跳详情失败')
    detailsData.value = null
  } finally {
    heartbeatDetailLoading.value = false
  }
}

async function showThoughtDetails(row) {
  thoughtDetailsTitle.value = `念头日志 #${row.id} 详情`
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
    message.error('加载念头详情失败')
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
    message.error('加载召回详情失败')
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
    message.error('加载念头详情失败')
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
    message.error('加载发送详情失败')
    sendDetailData.value = null
  } finally {
    sendDetailLoading.value = false
  }
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

// 情绪标签 → "中文（英文）" 格式
const EMOTION_LABEL_CN = {
  happy: '开心（happy）', content: '满足（content）', joy: '喜悦（joy）', calm: '平静（calm）', bored: '无聊（bored）',
  longing: '想念（longing）', missing: '思念（missing）', yearning: '渴望（yearning）', anxious: '焦虑（anxious）', concerned: '担忧（concerned）', worry: '忧虑（worry）',
  excited: '兴奋（excited）', energetic: '有活力（energetic）', sad: '悲伤（sad）', angry: '生气（angry）', neutral: '平静（neutral）'
}
function emotionLabelCn(dominant) {
  if (!dominant) return '-'
  return EMOTION_LABEL_CN[dominant.toLowerCase()] || dominant
}

// 念头类型 → "中文（英文）" 格式
const THOUGHT_TYPE_CN = {
  time: '时间（time）', silence: '沉默（silence）', assoc: '关联（assoc）',
  memory: '回忆（memory）', emotion: '情绪（emotion）', env: '环境（env）'
}
function thoughtTypeLabelCn(type) {
  if (!type) return '-'
  return THOUGHT_TYPE_CN[type] || type
}

// 决策类型 → "中文（英文）" 格式
const DECISION_TYPE_CN = {
  auto_send: '立即发送（auto_send）',
  skip: '跳过（skip）', memory: '存为记忆（memory）', pending: '待定（pending）',
  enhanced: '增强念头（enhanced）', gap_send: '间隔发送（gap_send）',
  idle_send: '空闲发送（idle_send）', long_idle_send: '长时空闲发送（long_idle_send）'
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
  if (details.message_sending?.success === true) return '已发送消息'
  if (details.message_sending?.success === false) return '发送失败'
  if (details.decision?.blocked_by_protection) return '被保护机制拦截'
  if (details.decision?.type === 'skip') return '跳过'
  if (details.decision?.type === 'memory') return '存为记忆'
  return '未知状态'
}

// "是否发送" 标签：读 message_sending.success（真实值），失败时显示具体原因
function getSendResultLabel(detail) {
  if (!detail) return '未知'
  if (detail.message_sending && typeof detail.message_sending.success === 'boolean') {
    if (detail.message_sending.success) return '✅ 已发送'
    return `❌ 发送失败`
  }
  // 兜底：旧字段 message_sent（active.db 列表）
  return detail.message_sent ? '✅ 已发送' : '未发送'
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
      || '未知错误'
}


// 念头结果标题
function getThoughtResultTitle(details) {
  // 优先：依据 type 判断（type=memory/silence/time 不会发送）
  const type = details.type || details.thought_type
  if (type === 'memory') return '存为记忆'
  if (type === 'silence') return '沉默念头'
  if (type === 'time') return '时间念头'
  // 否则：看 message_sending.success（真实发送结果）
  if (details.message_sending && typeof details.message_sending.success === 'boolean') {
    return details.message_sending.success ? '已发送消息' : '发送失败'
  }
  // 兜底：依 decision（auto_send/gap_send 等才是发送类）
  const sendDecisions = ['auto_send', 'gap_send', 'idle_send', 'long_idle_send']
  if (sendDecisions.includes(details.decision)) return '已发送消息'
  if (details.decision === 'memory') return '存为记忆'
  if (details.decision === 'skip') return '跳过'
  if (details.decision === 'enhanced') return '增强念头'
  return '未知状态'
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
    return details.decision.protection_reason || '保护机制拦截'
  }
  
  const type = details.decision?.type
  const score = details.decision?.score || 0
  
  if (type === 'skip') {
    return `分数 ${score.toFixed(2)} 未达到发送阈值`
  }
  if (type === 'memory') {
    return `分数 ${score.toFixed(2)} 存为记忆，不发送`
  }
  if (type === 'auto_send') {
    return `分数 ${score.toFixed(2)} 达到发送阈值`
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
  },
  { title: '时间', key: 'created_at', width: 160, render: (row) => formatTime(row.created_at) },
  { title: 'ID', key: 'id', width: 70 },
  { title: '心跳ID', key: 'heartbeat_id', width: 80, render(row) {
    if (!row.heartbeat_id) return '-'
    return h(NButton, { size: 'tiny', quaternary: true, type: 'info', onClick: () => {
      heartbeatIdFilter.value = row.heartbeat_id
      activeTab.value = 'heartbeat'
      loadHeartbeats(1)
    }}, { default: () => row.heartbeat_id })
  } },
  { title: '类型', key: 'type', width: 160, render: (row) => thoughtTypeLabelCn(row.type) },
  { title: '内容', key: 'content', ellipsis: { tooltip: true } },
  { title: '决策分数', key: 'score', width: 80, render: (row) => row.score != null ? Number(row.score).toFixed(3) : '' },
  { title: '决策', key: 'decision', width: 180, render: (row) => getDecisionLabelCn(row.decision) },
  { title: '结果', key: 'decision', width: 120, render(row) {
    if (row.decision === 'auto_send') return h(NTag, { type: 'success', size: 'small' }, { default: () => '✅ 已发送' })
    if (row.decision === 'memory') return h(NTag, { type: 'info', size: 'small' }, { default: () => '💾 已存记忆' })
    return h(NTag, { type: 'default', size: 'small' }, { default: () => '⏭️ 跳过' })
  } },
  { title: '来源', key: 'recall_source', width: 120 },
  { title: '存储 Hindsight', key: 'hindsight_stored', width: 110, render(row) {
    if (row.hindsight_stored === true || row.hindsight_stored === 1) {
      return h(NTag, { type: 'success', size: 'small' }, { default: () => '✅ 已存' })
    }
    if (row.hindsight_stored === false || row.hindsight_stored === 0) {
      return h(NTag, { type: 'default', size: 'small' }, { default: () => '未存' })
    }
    return '-'  // 历史 NULL 数据
  } },
]
// 格式化 prompt_sent（可能是字符串或 messages 数组）
const formatPrompt = (val) => {
  if (!val) return '无'
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

const heartbeatColumns = [
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
  },
  { title: 'ID', key: 'id', width: 70 },
  { title: '时间', key: 'created_at', width: 160, render: (row) => formatTime(row.created_at) },
  { title: '耗时(ms)', key: 'duration_ms', width: 80 },
  { title: '召回数量', key: 'recall_count', width: 80, render(row) { const v = row.recall_count || 0; return v ? h(NButton, { size: 'tiny', quaternary: true, type: 'info', onClick: () => showRecallDetail(row) }, { default: () => v }) : '0' } },
  { title: '生成念头', key: 'thoughts_generated', width: 80, render(row) { const v = row.thoughts_generated || 0; return v ? h(NButton, { size: 'tiny', quaternary: true, type: 'success', onClick: () => showThoughtContent(row) }, { default: () => v }) : '0' } },
  { title: '发送消息', key: 'message_sent', width: 100, render(row) {
    if (row.message_sent === true || row.message_sent === 1) {
      return h(NTag, { type: 'success', size: 'small' }, { default: () => '✅ 已发送' })
    }
    return h(NTag, { type: 'default', size: 'small' }, { default: () => '未发送' })
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
    message.error('加载念头日志失败')
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
    llmTestResult.value = result
  } catch (e) {
    message.error('LLM 测试失败')
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
    message.error('情绪评估 LLM 测试失败')
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
    message.error('念头生成 LLM 测试失败')
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
    message.error('测试失败')
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
    message.error('获取 Session 上下文失败')
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
    message.error('ContextCollector 测试失败')
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
    message.error('ThoughtEngine 测试失败')
    testResult.value = { success: false, error: e.message }
  } finally {
    testing.value.thoughtEngine = false
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
/* PC 端状态卡片等高对齐 */
@media (min-width: 769px) {
  .active-consciousness-page :deep(.n-grid-item > .n-card) {
    min-height: 120px;
    display: flex;
    flex-direction: column;
  }
  .active-consciousness-page :deep(.n-grid-item > .n-card .n-card__content) {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
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
  color: #999;
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
  :deep(.n-grid-item) {
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

