<template>
  <div class="login-page">
    <!-- 背景层（独立） -->
    <div class="login-bg">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
    </div>

    <!-- 卡片层（独立于背景，不使用 backdrop-filter） -->
    <div class="login-card-wrapper">
      <div class="login-card">
        <div class="login-logo">
          <div class="logo-icon">H</div>
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
  position: relative;
}

/* ========== 背景层 ========== */
.login-bg {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  z-index: 0;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
}

.bg-circle-1 {
  width: 300px;
  height: 300px;
  top: -80px;
  right: -60px;
  animation: float 8s ease-in-out infinite;
}

.bg-circle-2 {
  width: 200px;
  height: 200px;
  bottom: -40px;
  left: -40px;
  animation: float 6s ease-in-out infinite reverse;
}

.bg-circle-3 {
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

/* ========== 卡片层（独立） ========== */
.login-card-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 16px;
}

.login-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 40px 32px 32px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.login-logo {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.login-logo h1 {
  margin: 0 0 4px;
  font-size: 22px;
  color: #1a1a2e;
  font-weight: 700;
}

.login-logo p {
  margin: 0;
  font-size: 13px;
  color: #999;
}

.login-btn {
  margin-top: 4px;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.login-btn:hover {
  opacity: 0.9;
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 12px;
  color: #ccc;
}

/* ========== 移动端 ========== */
@media (max-width: 480px) {
  .login-card-wrapper {
    padding: 12px;
  }

  .login-card {
    padding: 28px 20px 24px;
    border-radius: 12px;
  }

  .logo-icon {
    width: 56px;
    height: 56px;
    font-size: 24px;
  }

  .login-logo h1 {
    font-size: 20px;
  }

  .bg-circle-1 { width: 200px; height: 200px; }
  .bg-circle-2 { width: 140px; height: 140px; }
  .bg-circle-3 { display: none; }
}
</style>
