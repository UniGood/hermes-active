<template>
  <div class="cron-page">
    <!-- 创建任务按钮 -->
    <n-button type="primary" @click="showCreate = true" style="margin-bottom: 16px">
      + 创建任务
    </n-button>

    <!-- 任务列表 -->
    <n-spin :show="loading">
      <div class="job-list">
        <div v-for="job in jobs" :key="job.id" class="job-card">
          <div class="job-header">
            <span class="job-name">{{ job.name }}</span>
            <n-switch :value="job.enabled" @update:value="toggleJob(job)" />
          </div>
          <div class="job-meta">
            <span>调度: {{ job.schedule }}</span>
            <span>状态: {{ job.enabled ? '运行中' : '已暂停' }}</span>
          </div>
          <div class="job-actions">
            <n-button size="small" @click="runJob(job)" :loading="job.running">运行</n-button>
            <n-button size="small" @click="editJob(job)">编辑</n-button>
            <n-button size="small" type="error" @click="deleteJob(job)">删除</n-button>
          </div>
        </div>
        <n-empty v-if="!loading && jobs.length === 0" description="暂无定时任务" />
      </div>
    </n-spin>

    <!-- 创建/编辑任务弹窗 -->
    <n-modal v-model:show="showCreate" preset="card" :title="editingJob ? '编辑任务' : '创建任务'" style="width: 90%; max-width: 500px">
      <n-form label-placement="left" label-width="80">
        <n-form-item label="任务名称">
          <n-input v-model:value="formData.name" placeholder="主动消息" />
        </n-form-item>
        <n-form-item label="调度表达式">
          <n-input v-model:value="formData.schedule" placeholder="0,20,40 6-23 * * *" />
        </n-form-item>
        <n-form-item label="提示词">
          <n-input
            v-model:value="formData.prompt"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="可选，覆盖默认提示词"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showCreate = false">取消</n-button>
          <n-button type="primary" @click="saveJob" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import api from '../api'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const saving = ref(false)
const showCreate = ref(false)
const jobs = ref([])
const editingJob = ref(null)

const formData = ref({
  name: '',
  schedule: '0,20,40 6-23 * * *',
  prompt: ''
})

async function loadJobs() {
  loading.value = true
  try {
    const data = await api.get('/cron')
    jobs.value = (data.jobs || []).map(j => ({ ...j, running: false }))
  } catch (e) {
    console.error('加载任务失败:', e)
  } finally {
    loading.value = false
  }
}

async function saveJob() {
  if (!formData.value.name || !formData.value.schedule) {
    message.warning('请填写任务名称和调度表达式')
    return
  }
  saving.value = true
  try {
    if (editingJob.value) {
      await api.put(`/cron/${editingJob.value.id}`, formData.value)
      message.success('任务已更新')
    } else {
      await api.post('/cron', formData.value)
      message.success('任务已创建')
    }
    showCreate.value = false
    editingJob.value = null
    formData.value = { name: '', schedule: '0,20,40 6-23 * * *', prompt: '' }
    await loadJobs()
  } catch (e) {
    message.error('保存失败: ' + (e?.detail || '未知错误'))
  } finally {
    saving.value = false
  }
}

async function toggleJob(job) {
  try {
    await api.post(`/cron/${job.id}/toggle`)
    message.success(job.enabled ? '任务已暂停' : '任务已恢复')
    await loadJobs()
  } catch (e) {
    message.error('操作失败')
  }
}

async function runJob(job) {
  job.running = true
  try {
    await api.post(`/cron/${job.id}/run`)
    message.success('任务已触发')
  } catch (e) {
    message.error('触发失败')
  } finally {
    job.running = false
  }
}

function editJob(job) {
  editingJob.value = job
  formData.value = {
    name: job.name,
    schedule: job.schedule,
    prompt: job.prompt || ''
  }
  showCreate.value = true
}

function deleteJob(job) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除任务 "${job.name}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.delete(`/cron/${job.id}`)
        message.success('任务已删除')
        await loadJobs()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(loadJobs)
</script>

<style scoped>
.cron-page {
  max-width: 800px;
  margin: 0 auto;
}

.job-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.job-name {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.job-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
}

.job-actions {
  display: flex;
  gap: 8px;
}
</style>
