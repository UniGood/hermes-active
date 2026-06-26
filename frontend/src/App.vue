<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-dialog-provider>
      <n-message-provider>
        <n-notification-provider>
          <router-view />
        </n-notification-provider>
      </n-message-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from './api'

const themeOverrides = ref({
  common: {
    primaryColor: '#4a90d9',
    primaryColorHover: '#6ba3e0',
    primaryColorPressed: '#3a7cc9',
    borderRadius: '12px',
    borderRadiusSmall: '8px'
  },
  Button: {
    borderRadiusMedium: '24px',
    borderRadiusSmall: '16px',
    borderRadiusLarge: '24px'
  },
  Input: {
    borderRadius: '12px'
  },
  Card: {
    borderRadius: '16px'
  },
  Tag: {
    borderRadius: '12px'
  }
})

const THEME_MAP = {
  kelly: {
    primary: '#ff9a9e', hover: '#ffb3b6', pressed: '#e8838a',
    secondary: '#fecfef', accent: '#f6d365',
    bg: '#faf9f7', text: '#2d2d2d', cardBg: '#ffffff',
    headerBg: '#ff9a9e', sidebarBg: '#fff0f3',
    tagBg: '#fff0f3', tagBorder: '#ffd0d6',
    borderColor: '#ffe0e6',
    shadowColor: 'rgba(255, 154, 158, 0.15)',
    primaryRgb: '255, 154, 158',
    textPrimary: '#333', textSecondary: '#666', textMuted: '#999',
    success: '#18a058', error: '#d03050', info: '#2080f0', warning: '#f0a020',
    borderLight: '#f0ece8',
    userMsgBg: '#fff0f3', assistantMsgBg: '#fff3e0',
    statusActive: '#a8e6cf',
    bgMuted: '#f8f6f4', bgLight: '#fafafa', textHint: '#aaa', errorLight: '#e53935'
  },
  elegant: {
    primary: '#4a90d9', hover: '#6ba3e0', pressed: '#3a7cc9',
    secondary: '#e8eef5', accent: '#8bb4e0',
    bg: '#f5f7fa', text: '#2d2d2d', cardBg: '#ffffff',
    headerBg: '#4a90d9', sidebarBg: '#e8eef5',
    tagBg: '#e8f0fe', tagBorder: '#b0c8e8',
    borderColor: '#d0d7de',
    shadowColor: 'rgba(74, 144, 217, 0.12)',
    primaryRgb: '74, 144, 217',
    textPrimary: '#333', textSecondary: '#666', textMuted: '#999',
    success: '#18a058', error: '#d03050', info: '#2080f0', warning: '#f0a020',
    borderLight: '#f0ece8',
    userMsgBg: '#e3f2fd', assistantMsgBg: '#fff3e0',
    statusActive: '#a8e6cf',
    bgMuted: '#f8f6f4', bgLight: '#fafafa', textHint: '#aaa', errorLight: '#e53935'
  }
}

function applyTheme(themeId) {
  const t = THEME_MAP[themeId] || THEME_MAP.elegant
  
  // Naive UI 主题（必须用具体颜色值，不能用 CSS 变量）
  themeOverrides.value.common.primaryColor = t.primary
  themeOverrides.value.common.primaryColorHover = t.hover
  themeOverrides.value.common.primaryColorPressed = t.pressed
  
  const root = document.documentElement
  
  // 核心颜色
  root.style.setProperty('--theme-primary', t.primary)
  root.style.setProperty('--theme-primary-hover', t.hover)
  root.style.setProperty('--theme-primary-pressed', t.pressed)
  root.style.setProperty('--theme-secondary', t.secondary)
  root.style.setProperty('--theme-accent', t.accent)
  
  // 背景和文字
  root.style.setProperty('--theme-bg', t.bg)
  root.style.setProperty('--theme-text', t.text)
  root.style.setProperty('--theme-card-bg', t.cardBg)
  
  // 组件背景
  root.style.setProperty('--theme-header-bg', t.headerBg)
  root.style.setProperty('--theme-sidebar-bg', t.sidebarBg)
  
  // Tag 样式
  root.style.setProperty('--theme-tag-bg', t.tagBg)
  root.style.setProperty('--theme-tag-border', t.tagBorder)
  
  // 边框和阴影
  root.style.setProperty('--theme-border', t.borderColor)
  root.style.setProperty('--theme-shadow', t.shadowColor)
  root.style.setProperty('--theme-border-light', t.borderLight)

  // 文字层级
  root.style.setProperty('--theme-text-primary', t.textPrimary)
  root.style.setProperty('--theme-text-secondary', t.textSecondary)
  root.style.setProperty('--theme-text-muted', t.textMuted)

  // 语义颜色
  root.style.setProperty('--theme-success', t.success)
  root.style.setProperty('--theme-error', t.error)
  root.style.setProperty('--theme-info', t.info)
  root.style.setProperty('--theme-warning', t.warning)

  // 聊天消息背景
  root.style.setProperty('--theme-user-msg-bg', t.userMsgBg)
  root.style.setProperty('--theme-assistant-msg-bg', t.assistantMsgBg)

  // 状态颜色
  root.style.setProperty('--theme-status-active', t.statusActive)

  // 背景色调
  root.style.setProperty('--theme-bg-muted', t.bgMuted)
  root.style.setProperty('--theme-bg-light', t.bgLight)
  root.style.setProperty('--theme-text-hint', t.textHint)
  root.style.setProperty('--theme-error-light', t.errorLight)

  // RGB 版本（用于 rgba()）
  root.style.setProperty('--theme-primary-rgb', t.primaryRgb)
  
  // body 样式
  document.body.style.background = t.bg
  document.body.style.color = t.text
}

onMounted(() => {
  // 默认使用 elegant 主题（亮蓝+浅灰）
  applyTheme('elegant')
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: var(--theme-text, #2d2d2d);
  background: var(--theme-bg, #f5f7fa);
  overflow-x: hidden;
}

#app {
  width: 100%;
  max-width: 100vw;
  min-height: 100vh;
  overflow-x: hidden;
}

/* 弹窗遮罩层 */
.n-modal-mask {
  background: rgba(0, 0, 0, 0.5) !important;
}

/* 强制所有弹窗真正全屏 */
.n-card.n-modal {
  width: 100vw !important;
  max-width: 100vw !important;
  height: 100dvh !important;
  max-height: 100dvh !important;
  border-radius: 0 !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  transform: none !important;
  margin: 0 !important;
  z-index: 2000;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
}

.n-card.n-modal .n-card-content {
  flex: 1 1 0% !important;
  min-height: 0 !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.n-card.n-modal .n-card-action {
  flex-shrink: 0 !important;
  border-top: 1px solid #eee;
}
</style>