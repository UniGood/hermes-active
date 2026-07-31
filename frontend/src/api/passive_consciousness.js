import http from './http'

export default {
  // 配置
  getConfig() {
    return http.get('/passive-consciousness/config')
  },
  saveConfig(data) {
    return http.put('/passive-consciousness/config', data)
  },

  // 状态
  getStatus() {
    return http.get('/passive-consciousness/status')
  },

  // 聊天记录
  getChats(limit = 50) {
    return http.get('/passive-consciousness/chats', { params: { limit } })
  },

  // 测试 - Hindsight
  testHindsightRecall() {
    return http.post('/passive-consciousness/test/hindsight-recall')
  },
  testHindsightReflect() {
    return http.post('/passive-consciousness/test/hindsight-reflect')
  },

  // 测试 - 被动意识插件
  testLonging() {
    return http.post('/passive-consciousness/test/longing')
  },
  testChatHeat() {
    return http.post('/passive-consciousness/test/chat-heat')
  },
  testEmotionalIntensity() {
    return http.post('/passive-consciousness/test/emotional-intensity')
  },
  testWeather() {
    return http.post('/passive-consciousness/test/weather')
  },
  testContext() {
    return http.post('/passive-consciousness/test/context')
  },
  testFull() {
    return http.get('/passive-consciousness/test/full')
  },

  // 平台
  getAvailablePlatforms() {
    return http.get('/passive-consciousness/platforms/available')
  },

  // 分析 API
  getAnalysisStats(params = {}) {
    return http.get('/passive-consciousness/analysis/stats', { params })
  },
  getAnalysisTrends(params = {}) {
    return http.get('/passive-consciousness/analysis/trends', { params })
  },
  getAnalysisSentiment(params = {}) {
    return http.get('/passive-consciousness/analysis/sentiment', { params })
  },

  // 天气 API
  getWeather() {
    return http.get('/passive-consciousness/weather')
  },
  clearWeatherCache() {
    return http.post('/passive-consciousness/weather/clear-cache')
  },

  // 模板 API
  getTemplates() {
    return http.get('/passive-consciousness/templates')
  },
  getTemplate(id) {
    return http.get(`/passive-consciousness/templates/${id}`)
  },
  createTemplate(template) {
    return http.post('/passive-consciousness/templates', template)
  },
  updateTemplate(id, template) {
    return http.put(`/passive-consciousness/templates/${id}`, template)
  },
  deleteTemplate(id) {
    return http.delete(`/passive-consciousness/templates/${id}`)
  },
  previewTemplate(id, data = {}) {
    return http.post(`/passive-consciousness/templates/${id}/preview`, data)
  },
  getTemplateVariables() {
    return http.get('/passive-consciousness/templates/variables')
  },
}
