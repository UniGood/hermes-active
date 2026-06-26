<template>
  <div class="time-format-selector">
    <div class="chip-group">
      <div
        v-for="opt in presetOptions" :key="opt.value"
        class="time-chip"
        :class="{ active: modelValue === opt.value }"
        @click="$emit('update:modelValue', opt.value)"
      >
        <span class="chip-label">{{ opt.label }}</span>
        <span class="chip-preview">{{ opt.preview }}</span>
      </div>
      <div
        class="time-chip"
        :class="{ active: isCustom }"
        @click="enableCustom"
      >
        <span class="chip-label">自定义</span>
        <span class="chip-preview">{{ isCustom ? '自由编辑' : '' }}</span>
      </div>
    </div>

    <div v-if="isCustom" class="custom-section">
      <n-input
        :value="modelValue"
        @update:value="$emit('update:modelValue', $event)"
        placeholder="%H:%M 星期{weekday}"
        size="small"
      />
      <div class="format-help">
        <div class="help-title">格式说明：</div>
        <div class="help-tags">
          <n-tag v-for="tag in formatTags" :key="tag.code" size="tiny" :bordered="false"
            @click="insertTag(tag.code)" style="cursor: pointer;">
            {{ tag.code }} → {{ tag.desc }}
          </n-tag>
        </div>
        <div class="help-example">
          示例：<code>{{ exampleOutput }}</code>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { NInput, NTag } from 'naive-ui'

const props = defineProps({
  modelValue: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])

const WEEKDAY_NAMES = ['一', '二', '三', '四', '五', '六', '日']

const presetOptions = [
  { label: '无', value: '', preview: '' },
  { label: '简短', value: '%H:%M 星期{weekday}', preview: formatNow('%H:%M 星期{weekday}') },
  { label: '时分秒', value: '%H:%M:%S', preview: formatNow('%H:%M:%S') },
  { label: '日期时分', value: '%m/%d %H:%M', preview: formatNow('%m/%d %H:%M') },
  { label: '完整', value: '%Y-%m-%d %H:%M:%S', preview: formatNow('%Y-%m-%d %H:%M:%S') },
  { label: '日期星期', value: '%m/%d 星期{weekday}', preview: formatNow('%m/%d 星期{weekday}') },
]

const formatTags = [
  { code: '%Y', desc: '年(2026)' },
  { code: '%m', desc: '月(06)' },
  { code: '%d', desc: '日(26)' },
  { code: '%H', desc: '时(09)' },
  { code: '%M', desc: '分(30)' },
  { code: '%S', desc: '秒(00)' },
  { code: '{weekday}', desc: '周(五)' },
]

const isCustom = computed(() => {
  return props.modelValue !== '' && !presetOptions.some(o => o.value === props.modelValue)
})

const exampleOutput = computed(() => {
  return props.modelValue ? formatNow(props.modelValue) : '（选择格式后预览）'
})

function formatNow(fmt) {
  if (!fmt) return ''
  const d = new Date()
  const weekday = WEEKDAY_NAMES[d.getDay() === 0 ? 6 : d.getDay() - 1]
  let s = fmt.replace('{weekday}', weekday)
  const map = {
    '%Y': d.getFullYear(),
    '%m': String(d.getMonth() + 1).padStart(2, '0'),
    '%d': String(d.getDate()).padStart(2, '0'),
    '%H': String(d.getHours()).padStart(2, '0'),
    '%M': String(d.getMinutes()).padStart(2, '0'),
    '%S': String(d.getSeconds()).padStart(2, '0'),
  }
  for (const [k, v] of Object.entries(map)) { s = s.replace(k, v) }
  return s
}

function enableCustom() {
  if (!isCustom.value) {
    emit('update:modelValue', '%H:%M')
  }
}

function insertTag(code) {
  emit('update:modelValue', (props.modelValue || '') + code)
}
</script>

<style scoped>
.time-format-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.time-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border: 1px solid var(--theme-border, #d0d7de);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--theme-card-bg, #fff);
  min-width: 80px;
  min-height: 48px;
}

.time-chip:hover {
  border-color: var(--theme-primary);
  background: var(--theme-tag-bg, #e8f0fe);
}

.time-chip.active {
  border-color: var(--theme-primary);
  background: var(--theme-tag-bg, #e8f0fe);
  box-shadow: 0 0 0 1px var(--theme-primary);
}

.chip-label {
  font-size: 12px;
  color: var(--theme-text-secondary, #666);
  margin-bottom: 2px;
}

.time-chip.active .chip-label {
  color: var(--theme-primary);
  font-weight: 500;
}

.chip-preview {
  font-size: 11px;
  color: var(--theme-text-muted, #999);
  font-family: monospace;
}

.custom-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.format-help {
  background: var(--theme-bg-muted, #f8f9fa);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
}

.help-title {
  color: var(--theme-text-secondary, #666);
  margin-bottom: 6px;
  font-weight: 500;
}

.help-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}

.help-example {
  color: var(--theme-text-muted, #999);
}

.help-example code {
  color: var(--theme-primary);
  font-weight: 500;
}
</style>
