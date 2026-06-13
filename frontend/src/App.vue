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
    primaryColor: '#ff9a9e',
    primaryColorHover: '#ffb3b6',
    primaryColorPressed: '#e8838a',
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
  kelly: { primary: '#ff9a9e', hover: '#ffb3b6', pressed: '#e8838a', secondary: '#fecfef', accent: '#f6d365' },
  elegant: { primary: '#a0c4e8', hover: '#b5d4f0', pressed: '#8ab4d8', secondary: '#e8e8e8', accent: '#c0c0c0' },
  dark: { primary: '#4fc3f7', hover: '#72d0fa', pressed: '#3ab0e0', secondary: '#2d2d2d', accent: '#4fc3f7' }
}

function applyTheme(themeId) {
  const t = THEME_MAP[themeId] || THEME_MAP.kelly
  themeOverrides.value.common.primaryColor = t.primary
  themeOverrides.value.common.primaryColorHover = t.hover
  themeOverrides.value.common.primaryColorPressed = t.pressed

  const root = document.documentElement
  root.style.setProperty('--theme-primary', t.primary)
  root.style.setProperty('--theme-primary-hover', t.hover)
  root.style.setProperty('--theme-primary-pressed', t.pressed)
  root.style.setProperty('--theme-secondary', t.secondary || '#fecfef')
  root.style.setProperty('--theme-accent', t.accent || '#f6d365')

  if (themeId === 'dark') {
    root.style.setProperty('--theme-bg', '#1a1a2e')
    root.style.setProperty('--theme-text', '#e0e0e0')
    root.style.setProperty('--theme-card-bg', '#16213e')
    document.body.style.background = '#1a1a2e'
    document.body.style.color = '#e0e0e0'
  } else if (themeId === 'elegant') {
    root.style.setProperty('--theme-bg', '#f5f7fa')
    root.style.setProperty('--theme-text', '#2d2d2d')
    root.style.setProperty('--theme-card-bg', '#ffffff')
    document.body.style.background = '#f5f7fa'
    document.body.style.color = '#2d2d2d'
  } else {
    root.style.setProperty('--theme-bg', '#faf9f7')
    root.style.setProperty('--theme-text', '#2d2d2d')
    root.style.setProperty('--theme-card-bg', '#ffffff')
    document.body.style.background = '#faf9f7'
    document.body.style.color = '#2d2d2d'
  }
}

onMounted(async () => {
  try {
    const data = await api.get('/config/get/theme').catch(() => null)
    if (data?.value) {
      applyTheme(data.value)
    }
  } catch (e) {
    // 使用默认主题
  }
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
  background: var(--theme-bg, #faf9f7);
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
  height: 100vh !important;
  max-height: 100vh !important;
  border-radius: 0 !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  transform: none !important;
  margin: 0 !important;
  z-index: 2000;
}

.n-card.n-modal .n-card-content {
  flex: 1;
  overflow-y: auto;
}

.n-card.n-modal .n-card__action {
  flex-shrink: 0;
  border-top: 1px solid #eee;
}
</style>
