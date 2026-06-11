import api from './http'

export const llmApi = {
  // 测试 LLM 连通性
  testConnection(config = {}) {
    return api.post('/llm/test', config)
  },

  // 生成消息
  generateMessage(prompt, options = {}) {
    return api.post('/llm/generate', { prompt, ...options })
  },

  // 获取 provider 列表
  getProviders() {
    return api.get('/llm/providers')
  }
}
