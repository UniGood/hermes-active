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
const themeOverrides = {
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
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: #2d2d2d;
  background: #faf9f7;
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
