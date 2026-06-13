<template>
  <div class="config-page">
    <!-- LLM 配置 -->
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
          <n-space>
            <n-button type="primary" @click="saveLLMConfig" :loading="saving">保存</n-button>
            <n-button @click="testLLM" :loading="testing" v-if="llmConfig.mode === 'custom'">测试连通性</n-button>
          </n-space>
        </n-form-item>
      </n-form>
    </n-card>

    <!-- 修改密码 -->
    <n-card title="修改密码" style="margin-top: 16px">
      <n-form label-placement="left" label-width="80">
        <n-form-item label="旧密码">
          <n-input v-model:value="passwordForm.old_password" type="password" show-password-on="click" />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input v-model:value="passwordForm.new_password" type="password" show-password-on="click" />
        </n-form-item>
        <n-form-item>
          <n-button type="warning" @click="changePassword" :loading="changingPassword">修改密码</n-button>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import api from '../api'

const message = useMessage()
const saving = ref(false)
const testing = ref(false)
const changingPassword = ref(false)

const llmConfig = ref({
  mode: 'hermes',
  provider: '',
  model: '',
  api_key: '',
  base_url: ''
})

const passwordForm = ref({
  old_password: '',
  new_password: ''
})

async function loadConfig() {
  try {
    const data = await api.get('/config/llm')
    llmConfig.value = data
  } catch (e) {
    console.error('加载 LLM 配置失败:', e)
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

onMounted(loadConfig)
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

.config-page :deep(.n-button--primary-type) {
  background: linear-gradient(135deg, #ff9a9e, #f6d365);
  border: none;
  color: #fff;
}

.config-page :deep(.n-button--primary-type:hover) {
  opacity: 0.9;
}

.config-page :deep(.n-input) {
  border-radius: 12px;
}

.config-page :deep(.n-input:focus-within) {
  box-shadow: 0 0 0 2px rgba(255, 154, 158, 0.2);
}
</style>
