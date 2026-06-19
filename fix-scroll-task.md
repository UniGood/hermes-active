# Task: 修复心跳日志表格移动端左右滑动问题

## 问题描述
主动意识页面的心跳日志表格在移动端不能左右滑动，导致右边的"操作"列看不到。

## 当前实现
文件：`/home/ubuntu/.hermes/hermes-active/frontend/src/views/ActiveConsciousness.vue`

当前代码：
```vue
<n-tab-pane name="heartbeats" tab="心跳日志">
  <div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
    <n-data-table :columns="heartbeatColumns" :data="heartbeats.items" :pagination="heartbeatPagination" @update:page="loadHeartbeats" :scroll-x="800" />
  </div>
</n-tab-pane>
```

列定义：
```js
const heartbeatColumns = [
  { title: '时间', key: 'created_at', width: 100, render: (row) => formatTime(row.created_at) },
  { title: '耗时(ms)', key: 'duration_ms', width: 80 },
  { title: '召回数量', key: 'recall_count', width: 70 },
  { title: '生成想法', key: 'thoughts_generated', width: 70 },
  { title: '发送消息', key: 'message_sent', width: 70 },
  {
    title: '操作',
    key: 'actions',
    width: 70,
    render(row) {
      return h(
        NButton,
        { size: 'small', type: 'info', onClick: () => showHeartbeatDetails(row) },
        { default: () => '详情' }
      )
    }
  }
]
```

## 可能的原因
1. naive-ui 的 n-data-table 的 scroll-x 属性可能和外层 overflow-x 冲突
2. 表格容器可能有 max-width 或 width: 100% 限制
3. 需要检查 naive-ui 的 n-data-table 正确的水平滚动实现方式

## 要求
1. 修复移动端（窄屏幕）表格能左右滑动
2. 不要破坏桌面端的显示
3. 测试验证修复有效
4. 只修改 ActiveConsciousness.vue 文件，不要改其他文件
5. 不要改 vite.config.js、config.py 等配置文件

## 验证方式
修改后运行 `cd /home/ubuntu/.hermes/hermes-active/frontend && npm run build` 确保构建成功
