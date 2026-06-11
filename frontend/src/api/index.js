import api from './index'

// 认证 API
export const authApi = {
  login: (username, password) => api.post('/auth/login', { username, password }),
  changePassword: (oldPassword, newPassword) => api.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  }),
  getMe: () => api.get('/auth/me'),
  refresh: () => api.post('/auth/refresh')
}

// Session API
export const sessionApi = {
  getList: (params) => api.get('/sessions', { params }),
  getDetail: (sessionId) => api.get(`/sessions/${sessionId}`),
  getLatest: (platform) => api.get(`/sessions/latest/${platform}`),
  getContext: (sessionId, params) => api.get(`/sessions/${sessionId}/context`, { params })
}

// 消息 API
export const messageApi = {
  getList: (sessionId, params) => api.get(`/messages/${sessionId}`, { params }),
  send: (data) => api.post('/messages/send', data),
  sendProactive: (data) => api.post('/messages/send-proactive', data),
  search: (params) => api.get('/messages/search', { params })
}

// 配置 API
export const configApi = {
  getLLM: () => api.get('/config/llm'),
  updateLLM: (data) => api.put('/config/llm', data),
  getPrompts: () => api.get('/config/prompts'),
  updatePrompts: (data) => api.put('/config/prompts', data)
}

// LLM API
export const llmApi = {
  test: (data) => api.post('/llm/test', data),
  generate: (data) => api.post('/llm/generate', data),
  getProviders: () => api.get('/llm/providers')
}

// 定时任务 API
export const cronApi = {
  getList: () => api.get('/cron'),
  create: (data) => api.post('/cron', data),
  update: (id, data) => api.put(`/cron/${id}`, data),
  delete: (id) => api.delete(`/cron/${id}`),
  run: (id) => api.post(`/cron/${id}/run`),
  toggle: (id) => api.post(`/cron/${id}/toggle`)
}

// 任务日志 API
export const taskLogApi = {
  getList: (params) => api.get('/task-logs', { params }),
  getDetail: (id) => api.get(`/task-logs/${id}`),
  delete: (id) => api.delete(`/task-logs/${id}`)
}

// 统计 API
export const statsApi = {
  getOverview: () => api.get('/stats/overview'),
  getTrend: (params) => api.get('/stats/trend', { params }),
  getProactive: (params) => api.get('/stats/proactive', { params })
}

// 测试 API
export const testApi = {
  fullTest: (data) => api.post('/test/full', data)
}

export default api
