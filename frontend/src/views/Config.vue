<template>
  <div class="config-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 基础配置 -->
      <n-tab-pane name="basic" :tab="t('config.tabs.basic')">
        <!-- 个性化设置 -->
        <n-card :title="t('config.personalization.title')" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="100">
            <n-form-item :label="t('config.personalization.userName')">
              <n-input v-model:value="userConfig.user_name" placeholder="曹凡" />
            </n-form-item>
            <n-form-item :label="t('config.personalization.assistantName')">
              <n-input v-model:value="userConfig.assistant_name" placeholder="凯莉" />
            </n-form-item>
            <n-form-item>
              <div class="form-actions">
                <n-button type="primary" @click="saveUserConfig" :loading="savingUserConfig">{{ t('common.common.save') }}</n-button>
              </div>
            </n-form-item>
          </n-form>
        </n-card>

        <!-- 语言设置 -->
        <n-card :title="t('config.language.title')" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="100">
            <n-form-item :label="t('config.language.label')">
              <n-select
                v-model:value="currentLocale"
                :options="localeOptions"
                @update:value="changeLocale"
              />
            </n-form-item>
          </n-form>
        </n-card>

        <!-- 主题配置 -->
        <n-card :title="t('config.theme.title')" style="margin-bottom: 16px">
          <div class="theme-list">
            <div
              v-for="th in themes" :key="th.id"
              class="theme-item"
              :class="{ active: currentTheme === th.id }"
              @click="selectTheme(th.id)"
            >
              <div class="theme-preview">
                <div class="theme-color" :style="{ background: th.color1 }"></div>
                <div class="theme-color" :style="{ background: th.color2 }"></div>
              </div>
              <div class="theme-info">
                <div class="theme-name">{{ th.name }}</div>
                <div class="theme-desc">{{ th.desc }}</div>
              </div>
              <n-tag v-if="currentTheme === th.id" type="success" size="small">{{ t('config.theme.current') }}</n-tag>
            </div>
          </div>
        </n-card>

        <!-- 修改密码 -->
        <n-card :title="t('config.password.title')" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="80">
            <n-form-item :label="t('config.password.oldPassword')">
              <n-input v-model:value="passwordForm.old_password" type="password" show-password-on="click" />
            </n-form-item>
            <n-form-item :label="t('config.password.newPassword')">
              <n-input v-model:value="passwordForm.new_password" type="password" show-password-on="click" />
            </n-form-item>
            <n-form-item>
              <div class="form-actions">
                <n-button type="warning" @click="changePassword" :loading="changingPassword">{{ t('config.password.submit') }}</n-button>
              </div>
            </n-form-item>
          </n-form>
        </n-card>
      </n-tab-pane>

      <!-- Tab 2: LLM 配置 -->
      <n-tab-pane name="llm" :tab="t('config.tabs.llm')">
        <n-card :title="t('config.llm.title')" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="80">
            <n-form-item :label="t('config.llm.mode')">
              <n-radio-group v-model:value="llmConfig.mode">
                <n-radio value="hermes">{{ t('config.llm.hermes') }}</n-radio>
                <n-radio value="custom">{{ t('config.llm.custom') }}</n-radio>
              </n-radio-group>
            </n-form-item>

            <template v-if="llmConfig.mode === 'custom'">
              <n-form-item :label="t('config.llm.provider')">
                <n-input v-model:value="llmConfig.provider" placeholder="openai" />
              </n-form-item>
              <n-form-item :label="t('config.llm.model')">
                <n-input v-model:value="llmConfig.model" placeholder="gpt-4" />
              </n-form-item>
              <n-form-item :label="t('config.llm.apiKey')">
                <n-input v-model:value="llmConfig.api_key" placeholder="API Key" />
              </n-form-item>
              <n-form-item :label="t('config.llm.baseUrl')">
                <n-input v-model:value="llmConfig.base_url" placeholder="https://api.openai.com/v1" />
              </n-form-item>
            </template>

            <n-form-item>
              <div class="form-actions">
                <n-space>
                  <n-button type="primary" @click="saveLLMConfig" :loading="saving">{{ t('common.common.save') }}</n-button>
                  <n-button @click="testLLM" :loading="testing" v-if="llmConfig.mode === 'custom'">{{ t('common.common.test') }}</n-button>
                </n-space>
              </div>
            </n-form-item>
          </n-form>
        </n-card>
      </n-tab-pane>

      <!-- Tab 3: Hindsight 配置 -->
      <n-tab-pane name="hindsight" :tab="t('config.tabs.hindsight')">
        <n-card :title="t('config.hindsight.title')" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="100">
            <n-form-item :label="t('config.hindsight.enable')">
              <n-switch v-model:value="hindsightConfig.enabled" />
            </n-form-item>

            <template v-if="hindsightConfig.enabled">
              <n-form-item :label="t('config.hindsight.baseUrl')">
                <n-input v-model:value="hindsightConfig.base_url" placeholder="http://localhost:8888" />
              </n-form-item>
              <n-form-item :label="t('config.hindsight.bankId')">
                <n-input v-model:value="hindsightConfig.bank_id" placeholder="hermes" />
              </n-form-item>
              <n-form-item :label="t('config.hindsight.recallLimit')">
                <n-input-number v-model:value="hindsightConfig.recall_limit" :min="1" :max="20" />
              </n-form-item>
              <n-form-item :label="t('config.hindsight.enableReflect')">
                <n-switch v-model:value="hindsightConfig.reflect_enabled" />
              </n-form-item>
              <n-form-item :label="t('config.hindsight.timeout')">
                <n-input-number v-model:value="hindsightConfig.timeout" :min="5" :max="300" />
              </n-form-item>
            </template>

            <n-form-item>
              <div class="form-actions">
                <n-space>
                  <n-button type="primary" @click="saveHindsightConfig" :loading="savingHindsight">{{ t('common.common.save') }}</n-button>
                  <n-button @click="testHindsightRecall" :loading="testingRecall">{{ t('config.hindsight.testRecall') }}</n-button>
                  <n-button @click="testHindsightReflect" :loading="testingReflect" v-if="hindsightConfig.reflect_enabled">{{ t('config.hindsight.testReflect') }}</n-button>
                </n-space>
              </div>
            </n-form-item>
          </n-form>
        </n-card>
      </n-tab-pane>

      <!-- Tab 4: 天气配置 -->
      <n-tab-pane name="weather" :tab="t('config.tabs.weather')">
        <n-card :title="t('config.weather.title')" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="120">
            <n-form-item :label="t('config.weather.enable')">
              <n-switch v-model:value="weatherConfig.enabled" />
            </n-form-item>

            <template v-if="weatherConfig.enabled">
              <n-form-item :label="t('config.weather.provider')">
                <n-radio-group v-model:value="weatherConfig.provider">
                  <n-radio value="qweather">{{ t('config.weather.qweather') }}</n-radio>
                  <n-radio value="amap">{{ t('config.weather.amap') }}</n-radio>
                </n-radio-group>
              </n-form-item>

              <n-form-item :label="t('config.weather.city')">
                <n-input
                  v-model:value="weatherConfig.city"
                  :placeholder="t('config.weather.cityPlaceholder')"
                />
                <span style="margin-left: 8px; font-size: 12px; color: #999;">
                  {{ t('config.weather.cityHint') }}
                </span>
              </n-form-item>

              <n-form-item :label="t('config.weather.cacheHours')">
                <n-input-number
                  v-model:value="weatherConfig.cache_hours"
                  :min="1" :max="24" :step="1"
                />
              </n-form-item>

              <!-- 高德地图配置 -->
              <template v-if="weatherConfig.provider === 'amap'">
                <n-divider>{{ t('config.weather.amapConfig') }}</n-divider>
                <n-form-item :label="t('config.weather.amapKey')">
                  <n-input
                    v-model:value="weatherConfig.amap_key"
                    placeholder="API Key"
                    show-password-on="click"
                    type="password"
                  />
                </n-form-item>
                <n-form-item :label="t('config.weather.adcode')">
                  <n-input
                    v-model:value="weatherConfig.adcode"
                    :placeholder="t('config.weather.adcodePlaceholder')"
                  />
                  <span style="margin-left: 8px; font-size: 12px; color: #999;">
                    {{ t('config.weather.adcodeHint') }}
                  </span>
                </n-form-item>
              </template>

              <!-- 和风天气配置 -->
              <template v-if="weatherConfig.provider === 'qweather'">
                <n-divider>{{ t('config.weather.qweatherConfig') }}</n-divider>
                <n-form-item :label="t('config.weather.qweatherKey')">
                  <n-input
                    v-model:value="weatherConfig.qweather_key"
                    placeholder="API Key"
                    show-password-on="click"
                    type="password"
                  />
                </n-form-item>
                <n-form-item :label="t('config.weather.geoApiUrl')">
                  <n-input
                    v-model:value="weatherConfig.qweather_geo_url"
                    placeholder="https://geoapi.qweather.com/v2/city/lookup"
                  />
                  <span style="margin-left: 8px; font-size: 12px; color: #999;">
                    {{ t('config.weather.geoApiHint') }}
                  </span>
                </n-form-item>
                <n-form-item :label="t('config.weather.weatherApiUrl')">
                  <n-input
                    v-model:value="weatherConfig.qweather_weather_url"
                    placeholder="https://devapi.qweather.com/v7/weather/now"
                  />
                  <span style="margin-left: 8px; font-size: 12px; color: #999;">
                    {{ t('config.weather.weatherApiHint') }}
                  </span>
                </n-form-item>
              </template>
            </template>

            <n-form-item>
              <div class="form-actions">
                <n-space>
                  <n-button type="primary" @click="saveWeatherConfig" :loading="savingWeather">{{ t('common.common.save') }}</n-button>
                  <n-button @click="testWeather" :loading="testingWeather">{{ t('common.common.test') }}</n-button>
                </n-space>
              </div>
            </n-form-item>
          </n-form>
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useConfig } from '../composables/useConfig'

// 从 App.vue 注入的主题函数
const applyTheme = inject('applyTheme')

const { t, locale } = useI18n()
const message = useMessage()
const activeTab = ref('basic')
const saving = ref(false)
const testing = ref(false)
const changingPassword = ref(false)
const savingUserConfig = ref(false)
const savingHindsight = ref(false)
const testingRecall = ref(false)
const testingReflect = ref(false)
const savingWeather = ref(false)
const testingWeather = ref(false)
const { config: globalConfig, loadConfig: loadGlobalConfig } = useConfig()

// 语言配置
const currentLocale = ref(locale.value)
const localeOptions = computed(() => [
  { label: t('config.language.zhCN'), value: 'zh-CN' },
  { label: t('config.language.enUS'), value: 'en-US' }
])

async function changeLocale(newLocale) {
  locale.value = newLocale
  currentLocale.value = newLocale
  localStorage.setItem('locale', newLocale)
  globalConfig.value.locale = newLocale
  try {
    await api.put('/config/set', null, { params: { key: 'locale', value: newLocale } })
    message.success(t('common.common.success'))
  } catch (e) {
    message.error(t('config.saveFailed'))
  }
}

const userConfig = ref({
  user_name: '曹凡',
  assistant_name: '凯莉'
})

const llmConfig = ref({
  mode: 'hermes',
  provider: '',
  model: '',
  api_key: '',
  base_url: ''
})

const hindsightConfig = ref({
  enabled: true,
  base_url: 'http://localhost:8888',
  bank_id: 'hermes',
  recall_limit: 5,
  reflect_enabled: true,
  timeout: 120
})

const weatherConfig = ref({
  enabled: false,
  provider: 'qweather',
  city: '北京',
  cache_hours: 4,
  amap_key: '',
  adcode: '370100',
  cache_ttl: 3600,
  temp_change_threshold: 5.0,
  qweather_key: '',
  qweather_geo_url: 'https://geoapi.qweather.com/v2/city/lookup',
  qweather_weather_url: 'https://devapi.qweather.com/v7/weather/now'
})

const passwordForm = ref({
  old_password: '',
  new_password: ''
})

// 主题配置
const themes = [
  { id: 'kelly', name: '凯莉', desc: '珊瑚粉 + 暖橙', color1: '#ff9a9e', color2: '#f6d365' },
  { id: 'elegant', name: '素雅', desc: '亮蓝 + 浅灰', color1: '#4a90d9', color2: '#e8eef5' }
]
const currentTheme = ref('kelly')

async function loadConfig() {
  try {
    const data = await api.get('/config/llm')
    llmConfig.value = data
  } catch (e) {
    console.error('加载 LLM 配置失败:', e)
  }
}

async function loadHindsightConfig() {
  try {
    const data = await api.get('/config/hindsight')
    if (data && typeof data === 'object' && Object.keys(data).length > 0) {
      hindsightConfig.value = { ...hindsightConfig.value, ...data }
    }
  } catch (e) {
    // 使用默认值
  }
}

async function saveHindsightConfig() {
  savingHindsight.value = true
  try {
    await api.put('/config/hindsight', hindsightConfig.value)
    message.success(t('config.hindsight.saveSuccess'))
  } catch (e) {
    message.error(t('config.saveFailed'))
  } finally {
    savingHindsight.value = false
  }
}

async function testHindsightRecall() {
  testingRecall.value = true
  try {
    const result = await api.post('/hindsight/recall?query=测试recall&limit=3')
    if (result.success) {
      message.success(t('config.hindsight.recallSuccess', { count: result.total }))
    } else {
      message.error(t('config.hindsight.testFailed'))
    }
  } catch (e) {
    message.error(t('config.hindsight.testFailed'))
  } finally {
    testingRecall.value = false
  }
}

async function testHindsightReflect() {
  testingReflect.value = true
  try {
    const result = await api.post('/hindsight/reflect?query=测试reflect')
    if (result.success) {
      message.success(t('config.hindsight.reflectSuccess'))
    } else {
      message.error(t('config.hindsight.testFailed'))
    }
  } catch (e) {
    message.error(t('config.hindsight.testFailed'))
  } finally {
    testingReflect.value = false
  }
}

async function loadUserConfig() {
  try {
    const userName = await api.get('/config/get/user_name').catch(() => null)
    const assistantName = await api.get('/config/get/assistant_name').catch(() => null)
    if (userName?.value) userConfig.value.user_name = userName.value
    if (assistantName?.value) userConfig.value.assistant_name = assistantName.value
  } catch (e) {
    // 使用默认值
  }
}

async function saveUserConfig() {
  savingUserConfig.value = true
  try {
    await api.put('/config/set', null, { params: { key: 'user_name', value: userConfig.value.user_name } })
    await api.put('/config/set', null, { params: { key: 'assistant_name', value: userConfig.value.assistant_name } })
    // 更新全局配置
    globalConfig.value.user_name = userConfig.value.user_name
    globalConfig.value.assistant_name = userConfig.value.assistant_name
    message.success(t('config.personalization.saveSuccess'))
  } catch (e) {
    message.error(t('config.saveFailed'))
  } finally {
    savingUserConfig.value = false
  }
}

async function saveLLMConfig() {
  saving.value = true
  try {
    await api.put('/config/llm', llmConfig.value)
    message.success(t('config.llm.saveSuccess'))
  } catch (e) {
    message.error(t('config.saveFailed'))
  } finally {
    saving.value = false
  }
}

async function testLLM() {
  testing.value = true
  try {
    const result = await api.post('/llm/test', llmConfig.value)
    if (result.success) {
      message.success(t('config.llm.testSuccess'))
    } else {
      message.error(t('config.llm.testFailed'))
    }
  } catch (e) {
    message.error(t('config.llm.testFailed'))
  } finally {
    testing.value = false
  }
}

async function changePassword() {
  if (!passwordForm.value.old_password || !passwordForm.value.new_password) {
    message.warning(t('config.password.fillComplete'))
    return
  }
  changingPassword.value = true
  try {
    await api.post('/auth/change-password', passwordForm.value)
    message.success(t('config.password.changeSuccess'))
    passwordForm.value = { old_password: '', new_password: '' }
  } catch (e) {
    message.error(t('config.password.changeFailed'))
  } finally {
    changingPassword.value = false
  }
}

async function loadTheme() {
  try {
    const data = await api.get('/config/get/theme').catch(() => null)
    if (data?.value) {
      currentTheme.value = data.value
      applyTheme(data.value)
    }
  } catch (e) {
    // 使用默认主题
  }
}

function selectTheme(themeId) {
  currentTheme.value = themeId
  applyTheme(themeId)
  api.put('/config/set', null, { params: { key: 'theme', value: themeId } }).catch(() => {})
  message.success(t('config.theme.switchSuccess'))
}



// 天气配置
async function loadWeatherConfig() {
  try {
    const data = await api.get('/config/weather')
    if (data && typeof data === 'object') {
      weatherConfig.value = { ...weatherConfig.value, ...data }
    }
  } catch (e) {
    // 使用默认值
  }
}

async function saveWeatherConfig() {
  savingWeather.value = true
  try {
    await api.put('/config/weather', weatherConfig.value)
    message.success(t('config.weather.saveSuccess'))
  } catch (e) {
    message.error(t('config.saveFailed'))
  } finally {
    savingWeather.value = false
  }
}

async function testWeather() {
  testingWeather.value = true
  try {
    // 先保存配置
    await api.put('/config/weather', weatherConfig.value)
    // 再测试
    const result = await api.get('/config/weather/test')
    if (result.success) {
      message.success(t('config.weather.testSuccess', { city: result.data.city, weather: result.data.weather, temperature: result.data.temperature }))
    } else {
      message.error(t('config.weather.testFailed'))
    }
  } catch (e) {
    message.error(t('config.weather.testFailed'))
  } finally {
    testingWeather.value = false
  }
}

onMounted(() => {
  // 并行加载所有配置，提高页面切换速度
  Promise.all([
    loadConfig(),
    loadUserConfig(),
    loadTheme(),
    loadHindsightConfig(),
    loadWeatherConfig()
  ])
})
</script>

<style scoped>
.config-page {
  max-width: 800px;
  margin: 0 auto;
}

.config-page :deep(.n-card) {
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.config-page :deep(.n-card:hover) {
  box-shadow: 0 4px 20px rgba(var(--theme-primary-rgb), 0.1);
}

.config-page :deep(.n-input) {
  border-radius: 12px;
}

.config-page :deep(.n-input:focus-within) {
  box-shadow: 0 0 0 2px rgba(var(--theme-primary-rgb), 0.2);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.theme-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.theme-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--theme-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-item:hover {
  border-color: var(--theme-primary);
  background: rgba(var(--theme-primary-rgb), 0.04);
}

.theme-item.active {
  border-color: var(--theme-primary);
  background: rgba(var(--theme-primary-rgb), 0.08);
  box-shadow: 0 0 0 1px var(--theme-primary);
}

.theme-preview {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.theme-color {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.theme-info {
  flex: 1;
}

.theme-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--theme-text);
}

.theme-desc {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .config-page {
    max-width: 100%;
  }

  .config-page :deep(.n-form-item) {
    margin-bottom: 12px;
  }

  .config-page :deep(.n-input),
  .config-page :deep(.n-select) {
    width: 100% !important;
  }

  .config-page :deep(.n-radio-group) {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .form-actions {
    justify-content: stretch;
  }

  .form-actions :deep(.n-button) {
    width: 100%;
  }

  .theme-item {
    padding: 10px 12px;
  }

  .theme-color {
    width: 20px;
    height: 20px;
    border-radius: 6px;
  }
}
</style>
