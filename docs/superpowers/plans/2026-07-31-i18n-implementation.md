# 国际化 (i18n) 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Hermes Active 前端添加中英文切换功能，支持完全国际化，默认语言为中文

**Architecture:** 使用 vue-i18n@9 实现国际化，按页面拆分翻译文件，语言偏好通过后端 config API 持久化存储。Config.vue 中添加语言切换 UI。

**Tech Stack:** Vue 3, vue-i18n@9, Naive UI, Pinia, Vite

---

## 文件结构

```
frontend/src/
├── i18n/
│   ├── index.js                    # vue-i18n 初始化
│   └── locales/
│       ├── zh-CN/
│       │   ├── common.json         # 公共翻译（侧边栏、通用按钮）
│       │   ├── login.json
│       │   ├── dashboard.json
│       │   ├── sessions.json
│       │   ├── session-detail.json
│       │   ├── messages.json
│       │   ├── config.json
│       │   ├── passive-consciousness.json
│       │   ├── active-consciousness.json
│       │   ├── free-consciousness.json
│       │   ├── cron-jobs.json
│       │   ├── task-logs.json
│       │   ├── system-logs.json
│       │   ├── analysis.json
│       │   ├── test.json
│       │   └── api-key-test.json
│       └── en-US/
│           ├── common.json
│           ├── login.json
│           ├── dashboard.json
│           ├── sessions.json
│           ├── session-detail.json
│           ├── messages.json
│           ├── config.json
│           ├── passive-consciousness.json
│           ├── active-consciousness.json
│           ├── free-consciousness.json
│           ├── cron-jobs.json
│           ├── task-logs.json
│           ├── system-logs.json
│           ├── analysis.json
│           ├── test.json
│           └── api-key-test.json
├── main.js                         # 修改：集成 vue-i18n
├── composables/
│   └── useConfig.js                # 修改：添加语言配置加载
├── components/
│   └── Layout.vue                  # 修改：侧边栏国际化
└── views/
    ├── Login.vue                   # 修改：登录页国际化
    ├── Dashboard.vue               # 修改：仪表盘国际化
    ├── Sessions.vue                # 修改：会话列表国际化
    ├── SessionDetail.vue           # 修改：会话详情国际化
    ├── Messages.vue                # 修改：消息管理国际化
    ├── Config.vue                  # 修改：配置页国际化 + 语言切换 UI
    ├── PassiveConsciousness.vue    # 修改：被动意识国际化
    ├── ActiveConsciousness.vue     # 修改：主动意识国际化
    ├── FreeConsciousness.vue       # 修改：自由意识国际化
    ├── CronJobs.vue                # 修改：定时任务国际化
    ├── TaskLogs.vue                # 修改：任务日志国际化
    ├── SystemLogs.vue              # 修改：系统日志国际化
    ├── Analysis.vue                # 修改：分析页国际化
    ├── Test.vue                    # 修改：测试页国际化
    └── ApiKeyTest.vue              # 修改：API Key 测试国际化
```

---

## Task 1: 安装依赖并创建 i18n 配置

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/i18n/index.js`

- [ ] **Step 1: 安装 vue-i18n**

```bash
cd /home/ubuntu/.hermes/hermes-active/frontend && npm install vue-i18n@9
```

- [ ] **Step 2: 创建 i18n 初始化文件**

创建 `frontend/src/i18n/index.js`:

```javascript
import { createI18n } from 'vue-i18n'

// 动态导入翻译文件
function loadLocaleMessages() {
  const locales = ['zh-CN', 'en-US']
  const messages = {}

  locales.forEach(locale => {
    // 使用 Vite 的 import.meta.glob 动态导入
    const modules = import.meta.glob(`./locales/${locale}/*.json`, { eager: true })
    messages[locale] = {}
    for (const path in modules) {
      const key = path.replace(`./locales/${locale}/`, '').replace('.json', '')
      messages[locale][key] = modules[path].default
    }
  })

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

- [ ] **Step 3: 验证文件创建成功**

```bash
ls -la /home/ubuntu/.hermes/hermes-active/frontend/src/i18n/index.js
```

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/package.json frontend/package-lock.json frontend/src/i18n/index.js
git commit -m "feat: 安装 vue-i18n 并创建 i18n 配置"
```

---

## Task 2: 创建中文翻译文件（公共部分）

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/common.json`

- [ ] **Step 1: 创建中文公共翻译文件**

创建 `frontend/src/i18n/locales/zh-CN/common.json`:

```json
{
  "sidebar": {
    "dashboard": "监控面板",
    "sessions": "会话管理",
    "messages": "消息管理",
    "passiveConsciousness": "被动意识",
    "activeConsciousness": "主动意识",
    "freeConsciousness": "自由意识",
    "config": "配置管理",
    "cronJobs": "定时任务",
    "taskLogs": "任务日志",
    "systemLogs": "系统日志",
    "test": "测试工具",
    "keyTest": "Key测试",
    "logout": "退出登录"
  },
  "common": {
    "save": "保存",
    "cancel": "取消",
    "confirm": "确认",
    "delete": "删除",
    "edit": "编辑",
    "create": "创建",
    "search": "搜索",
    "refresh": "刷新",
    "loading": "加载中...",
    "noData": "暂无数据",
    "success": "操作成功",
    "error": "操作失败",
    "warning": "警告",
    "yes": "是",
    "no": "否",
    "enable": "启用",
    "disable": "禁用",
    "test": "测试",
    "submit": "提交",
    "reset": "重置",
    "back": "返回",
    "more": "更多",
    "less": "收起",
    "expand": "展开",
    "collapse": "收起"
  },
  "pagination": {
    "total": "共 {total} 条",
    "page": "第 {page} 页"
  },
  "status": {
    "active": "活跃",
    "ended": "已结束",
    "success": "成功",
    "failed": "失败",
    "running": "运行中",
    "pending": "待处理"
  },
  "platform": {
    "weixin": "微信",
    "feishu": "飞书",
    "cli": "CLI",
    "cron": "定时任务",
    "unknown": "其他"
  }
}
```

- [ ] **Step 2: 验证 JSON 格式**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/i18n/locales/zh-CN/common.json | python3 -m json.tool
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/common.json
git commit -m "feat: 添加中文公共翻译文件"
```

---

## Task 3: 创建英文翻译文件（公共部分）

**Files:**
- Create: `frontend/src/i18n/locales/en-US/common.json`

- [ ] **Step 1: 创建英文公共翻译文件**

创建 `frontend/src/i18n/locales/en-US/common.json`:

```json
{
  "sidebar": {
    "dashboard": "Dashboard",
    "sessions": "Sessions",
    "messages": "Messages",
    "passiveConsciousness": "Passive Consciousness",
    "activeConsciousness": "Active Consciousness",
    "freeConsciousness": "Free Consciousness",
    "config": "Configuration",
    "cronJobs": "Cron Jobs",
    "taskLogs": "Task Logs",
    "systemLogs": "System Logs",
    "test": "Test Tools",
    "keyTest": "Key Test",
    "logout": "Logout"
  },
  "common": {
    "save": "Save",
    "cancel": "Cancel",
    "confirm": "Confirm",
    "delete": "Delete",
    "edit": "Edit",
    "create": "Create",
    "search": "Search",
    "refresh": "Refresh",
    "loading": "Loading...",
    "noData": "No Data",
    "success": "Success",
    "error": "Error",
    "warning": "Warning",
    "yes": "Yes",
    "no": "No",
    "enable": "Enable",
    "disable": "Disable",
    "test": "Test",
    "submit": "Submit",
    "reset": "Reset",
    "back": "Back",
    "more": "More",
    "less": "Less",
    "expand": "Expand",
    "collapse": "Collapse"
  },
  "pagination": {
    "total": "Total {total}",
    "page": "Page {page}"
  },
  "status": {
    "active": "Active",
    "ended": "Ended",
    "success": "Success",
    "failed": "Failed",
    "running": "Running",
    "pending": "Pending"
  },
  "platform": {
    "weixin": "WeChat",
    "feishu": "Feishu",
    "cli": "CLI",
    "cron": "Cron",
    "unknown": "Other"
  }
}
```

- [ ] **Step 2: 验证 JSON 格式**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/i18n/locales/en-US/common.json | python3 -m json.tool
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/en-US/common.json
git commit -m "feat: 添加英文公共翻译文件"
```

---

## Task 4: 创建登录页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/login.json`
- Create: `frontend/src/i18n/locales/en-US/login.json`

- [ ] **Step 1: 创建中文登录页翻译**

创建 `frontend/src/i18n/locales/zh-CN/login.json`:

```json
{
  "login": {
    "title": "{name}的控制台",
    "username": "用户名",
    "password": "密码",
    "submit": "登 录",
    "footer": "v0.1.0 · by {name}",
    "welcome": [
      "今天也要元气满满哦 ✨",
      "等你好久了，快来呀~",
      "想你了，终于来啦 ❤️",
      "今天天气不错，心情也是~",
      "嘿嘿，又见面啦",
      "有什么想聊的吗？",
      "一起加油吧 💪",
      "你来啦，开心~"
    ],
    "usernameRequired": "请输入用户名",
    "passwordRequired": "请输入密码",
    "loginSuccess": "登录成功",
    "loginFailed": "登录失败"
  }
}
```

- [ ] **Step 2: 创建英文登录页翻译**

创建 `frontend/src/i18n/locales/en-US/login.json`:

```json
{
  "login": {
    "title": "{name}'s Console",
    "username": "Username",
    "password": "Password",
    "submit": "Login",
    "footer": "v0.1.0 · by {name}",
    "welcome": [
      "Have a great day! ✨",
      "Been waiting for you~",
      "Missed you, welcome back! ❤️",
      "Nice weather, nice mood~",
      "Hey, good to see you again!",
      "What would you like to chat about?",
      "Let's do this! 💪",
      "You're here, yay~"
    ],
    "usernameRequired": "Please enter username",
    "passwordRequired": "Please enter password",
    "loginSuccess": "Login successful",
    "loginFailed": "Login failed"
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/login.json frontend/src/i18n/locales/en-US/login.json
git commit -m "feat: 添加登录页面中英文翻译"
```

---

## Task 5: 创建仪表盘页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/dashboard.json`
- Create: `frontend/src/i18n/locales/en-US/dashboard.json`

- [ ] **Step 1: 创建中文仪表盘翻译**

创建 `frontend/src/i18n/locales/zh-CN/dashboard.json`:

```json
{
  "dashboard": {
    "stats": {
      "totalSessions": "总会话数",
      "totalMessages": "总消息数",
      "todayMessages": "今日消息",
      "weekMessages": "本周消息"
    },
    "recentMessages": "最近消息",
    "platformDistribution": "平台分布",
    "noMessages": "暂无消息",
    "loadStatsFailed": "加载统计失败",
    "loadMessagesFailed": "加载消息失败"
  }
}
```

- [ ] **Step 2: 创建英文仪表盘翻译**

创建 `frontend/src/i18n/locales/en-US/dashboard.json`:

```json
{
  "dashboard": {
    "stats": {
      "totalSessions": "Total Sessions",
      "totalMessages": "Total Messages",
      "todayMessages": "Today",
      "weekMessages": "This Week"
    },
    "recentMessages": "Recent Messages",
    "platformDistribution": "Platform Distribution",
    "noMessages": "No messages",
    "loadStatsFailed": "Failed to load statistics",
    "loadMessagesFailed": "Failed to load messages"
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/dashboard.json frontend/src/i18n/locales/en-US/dashboard.json
git commit -m "feat: 添加仪表盘页面中英文翻译"
```

---

## Task 6: 创建会话页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/sessions.json`
- Create: `frontend/src/i18n/locales/en-US/sessions.json`

- [ ] **Step 1: 创建中文会话页翻译**

创建 `frontend/src/i18n/locales/zh-CN/sessions.json`:

```json
{
  "sessions": {
    "searchPlaceholder": "搜索会话（标题/ID）...",
    "platform": "平台",
    "status": "状态",
    "all": "全部",
    "unknown": "未知",
    "delete": "删除",
    "noTitle": "无标题",
    "messageCount": "消息数: {count}",
    "noSessions": "暂无会话",
    "confirmDelete": "确认删除",
    "confirmDeleteMessage": "确定要删除这个会话吗？",
    "deleteSuccess": "删除成功",
    "deleteFailed": "删除失败"
  }
}
```

- [ ] **Step 2: 创建英文会话页翻译**

创建 `frontend/src/i18n/locales/en-US/sessions.json`:

```json
{
  "sessions": {
    "searchPlaceholder": "Search sessions (title/ID)...",
    "platform": "Platform",
    "status": "Status",
    "all": "All",
    "unknown": "Unknown",
    "delete": "Delete",
    "noTitle": "Untitled",
    "messageCount": "Messages: {count}",
    "noSessions": "No sessions",
    "confirmDelete": "Confirm Delete",
    "confirmDeleteMessage": "Are you sure you want to delete this session?",
    "deleteSuccess": "Deleted successfully",
    "deleteFailed": "Delete failed"
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/sessions.json frontend/src/i18n/locales/en-US/sessions.json
git commit -m "feat: 添加会话页面中英文翻译"
```

---

## Task 7: 创建消息页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/messages.json`
- Create: `frontend/src/i18n/locales/en-US/messages.json`

- [ ] **Step 1: 创建中文消息页翻译**

创建 `frontend/src/i18n/locales/zh-CN/messages.json`:

```json
{
  "messages": {
    "searchPlaceholder": "搜索消息内容...",
    "search": "搜索",
    "backToSearch": "返回搜索",
    "sessionId": "Session ID",
    "title": "标题",
    "userId": "用户 ID",
    "messageCount": "消息数",
    "status": "状态",
    "noTitle": "无标题",
    "hideToolMessages": "隐藏工具消息",
    "totalCount": "共 {count} 条",
    "noMessages": "暂无消息",
    "inputPlaceholder": "输入消息...",
    "send": "发送",
    "loadFailed": "加载消息失败",
    "sendFailed": "发送失败"
  }
}
```

- [ ] **Step 2: 创建英文消息页翻译**

创建 `frontend/src/i18n/locales/en-US/messages.json`:

```json
{
  "messages": {
    "searchPlaceholder": "Search message content...",
    "search": "Search",
    "backToSearch": "Back to Search",
    "sessionId": "Session ID",
    "title": "Title",
    "userId": "User ID",
    "messageCount": "Messages",
    "status": "Status",
    "noTitle": "Untitled",
    "hideToolMessages": "Hide Tool Messages",
    "totalCount": "Total {count}",
    "noMessages": "No messages",
    "inputPlaceholder": "Type a message...",
    "send": "Send",
    "loadFailed": "Failed to load messages",
    "sendFailed": "Send failed"
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/messages.json frontend/src/i18n/locales/en-US/messages.json
git commit -m "feat: 添加消息页面中英文翻译"
```

---

## Task 8: 创建配置页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/config.json`
- Create: `frontend/src/i18n/locales/en-US/config.json`

- [ ] **Step 1: 创建中文配置页翻译**

创建 `frontend/src/i18n/locales/zh-CN/config.json`:

```json
{
  "config": {
    "tabs": {
      "basic": "基础配置",
      "llm": "LLM 配置",
      "hindsight": "Hindsight 配置",
      "weather": "天气配置"
    },
    "personalization": {
      "title": "个性化设置",
      "userName": "用户名称",
      "assistantName": "助手名称",
      "saveSuccess": "个性化设置已保存"
    },
    "language": {
      "title": "语言设置",
      "label": "界面语言",
      "zhCN": "简体中文",
      "enUS": "English"
    },
    "theme": {
      "title": "主题配置",
      "current": "当前",
      "switchSuccess": "主题已切换"
    },
    "password": {
      "title": "修改密码",
      "oldPassword": "旧密码",
      "newPassword": "新密码",
      "submit": "修改密码",
      "fillComplete": "请填写完整",
      "changeSuccess": "密码修改成功",
      "changeFailed": "修改失败"
    },
    "llm": {
      "title": "LLM 配置",
      "mode": "模式",
      "hermes": "使用 Hermes LLM",
      "custom": "自定义配置",
      "provider": "Provider",
      "model": "Model",
      "apiKey": "API Key",
      "baseUrl": "Base URL",
      "saveSuccess": "LLM 配置已保存",
      "testSuccess": "LLM 连通性测试成功",
      "testFailed": "测试失败"
    },
    "hindsight": {
      "title": "Hindsight 记忆配置",
      "enable": "启用 Hindsight",
      "baseUrl": "Base URL",
      "bankId": "Bank ID",
      "recallLimit": "Recall 结果数",
      "enableReflect": "启用 Reflect",
      "timeout": "超时时间（秒）",
      "saveSuccess": "Hindsight 配置已保存",
      "testRecall": "测试 Recall",
      "testReflect": "测试 Reflect",
      "testSuccess": "测试成功",
      "testFailed": "测试失败",
      "recallSuccess": "Recall 测试成功，返回 {count} 条结果",
      "reflectSuccess": "Reflect 测试成功"
    },
    "weather": {
      "title": "天气感知配置",
      "enable": "启用天气感知",
      "provider": "天气服务",
      "qweather": "和风天气",
      "amap": "高德地图",
      "city": "城市",
      "cityPlaceholder": "如：北京、济南、上海",
      "cityHint": "城市名称（中文或英文）",
      "cacheHours": "缓存时长（小时）",
      "amapConfig": "高德地图配置",
      "amapKey": "高德 API Key",
      "adcode": "城市编码",
      "adcodePlaceholder": "如：370100（济南）",
      "adcodeHint": "高德城市编码，可在高德开放平台查询",
      "qweatherConfig": "和风天气配置",
      "qweatherKey": "和风 API Key",
      "geoApiUrl": "GeoAPI URL",
      "geoApiHint": "城市查询 API",
      "weatherApiUrl": "天气 API URL",
      "weatherApiHint": "实时天气 API",
      "saveSuccess": "天气配置已保存",
      "testSuccess": "天气测试成功: {city} {weather} {temperature}°C",
      "testFailed": "测试失败"
    },
    "saveFailed": "保存失败"
  }
}
```

- [ ] **Step 2: 创建英文配置页翻译**

创建 `frontend/src/i18n/locales/en-US/config.json`:

```json
{
  "config": {
    "tabs": {
      "basic": "Basic",
      "llm": "LLM",
      "hindsight": "Hindsight",
      "weather": "Weather"
    },
    "personalization": {
      "title": "Personalization",
      "userName": "User Name",
      "assistantName": "Assistant Name",
      "saveSuccess": "Personalization settings saved"
    },
    "language": {
      "title": "Language Settings",
      "label": "Interface Language",
      "zhCN": "简体中文",
      "enUS": "English"
    },
    "theme": {
      "title": "Theme",
      "current": "Current",
      "switchSuccess": "Theme switched"
    },
    "password": {
      "title": "Change Password",
      "oldPassword": "Old Password",
      "newPassword": "New Password",
      "submit": "Change Password",
      "fillComplete": "Please fill in all fields",
      "changeSuccess": "Password changed successfully",
      "changeFailed": "Change failed"
    },
    "llm": {
      "title": "LLM Configuration",
      "mode": "Mode",
      "hermes": "Use Hermes LLM",
      "custom": "Custom Configuration",
      "provider": "Provider",
      "model": "Model",
      "apiKey": "API Key",
      "baseUrl": "Base URL",
      "saveSuccess": "LLM configuration saved",
      "testSuccess": "LLM connectivity test successful",
      "testFailed": "Test failed"
    },
    "hindsight": {
      "title": "Hindsight Memory Configuration",
      "enable": "Enable Hindsight",
      "baseUrl": "Base URL",
      "bankId": "Bank ID",
      "recallLimit": "Recall Limit",
      "enableReflect": "Enable Reflect",
      "timeout": "Timeout (seconds)",
      "saveSuccess": "Hindsight configuration saved",
      "testRecall": "Test Recall",
      "testReflect": "Test Reflect",
      "testSuccess": "Test successful",
      "testFailed": "Test failed",
      "recallSuccess": "Recall test successful, returned {count} results",
      "reflectSuccess": "Reflect test successful"
    },
    "weather": {
      "title": "Weather Configuration",
      "enable": "Enable Weather",
      "provider": "Weather Service",
      "qweather": "QWeather",
      "amap": "AMap",
      "city": "City",
      "cityPlaceholder": "e.g., Beijing, Shanghai",
      "cityHint": "City name (Chinese or English)",
      "cacheHours": "Cache Duration (hours)",
      "amapConfig": "AMap Configuration",
      "amapKey": "AMap API Key",
      "adcode": "City Code",
      "adcodePlaceholder": "e.g., 370100",
      "adcodeHint": "AMap city code, available on AMap Open Platform",
      "qweatherConfig": "QWeather Configuration",
      "qweatherKey": "QWeather API Key",
      "geoApiUrl": "GeoAPI URL",
      "geoApiHint": "City lookup API",
      "weatherApiUrl": "Weather API URL",
      "weatherApiHint": "Real-time weather API",
      "saveSuccess": "Weather configuration saved",
      "testSuccess": "Weather test successful: {city} {weather} {temperature}°C",
      "testFailed": "Test failed"
    },
    "saveFailed": "Save failed"
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/config.json frontend/src/i18n/locales/en-US/config.json
git commit -m "feat: 添加配置页面中英文翻译"
```

---

## Task 9: 创建定时任务页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/cron-jobs.json`
- Create: `frontend/src/i18n/locales/en-US/cron-jobs.json`

- [ ] **Step 1: 创建中文定时任务翻译**

创建 `frontend/src/i18n/locales/zh-CN/cron-jobs.json`:

```json
{
  "cronJobs": {
    "createJob": "+ 创建任务",
    "defaultPrompts": "默认提示词配置",
    "noJobs": "暂无定时任务",
    "editJob": "编辑任务",
    "createJobTitle": "创建任务",
    "form": {
      "name": "任务名称",
      "namePlaceholder": "主动消息",
      "schedule": "调度表达式",
      "schedulePlaceholder": "0,20,40 6-23 * * *",
      "frequency": "频率",
      "nextRunTimes": "未来运行时间",
      "expand": "展开",
      "collapse": "收起",
      "platform": "目标平台",
      "platformPlaceholder": "选择平台",
      "sessionMode": "Session 获取方式",
      "sessionModeLatest": "每次获取最新活跃 Session",
      "sessionModeFixed": "指定 Session",
      "sessionId": "指定 Session",
      "sessionIdPlaceholder": "选择 session",
      "systemPrompt": "系统提示词",
      "systemPromptPlaceholder": "系统提示词，定义 AI 的角色和行为规则",
      "appendSoulMd": "拼接 soul.md",
      "appendSoulMdHint": "将在系统提示词后追加 SOUL.md 内容",
      "noAppendSoulMd": "不追加 SOUL.md",
      "fillDefaultSystemPrompt": "填充默认系统提示词",
      "userPrompt": "用户提示词",
      "userPromptPlaceholder": "用户提示词，发送给 AI 的具体内容"
    },
    "actions": {
      "run": "运行",
      "edit": "编辑",
      "delete": "删除",
      "logs": "日志"
    },
    "scheduleInfo": "调度: {schedule}",
    "platformInfo": "平台: {platform}",
    "sessionInfo": "指定 Session: {sessionId}",
    "sessionModeLatestInfo": "获取方式: 最新活跃",
    "llmInfo": "LLM: {value}",
    "writeToDbInfo": "写入DB: {value}",
    "withMarkInfo": "带标记: {value}",
    "lastRun": "上次运行: {time}",
    "confirmDelete": "确认删除",
    "confirmDeleteMessage": "确定要删除这个定时任务吗？",
    "deleteSuccess": "删除成功",
    "deleteFailed": "删除失败",
    "runSuccess": "任务已触发运行",
    "runFailed": "运行失败",
    "saveSuccess": "保存成功",
    "saveFailed": "保存失败"
  }
}
```

- [ ] **Step 2: 创建英文定时任务翻译**

创建 `frontend/src/i18n/locales/en-US/cron-jobs.json`:

```json
{
  "cronJobs": {
    "createJob": "+ Create Job",
    "defaultPrompts": "Default Prompts Config",
    "noJobs": "No cron jobs",
    "editJob": "Edit Job",
    "createJobTitle": "Create Job",
    "form": {
      "name": "Job Name",
      "namePlaceholder": "Proactive Message",
      "schedule": "Schedule Expression",
      "schedulePlaceholder": "0,20,40 6-23 * * *",
      "frequency": "Frequency",
      "nextRunTimes": "Next Run Times",
      "expand": "Expand",
      "collapse": "Collapse",
      "platform": "Target Platform",
      "platformPlaceholder": "Select platform",
      "sessionMode": "Session Mode",
      "sessionModeLatest": "Get latest active session each time",
      "sessionModeFixed": "Fixed session",
      "sessionId": "Session ID",
      "sessionIdPlaceholder": "Select session",
      "systemPrompt": "System Prompt",
      "systemPromptPlaceholder": "System prompt, defines AI's role and behavior rules",
      "appendSoulMd": "Append soul.md",
      "appendSoulMdHint": "Will append SOUL.md content after system prompt",
      "noAppendSoulMd": "Don't append SOUL.md",
      "fillDefaultSystemPrompt": "Fill Default System Prompt",
      "userPrompt": "User Prompt",
      "userPromptPlaceholder": "User prompt, specific content sent to AI"
    },
    "actions": {
      "run": "Run",
      "edit": "Edit",
      "delete": "Delete",
      "logs": "Logs"
    },
    "scheduleInfo": "Schedule: {schedule}",
    "platformInfo": "Platform: {platform}",
    "sessionInfo": "Session: {sessionId}",
    "sessionModeLatestInfo": "Mode: Latest Active",
    "llmInfo": "LLM: {value}",
    "writeToDbInfo": "Write to DB: {value}",
    "withMarkInfo": "With Mark: {value}",
    "lastRun": "Last Run: {time}",
    "confirmDelete": "Confirm Delete",
    "confirmDeleteMessage": "Are you sure you want to delete this cron job?",
    "deleteSuccess": "Deleted successfully",
    "deleteFailed": "Delete failed",
    "runSuccess": "Job triggered",
    "runFailed": "Run failed",
    "saveSuccess": "Saved successfully",
    "saveFailed": "Save failed"
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/cron-jobs.json frontend/src/i18n/locales/en-US/cron-jobs.json
git commit -m "feat: 添加定时任务页面中英文翻译"
```

---

## Task 10: 创建任务日志页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/task-logs.json`
- Create: `frontend/src/i18n/locales/en-US/task-logs.json`

- [ ] **Step 1: 创建中文任务日志翻译**

创建 `frontend/src/i18n/locales/zh-CN/task-logs.json`:

```json
{
  "taskLogs": {
    "statusPlaceholder": "状态",
    "typePlaceholder": "类型",
    "refresh": "刷新",
    "noLogs": "暂无任务日志",
    "duration": "耗时: {time}s",
    "statusOptions": {
      "success": "成功",
      "failed": "失败"
    },
    "typeOptions": {
      "send_message": "发送消息",
      "generate": "LLM 生成",
      "send_proactive": "主动消息",
      "cron_run": "定时任务",
      "test_context": "上下文读取"
    }
  }
}
```

- [ ] **Step 2: 创建英文任务日志翻译**

创建 `frontend/src/i18n/locales/en-US/task-logs.json`:

```json
{
  "taskLogs": {
    "statusPlaceholder": "Status",
    "typePlaceholder": "Type",
    "refresh": "Refresh",
    "noLogs": "No task logs",
    "duration": "Duration: {time}s",
    "statusOptions": {
      "success": "Success",
      "failed": "Failed"
    },
    "typeOptions": {
      "send_message": "Send Message",
      "generate": "LLM Generate",
      "send_proactive": "Proactive Message",
      "cron_run": "Cron Run",
      "test_context": "Context Read"
    }
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/task-logs.json frontend/src/i18n/locales/en-US/task-logs.json
git commit -m "feat: 添加任务日志页面中英文翻译"
```

---

## Task 11: 创建剩余页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/passive-consciousness.json`
- Create: `frontend/src/i18n/locales/en-US/passive-consciousness.json`
- Create: `frontend/src/i18n/locales/zh-CN/active-consciousness.json`
- Create: `frontend/src/i18n/locales/en-US/active-consciousness.json`
- Create: `frontend/src/i18n/locales/zh-CN/free-consciousness.json`
- Create: `frontend/src/i18n/locales/en-US/free-consciousness.json`
- Create: `frontend/src/i18n/locales/zh-CN/system-logs.json`
- Create: `frontend/src/i18n/locales/en-US/system-logs.json`
- Create: `frontend/src/i18n/locales/zh-CN/analysis.json`
- Create: `frontend/src/i18n/locales/en-US/analysis.json`
- Create: `frontend/src/i18n/locales/zh-CN/test.json`
- Create: `frontend/src/i18n/locales/en-US/test.json`
- Create: `frontend/src/i18n/locales/zh-CN/api-key-test.json`
- Create: `frontend/src/i18n/locales/en-US/api-key-test.json`

- [ ] **Step 1: 创建被动意识页面翻译**

创建 `frontend/src/i18n/locales/zh-CN/passive-consciousness.json`:

```json
{
  "passiveConsciousness": {
    "title": "被动意识",
    "description": "被动意识系统在用户消息到达时自动注入上下文信息",
    "config": {
      "title": "被动意识配置",
      "enable": "启用被动意识",
      "missScore": "想念分数",
      "chatHeat": "聊天热度",
      "hindsight": "Hindsight 集成"
    },
    "status": {
      "enabled": "已启用",
      "disabled": "已禁用"
    }
  }
}
```

创建 `frontend/src/i18n/locales/en-US/passive-consciousness.json`:

```json
{
  "passiveConsciousness": {
    "title": "Passive Consciousness",
    "description": "Passive consciousness system automatically injects context when user messages arrive",
    "config": {
      "title": "Passive Consciousness Config",
      "enable": "Enable Passive Consciousness",
      "missScore": "Miss Score",
      "chatHeat": "Chat Heat",
      "hindsight": "Hindsight Integration"
    },
    "status": {
      "enabled": "Enabled",
      "disabled": "Disabled"
    }
  }
}
```

- [ ] **Step 2: 创建主动意识页面翻译**

创建 `frontend/src/i18n/locales/zh-CN/active-consciousness.json`:

```json
{
  "activeConsciousness": {
    "title": "主动意识",
    "description": "主动意识系统通过心跳调度器定期生成念头并决定是否发送消息",
    "config": {
      "title": "主动意识配置",
      "enable": "启用主动意识",
      "heartbeat": "心跳间隔",
      "emotion": "情绪系统",
      "decision": "决策矩阵"
    },
    "thoughts": {
      "title": "念头列表",
      "type": "类型",
      "content": "内容",
      "score": "评分",
      "time": "时间",
      "noThoughts": "暂无念头"
    }
  }
}
```

创建 `frontend/src/i18n/locales/en-US/active-consciousness.json`:

```json
{
  "activeConsciousness": {
    "title": "Active Consciousness",
    "description": "Active consciousness system periodically generates thoughts and decides whether to send messages",
    "config": {
      "title": "Active Consciousness Config",
      "enable": "Enable Active Consciousness",
      "heartbeat": "Heartbeat Interval",
      "emotion": "Emotion System",
      "decision": "Decision Matrix"
    },
    "thoughts": {
      "title": "Thoughts",
      "type": "Type",
      "content": "Content",
      "score": "Score",
      "time": "Time",
      "noThoughts": "No thoughts"
    }
  }
}
```

- [ ] **Step 3: 创建自由意识页面翻译**

创建 `frontend/src/i18n/locales/zh-CN/free-consciousness.json`:

```json
{
  "freeConsciousness": {
    "title": "自由意识",
    "description": "自由意识系统允许 AI 自主探索和思考",
    "config": {
      "title": "自由意识配置",
      "enable": "启用自由意识"
    }
  }
}
```

创建 `frontend/src/i18n/locales/en-US/free-consciousness.json`:

```json
{
  "freeConsciousness": {
    "title": "Free Consciousness",
    "description": "Free consciousness system allows AI to explore and think independently",
    "config": {
      "title": "Free Consciousness Config",
      "enable": "Enable Free Consciousness"
    }
  }
}
```

- [ ] **Step 4: 创建系统日志页面翻译**

创建 `frontend/src/i18n/locales/zh-CN/system-logs.json`:

```json
{
  "systemLogs": {
    "title": "系统日志",
    "refresh": "刷新",
    "clear": "清空",
    "noLogs": "暂无系统日志",
    "level": {
      "info": "信息",
      "warn": "警告",
      "error": "错误",
      "debug": "调试"
    }
  }
}
```

创建 `frontend/src/i18n/locales/en-US/system-logs.json`:

```json
{
  "systemLogs": {
    "title": "System Logs",
    "refresh": "Refresh",
    "clear": "Clear",
    "noLogs": "No system logs",
    "level": {
      "info": "Info",
      "warn": "Warning",
      "error": "Error",
      "debug": "Debug"
    }
  }
}
```

- [ ] **Step 5: 创建分析页面翻译**

创建 `frontend/src/i18n/locales/zh-CN/analysis.json`:

```json
{
  "analysis": {
    "title": "分析",
    "description": "数据分析和统计"
  }
}
```

创建 `frontend/src/i18n/locales/en-US/analysis.json`:

```json
{
  "analysis": {
    "title": "Analysis",
    "description": "Data analysis and statistics"
  }
}
```

- [ ] **Step 6: 创建测试页面翻译**

创建 `frontend/src/i18n/locales/zh-CN/test.json`:

```json
{
  "test": {
    "title": "测试工具",
    "description": "系统测试和调试工具"
  }
}
```

创建 `frontend/src/i18n/locales/en-US/test.json`:

```json
{
  "test": {
    "title": "Test Tools",
    "description": "System testing and debugging tools"
  }
}
```

- [ ] **Step 7: 创建 API Key 测试页面翻译**

创建 `frontend/src/i18n/locales/zh-CN/api-key-test.json`:

```json
{
  "apiKeyTest": {
    "title": "Key 测试",
    "description": "API Key 连通性测试"
  }
}
```

创建 `frontend/src/i18n/locales/en-US/api-key-test.json`:

```json
{
  "apiKeyTest": {
    "title": "Key Test",
    "description": "API Key connectivity test"
  }
}
```

- [ ] **Step 8: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/
git commit -m "feat: 添加剩余页面中英文翻译文件"
```

---

## Task 12: 修改 main.js 集成 vue-i18n

**Files:**
- Modify: `frontend/src/main.js`

- [ ] **Step 1: 读取当前 main.js**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/main.js
```

- [ ] **Step 2: 修改 main.js 集成 vue-i18n**

将 `frontend/src/main.js` 修改为：

```javascript
import { createApp } from 'vue'
import naive from 'naive-ui'
import hljs from 'highlight.js/lib/core'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import i18n from './i18n'

// 配置 hljs 给 naive-ui 的 n-code 组件使用
const app = createApp(App)
app.provide('hljs', hljs)

const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(naive)

app.mount('#app')
```

- [ ] **Step 3: 验证修改**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/main.js
```

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/main.js
git commit -m "feat: 集成 vue-i18n 到 main.js"
```

---

## Task 13: 修改 Layout.vue 实现侧边栏国际化

**Files:**
- Modify: `frontend/src/components/Layout.vue`

- [ ] **Step 1: 读取当前 Layout.vue**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/components/Layout.vue
```

- [ ] **Step 2: 修改 Layout.vue**

将 `frontend/src/components/Layout.vue` 的 `<script setup>` 部分修改为：

```vue
<script setup>
import { ref, markRaw, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../store/auth'
import api from '../api'
import {
  HomeOutline,
  ChatbubblesOutline,
  PersonOutline,
  SettingsOutline,
  TimeOutline,
  DocumentTextOutline,
  FlaskOutline,
  LogOutOutline,
  TerminalOutline,
  MenuOutline,
  BulbOutline,
  HeartOutline,
  KeyOutline,
  SparklesOutline
} from '@vicons/ionicons5'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const message = useMessage()
// PC端默认展开，移动端默认折叠
const sidebarCollapsed = ref(window.innerWidth <= 768)
const userAvatar = ref('')
const avatarInput = ref(null)

// 加载用户头像
async function loadAvatar() {
  try {
    const data = await api.get('/auth/me')
    if (data.avatar) {
      userAvatar.value = data.avatar
    }
  } catch (e) {
    // 忽略
  }
}

function triggerAvatarUpload() {
  avatarInput.value?.click()
}

async function handleAvatarUpload(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 500 * 1024) {
    message.error('图片大小不能超过 500KB')
    return
  }
  const reader = new FileReader()
  reader.onload = async (ev) => {
    const base64 = ev.target.result
    try {
      await api.post('/auth/avatar', { avatar: base64 })
      userAvatar.value = base64
      message.success('头像上传成功')
    } catch (err) {
      message.error('上传失败: ' + (err?.detail || '未知错误'))
    }
  }
  reader.readAsDataURL(file)
}

onMounted(loadAvatar)

const menuItems = [
  { path: '/', label: t('sidebar.dashboard'), icon: markRaw(HomeOutline) },
  { path: '/sessions', label: t('sidebar.sessions'), icon: markRaw(PersonOutline) },
  { path: '/messages', label: t('sidebar.messages'), icon: markRaw(ChatbubblesOutline) },
  { path: '/passive-consciousness', label: t('sidebar.passiveConsciousness'), icon: markRaw(BulbOutline) },
  { path: '/active-consciousness', label: t('sidebar.activeConsciousness'), icon: markRaw(HeartOutline) },
  { path: '/free-consciousness', label: t('sidebar.freeConsciousness'), icon: markRaw(SparklesOutline) },
  { path: '/config', label: t('sidebar.config'), icon: markRaw(SettingsOutline) },
  { path: '/cron-jobs', label: t('sidebar.cronJobs'), icon: markRaw(TimeOutline) },
  { path: '/task-logs', label: t('sidebar.taskLogs'), icon: markRaw(DocumentTextOutline) },
  { path: '/system-logs', label: t('sidebar.systemLogs'), icon: markRaw(TerminalOutline) },
  { path: '/test', label: t('sidebar.test'), icon: markRaw(FlaskOutline) },
  { path: '/key-test', label: t('sidebar.keyTest'), icon: markRaw(KeyOutline) }
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

// 路由切换时关闭移动端侧边栏
watch(() => route.path, () => {
  if (window.innerWidth <= 768) {
    sidebarCollapsed.value = true
  }
})
</script>
```

同时修改模板中的硬编码文本：

将 `<span v-if="!sidebarCollapsed" class="sidebar-title">Hermes Active</span>` 保持不变（品牌名不翻译）。

将 `<span v-if="!sidebarCollapsed">退出登录</span>` 修改为 `<span v-if="!sidebarCollapsed">{{ t('sidebar.logout') }}</span>`。

将 `<span class="mobile-title">Hermes Active</span>` 保持不变。

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/components/Layout.vue
git commit -m "feat: Layout.vue 侧边栏国际化"
```

---

## Task 14: 修改 Login.vue 实现登录页国际化

**Files:**
- Modify: `frontend/src/views/Login.vue`

- [ ] **Step 1: 读取当前 Login.vue**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/views/Login.vue
```

- [ ] **Step 2: 修改 Login.vue**

将 `frontend/src/views/Login.vue` 的 `<script setup>` 部分修改为：

```vue
<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NIcon } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { PersonOutline, LockClosedOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../store/auth'
import { useConfig } from '../composables/useConfig'
import api from '../api'

const { t } = useI18n()
const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()
const { config: globalConfig, loadConfig } = useConfig()

const formRef = ref(null)
const loading = ref(false)
const avatarUrl = ref('')

const welcomeMessages = computed(() => t('login.welcome'))

const welcomeText = ref('')

function setRandomWelcome() {
  const messages = t('login.welcome')
  if (Array.isArray(messages) && messages.length > 0) {
    welcomeText.value = messages[Math.floor(Math.random() * messages.length)]
  }
}

// 加载用户头像（公开接口，不需要登录）
async function loadAvatar() {
  try {
    const data = await api.get('/auth/avatar')
    if (data.avatar) {
      avatarUrl.value = data.avatar
    }
  } catch (e) {
    // 忽略错误
  }
}

onMounted(() => {
  loadAvatar()
  setRandomWelcome()
})

const formData = reactive({
  username: '',
  password: ''
})

const rules = computed(() => ({
  username: { required: true, message: t('login.usernameRequired'), trigger: 'blur' },
  password: { required: true, message: t('login.passwordRequired'), trigger: 'blur' }
}))

async function handleLogin() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await authStore.login(formData.username, formData.password)
    message.success(t('login.loginSuccess'))
    router.push('/')
  } catch (error) {
    message.error(error?.detail || t('login.loginFailed'))
  } finally {
    loading.value = false
  }
}
</script>
```

同时修改模板中的硬编码文本：

将 `<h1>{{ globalConfig.assistant_name }}的控制台</h1>` 修改为 `<h1>{{ t('login.title', { name: globalConfig.assistant_name }) }}</h1>`。

将 `placeholder="用户名"` 修改为 `:placeholder="t('login.username')"`。

将 `placeholder="密码"` 修改为 `:placeholder="t('login.password')"`。

将 `登 录` 修改为 `{{ t('login.submit') }}`。

将 `<div class="login-footer">v0.1.0 · by {{ globalConfig.assistant_name }}</div>` 修改为 `<div class="login-footer">{{ t('login.footer', { name: globalConfig.assistant_name }) }}</div>`。

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/views/Login.vue
git commit -m "feat: Login.vue 登录页国际化"
```

---

## Task 15: 修改 Dashboard.vue 实现仪表盘国际化

**Files:**
- Modify: `frontend/src/views/Dashboard.vue`

- [ ] **Step 1: 读取当前 Dashboard.vue**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/views/Dashboard.vue
```

- [ ] **Step 2: 修改 Dashboard.vue**

将 `frontend/src/views/Dashboard.vue` 的 `<script setup>` 部分修改为：

```vue
<script setup>
import { ref, onMounted, markRaw } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ChatbubblesOutline,
  PeopleOutline,
  TimeOutline,
  TrendingUpOutline
} from '@vicons/ionicons5'
import api from '../api'
import { useConfig } from '../composables/useConfig'

const { t } = useI18n()
const loading = ref(false)
const recentMessages = ref([])
const { config, loadConfig } = useConfig()

const stats = ref([
  { label: t('dashboard.stats.totalSessions'), value: 0, icon: markRaw(ChatbubblesOutline), color: 'var(--theme-primary)' },
  { label: t('dashboard.stats.totalMessages'), value: 0, icon: markRaw(PeopleOutline), color: 'var(--theme-accent)' },
  { label: t('dashboard.stats.todayMessages'), value: 0, icon: markRaw(TimeOutline), color: '#a8e6cf' },
  { label: t('dashboard.stats.weekMessages'), value: 0, icon: markRaw(TrendingUpOutline), color: '#ffd3b6' }
])

const platforms = ref([])

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

async function loadStats() {
  try {
    const data = await api.get('/stats/overview')
    stats.value[0].value = data.total_sessions || 0
    stats.value[1].value = data.total_messages || 0
    stats.value[2].value = data.today_messages || 0
    stats.value[3].value = data.week_messages || 0

    // 加载平台分布
    const total = data.total_messages || 1
    const platformData = await api.get('/stats/platforms')
    const platformColors = { weixin: 'var(--theme-primary)', feishu: 'var(--theme-accent)', cli: '#a8e6cf', cron: '#ffd3b6' }
    platforms.value = (platformData || []).map(p => ({
      name: t(`platform.${p.platform}`) || p.platform,
      count: p.count,
      percent: Math.round((p.count / total) * 100),
      color: platformColors[p.platform] || '#999'
    }))
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

async function loadRecentMessages() {
  loading.value = true
  try {
    const data = await api.get('/messages/recent', { params: { limit: 20 } })
    recentMessages.value = (data.items || []).filter(msg => msg.content)
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // 并行加载所有数据，提高页面切换速度
  Promise.all([
    loadConfig(),
    loadStats(),
    loadRecentMessages()
  ])
})
</script>
```

同时修改模板中的硬编码文本：

将 `<n-card title="最近消息" style="margin-top: 16px">` 修改为 `<n-card :title="t('dashboard.recentMessages')" style="margin-top: 16px">`。

将 `<n-empty v-if="!loading && recentMessages.length === 0" description="暂无消息" />` 修改为 `<n-empty v-if="!loading && recentMessages.length === 0" :description="t('dashboard.noMessages')" />`。

将 `<n-card title="平台分布" style="margin-top: 16px">` 修改为 `<n-card :title="t('dashboard.platformDistribution')" style="margin-top: 16px">`。

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/views/Dashboard.vue
git commit -m "feat: Dashboard.vue 仪表盘国际化"
```

---

## Task 16: 修改 Sessions.vue 实现会话列表国际化

**Files:**
- Modify: `frontend/src/views/Sessions.vue`

- [ ] **Step 1: 读取当前 Sessions.vue**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/views/Sessions.vue
```

- [ ] **Step 2: 修改 Sessions.vue**

将 `frontend/src/views/Sessions.vue` 的 `<script setup>` 部分修改为：

```vue
<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { SearchOutline } from '@vicons/ionicons5'
import { useMessage, useDialog } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const sessions = ref([])
const searchText = ref('')
const platformFilter = ref(null)
const statusFilter = ref(null)
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)

const platformOptions = computed(() => [
  { label: t('sessions.all'), value: null },
  { label: t('platform.weixin'), value: 'weixin' },
  { label: t('platform.feishu'), value: 'feishu' },
  { label: t('platform.cli'), value: 'cli' }
])

const statusOptions = computed(() => [
  { label: t('status.active'), value: 'active' },
  { label: t('status.ended'), value: 'ended' }
])

// ... 其余代码保持不变，但需要将硬编码文本替换为 t() 调用
```

同时修改模板中的硬编码文本：

将 `placeholder="搜索会话（标题/ID）..."` 修改为 `:placeholder="t('sessions.searchPlaceholder')"`。

将 `placeholder="平台"` 修改为 `:placeholder="t('sessions.platform')"`。

将 `placeholder="状态"` 修改为 `:placeholder="t('sessions.status')"`。

将 `{{ session.source || '未知' }}` 修改为 `{{ session.source || t('sessions.unknown') }}`。

将 `删除` 修改为 `{{ t('sessions.delete') }}`。

将 `{{ session.title || '无标题' }}` 修改为 `{{ session.title || t('sessions.noTitle') }}`。

将 `消息数: {{ session.message_count || 0 }}` 修改为 `{{ t('sessions.messageCount', { count: session.message_count || 0 }) }}`。

将 `{{ session.ended_at ? '已结束' : '活跃' }}` 修改为 `{{ session.ended_at ? t('status.ended') : t('status.active') }}`。

将 `<n-empty v-if="!loading && sessions.length === 0" description="暂无会话" />` 修改为 `<n-empty v-if="!loading && sessions.length === 0" :description="t('sessions.noSessions')" />`。

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/views/Sessions.vue
git commit -m "feat: Sessions.vue 会话列表国际化"
```

---

## Task 17: 修改 Messages.vue 实现消息管理国际化

**Files:**
- Modify: `frontend/src/views/Messages.vue`

- [ ] **Step 1: 读取当前 Messages.vue**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/views/Messages.vue
```

- [ ] **Step 2: 修改 Messages.vue**

将 `frontend/src/views/Messages.vue` 的 `<script setup>` 部分修改为：

```vue
<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useConfig } from '../composables/useConfig'

const { t } = useI18n()
const message = useMessage()
const { config, loadConfig } = useConfig()
// ... 其余代码保持不变
```

同时修改模板中的硬编码文本：

将 `placeholder="搜索消息内容..."` 修改为 `:placeholder="t('messages.searchPlaceholder')"`。

将 `搜索` 修改为 `{{ t('messages.search') }}`。

将 `返回搜索` 修改为 `{{ t('messages.backToSearch') }}`。

将 `<div><strong>Session ID:</strong> {{ selectedSession.id }}</div>` 保持不变。

将 `<div><strong>标题:</strong> {{ selectedSession.title || '无标题' }}</div>` 修改为 `<div><strong>{{ t('messages.title') }}:</strong> {{ selectedSession.title || t('messages.noTitle') }}</div>`。

将 `<div><strong>用户 ID:</strong> {{ selectedSession.user_id || selectedSession.chat_id || selectedSession.source }}</div>` 修改为 `<div><strong>{{ t('messages.userId') }}:</strong> {{ selectedSession.user_id || selectedSession.chat_id || selectedSession.source }}</div>`。

将 `<div><strong>消息数:</strong> {{ selectedSession.message_count || 0 }}</div>` 修改为 `<div><strong>{{ t('messages.messageCount') }}:</strong> {{ selectedSession.message_count || 0 }}</div>`。

将 `<div><strong>状态:</strong> {{ selectedSession.ended_at ? '已结束' : '活跃' }}</div>` 修改为 `<div><strong>{{ t('messages.status') }}:</strong> {{ selectedSession.ended_at ? t('status.ended') : t('status.active') }}</div>`。

将 `<n-checkbox v-model:checked="hideTool">隐藏工具消息</n-checkbox>` 修改为 `<n-checkbox v-model:checked="hideTool">{{ t('messages.hideToolMessages') }}</n-checkbox>`。

将 `<span class="result-count">共 {{ filteredMessages.length }} 条</span>` 修改为 `<span class="result-count">{{ t('messages.totalCount', { count: filteredMessages.length }) }}</span>`。

将 `<n-empty v-if="!loading && filteredMessages.length === 0 && selectedSession" description="暂无消息" />` 修改为 `<n-empty v-if="!loading && filteredMessages.length === 0 && selectedSession" :description="t('messages.noMessages')" />`。

将 `placeholder="输入消息..."` 修改为 `:placeholder="t('messages.inputPlaceholder')"`。

将 `发送` 修改为 `{{ t('messages.send') }}`。

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/views/Messages.vue
git commit -m "feat: Messages.vue 消息管理国际化"
```

---

## Task 18: 修改 Config.vue 实现配置页国际化 + 语言切换 UI

**Files:**
- Modify: `frontend/src/views/Config.vue`
- Modify: `frontend/src/composables/useConfig.js`

- [ ] **Step 1: 读取当前 Config.vue**

```bash
cat /home/ubuntu/.hermes/hermes-active/frontend/src/views/Config.vue
```

- [ ] **Step 2: 修改 useConfig.js 添加语言配置**

将 `frontend/src/composables/useConfig.js` 修改为：

```javascript
import { ref } from 'vue'
import api from '../api'

const config = ref({
  user_name: '曹凡',
  assistant_name: '凯莉',
  locale: 'zh-CN'
})

let loaded = false

export function useConfig() {
  async function loadConfig() {
    if (loaded) return
    try {
      const [userName, assistantName, locale] = await Promise.all([
        api.get('/config/get/user_name').catch(() => null),
        api.get('/config/get/assistant_name').catch(() => null),
        api.get('/config/get/locale').catch(() => null)
      ])
      if (userName?.value) config.value.user_name = userName.value
      if (assistantName?.value) config.value.assistant_name = assistantName.value
      if (locale?.value) config.value.locale = locale.value
      loaded = true
    } catch (e) {
      // 使用默认值
    }
  }

  return { config, loadConfig }
}
```

- [ ] **Step 3: 修改 Config.vue 添加语言切换 UI**

将 `frontend/src/views/Config.vue` 的 `<script setup>` 部分修改为：

```vue
<script setup>
import { ref, onMounted, inject, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useConfig } from '../composables/useConfig'

// 从 App.vue 注入的主题函数
const applyTheme = inject('applyTheme')

const { t, locale } = useI18n()
const message = useMessage()
const activeTab = ref('basic')
const saving = ref(false)
const testing = ref(false)
const changingPassword = ref(false)
const savingUserConfig = ref(false)
const savingHindsight = ref(false)
const testingRecall = ref(false)
const testingReflect = ref(false)
const savingWeather = ref(false)
const testingWeather = ref(false)
const { config: globalConfig, loadConfig: loadGlobalConfig } = useConfig()

// 语言配置
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

const userConfig = ref({
  user_name: '曹凡',
  assistant_name: '凯莉'
})

// ... 其余代码保持不变，但需要将所有硬编码文本替换为 t() 调用
```

同时修改模板，将所有硬编码文本替换为 `t()` 调用。例如：

将 `<n-tab-pane name="basic" tab="基础配置">` 修改为 `<n-tab-pane name="basic" :tab="t('config.tabs.basic')">`。

将 `<n-card title="个性化设置" style="margin-bottom: 16px">` 修改为 `<n-card :title="t('config.personalization.title')" style="margin-bottom: 16px">`。

将 `<n-form-item label="用户名称">` 修改为 `<n-form-item :label="t('config.personalization.userName')">`。

将 `<n-form-item label="助手名称">` 修改为 `<n-form-item :label="t('config.personalization.assistantName')">`。

将 `<n-button type="primary" @click="saveUserConfig" :loading="savingUserConfig">保存</n-button>` 修改为 `<n-button type="primary" @click="saveUserConfig" :loading="savingUserConfig">{{ t('common.save') }}</n-button>`。

在"个性化设置"卡片之后添加语言设置卡片：

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

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/views/Config.vue frontend/src/composables/useConfig.js
git commit -m "feat: Config.vue 配置页国际化 + 语言切换 UI"
```

---

## Task 19: 修改剩余页面实现国际化

**Files:**
- Modify: `frontend/src/views/TaskLogs.vue`
- Modify: `frontend/src/views/PassiveConsciousness.vue`
- Modify: `frontend/src/views/ActiveConsciousness.vue`
- Modify: `frontend/src/views/FreeConsciousness.vue`
- Modify: `frontend/src/views/SystemLogs.vue`
- Modify: `frontend/src/views/Analysis.vue`
- Modify: `frontend/src/views/Test.vue`
- Modify: `frontend/src/views/ApiKeyTest.vue`

- [ ] **Step 1: 修改 TaskLogs.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

将 `statusOptions` 和 `typeOptions` 改为 `computed`：

```javascript
const statusOptions = computed(() => [
  { label: t('taskLogs.statusOptions.success'), value: 'success' },
  { label: t('taskLogs.statusOptions.failed'), value: 'failed' }
])

const typeOptions = computed(() => [
  { label: t('taskLogs.typeOptions.send_message'), value: 'send_message' },
  { label: t('taskLogs.typeOptions.generate'), value: 'generate' },
  { label: t('taskLogs.typeOptions.send_proactive'), value: 'send_proactive' },
  { label: t('taskLogs.typeOptions.cron_run'), value: 'cron_run' },
  { label: t('taskLogs.typeOptions.test_context'), value: 'test_context' }
])

const typeLabelMap = computed(() => ({
  send_message: t('taskLogs.typeOptions.send_message'),
  generate: t('taskLogs.typeOptions.generate'),
  send_proactive: t('taskLogs.typeOptions.send_proactive'),
  cron_run: t('taskLogs.typeOptions.cron_run'),
  test_context: t('taskLogs.typeOptions.test_context')
}))
```

修改模板中的硬编码文本：

将 `placeholder="状态"` 修改为 `:placeholder="t('taskLogs.statusPlaceholder')"`。

将 `placeholder="类型"` 修改为 `:placeholder="t('taskLogs.typePlaceholder')"`。

将 `刷新` 修改为 `{{ t('taskLogs.refresh') }}`。

将 `耗时: {{ log.duration.toFixed(2) }}s` 修改为 `{{ t('taskLogs.duration', { time: log.duration.toFixed(2) }) }}`。

将 `<n-empty v-if="!loading && logs.length === 0" description="暂无任务日志" />` 修改为 `<n-empty v-if="!loading && logs.length === 0" :description="t('taskLogs.noLogs')" />`。

- [ ] **Step 2: 修改 PassiveConsciousness.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

修改模板中的硬编码文本为 `t()` 调用。

- [ ] **Step 3: 修改 ActiveConsciousness.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

修改模板中的硬编码文本为 `t()` 调用。

- [ ] **Step 4: 修改 FreeConsciousness.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

修改模板中的硬编码文本为 `t()` 调用。

- [ ] **Step 5: 修改 SystemLogs.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

修改模板中的硬编码文本为 `t()` 调用。

- [ ] **Step 6: 修改 Analysis.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

修改模板中的硬编码文本为 `t()` 调用。

- [ ] **Step 7: 修改 Test.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

修改模板中的硬编码文本为 `t()` 调用。

- [ ] **Step 8: 修改 ApiKeyTest.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

修改模板中的硬编码文本为 `t()` 调用。

- [ ] **Step 9: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/views/
git commit -m "feat: 剩余页面国际化"
```

---

## Task 20: 创建会话详情页面翻译文件

**Files:**
- Create: `frontend/src/i18n/locales/zh-CN/session-detail.json`
- Create: `frontend/src/i18n/locales/en-US/session-detail.json`
- Modify: `frontend/src/views/SessionDetail.vue`

- [ ] **Step 1: 创建会话详情页翻译**

创建 `frontend/src/i18n/locales/zh-CN/session-detail.json`:

```json
{
  "sessionDetail": {
    "title": "会话详情",
    "back": "返回",
    "sessionId": "Session ID",
    "title": "标题",
    "noTitle": "无标题",
    "userId": "用户 ID",
    "platform": "平台",
    "status": "状态",
    "messageCount": "消息数",
    "startTime": "开始时间",
    "endTime": "结束时间",
    "messages": "消息列表",
    "noMessages": "暂无消息"
  }
}
```

创建 `frontend/src/i18n/locales/en-US/session-detail.json`:

```json
{
  "sessionDetail": {
    "title": "Session Detail",
    "back": "Back",
    "sessionId": "Session ID",
    "title": "Title",
    "noTitle": "Untitled",
    "userId": "User ID",
    "platform": "Platform",
    "status": "Status",
    "messageCount": "Messages",
    "startTime": "Start Time",
    "endTime": "End Time",
    "messages": "Messages",
    "noMessages": "No messages"
  }
}
```

- [ ] **Step 2: 修改 SessionDetail.vue**

在 `<script setup>` 中添加：

```javascript
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

修改模板中的硬编码文本为 `t()` 调用。

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add frontend/src/i18n/locales/zh-CN/session-detail.json frontend/src/i18n/locales/en-US/session-detail.json frontend/src/views/SessionDetail.vue
git commit -m "feat: SessionDetail.vue 会话详情国际化"
```

---

## Task 21: 验证和测试

**Files:**
- None (testing only)

- [ ] **Step 1: 启动开发服务器**

```bash
cd /home/ubuntu/.hermes/hermes-active/frontend && npm run dev
```

- [ ] **Step 2: 测试中文显示**

1. 打开浏览器访问 http://localhost:5173
2. 确认所有页面显示中文
3. 确认侧边栏菜单显示中文
4. 确认配置页面语言切换 UI 正常显示

- [ ] **Step 3: 测试语言切换**

1. 进入配置页面
2. 在"语言设置"中选择 "English"
3. 确认所有页面文本切换为英文
4. 确认 Naive UI 组件（分页、空状态）也切换为英文

- [ ] **Step 4: 测试语言持久化**

1. 切换语言后刷新页面
2. 确认语言偏好保持不变
3. 退出登录后重新登录
4. 确认语言偏好仍然保持

- [ ] **Step 5: 测试浏览器语言检测**

1. 清除 localStorage 中的 locale
2. 清除后端的 locale 配置
3. 刷新页面
4. 确认根据浏览器语言自动选择正确的语言

- [ ] **Step 6: Commit 最终版本**

```bash
cd /home/ubuntu/.hermes/hermes-active && git add -A && git commit -m "feat: 国际化功能完成"
```

---

## 验收检查清单

- [ ] 语言切换 UI 在 Config.vue 的"基础配置" Tab 中正常显示
- [ ] 切换语言后，所有页面文本立即更新
- [ ] Naive UI 组件（分页、空状态、验证消息）跟随语言切换
- [ ] 语言偏好保存到后端，下次登录自动加载
- [ ] 默认语言为中文
- [ ] 翻译缺失时显示 key 本身，不报错
- [ ] 所有 15 个页面的硬编码文本都已替换为 t() 调用
- [ ] 侧边栏菜单文本正确翻译
- [ ] 登录页面欢迎语正确翻译
- [ ] 仪表盘统计标签正确翻译
- [ ] 会话列表和详情页正确翻译
- [ ] 消息管理页面正确翻译
- [ ] 配置页面所有 Tab 内容正确翻译
- [ ] 定时任务页面正确翻译
- [ ] 任务日志页面正确翻译
- [ ] 系统日志页面正确翻译
