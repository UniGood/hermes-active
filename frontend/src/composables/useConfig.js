import { ref } from 'vue'

const config = ref({
  user_name: '曹凡',
  assistant_name: '凯莉'
})

export function useConfig() {
  // 使用默认值，不再请求后端（这两个配置不存在于 active.db）
  return { config }
}
