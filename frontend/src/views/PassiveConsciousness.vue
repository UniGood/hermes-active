<template>
  <div class="passive-consciousness-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 配置 -->
      <n-tab-pane name="config" tab="配置">
        <n-card title="💡 被动意识配置" style="margin-bottom: 16px">
          <!-- 总开关 -->
          <n-form-item label="启用被动意识">
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

            <!-- 被动意识配置 -->
            <n-divider>注入配置</n-divider>
            <n-form-item label="启用注入">
              <n-switch v-model:value="config.passive.enabled" />
            </n-form-item>
            <n-form-item label="注入情绪">
              <n-switch v-model:value="config.passive.inject_emotion" />
            </n-form-item>
            <n-form-item label="注入热度">
              <n-switch v-model:value="config.passive.inject_heat" />
            </n-form-item>
            <n-form-item label="注入记忆">
              <n-switch v-model:value="config.passive.inject_memory" />
            </n-form-item>
            <n-form-item label="注入想法">
              <n-switch v-model:value="config.passive.inject_thought" />
            </n-form-item>
            <n-form-item label="注入标记">
              <n-input v-model:value="config.passive.inject_tag" placeholder="[CONSCIOUSNESS_CONTEXT]" />
            </n-form-item>
            <n-form-item label="时间格式">
              <n-input v-model:value="config.passive.time_format" placeholder="%H:%M" />
            </n-form-item>
            <n-form-item label="想法最大字符">
              <n-input-number v-model:value="config.passive.thought_max_chars" :min="50" :max="500" />
            </n-form-item>
            <n-form-item label="Vibe 最大字符">
              <n-input-number v-model:value="config.passive.vibe_max_chars" :min="20" :max="200" />
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

            <!-- Hindsight -->
            <n-divider>Hindsight 记忆</n-divider>
            <n-form-item label="启用 Hindsight">
              <n-switch v-model:value="config.hindsight.enabled" />
            </n-form-item>
            <n-form-item label="Recall 结果数">
              <n-input-number v-model:value="config.hindsight.recall_limit" :min="1" :max="20" />
            </n-form-item>
            <n-form-item label="启用 Reflect">
              <n-switch v-model:value="config.hindsight.reflect_enabled" />
            </n-form-item>

            <!-- 天气感知 -->
            <n-divider>天气感知（高德 API）</n-divider>
            <n-form-item label="启用天气感知">
              <n-switch v-model:value="config.weather.enabled" />
            </n-form-item>
            <n-form-item label="城市编码">
              <n-input v-model:value="config.weather.adcode" placeholder="370100" />
            </n-form-item>
            <n-form-item label="高德 API Key">
              <n-input v-model:value="config.weather.amap_key" type="password" show-password-on="mousedown" placeholder="输入高德 API Key" />
            </n-form-item>
            <n-form-item label="缓存时长（秒）">
              <n-input-number v-model:value="config.weather.cache_ttl" :min="60" :max="3600" />
            </n-form-item>
          </template>

          <n-button type="primary" @click="saveConfig" :loading="saving" style="margin-top: 16px">
            保存配置
          </n-button>
        </n-card>
      </n-tab-pane>

      <!-- Tab 2: 状态 -->
      <n-tab-pane name="status" tab="状态">
        <n-grid :cols="3" :x-gap="12" :y-gap="12">
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
        </n-grid>
      </n-tab-pane>

      <!-- Tab 3: 聊天记录 -->
      <n-tab-pane name="chat" tab="聊天记录">
        <n-list bordered>
          <n-list-item v-for="msg in chats.items" :key="msg.id">
            <div :class="['chat-msg', msg.role === 'user' ? 'user-msg' : 'assistant-msg']">
              <div class="msg-header">
                <n-tag :type="msg.role === 'user' ? 'info' : 'warning'" size="small">
                  {{ msg.role === 'user' ? '用户' : '凯莉' }}
                </n-tag>
                <span class="msg-time">{{ msg.timestamp }}</span>
              </div>
              <div class="msg-content">{{ msg.content }}</div>
            </div>
          </n-list-item>
        </n-list>
      </n-tab-pane>

      <!-- Tab 4: 测试 -->
      <n-tab-pane name="test" tab="测试">
        <!-- 一键全量测试 -->
        <n-card title="🚀 一键全量测试" style="margin-bottom: 16px">
          <n-space vertical>
            <n-button
              type="primary"
              size="large"
              @click="runFullTest"
              :loading="testing.full"
              block
            >
              运行全量测试
            </n-button>
            <template v-if="fullTestResult">
              <n-alert
                :type="fullTestResult.failed === 0 ? 'success' : 'warning'"
                :title="`测试完成：${fullTestResult.success}/${fullTestResult.total} 项成功`"
                style="margin-top: 8px"
              >
                <template v-if="fullTestResult.failed > 0">
                  失败项：
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
            <n-card title="💕 想念分数" size="small">
              <n-button @click="runTest('longing')" :loading="testing.longing" size="small" style="margin-bottom: 12px">
                测试
              </n-button>
              <n-alert v-if="testResults.longing?.error" type="error" style="margin-bottom: 8px">
                {{ testResults.longing.error }}
              </n-alert>
              <n-descriptions v-if="testResults.longing?.data" :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item label="分数">{{ testResults.longing.data.score }}</n-descriptions-item>
                <n-descriptions-item label="等级">{{ testResults.longing.data.level }} ({{ testResults.longing.data.label }})</n-descriptions-item>
                <n-descriptions-item label="间隔分钟">{{ testResults.longing.data.gap_minutes }}</n-descriptions-item>
                <n-descriptions-item label="最近消息">{{ testResults.longing.data.last_user_msg_at || '无' }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-grid-item>

          <!-- 🔥 聊天热度 -->
          <n-grid-item>
            <n-card title="🔥 聊天热度" size="small">
              <n-button @click="runTest('chatHeat')" :loading="testing.chatHeat" size="small" style="margin-bottom: 12px">
                测试
              </n-button>
              <n-alert v-if="testResults.chatHeat?.error" type="error" style="margin-bottom: 8px">
                {{ testResults.chatHeat.error }}
              </n-alert>
              <n-descriptions v-if="testResults.chatHeat?.data" :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item label="热度">{{ testResults.chatHeat.data.heat }}</n-descriptions-item>
                <n-descriptions-item label="等级">{{ testResults.chatHeat.data.label }}</n-descriptions-item>
                <n-descriptions-item label="近1小时消息数">{{ testResults.chatHeat.data.recent_count }}</n-descriptions-item>
                <n-descriptions-item label="最近消息">{{ testResults.chatHeat.data.recent_msg_at || '无' }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-grid-item>

          <!-- 🎭 情绪值 -->
          <n-grid-item>
            <n-card title="🎭 情绪值" size="small">
              <n-button @click="runTest('emotionalIntensity')" :loading="testing.emotionalIntensity" size="small" style="margin-bottom: 12px">
                测试
              </n-button>
              <n-alert v-if="testResults.emotionalIntensity?.error" type="error" style="margin-bottom: 8px">
                {{ testResults.emotionalIntensity.error }}
              </n-alert>
              <n-descriptions v-if="testResults.emotionalIntensity?.data" :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item label="强度">{{ testResults.emotionalIntensity.data.intensity }}</n-descriptions-item>
                <n-descriptions-item label="标签">{{ testResults.emotionalIntensity.data.label }}</n-descriptions-item>
                <n-descriptions-item label="原始值">{{ testResults.emotionalIntensity.data.raw_value || '未设置' }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-grid-item>

          <!-- 🌤 天气感知 -->
          <n-grid-item>
            <n-card title="🌤 天气感知（高德 API）" size="small">
              <n-button @click="runTest('weather')" :loading="testing.weather" size="small" style="margin-bottom: 12px">
                测试
              </n-button>
              <n-alert v-if="testResults.weather?.error" type="error" style="margin-bottom: 8px">
                {{ testResults.weather.error }}
              </n-alert>
              <n-descriptions v-if="testResults.weather?.data" :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item label="城市">{{ testResults.weather.data.city }}</n-descriptions-item>
                <n-descriptions-item label="天气">{{ testResults.weather.data.weather }}</n-descriptions-item>
                <n-descriptions-item label="温度">{{ testResults.weather.data.temperature }}°C</n-descriptions-item>
                <n-descriptions-item label="湿度">{{ testResults.weather.data.humidity }}%</n-descriptions-item>
                <n-descriptions-item label="风向">{{ testResults.weather.data.winddirection }}</n-descriptions-item>
                <n-descriptions-item label="更新时间">{{ testResults.weather.data.reporttime }}</n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-grid-item>

          <!-- 📖 Hindsight 记忆 -->
          <n-grid-item>
            <n-card title="📖 Hindsight 记忆" size="small">
              <n-space style="margin-bottom: 12px">
                <n-button @click="runTest('hindsightRecall')" :loading="testing.hindsightRecall" size="small">
                  Recall 测试
                </n-button>
                <n-button @click="runTest('hindsightReflect')" :loading="testing.hindsightReflect" size="small">
                  Reflect 测试
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
                  <n-descriptions-item label="Recall 结果数">{{ testResults.hindsightRecall.data.count }}</n-descriptions-item>
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
                <n-card title="Reflect 结果" size="small" style="margin-top: 8px">
                  <n-text>{{ testResults.hindsightReflect.data.reflection }}</n-text>
                </n-card>
              </template>
            </n-card>
          </n-grid-item>

          <!-- 📋 完整上下文预览 -->
          <n-grid-item :span="2">
            <n-card title="📋 完整上下文预览" size="small">
              <n-button
                type="primary"
                @click="runContextTest"
                :loading="testing.context"
                style="margin-bottom: 12px"
              >
                模拟完整流程
              </n-button>

              <template v-if="contextResult">
                <!-- 步骤状态 -->
                <n-card title="执行步骤" size="small" style="margin-bottom: 12px">
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
                  title="部分步骤失败"
                  style="margin-bottom: 12px"
                >
                  <n-list size="small">
                    <n-list-item v-for="(err, i) in contextResult.errors" :key="i">
                      <n-text type="error">{{ err }}</n-text>
                    </n-list-item>
                  </n-list>
                </n-alert>

                <!-- 最终上下文 -->
                <n-card title="注入上下文" size="small">
                  <n-code
                    :code="contextResult.context || '（空）'"
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
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import api from '../api/passive_consciousness'

const message = useMessage()
const activeTab = ref('config')

// 配置
const config = ref({
  enabled: false,
  llm: { mode: 'hermes', provider: 'openai', model: 'deepseek-chat', api_key: '', base_url: '' },
  passive: { enabled: true, inject_emotion: true, inject_heat: true, inject_memory: true, inject_thought: true, thought_max_chars: 200, vibe_max_chars: 50, inject_tag: '[CONSCIOUSNESS_CONTEXT]', time_format: '%H:%M' },
  session: { sources: ['weixin'], time_range_hours: 24, max_messages_per_session: 15, filter_tool_messages: true },
  hindsight: { enabled: true, recall_limit: 5, reflect_enabled: true },
  weather: { enabled: false, adcode: '370100', amap_key: '', cache_ttl: 600 }
})

// 状态
const status = ref({
  enabled: false,
  longing: { score: 0, level: 0, label: 'calm', last_user_msg_at: null, last_self_msg_at: null },
  chat_heat: { heat: 0, label: 'cold', recent_count: 0, recent_hours: 0, recent_user_msg_at: null },
  emotional_intensity: { intensity: 0, label: '工作' }
})

// 聊天记录
const chats = ref({ total: 0, items: [] })

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
const loadChats = async () => {
  try {
    const data = await api.getChats()
    chats.value = data
  } catch (e) {
    message.error('加载聊天记录失败')
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

// 单项测试 API 映射
const testApiMap = {
  longing: () => api.testLonging(),
  chatHeat: () => api.testChatHeat(),
  emotionalIntensity: () => api.testEmotionalIntensity(),
  weather: () => api.testWeather(),
  hindsightRecall: () => api.testHindsightRecall(),
  hindsightReflect: () => api.testHindsightReflect(),
}

// 运行单项测试
const runTest = async (name) => {
  testing.value[name] = true
  try {
    const resp = await testApiMap[name]()
    testResults.value[name] = resp
    if (resp?.success) {
      message.success(`${name} 测试成功`)
    } else {
      message.warning(`${name} 测试返回: ${resp?.error || '未知'}`)
    }
  } catch (e) {
    testResults.value[name] = { success: false, error: e.message || String(e) }
    message.error(`${name} 测试失败: ${e.message}`)
  } finally {
    testing.value[name] = false
  }
}

// 运行全量测试
const runFullTest = async () => {
  testing.value.full = true
  try {
    const resp = await api.testFull()
    fullTestResult.value = resp
    if (resp?.failed === 0) {
      message.success(`全量测试通过：${resp.success}/${resp.total}`)
    } else {
      message.warning(`全量测试：${resp?.success}/${resp?.total} 项成功`)
    }
  } catch (e) {
    message.error(`全量测试失败: ${e.message}`)
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
      message.success(`上下文拼装完成：${okCount}/${totalSteps} 步骤成功`)
    } else {
      message.warning(`上下文拼装：${okCount}/${totalSteps} 步骤成功，${resp?.errors?.length} 个错误`)
    }
  } catch (e) {
    message.error(`上下文测试失败: ${e.message}`)
  } finally {
    testing.value.context = false
  }
}

// 初始化
onMounted(async () => {
  await Promise.all([
    loadConfig(),
    loadStatus(),
    loadChats()
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
  background: #e3f2fd;
  margin-left: 20%;
}

.assistant-msg {
  background: #fff3e0;
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
  color: #666;
}

.msg-content {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
