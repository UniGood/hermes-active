import api from './http'

export const cronApi = {
  // 获取任务列表
  getCronJobs() {
    return api.get('/cron')
  },

  // 创建任务
  createCronJob(job) {
    return api.post('/cron', job)
  },

  // 更新任务
  updateCronJob(jobId, job) {
    return api.put(`/cron/${jobId}`, job)
  },

  // 删除任务
  deleteCronJob(jobId) {
    return api.delete(`/cron/${jobId}`)
  },

  // 手动运行任务
  runCronJob(jobId) {
    return api.post(`/cron/${jobId}/run`)
  },

  // 切换任务状态
  toggleCronJob(jobId) {
    return api.post(`/cron/${jobId}/toggle`)
  }
}
