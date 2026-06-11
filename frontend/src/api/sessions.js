import api from './index'

export const sessionsApi = {
  // 获取 session 列表
  getSessions(params = {}) {
    return api.get('/sessions', { params })
  },

  // 获取 session 详情
  getSession(sessionId) {
    return api.get(`/sessions/${sessionId}`)
  },

  // 获取最新 session
  getLatestSession(platform) {
    return api.get(`/sessions/latest/${platform}`)
  },

  // 获取 session 上下文
  getSessionContext(sessionId, limit = 50) {
    return api.get(`/sessions/${sessionId}/context`, { params: { limit } })
  }
}
