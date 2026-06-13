<template>
  <div class="layout">
    <!-- PC 端侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header" @click="triggerAvatarUpload" style="cursor: pointer;">
        <div class="sidebar-avatar-wrap">
          <img v-if="userAvatar" :src="userAvatar" class="sidebar-avatar-img" />
          <n-avatar v-else :size="40" round>H</n-avatar>
        </div>
        <span v-if="!sidebarCollapsed" class="sidebar-title">Hermes Active</span>
        <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="handleAvatarUpload" />
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <n-icon :size="20"><component :is="item.icon" /></n-icon>
          <span v-if="!sidebarCollapsed" class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <n-button quaternary @click="handleLogout" style="width: 100%">
          <template #icon><n-icon><LogOutOutline /></n-icon></template>
          <span v-if="!sidebarCollapsed">退出登录</span>
        </n-button>
      </div>
    </aside>
    
    <!-- 移动端遮罩层 -->
    <div class="sidebar-overlay" :class="{ show: !sidebarCollapsed }" @click="sidebarCollapsed = true"></div>

    <!-- 主内容区 -->
    <div class="main-area">
      <!-- 移动端顶部栏 -->
      <header class="mobile-header">
        <n-button quaternary @click="sidebarCollapsed = !sidebarCollapsed">
          <n-icon :size="22"><MenuOutline /></n-icon>
        </n-button>
        <span class="mobile-title">Hermes Active</span>
        <n-button quaternary @click="handleLogout">
          <n-icon :size="20"><LogOutOutline /></n-icon>
        </n-button>
      </header>

      <!-- 页面内容 -->
      <main class="page-content">
        <router-view />
      </main>
    </div>

  </div>
</template>

<script setup>
import { ref, markRaw, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '../store/auth'
import api from '../api'
import {
  HomeOutline,
  ChatbubblesOutline,
  PersonOutline,
  SettingsOutline,
  TimeOutline,
  DocumentTextOutline,
  FlaskOutline,
  LogOutOutline,
  TerminalOutline,
  MenuOutline
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const message = useMessage()
// PC端默认展开，移动端默认折叠
const sidebarCollapsed = ref(window.innerWidth <= 768)
const userAvatar = ref('')
const avatarInput = ref(null)

// 加载用户头像
async function loadAvatar() {
  try {
    const data = await api.get('/auth/me')
    if (data.avatar) {
      userAvatar.value = data.avatar
    }
  } catch (e) {
    // 忽略
  }
}

function triggerAvatarUpload() {
  avatarInput.value?.click()
}

async function handleAvatarUpload(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 500 * 1024) {
    message.error('图片大小不能超过 500KB')
    return
  }
  const reader = new FileReader()
  reader.onload = async (ev) => {
    const base64 = ev.target.result
    try {
      await api.post('/auth/avatar', { avatar: base64 })
      userAvatar.value = base64
      message.success('头像上传成功')
    } catch (err) {
      message.error('上传失败: ' + (err?.detail || '未知错误'))
    }
  }
  reader.readAsDataURL(file)
}

onMounted(loadAvatar)

const menuItems = [
  { path: '/', label: '监控面板', icon: markRaw(HomeOutline) },
  { path: '/sessions', label: '会话管理', icon: markRaw(PersonOutline) },
  { path: '/messages', label: '消息管理', icon: markRaw(ChatbubblesOutline) },
  { path: '/config', label: '配置管理', icon: markRaw(SettingsOutline) },
  { path: '/cron-jobs', label: '定时任务', icon: markRaw(TimeOutline) },
  { path: '/task-logs', label: '任务日志', icon: markRaw(DocumentTextOutline) },
  { path: '/system-logs', label: '系统日志', icon: markRaw(TerminalOutline,
  MenuOutline) },
  { path: '/test', label: '测试工具', icon: markRaw(FlaskOutline) }
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

// 路由切换时关闭移动端侧边栏
watch(() => route.path, () => {
  if (window.innerWidth <= 768) {
    sidebarCollapsed.value = true
  }
})
</script>

<style scoped>
/* ========== 布局 ========== */
.layout {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

/* ========== PC 端侧边栏 ========== */
.sidebar {
  width: 220px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.3s;
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  z-index: 100;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  padding: 20px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.sidebar-avatar-wrap {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.sidebar-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #666;
  text-decoration: none;
  transition: all 0.2s;
}

.nav-item:hover {
  background: #f5f7fa;
  color: #333;
}

.nav-item.active {
  background: #e8f5e9;
  color: #18a058;
}

.nav-label {
  font-size: 14px;
}

.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid #f0f0f0;
}

/* ========== 主内容区 ========== */
.main-area {
  flex: 1;
  margin-left: 220px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.page-content {
  flex: 1;
  padding: 20px;
}

/* ========== 移动端顶部栏（PC 端隐藏） ========== */
.mobile-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 99;
}

.mobile-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

/* ========== 移动端适配（< 768px） ========== */
@media (max-width: 768px) {
  /* 移动端顶部栏 */
  .mobile-header {
    display: flex;
  }

  /* 移动端侧边栏 - 默认隐藏，点击汉堡按钮展开 */
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 200px;
    z-index: 1001;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    background: #fff;
  }

  .sidebar:not(.collapsed) {
    transform: translateX(0);
  }

  /* 遮罩层 */
  .sidebar-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 1000;
  }

  .sidebar-overlay.show {
    display: block;
  }

  /* 主内容区 */
  .main-area {
    margin-left: 0;
    margin-top: 56px;
  }
}
</style>
