import { ref } from 'vue'
import api from '../api'

const config = ref({
  user_name: '曹凡',
  assistant_name: '凯莉',
  locale: 'zh-CN'
})

let loaded = false

export function useConfig() {
  async function loadConfig() {
    if (loaded) return
    try {
      const [userName, assistantName, locale] = await Promise.all([
        api.get('/config/get/user_name').catch(() => null),
        api.get('/config/get/assistant_name').catch(() => null),
        api.get('/config/get/locale').catch(() => null)
      ])
      if (userName?.value) config.value.user_name = userName.value
      if (assistantName?.value) config.value.assistant_name = assistantName.value
      if (locale?.value) config.value.locale = locale.value
      loaded = true
    } catch (e) {
      // 使用默认值
    }
  }

  return { config, loadConfig }
}
