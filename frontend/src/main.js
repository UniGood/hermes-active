import { createApp } from 'vue'
import naive from 'naive-ui'
import hljs from 'highlight.js/lib/core'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import i18n from './i18n'

// 配置 hljs 给 naive-ui 的 n-code 组件使用
const app = createApp(App)
app.provide('hljs', hljs)

const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(naive)

app.mount('#app')
