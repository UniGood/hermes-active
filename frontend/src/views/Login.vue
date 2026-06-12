<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>

    <div class="login-card">
      <div class="login-logo">
        <n-avatar :size="72" round color="#667eea">
          <span style="font-size: 32px; font-weight: 700;">H</span>
        </n-avatar>
        <h1>Hermes Active</h1>
        <p>主动会话管理系统</p>
      </div>

      <n-form ref="formRef" :model="formData" :rules="rules">
        <n-form-item path="username">
          <n-input
            v-model:value="formData.username"
            placeholder="用户名"
            size="large"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <n-icon :size="18"><PersonOutline /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-form-item path="password">
          <n-input
            v-model:value="formData.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password-on="click"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <n-icon :size="18"><LockClosedOutline /></n-icon>
            </template>
          </n-input>
        </n-form-item>

        <n-button
          type="primary"
          block
          size="large"
          :loading="loading"
          @click="handleLogin"
          class="login-btn"
        >
          登 录
        </n-button>
      </n-form>

      <div class="login-footer">
        <span>v0.1.0</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NIcon } from 'naive-ui'
import { PersonOutline, LockClosedOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const formRef = ref(null)
const loading = ref(false)

const formData = reactive({
  username: '',
  password: ''
})

const rules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' }
}

async function handleLogin() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true

  try {
    await authStore.login(formData.username, formData.password)
    message.success('登录成功')
    router.push('/')
  } catch (error) {
    message.error(error?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 16px;
  position: relative;
  overflow: hidden;
}

/* 背景装饰圆 */
.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -80px;
  right: -60px;
  animation: float 8s ease-in-out infinite;
}

.circle-2 {
  width: 200px;
  height: 200px;
  bottom: -40px;
  left: -40px;
  animation: float 6s ease-in-out infinite reverse;
}

.circle-3 {
  width: 150px;
  height: 150px;
  top: 40%;
  left: 10%;
  animation: float 10s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 40px 32px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 1;
  transition: transform 0.3s ease;
}

.login-card:hover {
  transform: translateY(-4px);
}

.login-logo {
  text-align: center;
  margin-bottom: 36px;
}

.login-logo h1 {
  margin: 16px 0 6px;
  font-size: 26px;
  color: #1a1a2e;
  font-weight: 700;
  letter-spacing: 1px;
}

.login-logo p {
  margin: 0;
  font-size: 14px;
  color: #888;
}

.login-btn {
  margin-top: 8px;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  transition: opacity 0.2s;
}

.login-btn:hover {
  opacity: 0.9;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 12px;
  color: #bbb;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .login-card {
    padding: 32px 20px;
    border-radius: 16px;
  }

  .login-logo h1 {
    font-size: 22px;
  }

  .circle-1 {
    width: 200px;
    height: 200px;
  }

  .circle-2 {
    width: 140px;
    height: 140px;
  }

  .circle-3 {
    display: none;
  }
}
</style>
