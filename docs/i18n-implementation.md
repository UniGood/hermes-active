# 国际化 (i18n) 功能实现文档

## 概述

为 Hermes Active 前端系统添加中英文切换功能，支持完全国际化，默认语言为中文。

**实现日期：** 2026-07-31
**版本：** v0.2.2
**状态：** ✅ 完成

---

## 技术方案

### 技术栈

- **vue-i18n@9**：Vue 3 官方国际化插件
- **按页面拆分翻译文件**：每个页面一个 JSON 文件
- **后端持久化**：语言偏好存储在 active.db 的 config 表中

### 核心流程

1. 应用启动时从后端加载语言偏好
2. 如果后端没有配置，使用默认值 `zh-CN`
3. 用户切换语言时，同步更新 vue-i18n locale 和后端配置
4. Naive UI 组件自动跟随语言切换

---

## 文件变更清单

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `frontend/src/i18n/index.js` | vue-i18n 初始化配置 |
| `frontend/src/i18n/locales/zh-CN/*.json` | 中文翻译文件（16个） |
| `frontend/src/i18n/locales/en-US/*.json` | 英文翻译文件（16个） |

### 翻译文件列表

```
frontend/src/i18n/locales/
├── zh-CN/
│   ├── common.json              # 公共翻译（侧边栏、通用按钮）
│   ├── login.json               # 登录页面
│   ├── dashboard.json           # 仪表盘
│   ├── sessions.json            # 会话列表
│   ├── session-detail.json      # 会话详情
│   ├── messages.json            # 消息管理
│   ├── config.json              # 配置页面
│   ├── cron-jobs.json           # 定时任务
│   ├── task-logs.json           # 任务日志
│   ├── passive-consciousness.json
│   ├── active-consciousness.json
│   ├── free-consciousness.json
│   ├── system-logs.json
│   ├── analysis.json
│   ├── test.json
│   └── api-key-test.json
└── en-US/
    └── (同上)
```

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `frontend/package.json` | 添加 vue-i18n 依赖 |
| `frontend/src/main.js` | 集成 vue-i18n |
| `frontend/src/composables/useConfig.js` | 添加语言配置加载 |
| `frontend/src/components/Layout.vue` | 侧边栏国际化 |
| `frontend/src/views/Login.vue` | 登录页国际化 |
| `frontend/src/views/Dashboard.vue` | 仪表盘国际化 |
| `frontend/src/views/Sessions.vue` | 会话列表国际化 |
| `frontend/src/views/SessionDetail.vue` | 会话详情国际化 |
| `frontend/src/views/Messages.vue` | 消息管理国际化 |
| `frontend/src/views/Config.vue` | 配置页国际化 + 语言切换 UI |
| `frontend/src/views/CronJobs.vue` | 定时任务国际化 |
| `frontend/src/views/TaskLogs.vue` | 任务日志国际化 |
| `frontend/src/views/PassiveConsciousness.vue` | 被动意识国际化 |
| `frontend/src/views/ActiveConsciousness.vue` | 主动意识国际化 |
| `frontend/src/views/FreeConsciousness.vue` | 自由意识国际化 |
| `frontend/src/views/SystemLogs.vue` | 系统日志国际化 |
| `frontend/src/views/Analysis.vue` | 分析页国际化 |
| `frontend/src/views/Test.vue` | 测试页国际化 |
| `frontend/src/views/ApiKeyTest.vue` | API Key 测试国际化 |

---

## 实现细节

### 1. i18n 初始化配置

**文件：** `frontend/src/i18n/index.js`

```javascript
import { createI18n } from 'vue-i18n'

// 静态导入翻译文件（Vite 要求 import.meta.glob 使用静态字符串）
const zhCNModules = import.meta.glob('./locales/zh-CN/*.json', { eager: true })
const enUSModules = import.meta.glob('./locales/en-US/*.json', { eager: true })

// 将连字符命名转换为驼峰命名
function toCamelCase(str) {
  return str.replace(/-([a-z])/g, (match, letter) => letter.toUpperCase())
}

function loadLocaleMessages() {
  const messages = {
    'zh-CN': {},
    'en-US': {}
  }

  // 加载中文翻译
  for (const path in zhCNModules) {
    const key = path.replace('./locales/zh-CN/', '').replace('.json', '')
    const camelKey = toCamelCase(key)
    messages['zh-CN'][camelKey] = zhCNModules[path].default
  }

  // 加载英文翻译
  for (const path in enUSModules) {
    const key = path.replace('./locales/en-US/', '').replace('.json', '')
    const camelKey = toCamelCase(key)
    messages['en-US'][camelKey] = enUSModules[path].default
  }

  return messages
}

// 检测浏览器语言
function detectBrowserLanguage() {
  const saved = localStorage.getItem('locale')
  if (saved) return saved

  const browserLang = navigator.language || navigator.userLanguage
  if (browserLang.startsWith('zh')) return 'zh-CN'
  if (browserLang.startsWith('en')) return 'en-US'
  return 'zh-CN' // 默认中文
}

const i18n = createI18n({
  legacy: false, // 使用 Composition API
  locale: detectBrowserLanguage(),
  fallbackLocale: 'zh-CN',
  messages: loadLocaleMessages()
})

export default i18n
```

**关键点：**
- 使用 `import.meta.glob` 静态导入翻译文件（Vite 要求）
- 使用 `toCamelCase()` 将连字符命名转换为驼峰命名（如 `active-consciousness` → `activeConsciousness`）
- 支持浏览器语言检测和 localStorage 持久化

### 2. 语言切换 UI

**位置：** Config.vue 的"基础配置" Tab 中

```vue
<!-- 语言设置 -->
<n-card :title="t('config.language.title')" style="margin-bottom: 16px">
  <n-form label-placement="left" label-width="100">
    <n-form-item :label="t('config.language.label')">
      <n-select
        v-model:value="currentLocale"
        :options="localeOptions"
        @update:value="changeLocale"
      />
    </n-form-item>
  </n-form>
</n-card>
```

**切换逻辑：**

```javascript
const currentLocale = ref(locale.value)
const localeOptions = computed(() => [
  { label: t('config.language.zhCN'), value: 'zh-CN' },
  { label: t('config.language.enUS'), value: 'en-US' }
])

async function changeLocale(newLocale) {
  locale.value = newLocale
  currentLocale.value = newLocale
  localStorage.setItem('locale', newLocale)
  globalConfig.value.locale = newLocale
  try {
    await api.put('/config/set', null, { params: { key: 'locale', value: newLocale } })
    message.success(t('common.success'))
  } catch (e) {
    message.error(t('config.saveFailed'))
  }
}
```

### 3. 翻译文件结构

翻译文件使用扁平结构，按功能模块组织：

```json
{
  "tabs": {
    "status": "状态",
    "config": "配置"
  },
  "status": {
    "overview": "状态概览",
    "heartbeat": "心跳状态"
  }
}
```

**使用方式：**

```vue
<!-- 模板中 -->
{{ t('activeConsciousness.tabs.status') }}

<!-- 带参数 -->
{{ t('login.title', { name: globalConfig.assistant_name }) }}

<!-- 脚本中 -->
const { t } = useI18n()
t('common.save')
```

### 4. 后端配置持久化

使用现有的 `/config/set` 和 `/config/get` 接口：

```javascript
// 保存语言配置
await api.put('/config/set', null, { params: { key: 'locale', value: 'en-US' } })

// 读取语言配置
const locale = await api.get('/config/get/locale')
```

---

## 遇到的问题和解决方案

### 问题 1：翻译文件双重嵌套

**现象：** 翻译文件有顶层包装，导致 key 路径错误

**原因：** 翻译文件结构为 `{"activeConsciousness": {...}}`，但代码中使用 `t('activeConsciousness.tabs.status')`

**解决方案：** 移除所有翻译文件的顶层包装

### 问题 2：命名空间不匹配

**现象：** 页面显示变量名而非翻译文本

**原因：** 翻译文件名使用连字符（`active-consciousness.json`），但 Vue 文件中使用驼峰命名（`t('activeConsciousness.xxx')`）

**解决方案：** 在 `i18n/index.js` 中添加 `toCamelCase()` 函数，自动转换命名空间

### 问题 3：t() key 路径双重命名空间

**现象：** 部分页面显示变量名

**原因：** 代码中使用 `t('config.config.tabs.basic')` 而非 `t('config.tabs.basic')`

**解决方案：** 批量替换所有 Vue 文件中的双重命名空间

### 问题 4：浏览器缓存

**现象：** 代码修改后页面仍显示旧内容

**原因：** 浏览器缓存了旧的 JavaScript 文件

**解决方案：**
- 强制刷新：`Ctrl + Shift + R`（Windows/Linux）或 `Cmd + Shift + R`（Mac）
- 使用无痕/隐私窗口
- 清理 Vite 缓存：`rm -rf node_modules/.vite`

---

## 使用说明

### 切换语言

1. 登录系统
2. 进入 **配置管理** → **基础配置**
3. 在 **语言设置** 中选择语言
4. 页面自动刷新并显示对应语言

### 添加新翻译

1. 在 `frontend/src/i18n/locales/zh-CN/` 目录下创建或编辑 JSON 文件
2. 在 `frontend/src/i18n/locales/en-US/` 目录下创建对应的英文翻译
3. 在 Vue 组件中使用 `t('namespace.key')` 调用

### 翻译文件命名规范

- 文件名使用连字符：`active-consciousness.json`
- 自动转换为驼峰命名空间：`activeConsciousness`
- 翻译 key 使用驼峰：`tabs.status`、`config.title`

---

## 测试清单

- [ ] 语言切换 UI 在 Config.vue 的"基础配置" Tab 中正常显示
- [ ] 切换语言后，所有页面文本立即更新
- [ ] Naive UI 组件（分页、空状态、验证消息）跟随语言切换
- [ ] 语言偏好保存到后端，下次登录自动加载
- [ ] 默认语言为中文
- [ ] 翻译缺失时显示 key 本身，不报错
- [ ] 登录页面欢迎语正确显示
- [ ] 侧边栏菜单正确翻译
- [ ] 所有表单标签、按钮文本正确翻译

---

## 后续优化

1. **翻译覆盖率检查**：添加工具检查未翻译的文本
2. **动态加载**：按需加载翻译文件，减少初始包大小
3. **更多语言**：支持日语、韩语等其他语言
4. **翻译管理平台**：集成 Crowdin 或 Weblate 等翻译管理工具

---

## 相关提交

| 提交哈希 | 说明 |
|----------|------|
| `c1590e77` | 安装 vue-i18n 并创建 i18n 配置 |
| `7e15e76b` | 添加中英文公共翻译文件 |
| `32e45ce9` | 添加所有页面中英文翻译文件 |
| `ea794755` | 集成 vue-i18n 到 main.js |
| `f2ee5575` | Layout.vue 侧边栏国际化 |
| `8cbe358e` | Login.vue 登录页国际化 |
| `0401adef` | Dashboard.vue 仪表盘国际化 |
| `b4e3918a` | Config.vue 配置页国际化 + 语言切换 UI |
| `4d097122` | Sessions.vue 会话列表国际化 |
| `12c00fbf` | Messages.vue 消息管理国际化 |
| `0a44f488` | TaskLogs.vue 任务日志国际化 |
| `b858629c` | CronJobs.vue 定时任务国际化 |
| `aff62381` | 剩余页面国际化 |
| `84582a79` | 修复构建错误 |
| `c1b574ab` | 修复翻译文件双重嵌套 |
| `386a8327` | 修复 t() key 路径双重命名空间 |
| `b36b46d6` | 修复 i18n 命名空间映射 |
