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
  getThoughts(page = 1, date = null, heartbeatId = null, thoughtId = null) {
    const params = { page, page_size: 10 }
    if (date) params.date = date
    if (heartbeatId != null && heartbeatId !== '') params.heartbeat_id = heartbeatId
    if (thoughtId != null && thoughtId !== '') params.thought_id = thoughtId
    return http.get('/active-consciousness/thoughts', { params })
  },
  getThoughtDetail(id) {
    return http.get(`/active-consciousness/thoughts/${id}`)
  },
  deleteThought(id) {
    return http.delete(`/active-consciousness/thoughts/${id}`)
  },
  retryThought(id) {
    return http.post(`/active-consciousness/thoughts/${id}/retry`)
  },

  // 心跳日志
  getHeartbeats(page = 1, date = null, heartbeatId = null) {
    const params = { page }
    if (date) params.date = date
    if (heartbeatId != null && heartbeatId !== '') params.heartbeat_id = heartbeatId
    return http.get('/active-consciousness/heartbeats', { params })
  },
  getHeartbeatDetail(id) {
    return http.get(`/active-consciousness/heartbeats/${id}`)
  },
  deleteHeartbeat(id) {
    return http.delete(`/active-consciousness/heartbeats/${id}`)
  },

  // 测试（form 传未保存的表单配置，null = 用已保存配置）
  testLLMConnect(form = null) {
    return http.post('/active-consciousness/test/llm-connect', form)
  },
  testEmotionLLMConnect(form = null) {
    return http.post('/active-consciousness/test/emotion-llm-connect', form)
  },
  testThoughtLLMConnect(form = null) {
    return http.post('/active-consciousness/test/thought-llm-connect', form)
  },
  testContextCollector() {
    return http.post('/active-consciousness/test/context-collector')
  },
  testThoughtEngine() {
    return http.post('/active-consciousness/test/thought-engine')
  },
  testThoughtGeneration() {
    return http.post('/active-consciousness/test/thought-generation')
  },
  testSessionContext() {
    return http.post('/active-consciousness/test/session-context')
  }
}
