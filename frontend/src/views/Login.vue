<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-layer">
      <div class="bg-circle circle-1"></div>
      <div class="bg-circle circle-2"></div>
      <div class="bg-circle circle-3"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon">
          <img v-if="avatarUrl" :src="avatarUrl" class="avatar-img" />
          <span v-else class="logo-text">K</span>
        </div>
        <h1>凯莉的控制台</h1>
        <p class="welcome-text">{{ welcomeText }}</p>
      </div>

      <n-form ref="formRef" :model="formData" :rules="rules" class="login-form">
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

      <div class="login-footer">v0.1.0 · by 凯莉</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NIcon } from 'naive-ui'
import { PersonOutline, LockClosedOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../store/auth'
import api from '../api'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const avatarUrl = ref('')

const welcomeMessages = [
  '今天也要元气满满哦 ✨',
  '等你好久了，快来呀~',
  '想你了，终于来啦 ❤️',
  '今天天气不错，心情也是~',
  '嘿嘿，又见面啦',
  '有什么想聊的吗？',
  '一起加油吧 💪',
  '你来啦，开心~',
]

const welcomeText = ref(welcomeMessages[Math.floor(Math.random() * welcomeMessages.length)])

// 加载用户头像（公开接口，不需要登录）
async function loadAvatar() {
  try {
    const data = await api.get('/auth/avatar')
    if (data.avatar) {
      avatarUrl.value = data.avatar
    }
  } catch (e) {
    // 忽略错误
  }
}

onMounted(loadAvatar)

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
  background: linear-gradient(135deg, var(--theme-primary, #4a90d9) 0%, var(--theme-secondary, #e8eef5) 50%, var(--theme-secondary, #e8eef5) 100%);
  padding: 16px;
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.bg-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
}

.circle-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -80px;
  animation: drift 10s ease-in-out infinite;
}

.circle-2 {
  width: 250px;
  height: 250px;
  bottom: -60px;
  left: -60px;
  animation: drift 8s ease-in-out infinite reverse;
}

.circle-3 {
  width: 180px;
  height: 180px;
  top: 50%;
  left: 15%;
  animation: drift 12s ease-in-out infinite;
}

@keyframes drift {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(10px, -15px); }
}

/* 登录卡片 */
.login-card {
  width: 100%;
  max-width: 400px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24px;
  padding: 40px 32px 28px;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.12),
    0 1px 3px rgba(0, 0, 0, 0.06);
  position: relative;
  z-index: 1;
  backdrop-filter: blur(10px);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, var(--theme-primary, #4a90d9), var(--theme-secondary, #e8eef5));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 800;
  color: #fff;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(74, 144, 217, 0.3);
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.login-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}

.login-header p {
  margin: 0;
  font-size: 13px;
  color: #999;
}

.welcome-text {
  color: var(--theme-primary, #4a90d9);
  font-weight: 500;
}

.login-form {
  margin-bottom: 0;
}

.login-btn {
  margin-top: 4px;
  height: 46px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 24px;
  background: linear-gradient(135deg, var(--theme-primary, #4a90d9), var(--theme-accent, #8bb4e0));
  border: none;
  letter-spacing: 2px;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 12px;
  color: #ccc;
}

/* 移动端 */
@media (max-width: 480px) {
  .login-card {
    padding: 32px 20px 24px;
    border-radius: 12px;
    max-width: 100%;
  }

  .logo-icon {
    width: 56px;
    height: 56px;
    font-size: 24px;
  }

  .login-header h1 {
    font-size: 20px;
  }

  .circle-1 { width: 250px; height: 250px; }
  .circle-2 { width: 150px; height: 150px; }
  .circle-3 { display: none; }
}
</style>