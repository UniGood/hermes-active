<template>
  <div class="analysis-page">
    <n-card title="被动意识注入分析" style="margin-bottom: 16px">
      <!-- 筛选区 -->
      <n-space align="center" style="margin-bottom: 16px">
        <n-select
          v-model:value="timeRange"
          :options="timeRangeOptions"
          style="width: 160px"
          @update:value="fetchAll"
        />
        <n-select
          v-model:value="selectedPlatform"
          :options="platformOptions"
          clearable
          placeholder="全部平台"
          style="width: 160px"
          @update:value="fetchStats"
        />
        <n-button @click="fetchAll" :loading="loading">刷新</n-button>
      </n-space>

      <!-- 概览卡片 -->
      <n-grid :cols="4" :x-gap="12" :y-gap="12" style="margin-bottom: 24px">
        <n-gi>
          <n-card size="small">
            <n-statistic label="总注入次数" :value="stats.total" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="成功率">
              <template #default>
                {{ (stats.success_rate * 100).toFixed(1) }}%
              </template>
            </n-statistic>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="平均上下文长度" :value="stats.avg_context_length" :precision="0" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="平均情感强度" :value="stats.avg_emotional_intensity" :precision="3" />
          </n-card>
        </n-gi>
      </n-grid>

      <!-- 额外指标 -->
      <n-grid :cols="3" :x-gap="12" :y-gap="12" style="margin-bottom: 24px">
        <n-gi>
          <n-card size="small">
            <n-statistic label="平均想念分数" :value="stats.avg_longing_score" :precision="3" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="平均聊天热度" :value="stats.avg_chat_heat" :precision="2" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="成功 / 跳过 / 错误">
              <template #default>
                {{ stats.success }} / {{ stats.skipped }} / {{ stats.error }}
              </template>
            </n-statistic>
          </n-card>
        </n-gi>
      </n-grid>
    </n-card>

    <!-- 趋势图 -->
    <n-card title="注入趋势" style="margin-bottom: 16px">
      <div ref="trendChartRef" style="width: 100%; height: 360px"></div>
    </n-card>

    <!-- 情感分布 -->
    <n-grid :cols="2" :x-gap="12" style="margin-bottom: 16px">
      <n-gi>
        <n-card title="情绪分布">
          <div ref="emotionChartRef" style="width: 100%; height: 320px"></div>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="想念等级分布">
          <div ref="longingChartRef" style="width: 100%; height: 320px"></div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-grid :cols="2" :x-gap="12" style="margin-bottom: 16px">
      <n-gi>
        <n-card title="聊天热度分布">
          <div ref="heatChartRef" style="width: 100%; height: 320px"></div>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="平台分布">
          <div ref="platformChartRef" style="width: 100%; height: 320px"></div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 状态分布 -->
    <n-card title="注入状态分布" style="margin-bottom: 16px">
      <div ref="statusChartRef" style="width: 100%; height: 320px"></div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../api/passive_consciousness'

const loading = ref(false)
const timeRange = ref(24)
const selectedPlatform = ref(null)

const timeRangeOptions = [
  { label: '最近 6 小时', value: 6 },
  { label: '最近 24 小时', value: 24 },
  { label: '最近 3 天', value: 72 },
  { label: '最近 7 天', value: 168 },
  { label: '最近 30 天', value: 720 },
]

const platformOptions = ref([])

const stats = reactive({
  total: 0,
  success: 0,
  skipped: 0,
  error: 0,
  success_rate: 0,
  avg_context_length: 0,
  avg_longing_score: 0,
  avg_chat_heat: 0,
  avg_emotional_intensity: 0,
  by_platform: [],
  by_hour: [],
})

const sentiment = reactive({
  emotional_distribution: [],
  longing_distribution: [],
  heat_distribution: [],
  avg_scores: { longing: 0, heat: 0, emotion: 0 },
  correlation: { high_emotion_high_heat_count: 0, high_longing_success_count: 0 },
})

const trends = reactive({ data: [] })

// Chart refs
const trendChartRef = ref(null)
const emotionChartRef = ref(null)
const longingChartRef = ref(null)
const heatChartRef = ref(null)
const platformChartRef = ref(null)
const statusChartRef = ref(null)

let charts = []

function initChart(el) {
  if (!el) return null
  const chart = echarts.init(el)
  charts.push(chart)
  return chart
}

function resizeAllCharts() {
  charts.forEach(c => c.resize())
}

async function fetchPlatforms() {
  try {
    const res = await api.getAvailablePlatforms()
    if (res.data?.success) {
      platformOptions.value = (res.data.data || []).map(p => ({
        label: p,
        value: p,
      }))
    }
  } catch { /* ignore */ }
}

async function fetchStats() {
  try {
    const params = { hours: timeRange.value }
    if (selectedPlatform.value) params.platform = selectedPlatform.value
    const res = await api.getAnalysisStats(params)
    if (res.data?.success) {
      Object.assign(stats, res.data.data)
      await nextTick()
      renderPlatformChart()
      renderStatusChart()
    }
  } catch { /* ignore */ }
}

async function fetchTrends() {
  try {
    const res = await api.getAnalysisTrends({
      hours: timeRange.value,
      interval: timeRange.value <= 24 ? 'hour' : 'day',
    })
    if (res.data?.success) {
      trends.data = res.data.data.data || []
      await nextTick()
      renderTrendChart()
    }
  } catch { /* ignore */ }
}

async function fetchSentiment() {
  try {
    const res = await api.getAnalysisSentiment({ hours: timeRange.value })
    if (res.data?.success) {
      Object.assign(sentiment, res.data.data)
      await nextTick()
      renderEmotionChart()
      renderLongingChart()
      renderHeatChart()
    }
  } catch { /* ignore */ }
}

async function fetchAll() {
  loading.value = true
  try {
    await Promise.all([fetchStats(), fetchTrends(), fetchSentiment()])
  } finally {
    loading.value = false
  }
}

// ---- Chart Renderers ----

function renderTrendChart() {
  const el = trendChartRef.value
  if (!el || !trends.data.length) return
  const chart = initChart(el)
  const periods = trends.data.map(d => d.period)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['注入次数', '成功次数', '平均想念', '平均情感'] },
    xAxis: { type: 'category', data: periods, axisLabel: { rotate: 30 } },
    yAxis: [
      { type: 'value', name: '次数' },
      { type: 'value', name: '分数', min: 0, max: 1 },
    ],
    series: [
      { name: '注入次数', type: 'bar', data: trends.data.map(d => d.count) },
      { name: '成功次数', type: 'bar', data: trends.data.map(d => d.success_count) },
      { name: '平均想念', type: 'line', yAxisIndex: 1, data: trends.data.map(d => d.avg_longing), smooth: true },
      { name: '平均情感', type: 'line', yAxisIndex: 1, data: trends.data.map(d => d.avg_emotion), smooth: true },
    ],
    grid: { left: 60, right: 60, bottom: 60 },
  })
}

function renderPieChart(el, data, name) {
  if (!el || !data.length) return
  const chart = initChart(el)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      name,
      type: 'pie',
      radius: ['40%', '70%'],
      label: { formatter: '{b}\n{d}%' },
      data: data.map(d => ({ name: d.label, value: d.count })),
    }],
  })
}

function renderEmotionChart() {
  renderPieChart(emotionChartRef.value, sentiment.emotional_distribution, '情绪分布')
}

function renderLongingChart() {
  renderPieChart(longingChartRef.value, sentiment.longing_distribution, '想念等级')
}

function renderHeatChart() {
  renderPieChart(heatChartRef.value, sentiment.heat_distribution, '聊天热度')
}

function renderPlatformChart() {
  const el = platformChartRef.value
  if (!el || !stats.by_platform.length) return
  const chart = initChart(el)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      name: '平台',
      type: 'pie',
      radius: ['40%', '70%'],
      label: { formatter: '{b}\n{d}%' },
      data: stats.by_platform.map(d => ({ name: d.platform, value: d.count })),
    }],
  })
}

function renderStatusChart() {
  const el = statusChartRef.value
  if (!el) return
  const chart = initChart(el)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['成功', '跳过', '错误'],
    },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: [
        { value: stats.success, itemStyle: { color: '#18a058' } },
        { value: stats.skipped, itemStyle: { color: '#f0a020' } },
        { value: stats.error, itemStyle: { color: '#d03050' } },
      ],
      barWidth: '40%',
    }],
    grid: { left: 60, right: 30, bottom: 30 },
  })
}

// ---- Lifecycle ----

onMounted(() => {
  fetchPlatforms()
  fetchAll()
  window.addEventListener('resize', resizeAllCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAllCharts)
  charts.forEach(c => c.dispose())
  charts = []
})
</script>

<style scoped>
.analysis-page {
  padding: 4px 0;
}
</style>
