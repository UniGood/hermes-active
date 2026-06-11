import api from './http'

export const messagesApi = {
  // 获取消息列表
  getMessages(sessionId, params = {}) {
    return api.get(`/messages/${sessionId}`, { params })
  },

  // 发送消息
  sendMessage(sessionId, message) {
    return api.post('/messages/send', { session_id: sessionId, message })
  },

  // 发送主动消息
  sendProactiveMessage(sessionId, message, useLlm = false) {
    return api.post('/messages/send-proactive', {
      session_id: sessionId,
      message,
      use_llm: useLlm
    })
  },

  // 搜索消息
  searchMessages(keyword, params = {}) {
    return api.get('/messages/search', { params: { keyword, ...params } })
  }
}
