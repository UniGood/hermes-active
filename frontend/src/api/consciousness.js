/**
 * 自主意识 API
 */
import http from './http'

export default {
  // 配置
  getConfig: () => http.get('/consciousness/config'),
  saveConfig: (data) => http.put('/consciousness/config', data),

  // 状态
  getStatus: () => http.get('/consciousness/status'),

  // 日志
  getThoughts: (page = 1) => http.get('/consciousness/thoughts', { params: { page, page_size: 20 } }),
  deleteThought: (id) => http.delete(`/consciousness/thoughts/${id}`),
  retryThought: (id) => http.post(`/consciousness/thoughts/${id}/retry`),

  getHeartbeats: (page = 1) => http.get('/consciousness/heartbeats', { params: { page, page_size: 20 } }),
  deleteHeartbeat: (id) => http.delete(`/consciousness/heartbeats/${id}`),

  // 聊天记录
  getChats: (limit = 50) => http.get('/consciousness/chats', { params: { limit } }),

  // 测试
  testWeather: () => http.post('/consciousness/test/weather'),
  testHindsightRecall: () => http.post('/consciousness/test/hindsight-recall'),
  testHindsightReflect: () => http.post('/consciousness/test/hindsight-reflect'),
  testThoughtGeneration: () => http.post('/consciousness/test/thought-generation')
}
