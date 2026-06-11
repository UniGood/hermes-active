import api from './index'

export const configApi = {
  // 获取 LLM 配置
  getLLMConfig() {
    return api.get('/config/llm')
  },

  // 更新 LLM 配置
  updateLLMConfig(config) {
    return api.put('/config/llm', config)
  },

  // 获取提示词配置
  getPromptsConfig() {
    return api.get('/config/prompts')
  },

  // 更新提示词配置
  updatePromptsConfig(prompts) {
    return api.put('/config/prompts', prompts)
  },

  // 获取 hermes 配置
  getHermesConfig() {
    return api.get('/prompts/hermes')
  },

  // 获取提示词模板
  getPromptTemplates() {
    return api.get('/prompts/templates')
  }
}
