<template>
  <div class="config-page">
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 基础配置 -->
      <n-tab-pane name="basic" tab="基础配置">
        <!-- 个性化设置 -->
        <n-card title="个性化设置" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="100">
            <n-form-item label="用户名称">
              <n-input v-model:value="userConfig.user_name" placeholder="曹凡" />
            </n-form-item>
            <n-form-item label="助手名称">
              <n-input v-model:value="userConfig.assistant_name" placeholder="凯莉" />
            </n-form-item>
            <n-form-item>
              <div class="form-actions">
                <n-button type="primary" @click="saveUserConfig" :loading="savingUserConfig">保存</n-button>
              </div>
            </n-form-item>
          </n-form>
        </n-card>

        <!-- 主题配置 -->
        <n-card title="主题配置" style="margin-bottom: 16px">
          <div class="theme-list">
            <div
              v-for="t in themes" :key="t.id"
              class="theme-item"
              :class="{ active: currentTheme === t.id }"
              @click="selectTheme(t.id)"
            >
              <div class="theme-preview">
                <div class="theme-color" :style="{ background: t.color1 }"></div>
                <div class="theme-color" :style="{ background: t.color2 }"></div>
              </div>
              <div class="theme-info">
                <div class="theme-name">{{ t.name }}</div>
                <div class="theme-desc">{{ t.desc }}</div>
              </div>
              <n-tag v-if="currentTheme === t.id" type="success" size="small">当前</n-tag>
            </div>
          </div>
        </n-card>

        <!-- 修改密码 -->
        <n-card title="修改密码" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="80">
            <n-form-item label="旧密码">
              <n-input v-model:value="passwordForm.old_password" type="password" show-password-on="click" />
            </n-form-item>
            <n-form-item label="新密码">
              <n-input v-model:value="passwordForm.new_password" type="password" show-password-on="click" />
            </n-form-item>
            <n-form-item>
              <div class="form-actions">
                <n-button type="warning" @click="changePassword" :loading="changingPassword">修改密码</n-button>
              </div>
            </n-form-item>
          </n-form>
        </n-card>
      </n-tab-pane>

      <!-- Tab 2: LLM 配置 -->
      <n-tab-pane name="llm" tab="LLM 配置">
        <n-card title="LLM 配置" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="80">
            <n-form-item label="模式">
              <n-radio-group v-model:value="llmConfig.mode">
                <n-radio value="hermes">使用 Hermes LLM</n-radio>
                <n-radio value="custom">自定义配置</n-radio>
              </n-radio-group>
            </n-form-item>

            <template v-if="llmConfig.mode === 'custom'">
              <n-form-item label="Provider">
                <n-input v-model:value="llmConfig.provider" placeholder="openai" />
              </n-form-item>
              <n-form-item label="Model">
                <n-input v-model:value="llmConfig.model" placeholder="gpt-4" />
              </n-form-item>
              <n-form-item label="API Key">
                <n-input v-model:value="llmConfig.api_key" type="password" show-password-on="click" />
              </n-form-item>
              <n-form-item label="Base URL">
                <n-input v-model:value="llmConfig.base_url" placeholder="https://api.openai.com/v1" />
              </n-form-item>
            </template>

            <n-form-item>
              <div class="form-actions">
                <n-space>
                  <n-button type="primary" @click="saveLLMConfig" :loading="saving">保存</n-button>
                  <n-button @click="testLLM" :loading="testing" v-if="llmConfig.mode === 'custom'">测试连通性</n-button>
                </n-space>
              </div>
            </n-form-item>
          </n-form>
        </n-card>
      </n-tab-pane>

      <!-- Tab 3: Hindsight 配置 -->
      <n-tab-pane name="hindsight" tab="Hindsight 配置">
        <n-card title="Hindsight 记忆配置" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="100">
            <n-form-item label="启用 Hindsight">
              <n-switch v-model:value="hindsightConfig.enabled" />
            </n-form-item>

            <template v-if="hindsightConfig.enabled">
              <n-form-item label="Base URL">
                <n-input v-model:value="hindsightConfig.base_url" placeholder="http://localhost:8888" />
              </n-form-item>
              <n-form-item label="Bank ID">
                <n-input v-model:value="hindsightConfig.bank_id" placeholder="hermes" />
              </n-form-item>
              <n-form-item label="Recall 结果数">
                <n-input-number v-model:value="hindsightConfig.recall_limit" :min="1" :max="20" />
              </n-form-item>
              <n-form-item label="启用 Reflect">
                <n-switch v-model:value="hindsightConfig.reflect_enabled" />
              </n-form-item>
              <n-form-item label="超时时间（秒）">
                <n-input-number v-model:value="hindsightConfig.timeout" :min="5" :max="300" />
              </n-form-item>
            </template>

            <n-form-item>
              <div class="form-actions">
                <n-space>
                  <n-button type="primary" @click="saveHindsightConfig" :loading="savingHindsight">保存</n-button>
                  <n-button @click="testHindsightRecall" :loading="testingRecall">测试 Recall</n-button>
                  <n-button @click="testHindsightReflect" :loading="testingReflect" v-if="hindsightConfig.reflect_enabled">测试 Reflect</n-button>
                </n-space>
              </div>
            </n-form-item>
          </n-form>
        </n-card>
      </n-tab-pane>

      <!-- Tab 4: 天气配置 -->
      <n-tab-pane name="weather" tab="天气配置">
        <n-card title="高德地图天气配置" style="margin-bottom: 16px">
          <n-form label-placement="left" label-width="100">
            <n-form-item label="启用天气">
              <n-switch v-model:value="weatherConfig.enabled" />
            </n-form-item>

            <template v-if="weatherConfig.enabled">
              <n-form-item label="高德 API Key">
                <n-input
                  v-model:value="weatherConfig.amap_key"
                  placeholder="输入高德开放平台 Key"
                  type="password"
                  show-password-on="mousedown"
                />
              </n-form-item>

              <n-form-item label="城市编码">
                <n-input
                  v-model:value="weatherConfig.adcode"
                  placeholder="如：370100（济南）"
                />
                <span style="margin-left: 8px; font-size: 12px; color: #999;">
                  高德城市编码，可在高德开放平台查询
                </span>
              </n-form-item>

              <n-form-item label="缓存时长（秒）">
                <n-input-number
                  v-model:value="weatherConfig.cache_ttl"
                  :min="60" :max="86400" :step="60"
                />
              </n-form-item>

              <n-form-item label="温度变化阈值（°C）">
                <n-input-number
                  v-model:value="weatherConfig.temp_change_threshold"
                  :min="1" :max="20" :step="1"
                />
                <span style="margin-left: 8px; font-size: 12px; color: #999;">
                  温度变化超过此值时触发天气变化检测
                </span>
              </n-form-item>
            </template>

            <n-form-item>
              <div class="form-actions">
                <n-space>
                  <n-button type="primary" @click="saveWeatherConfig" :loading="savingWeather">保存</n-button>
                  <n-button @click="testWeather" :loading="testingWeather" v-if="weatherConfig.enabled && weatherConfig.amap_key">测试天气</n-button>
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
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import api from '../api'
import { useConfig } from '../composables/useConfig'

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
  amap_key: '',
  adcode: '370100',
  cache_ttl: 3600,
  temp_change_threshold: 5.0
})

const passwordForm = ref({
  old_password: '',
  new_password: ''
})

// 主题配置
const themes = [
  { id: 'kelly', name: '凯莉', desc: '珊瑚粉 + 暖橙', color1: '#ff9a9e', color2: '#f6d365' },
  { id: 'elegant', name: '素雅', desc: '淡蓝 + 浅灰', color1: '#a0c4e8', color2: '#e8e8e8' },
  { id: 'dark', name: '酷黑', desc: '深灰 + 亮蓝', color1: '#2d2d2d', color2: '#4fc3f7' }
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
    message.success('Hindsight 配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e?.detail || '未知错误'))
  } finally {
    savingHindsight.value = false
  }
}

async function testHindsightRecall() {
  testingRecall.value = true
  try {
    const result = await api.post('/hindsight/recall?query=测试recall&limit=3')
    if (result.success) {
      message.success(`Recall 测试成功，返回 ${result.total} 条结果`)
    } else {
      message.error('测试失败: ' + (result.message || '未知错误'))
    }
  } catch (e) {
    message.error('测试失败: ' + (e?.detail || '未知错误'))
  } finally {
    testingRecall.value = false
  }
}

async function testHindsightReflect() {
  testingReflect.value = true
  try {
    const result = await api.post('/hindsight/reflect?query=测试reflect')
    if (result.success) {
      message.success('Reflect 测试成功')
    } else {
      message.error('测试失败: ' + (result.message || '未知错误'))
    }
  } catch (e) {
    message.error('测试失败: ' + (e?.detail || '未知错误'))
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
    message.success('个性化设置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e?.detail || '未知错误'))
  } finally {
    savingUserConfig.value = false
  }
}

async function saveLLMConfig() {
  saving.value = true
  try {
    await api.put('/config/llm', llmConfig.value)
    message.success('LLM 配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e?.detail || '未知错误'))
  } finally {
    saving.value = false
  }
}

async function testLLM() {
  testing.value = true
  try {
    const result = await api.post('/llm/test', llmConfig.value)
    if (result.success) {
      message.success('LLM 连通性测试成功')
    } else {
      message.error('测试失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    message.error('测试失败: ' + (e?.detail || '未知错误'))
  } finally {
    testing.value = false
  }
}

async function changePassword() {
  if (!passwordForm.value.old_password || !passwordForm.value.new_password) {
    message.warning('请填写完整')
    return
  }
  changingPassword.value = true
  try {
    await api.post('/auth/change-password', passwordForm.value)
    message.success('密码修改成功')
    passwordForm.value = { old_password: '', new_password: '' }
  } catch (e) {
    message.error('修改失败: ' + (e?.detail || '未知错误'))
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
  message.success('主题已切换')
}

function applyTheme(themeId) {
  const root = document.documentElement
  const themeMap = {
    kelly: { primary: '#ff9a9e', primaryHover: '#ffb3b6', primaryPressed: '#e8838a', bg: '#faf9f7', accent: '#f6d365' },
    elegant: { primary: '#a0c4e8', primaryHover: '#b5d4f0', primaryPressed: '#8ab4d8', bg: '#f5f7fa', accent: '#e8e8e8' },
    dark: { primary: '#4fc3f7', primaryHover: '#72d0fa', primaryPressed: '#3ab0e0', bg: '#1a1a2e', accent: '#2d2d2d' }
  }
  const t = themeMap[themeId] || themeMap.kelly
  root.style.setProperty('--theme-primary', t.primary)
  root.style.setProperty('--theme-primary-hover', t.primaryHover)
  root.style.setProperty('--theme-primary-pressed', t.primaryPressed)
  root.style.setProperty('--theme-bg', t.bg)
  root.style.setProperty('--theme-accent', t.accent)

  // 更新 body 背景
  document.body.style.background = t.bg

  // 深色主题特殊处理
  if (themeId === 'dark') {
    document.body.style.color = '#e0e0e0'
  } else {
    document.body.style.color = '#2d2d2d'
  }
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
    message.success('天气配置已保存')
  } catch (e) {
    message.error('保存失败: ' + (e?.detail || '未知错误'))
  } finally {
    savingWeather.value = false
  }
}

async function testWeather() {
  testingWeather.value = true
  try {
    const result = await api.get('/config/weather/test')
    if (result.success) {
      message.success(`天气测试成功: ${result.data.city} ${result.data.weather} ${result.data.temperature}°C`)
    } else {
      message.error('测试失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    message.error('测试失败: ' + (e?.detail || '未知错误'))
  } finally {
    testingWeather.value = false
  }
}

onMounted(() => {
  loadConfig()
  loadUserConfig()
  loadTheme()
  loadHindsightConfig()
  loadWeatherConfig()
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
  box-shadow: 0 4px 20px rgba(255, 154, 158, 0.1);
}

.config-page :deep(.n-input) {
  border-radius: 12px;
}

.config-page :deep(.n-input:focus-within) {
  box-shadow: 0 0 0 2px rgba(255, 154, 158, 0.2);
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
  border: 1px solid #e0e0e6;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-item:hover {
  border-color: var(--theme-primary, #ff9a9e);
  background: rgba(255, 154, 158, 0.04);
}

.theme-item.active {
  border-color: var(--theme-primary, #ff9a9e);
  background: rgba(255, 154, 158, 0.08);
  box-shadow: 0 0 0 1px var(--theme-primary, #ff9a9e);
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
  color: #2d2d2d;
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
