<template>
  <div class="active-consciousness-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 状态 -->
      <n-tab-pane name="status" tab="状态">
        <n-grid :cols="2" :x-gap="12" :y-gap="12" responsive="screen">
          <n-grid-item>
            <n-card title="心跳状态">
              <n-tooltip trigger="hover" :width="240">
                <template #trigger>
                  <n-icon size="14" style="cursor: help; color: #999; position: absolute; top: 12px; right: 12px;"><HelpCircleOutline /></n-icon>
                </template>
                <div style="line-height: 1.6;">
                  心跳调度器定期触发的状态。<br/>
                  🟢 绿灯：最近 5 分钟内有心跳<br/>
                  🔴 红灯：心跳超时
                </div>
              </n-tooltip>
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
              <n-tooltip trigger="hover" :width="260">
                <template #trigger>
                  <n-icon size="14" style="cursor: help; color: #999; position: absolute; top: 12px; right: 12px;"><HelpCircleOutline /></n-icon>
                </template>
                <div style="line-height: 1.6;">
                  基于用户最后一条消息的时间间隔计算。<br/>
                  <strong>公式：</strong>min(沉默分钟数 / 300, 1.0)<br/>
                  <strong>等级：</strong><br/>
                  平静(0) → 想念(0.1) → 思念(0.3) → 渴望(0.5) → 焦虑(0.7)
                </div>
              </n-tooltip>
              <n-statistic :value="status.longing.score" :precision="3">
                <template #suffix>
                  <n-tag :type="longingTagType" size="small">{{ status.longing.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="Number((status.longing.score * 100).toFixed(1))" :color="longingColor" style="margin-top: 8px" />
              <div style="margin-top: 4px; font-size: 11px; color: #999;">
                沉默时长：{{ status.longing.silence_minutes ? Math.round(status.longing.silence_minutes) + ' 分钟' : '-' }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="聊天热度">
              <n-tooltip trigger="hover" :width="260">
                <template #trigger>
                  <n-icon size="14" style="cursor: help; color: #999; position: absolute; top: 12px; right: 12px;"><HelpCircleOutline /></n-icon>
                </template>
                <div style="line-height: 1.6;">
                  最近 1 小时内用户消息的密度。<br/>
                  <strong>公式：</strong>消息数 / 小时数<br/>
                  <strong>等级：</strong><br/>
                  冷清(0) → 温暖(0.5) → 火热(1.0) → 沸腾(3.0)<br/>
                  热度越高，越不适合主动发消息。
                </div>
              </n-tooltip>
              <n-statistic :value="status.chat_heat.heat" :precision="2">
                <template #suffix>
                  <n-tag :type="heatTagType" size="small">{{ status.chat_heat.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="Math.min(status.chat_heat.heat * 20, 100)" :color="heatColor" style="margin-top: 8px" />
              <div style="margin-top: 4px; font-size: 11px; color: #999;">
                近1小时消息数：{{ status.chat_heat.recent_count || 0 }}
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="情绪值（强度）">
              <n-tooltip trigger="hover" :width="260">
                <template #trigger>
                  <n-icon size="14" style="cursor: help; color: #999; position: absolute; top: 12px; right: 12px;"><HelpCircleOutline /></n-icon>
                </template>
                <div style="line-height: 1.6;">
                  综合情绪强度，由 LLM 根据最近对话内容评估。<br/>
                  <strong>范围：</strong>0-1，越高表示对话越深入/情感化<br/>
                  <strong>标签：</strong><br/>
                  工作(0-0.3) → 日常(0.3-0.5) → 八卦(0.5-0.7) → 情感(0.7-0.9) → 深度情感(0.9+)
                </div>
              </n-tooltip>
              <n-statistic :value="status.emotional_intensity.intensity" :precision="3">
                <template #suffix>
                  <n-tag size="small">{{ status.emotional_intensity.label }}</n-tag>
                </template>
              </n-statistic>
              <n-progress :percentage="status.emotional_intensity.intensity * 100" :color="intensityColor" style="margin-top: 8px" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="情绪状态（VA 模型）">
              <n-tooltip trigger="hover" :width="280">
                <template #trigger>
                  <n-icon size="14" style="cursor: help; color: #999; position: absolute; top: 12px; right: 12px;"><HelpCircleOutline /></n-icon>
                </template>
                <div style="line-height: 1.6;">
                  <strong>VA 情绪模型：</strong><br/>
                  Valence（效价）= 情感正负性<br/>
                  0消极 → 1积极<br/><br/>
                  Arousal（唤醒度）= 情感激活程度<br/>
                  0平静 → 1激动<br/><br/>
                  Social Need（社交需求）= 想聊天的程度<br/><br/>
                  <strong>自然演化：</strong><br/>
                  唤醒度衰减 · 社交需求增长 · 效价回归中性
                </div>
              </n-tooltip>
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <n-tooltip trigger="hover" :width="200">
                    <template #trigger>
                      <span style="font-size: 13px; color: #666; cursor: help;">效价（Valence）</span>
                    </template>
                    <div style="line-height: 1.6;">
                      情感的正负性。<br/>
                      0 = 消极，1 = 积极<br/>
                      会随时间回归中性(0.5)。
                    </div>
                  </n-tooltip>
                  <span style="font-weight: 600;">{{ status.emotion_state?.valence ?? '-' }}</span>
                </div>
                <n-progress :percentage="(status.emotion_state?.valence ?? 0) * 100" :show-indicator="false" :height="6" />
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <n-tooltip trigger="hover" :width="200">
                    <template #trigger>
                      <span style="font-size: 13px; color: #666; cursor: help;">唤醒度（Arousal）</span>
                    </template>
                    <div style="line-height: 1.6;">
                      情感的激活程度。<br/>
                      0 = 平静，1 = 激动<br/>
                      越久没聊天会越平静（自然衰减）。
                    </div>
                  </n-tooltip>
                  <span style="font-weight: 600;">{{ status.emotion_state?.arousal ?? '-' }}</span>
                </div>
                <n-progress :percentage="(status.emotion_state?.arousal ?? 0) * 100" :show-indicator="false" :height="6" />
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <n-tooltip trigger="hover" :width="200">
                    <template #trigger>
                      <span style="font-size: 13px; color: #666; cursor: help;">社交需求（Social Need）</span>
                    </template>
                    <div style="line-height: 1.6;">
                      想要社交/聊天的程度。<br/>
                      0 = 不需要，1 = 非常想<br/>
                      越久没聊天会越想聊天（自然增长）。
                    </div>
                  </n-tooltip>
                  <span style="font-weight: 600;">{{ status.emotion_state?.social_need ?? '-' }}</span>
                </div>
                <n-progress :percentage="(status.emotion_state?.social_need ?? 0) * 100" :show-indicator="false" :height="6" />
                <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 4px;">
                  <span style="font-size: 13px; color: #666;">主导情绪</span>
                  <n-tag :type="getEmotionTagType(status.emotion_state?.dominant)" size="small">
                    {{ emotionLabelCn(status.emotion_state?.dominant) }}
                  </n-tag>
                </div>
              </div>
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card title="发送统计">
              <n-tooltip trigger="hover" :width="240">
                <template #trigger>
                  <n-icon size="14" style="cursor: help; color: #999; position: absolute; top: 12px; right: 12px;"><HelpCircleOutline /></n-icon>
                </template>
                <div style="line-height: 1.6;">
                  今日和本小时的主动消息发送数量。<br/>
                  受配置中的频率限制控制：<br/>
                  默认每小时最多 2 条，每天最多 5 条。
                </div>
              </n-tooltip>
              <div style="display: flex; flex-direction: column; gap: 12px;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <span style="font-size: 13px; color: #666;">今日发送</span>
                  <n-statistic :value="status.today_sent_count" style="font-size: 20px;" />
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <span style="font-size: 13px; color: #666;">本小时发送</span>
                  <n-statistic :value="status.hour_sent_count" style="font-size: 20px;" />
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <span style="font-size: 13px; color: #666;">延迟队列</span>
                  <n-statistic :value="status.delayed_count ?? 0" style="font-size: 20px;" />
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
              <n-button size="small" @click="heartbeatDate = Date.now(); loadHeartbeats(1)">今天</n-button>
              <n-button size="small" quaternary @click="heartbeatDate = null; loadHeartbeats(1)">全部</n-button>
            </div>
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100vw;">
              <n-data-table :columns="heartbeatColumns" :data="heartbeats.items" :pagination="heartbeatPagination" @update:page="loadHeartbeats" :scroll-x="960" remote />
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
              <n-data-table :columns="thoughtColumns" :data="thoughts.items" :pagination="thoughtPagination" @update:page="loadThoughts" :scroll-x="860" remote />
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

            <!-- Session 来源 -->
            <n-divider>Session 来源</n-divider>
            <n-form-item label="来源平台">
              <n-select v-model:value="config.session.sources" multiple :options="platformOptions" />
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

            <!-- 发送保护 -->
            <n-divider>发送保护</n-divider>
            <n-form-item label="禁止窗口（用户消息后分钟）">
              <n-input-number v-model:value="config.active.no_send_after_user_msg_minutes" :min="1" :max="60" />
            </n-form-item>
            <n-form-item label="热度阈值（高于此不发送）">
              <n-input-number v-model:value="config.active.no_send_while_heat_above" :min="0" :max="10" :step="0.1" />
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

            <!-- ThoughtEngine 引擎配置 -->
            <n-divider>🧠 ThoughtEngine 引擎</n-divider>
            <n-form-item label="启用 ThoughtEngine">
              <n-switch v-model:value="config.thought_engine.enabled" />
              <span class="form-item-hint">统一念头生成器：收集上下文 → 构建提示词 → LLM 生成 → 解析结果</span>
            </n-form-item>
            <template v-if="config.thought_engine.enabled">
              <n-form-item label="最大 Token 数">
                <n-input-number v-model:value="config.thought_engine.max_tokens" :min="100" :max="2000" />
                <span class="form-item-hint">LLM 生成念头的最大长度，越大越详细但越慢（推荐 200-500）</span>
              </n-form-item>
              <n-form-item label="Temperature">
                <n-input-number v-model:value="config.thought_engine.temperature" :min="0" :max="2" :step="0.1" />
                <span class="form-item-hint">控制念头生成的随机性，越高越随机（推荐 0.7-1.0）</span>
              </n-form-item>
            </template>

            <!-- 上下文收集配置 -->
            <n-divider>📦 上下文收集</n-divider>
            <n-form-item label="对话消息数量">
              <n-input-number v-model:value="config.context.conversation_limit" :min="10" :max="50" />
              <span class="form-item-hint">从 Session 中获取最近多少条对话消息作为上下文</span>
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

            <!-- 提示词配置 -->
            <n-divider>📝 提示词配置</n-divider>
            <n-collapse>
              <n-collapse-item title="念头生成提示词" name="thought_generation">
                <n-input v-model:value="config.prompts.thought_generation" type="textarea" :rows="8" placeholder="输入念头生成提示词模板" />
                <div style="margin-top: 4px; font-size: 11px; color: #999;">
                  可用变量：{persona} {session_context} {hindsight_context} {time} {emotion_display}
                </div>
              </n-collapse-item>
              <n-collapse-item title="情绪评估提示词" name="emotion_evaluation">
                <n-input v-model:value="config.prompts.emotion_evaluation" type="textarea" :rows="10" placeholder="输入情绪评估提示词模板" />
                <div style="margin-top: 4px; font-size: 11px; color: #999;">
                  可用变量：{time} {longing_score} {longing_label} {chat_heat} {chat_label} {silence_minutes} {context}
                </div>
              </n-collapse-item>
            </n-collapse>

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
                {{ thoughtTypeLabelCn(detailsData.thought_type) }}
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
                {{ thoughtTypeLabelCn(detailsData.message_sending.thought_type) }}
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
              {{ thoughtTypeLabelCn(thoughtDetailsData.thought_type) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="决策类型">
            <n-tag :type="getDecisionTagType(thoughtDetailsData.decision)" size="small">
              {{ getDecisionLabelCn(thoughtDetailsData.decision) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="决策分数">{{ thoughtDetailsData.score?.toFixed(3) }}</n-descriptions-item>
          <n-descriptions-item v-if="thoughtDetailsData.thought" label="念头内容" :span="2">
            {{ thoughtDetailsData.thought }}
          </n-descriptions-item>
        </n-descriptions>

        <!-- 情绪状态 -->
        <template v-if="thoughtDetailsData.emotion_state">
          <n-divider title-placement="left">情绪状态（VA 模型）</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="效价（Valence）">
              <n-tooltip trigger="hover">
                <template #trigger>
                  <span style="cursor: help;">{{ thoughtDetailsData.emotion_state.valence?.toFixed(3) }}</span>
                </template>
                情感的正负性。0=消极，1=积极。
              </n-tooltip>
            </n-descriptions-item>
            <n-descriptions-item label="唤醒度（Arousal）">
              <n-tooltip trigger="hover">
                <template #trigger>
                  <span style="cursor: help;">{{ thoughtDetailsData.emotion_state.arousal?.toFixed(3) }}</span>
                </template>
                情感的激活程度。0=平静，1=激动。
              </n-tooltip>
            </n-descriptions-item>
            <n-descriptions-item label="社交需求（Social Need）">
              <n-tooltip trigger="hover">
                <template #trigger>
                  <span style="cursor: help;">{{ thoughtDetailsData.emotion_state.social_need?.toFixed(3) }}</span>
                </template>
                想要社交/聊天的程度。0=不需要，1=非常想。
              </n-tooltip>
            </n-descriptions-item>
            <n-descriptions-item label="主导情绪（Dominant）">
              <n-tag :type="getEmotionTagType(thoughtDetailsData.emotion_state.dominant)" size="small">
                {{ emotionLabelCn(thoughtDetailsData.emotion_state.dominant) }}
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

        <!-- ThoughtEngine: 联系意愿 -->
        <template v-if="thoughtDetailsData.details_parsed?.thought_generation?.want_to_contact !== undefined">
          <n-divider title-placement="left">🧠 ThoughtEngine 结果</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="想联系用户">
              <n-tag :type="thoughtDetailsData.details_parsed.thought_generation.want_to_contact ? 'success' : 'default'" size="small">
                {{ thoughtDetailsData.details_parsed.thought_generation.want_to_contact ? '是' : '否 (SKIP)' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="LLM 是否 SKIP">
              <n-tag :type="thoughtDetailsData.details_parsed.thought_generation.is_skip ? 'warning' : 'success'" size="small">
                {{ thoughtDetailsData.details_parsed.thought_generation.is_skip ? 'SKIP' : '有念头' }}
              </n-tag>
            </n-descriptions-item>
          </n-descriptions>
        </template>

        <!-- ThoughtEngine: 上下文信息 -->
        <template v-if="thoughtDetailsData.details_parsed?.context_bundle">
          <n-divider title-placement="left">📦 上下文信息（Context Bundle）</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="对话条数">
              {{ thoughtDetailsData.details_parsed.context_bundle.conversations?.length || 0 }}
            </n-descriptions-item>
            <n-descriptions-item label="记忆条数">
              {{ thoughtDetailsData.details_parsed.context_bundle.memories?.length || 0 }}
            </n-descriptions-item>
            <n-descriptions-item label="主导情绪">
              <n-tag :type="getEmotionTagType(thoughtDetailsData.details_parsed.context_bundle.emotion?.dominant)" size="small">
                {{ emotionLabelCn(thoughtDetailsData.details_parsed.context_bundle.emotion?.dominant) }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="时间感知">
              {{ thoughtDetailsData.details_parsed.context_bundle.time_context?.time_display || '-' }}
            </n-descriptions-item>
            <n-descriptions-item label="天气" v-if="thoughtDetailsData.details_parsed.context_bundle.weather">
              {{ thoughtDetailsData.details_parsed.context_bundle.weather.weather || '-' }} {{ thoughtDetailsData.details_parsed.context_bundle.weather.temp || '' }}
            </n-descriptions-item>
          </n-descriptions>
          <n-collapse style="margin-bottom: 16px">
            <n-collapse-item title="对话详情" name="conversations" v-if="thoughtDetailsData.details_parsed.context_bundle.conversations?.length">
              <n-list bordered size="small">
                <n-list-item v-for="(msg, idx) in thoughtDetailsData.details_parsed.context_bundle.conversations" :key="idx">
                  <div style="font-size: 13px;">
                    <n-tag :type="msg.role === 'user' ? 'info' : 'success'" size="tiny">{{ msg.role }}</n-tag>
                    <span style="margin-left: 4px; font-size: 11px; color: #999;">{{ msg.time }}</span>
                    <div style="margin-top: 4px; white-space: pre-wrap;">{{ msg.content }}</div>
                  </div>
                </n-list-item>
              </n-list>
            </n-collapse-item>
            <n-collapse-item title="记忆内容" name="memories" v-if="thoughtDetailsData.details_parsed.context_bundle.memories?.length">
              <n-list bordered size="small">
                <n-list-item v-for="(mem, idx) in thoughtDetailsData.details_parsed.context_bundle.memories" :key="idx">
                  <div style="font-size: 13px; white-space: pre-wrap;">{{ mem }}</div>
                </n-list-item>
              </n-list>
            </n-collapse-item>
            <n-collapse-item title="用户习惯" name="user_habits" v-if="thoughtDetailsData.details_parsed.context_bundle.user_habits">
              <div style="font-size: 13px; white-space: pre-wrap;">{{ thoughtDetailsData.details_parsed.context_bundle.user_habits }}</div>
            </n-collapse-item>
          </n-collapse>
        </template>

        <!-- ThoughtEngine: LLM 调用详情 -->
        <template v-if="thoughtDetailsData.details_parsed?.thought_generation || thoughtDetailsData.details_parsed?.llm_call">
          <n-divider title-placement="left">🤖 LLM 调用详情</n-divider>
          <n-descriptions bordered :column="2" size="small" style="margin-bottom: 16px">
            <n-descriptions-item label="模型">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.model || '-' }}</n-descriptions-item>
            <n-descriptions-item label="Provider">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.provider || '-' }}</n-descriptions-item>
            <n-descriptions-item label="模式">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.mode || '-' }}</n-descriptions-item>
            <n-descriptions-item label="Temperature">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.temperature }}</n-descriptions-item>
            <n-descriptions-item label="Max Tokens">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.max_tokens }}</n-descriptions-item>
            <n-descriptions-item label="总耗时">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.duration_ms }}ms</n-descriptions-item>
            <n-descriptions-item label="Prompt Tokens">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.prompt_tokens ?? '-' }}</n-descriptions-item>
            <n-descriptions-item label="Completion Tokens">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.completion_tokens ?? '-' }}</n-descriptions-item>
            <n-descriptions-item label="Total Tokens">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.total_tokens ?? '-' }}</n-descriptions-item>
            <n-descriptions-item v-if="(thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.error" label="错误" :span="2">
              <span style="color: #d03050;">{{ (thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.error }}</span>
            </n-descriptions-item>
          </n-descriptions>
          <n-collapse style="margin-bottom: 16px">
            <n-collapse-item title="发送的提示词" name="prompt_sent" v-if="(thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.prompt_sent">
              <n-code :code="(thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.prompt_sent" language="text" word-wrap />
            </n-collapse-item>
            <n-collapse-item title="LLM 返回内容" name="response_received" v-if="(thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.response_received">
              <n-code :code="(thoughtDetailsData.details_parsed.thought_generation || thoughtDetailsData.details_parsed.llm_call)?.response_received" language="text" word-wrap />
            </n-collapse-item>
          </n-collapse>
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
import { HelpCircleOutline } from '@vicons/ionicons5'
import api from '../api/active_consciousness'
import mainApi from '../api'

const message = useMessage()
const activeTab = ref('status')

// 配置
const config = ref({
  enabled: false,
  llm: { mode: 'hermes', provider: 'openai', model: 'deepseek-chat', api_key: '', base_url: '' },
  active: { enabled: true, heartbeat_interval: 600, send_tag: '[凯莉主动发送]', time_format: '%H:%M', no_send_after_user_msg_minutes: 5, no_send_while_heat_above: 1.0, no_send_while_vibe_below: 0.15, cooldown_minutes: 30 },
  session: { sources: ['weixin'], max_messages_per_session: 15, filter_tool_messages: true },
  decision: { send_threshold: 0.35, delay_threshold: 0.15, memory_threshold: 0.05, max_per_hour: 2, max_per_day: 5, longing_gap_threshold: 3 },
  thought: { retain_enabled: false, retain_threshold: 0.5 },
  thought_engine: {
    enabled: true,
    max_tokens: 300,
    temperature: 0.9
  },
  context: {
    conversation_limit: 30,
    memory_limit: 5,
    weather_enabled: false
  },
  hindsight: { enabled: true, base_url: 'http://localhost:8888', bank_id: 'hermes', store: { bank_id: 'hermes-active' }, recall_limit: 5, reflect_enabled: true, timeout: 30 },
  notify: { platform: 'weixin', chat_id: '' },
  prompts: {
    thought_generation: '你是凯莉，曹凡的 AI 朋友。你们认识很久了，你了解他的生活习惯、工作状态、兴趣爱好。\n\n{persona}\n\n【最近对话】\n{session_context}\n\n【你记得的事情】\n{hindsight_context}\n\n【现在】\n{time}\n{emotion_display}\n\n想到曹凡了吗？如果你想联系他，说你想说什么。\n如果没想到，回复 \'SKIP\'。\n直接说，不要解释。',
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
  delayed_count: 0
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
  auto_send: '立即发送（auto_send）', delay_send: '延迟发送（delay_send）',
  skip: '跳过（skip）', memory: '存为记忆（memory）', pending: '待定（pending）'
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
  { title: '类型', key: 'type', width: 120, render: (row) => thoughtTypeLabelCn(row.type) },
  { title: '内容', key: 'content', ellipsis: { tooltip: true } },
  { title: '强度', key: 'intensity', width: 80, render: (row) => row.intensity != null ? Number(row.intensity).toFixed(2) : '' },
  { title: '决策', key: 'decision', width: 130, render: (row) => getDecisionLabelCn(row.decision) },
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
    // 更新分页配置
    thoughtPagination.value = {
      ...thoughtPagination.value,
      page: page,
      pageCount: Math.ceil((data.total || 0) / 10)
    }
  } catch (e) {
    message.error('加载念头日志失败')
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
    const data = await api.getHeartbeats(page, dateParam)
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

/* 表单项提示文字 */
.form-item-hint {
  margin-left: 8px;
  font-size: 12px;
  color: #999;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .active-consciousness-page {
    padding: 0 4px;
  }

  /* 状态卡片：单列布局 */
  :deep(.n-grid) {
    grid-template-columns: 1fr !important;
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

