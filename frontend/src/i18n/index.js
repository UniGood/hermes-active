import { createI18n } from 'vue-i18n'

// 动态导入翻译文件
function loadLocaleMessages() {
  const locales = ['zh-CN', 'en-US']
  const messages = {}

  locales.forEach(locale => {
    // 使用 Vite 的 import.meta.glob 动态导入
    const modules = import.meta.glob(`./locales/${locale}/*.json`, { eager: true })
    messages[locale] = {}
    for (const path in modules) {
      const key = path.replace(`./locales/${locale}/`, '').replace('.json', '')
      messages[locale][key] = modules[path].default
    }
  })

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
