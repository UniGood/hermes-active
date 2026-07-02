import http from './http'

export default {
  getStatus: () => http.get('/free-consciousness/status'),
  toggle: (enabled) => http.post('/free-consciousness/toggle', { enabled }),
  restart: () => http.post('/free-consciousness/restart'),
  getConfig: () => http.get('/free-consciousness/config'),
  saveConfig: (config) => http.post('/free-consciousness/config', config),
  testLlm: () => http.post('/free-consciousness/test-llm'),
  getLogs: (params) => http.get('/free-consciousness/logs', { params }),
  getLogDetail: (id) => http.get(`/free-consciousness/logs/${id}`),
  deleteLog: (id) => http.delete(`/free-consciousness/logs/${id}`),
  getChain: () => http.get('/free-consciousness/chain'),
  manualRun: () => http.post('/free-consciousness/run'),
}
