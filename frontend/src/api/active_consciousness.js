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
  getThoughts(page = 1) {
    return http.get('/active-consciousness/thoughts', { params: { page } })
  },
  deleteThought(id) {
    return http.delete(`/active-consciousness/thoughts/${id}`)
  },
  retryThought(id) {
    return http.post(`/active-consciousness/thoughts/${id}/retry`)
  },

  // 心跳日志
  getHeartbeats(page = 1) {
    return http.get('/active-consciousness/heartbeats', { params: { page } })
  },
  deleteHeartbeat(id) {
    return http.delete(`/active-consciousness/heartbeats/${id}`)
  },

  // 测试
  testLLMConnect() {
    return http.post('/active-consciousness/test/llm-connect')
  },
  testThoughtGeneration() {
    return http.post('/active-consciousness/test/thought-generation')
  },
  testSessionContext() {
    return http.post('/active-consciousness/test/session-context')
  }
}
