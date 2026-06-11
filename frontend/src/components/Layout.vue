<template>
  <div class="app-layout">
    <!-- 顶部导航栏（移动端） -->
    <header class="app-header">
      <div class="header-left">
        <n-button quaternary circle @click="showMenu = !showMenu">
          <template #icon><n-icon><MenuOutline /></n-icon></template>
        </n-button>
        <span class="header-title">{{ currentTitle }}</span>
      </div>
      <div class="header-right">
        <n-button quaternary circle @click="handleLogout">
          <template #icon><n-icon><LogOutOutline /></n-icon></template>
        </n-button>
      </div>
    </header>

    <!-- 侧边抽屉菜单（移动端） -->
    <n-drawer v-model:show="showMenu" placement="left" :width="280">
      <n-drawer-content>
        <template #header>
          <div class="drawer-header">
            <n-avatar :size="48" round>H</n-avatar>
            <div class="drawer-user">
              <div class="drawer-username">Hermes Active</div>
              <div class="drawer-subtitle">主动会话系统</div>
            </div>
          </div>
        </template>
        <n-menu :options="menuOptions" :value="currentRoute" @update:value="handleMenuClick" />
      </n-drawer-content>
    </n-drawer>

    <!-- 主内容区 -->
    <main class="app-content">
      <router-view />
    </main>

    <!-- 底部导航栏（移动端） -->
    <nav class="app-bottom-nav">
      <div
        v-for="item in bottomNavItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: currentRoute === item.key }"
        @click="router.push(item.path)"
      >
        <n-icon :size="24"><component :is="item.icon" /></n-icon>
        <span class="nav-label">{{ item.label }}</span>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, NIcon } from 'naive-ui'
import {
  MenuOutline,
  LogOutOutline,
  HomeOutline,
  ChatbubblesOutline,
  SettingsOutline,
  TimeOutline,
  FlaskOutline,
  ListOutline,
  DocumentTextOutline
} from '@vicons/ionicons5'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const authStore = useAuthStore()

const showMenu = ref(false)

const currentRoute = computed(() => route.name)
const currentTitle = computed(() => {
  const titles = {
    Dashboard: '监控面板',
    Sessions: '会话管理',
    SessionDetail: '会话详情',
    Messages: '消息管理',
    Config: '配置管理',
    CronJobs: '定时任务',
    TaskLogs: '任务日志',
    Test: '测试工具'
  }
  return titles[route.name] || 'Hermes Active'
})

const bottomNavItems = [
  { key: 'Dashboard', label: '监控', icon: HomeOutline, path: '/' },
  { key: 'Sessions', label: '会话', icon: ChatbubblesOutline, path: '/sessions' },
  { key: 'Messages', label: '消息', icon: DocumentTextOutline, path: '/messages' },
  { key: 'Config', label: '配置', icon: SettingsOutline, path: '/config' },
  { key: 'Test', label: '测试', icon: FlaskOutline, path: '/test' }
]

const menuOptions = [
  { label: '监控面板', key: 'Dashboard', icon: () => h(NIcon, null, { default: () => h(HomeOutline) }) },
  { label: '会话管理', key: 'Sessions', icon: () => h(NIcon, null, { default: () => h(ChatbubblesOutline) }) },
  { label: '消息管理', key: 'Messages', icon: () => h(NIcon, null, { default: () => h(DocumentTextOutline) }) },
  { label: '配置管理', key: 'Config', icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }) },
  { label: '定时任务', key: 'CronJobs', icon: () => h(NIcon, null, { default: () => h(TimeOutline) }) },
  { label: '任务日志', key: 'TaskLogs', icon: () => h(NIcon, null, { default: () => h(ListOutline) }) },
  { label: '测试工具', key: 'Test', icon: () => h(NIcon, null, { default: () => h(FlaskOutline) }) }
]

const pathMap = {
  Dashboard: '/',
  Sessions: '/sessions',
  Messages: '/messages',
  Config: '/config',
  CronJobs: '/cron-jobs',
  TaskLogs: '/task-logs',
  Test: '/test'
}

function handleMenuClick(key) {
  router.push(pathMap[key])
  showMenu.value = false
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
  message.success('已退出登录')
}
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #f5f7fa;
}

.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.app-content {
  flex: 1;
  margin-top: 56px;
  margin-bottom: 64px;
  padding: 16px;
  overflow-y: auto;
}

.app-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: #fff;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 100;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  cursor: pointer;
  color: #999;
  transition: color 0.2s;
}

.nav-item.active {
  color: #18a058;
}

.nav-label {
  font-size: 12px;
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.drawer-user {
  display: flex;
  flex-direction: column;
}

.drawer-username {
  font-size: 16px;
  font-weight: 600;
}

.drawer-subtitle {
  font-size: 12px;
  color: #999;
}
</style>
