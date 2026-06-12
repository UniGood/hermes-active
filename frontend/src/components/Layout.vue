<template>
  <div class="layout">
    <!-- PC 端侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <n-avatar :size="40" round>H</n-avatar>
        <span v-if="!sidebarCollapsed" class="sidebar-title">Hermes Active</span>
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

    <!-- 主内容区 -->
    <div class="main-area">
      <!-- 移动端顶部栏（仅退出按钮） -->
      <header class="mobile-header">
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
import { ref, markRaw } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../store/auth'
import {
  HomeOutline,
  ChatbubblesOutline,
  PersonOutline,
  SettingsOutline,
  TimeOutline,
  DocumentTextOutline,
  FlaskOutline,
  LogOutOutline,
  TerminalOutline
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const sidebarCollapsed = ref(false)

const menuItems = [
  { path: '/', label: '监控面板', icon: markRaw(HomeOutline) },
  { path: '/sessions', label: '会话管理', icon: markRaw(PersonOutline) },
  { path: '/messages', label: '消息管理', icon: markRaw(ChatbubblesOutline) },
  { path: '/config', label: '配置管理', icon: markRaw(SettingsOutline) },
  { path: '/cron-jobs', label: '定时任务', icon: markRaw(TimeOutline) },
  { path: '/task-logs', label: '任务日志', icon: markRaw(DocumentTextOutline) },
  { path: '/system-logs', label: '系统日志', icon: markRaw(TerminalOutline) },
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
}

/* ========== 移动端适配（< 768px） ========== */
@media (max-width: 768px) {
  /* 移动端侧边栏改为顶部横向导航 */
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    width: 100%;
    height: auto;
    flex-direction: row;
    align-items: center;
    padding: 8px 12px;
    z-index: 1000;
    border-right: none;
    border-bottom: 1px solid #e8e8e8;
    overflow-x: auto;
    white-space: nowrap;
  }

  .sidebar-header {
    display: none;
  }

  .sidebar-nav {
    flex-direction: row;
    gap: 4px;
    overflow-x: auto;
    flex: 1;
  }

  .nav-item {
    flex-direction: column;
    padding: 4px 8px;
    font-size: 11px;
    min-width: 48px;
  }

  .nav-label {
    font-size: 10px;
  }

  .sidebar-footer {
    display: none;
  }

  /* 主内容区顶部留出空间 */
  .main-area {
    margin-left: 0;
    margin-top: 56px;
  }

  /* 显示移动端顶部栏 */
  .mobile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    background: #fff;
    border-bottom: 1px solid #e8e8e8;
    position: sticky;
    top: 0;
    z-index: 50;
  }

  .mobile-title {
    font-size: 16px;
    font-weight: 600;
    color: #333;
  }

  /* 页面内容适配 */
  .page-content {
    padding: 12px;
  }
}
</style>
