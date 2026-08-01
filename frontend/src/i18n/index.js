import { createI18n } from 'vue-i18n'

// 静态导入翻译文件（Vite 要求 import.meta.glob 使用静态字符串）
const zhCNModules = import.meta.glob('./locales/zh-CN/*.json', { eager: true })
const enUSModules = import.meta.glob('./locales/en-US/*.json', { eager: true })

// 将连字符命名转换为驼峰命名
function toCamelCase(str) {
  return str.replace(/-([a-z])/g, (match, letter) => letter.toUpperCase())
}

function loadLocaleMessages() {
  const messages = {
    'zh-CN': {},
    'en-US': {}
  }

  // 加载中文翻译
  for (const path in zhCNModules) {
    const key = path.replace('./locales/zh-CN/', '').replace('.json', '')
    const camelKey = toCamelCase(key)
    messages['zh-CN'][camelKey] = zhCNModules[path].default
  }

  // 加载英文翻译
  for (const path in enUSModules) {
    const key = path.replace('./locales/en-US/', '').replace('.json', '')
    const camelKey = toCamelCase(key)
    messages['en-US'][camelKey] = enUSModules[path].default
  }

  return messages
}

// 检测浏览器语言
function detectBrowserLanguage() {
  const saved = localStorage.getItem('locale')
  if (saved) return saved

  const browserLang = navigator.language || navigator.userLanguage
  if (browserLang.startsWith('zh')) return 'zh-CN'
  if (browserLang.startsWith('en')) return 'en-US'
  return 'zh-CN' // 默认中文
}

const i18n = createI18n({
  legacy: false, // 使用 Composition API
  locale: detectBrowserLanguage(),
  fallbackLocale: 'zh-CN',
  messages: loadLocaleMessages()
})

export default i18n
