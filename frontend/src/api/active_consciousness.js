import http from './http'

export default {
  // 配置
  getConfig() {
    return http.get('/active-consciousness/config')
  },
  saveConfig(data) {
    return http.put('/active-consciousness/config', data)
  },

  // 状态
  getStatus() {
    return http.get('/active-consciousness/status')
  },

  // 念头日志
  getThoughts(page = 1, date = null) {
    const params = { page, page_size: 10 }
    if (date) params.date = date
    return http.get('/active-consciousness/thoughts', { params })
  },
  deleteThought(id) {
    return http.delete(`/active-consciousness/thoughts/${id}`)
  },
  retryThought(id) {
    return http.post(`/active-consciousness/thoughts/${id}/retry`)
  },

  // 心跳日志
  getHeartbeats(page = 1, date = null) {
    const params = { page }
    if (date) params.date = date
    return http.get('/active-consciousness/heartbeats', { params })
  },
  getHeartbeatDetail(id) {
    return http.get(`/active-consciousness/heartbeats/${id}`)
  },
  deleteHeartbeat(id) {
    return http.delete(`/active-consciousness/heartbeats/${id}`)
  },

  // 测试
  testLLMConnect() {
    return http.post('/active-consciousness/test/llm-connect')
  },
  testEmotionLLMConnect() {
    return http.post('/active-consciousness/test/emotion-llm-connect')
  },
  testThoughtLLMConnect() {
    return http.post('/active-consciousness/test/thought-llm-connect')
  },
  testThoughtGeneration() {
    return http.post('/active-consciousness/test/thought-generation')
  },
  testSessionContext() {
    return http.post('/active-consciousness/test/session-context')
  }
}
