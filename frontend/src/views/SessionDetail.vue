<template>
  <div class="session-detail-page">
    <!-- 返回按钮 -->
    <n-button quaternary @click="router.back()" style="margin-bottom: 16px">
      ← 返回
    </n-button>

    <!-- Session 信息 -->
    <n-card v-if="session">
      <div class="session-info">
        <div class="info-item">
          <span class="label">Session ID</span>
          <n-text code>{{ session.id }}</n-text>
        </div>
        <div class="info-item">
          <span class="label">平台</span>
          <n-tag :type="getPlatformType(session.source)" size="small">
            {{ session.source || '未知' }}
          </n-tag>
        </div>
        <div class="info-item">
          <span class="label">标题</span>
          <span class="value">{{ session.title || '无标题' }}</span>
        </div>
        <div class="info-item">
          <span class="label">消息数</span>
          <span class="value">{{ session.message_count || 0 }}</span>
        </div>
        <div class="info-item">
          <span class="label">状态</span>
          <n-tag :type="session.ended_at ? 'default' : 'success'" size="small">
            {{ session.ended_at ? '已结束' : '活跃' }}
          </n-tag>
        </div>
        <div class="info-item">
          <span class="label">开始时间</span>
          <span class="value">{{ formatTime(session.started_at) }}</span>
        </div>
      </div>
    </n-card>

    <!-- 消息历史 -->
    <n-card title="消息历史" style="margin-top: 16px">
      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          placeholder="搜索消息内容..."
          clearable
          size="small"
          style="max-width: 300px"
        >
          <template #prefix>
            <n-icon><SearchOutline /></n-icon>
          </template>
        </n-input>
        <n-checkbox v-model:checked="showToolMessages">
          显示工具消息
        </n-checkbox>
        <n-checkbox v-model:checked="showAllFields">
          显示全部字段
        </n-checkbox>
      </div>

      <n-spin :show="loading">
        <div class="message-list">
          <div
            v-for="msg in filteredMessages"
            :key="msg.id"
            class="message-item"
            :class="msg.role"
          >
            <!-- 基本信息 -->
            <div class="message-header">
              <div class="message-header-left">
                <n-tag :type="getRoleType(msg.role)" size="small">
                  {{ getRoleName(msg.role) }}
                </n-tag>
                <span class="message-id">ID: {{ msg.id }}</span>
              </div>
              <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
            </div>

            <!-- 消息内容 -->
            <div class="message-content" v-html="formatContent(msg.content)"></div>

            <!-- 全部字段（调试模式） -->
            <div v-if="showAllFields" class="message-fields">
              <n-table :single-line="false" size="small">
                <tbody>
                  <tr v-for="(value, key) in msg" :key="key">
                    <td class="field-key">{{ key }}</td>
                    <td class="field-value">
                      <template v-if="value === null">
                        <n-text type="warning">null</n-text>
                      </template>
                      <template v-else-if="typeof value === 'object'">
                        <n-text code style="font-size: 11px">{{ JSON.stringify(value) }}</n-text>
                      </template>
                      <template v-else-if="key === 'content'">
                        <n-text style="white-space: pre-wrap; word-break: break-all">
                          {{ String(value).substring(0, 500) }}{{ String(value).length > 500 ? '...' : '' }}
                        </n-text>
                      </template>
                      <template v-else-if="key === 'reasoning' || key === 'reasoning_content'">
                        <n-text style="white-space: pre-wrap; word-break: break-all; font-size: 11px; color: #999">
                          {{ String(value).substring(0, 300) }}{{ String(value).length > 300 ? '...' : '' }}
                        </n-text>
                      </template>
                      <template v-else>
                        <n-text>{{ value }}</n-text>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </n-table>
            </div>

            <!-- 字段摘要 -->
            <div v-if="!showAllFields" class="message-meta">
              <span v-if="msg.token_count">Tokens: {{ msg.token_count }}</span>
              <span v-if="msg.finish_reason">Reason: {{ msg.finish_reason }}</span>
              <span v-if="msg.tool_name">Tool: {{ msg.tool_name }}</span>
              <span v-if="msg.platform_message_id">MsgID: {{ msg.platform_message_id }}</span>
              <span v-if="msg.active">Active: {{ msg.active }}</span>
              <span v-if="msg.observed">Observed: {{ msg.observed }}</span>
            </div>
          </div>
          <n-empty v-if="!loading && filteredMessages.length === 0" description="暂无消息" />
        </div>
      </n-spin>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SearchOutline } from '@vicons/ionicons5'
import api from '../api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const session = ref(null)
const messages = ref([])
const showAllFields = ref(true)
const showToolMessages = ref(false)
const searchText = ref('')

const filteredMessages = computed(() => {
  let result = messages.value

  // 过滤 tool 消息
  if (!showToolMessages.value) {
    result = result.filter(msg => msg.role !== 'tool')
  }

  // 关键词搜索
  if (searchText.value) {
    const keyword = searchText.value.toLowerCase()
    result = result.filter(msg => {
      const content = (msg.content || '').toLowerCase()
      const toolName = (msg.tool_name || '').toLowerCase()
      const reasoning = (msg.reasoning_content || '').toLowerCase()
      return content.includes(keyword) || toolName.includes(keyword) || reasoning.includes(keyword)
    })
  }

  return result
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
}

function getPlatformType(source) {
  const map = { weixin: 'success', feishu: 'info', cli: 'default', telegram: 'warning' }
  return map[source] || 'default'
}

function getRoleType(role) {
  const map = { user: 'info', assistant: 'success', system: 'warning', tool: 'default' }
  return map[role] || 'default'
}

function getRoleName(role) {
  const map = { user: '曹凡', assistant: '凯莉', system: '系统', tool: '工具' }
  return map[role] || role
}

function formatContent(content) {
  if (!content) return '<span style="color:#999">（空）</span>'
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

async function loadSession() {
  const sessionId = route.params.id
  try {
    const data = await api.get(`/sessions/${sessionId}`)
    session.value = data
  } catch (e) {
    console.error('加载会话失败:', e)
  }
}

async function loadMessages() {
  const sessionId = route.params.id
  loading.value = true
  try {
    const data = await api.get(`/messages/${sessionId}`, { params: { page: 1, page_size: 200 } })
    messages.value = data.items || []
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSession()
  loadMessages()
})
</script>

<style scoped>
.session-detail-page {
  max-width: 1000px;
  margin: 0 auto;
}

.session-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  color: #999;
}

.info-item .value {
  font-size: 14px;
  color: #2d2d2d;
  word-break: break-all;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.message-list {
  max-height: 80vh;
  overflow-y: auto;
}

.message-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.message-item:last-child {
  border-bottom: none;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-id {
  font-size: 11px;
  color: #999;
  font-family: monospace;
}

.message-time {
  font-size: 12px;
  color: #999;
}

.message-content {
  font-size: 14px;
  color: #2d2d2d;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 8px 12px;
  background: #f8f6f4;
  border-radius: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.message-item.user .message-content {
  background: linear-gradient(135deg, #ff9a9e, #f6d365);
  color: #fff;
}

.message-item.assistant .message-content {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.message-item.tool .message-content {
  background: #fdf6ec;
}

.message-fields {
  margin-top: 8px;
  border: 1px solid #f0ece8;
  border-radius: 12px;
  overflow: hidden;
}

.message-fields .n-table {
  font-size: 12px;
}

.field-key {
  width: 180px;
  font-weight: 600;
  color: #666;
  font-family: monospace;
  background: #f8f6f4;
}

.field-value {
  word-break: break-all;
}

.message-meta {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  font-size: 12px;
  color: #999;
}
</style>
