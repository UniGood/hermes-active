# hermes-active 文档索引

> 项目文档统一入口

---

## 📚 核心文档

| 文档 | 说明 | 状态 |
|------|------|------|
| [README.md](../README.md) | 项目说明 | ✅ 最新 |
| [CLAUDE.md](../CLAUDE.md) | Claude Code 指南 | ✅ 最新 |
| [DEPLOY.md](../DEPLOY.md) | 部署指南 | ✅ 最新 |

---

## 🎯 版本设计文档

### v0.1 - 基础版本

| 文档 | 说明 |
|------|------|
| [design-v0.1.md](./design-v0.1.md) | v0.1 设计文档（基础架构） |

### v0.2 - 主动意识增强

| 文档 | 说明 |
|------|------|
| [design-v0.2.md](./design-v0.2.md) | v0.2 设计方案（借鉴 Hermes_Soul_patch） |
| [design-v0.2-brainstorm.md](./design-v0.2-brainstorm.md) | v0.2 头脑风暴 |
| [v0.2-implementation-plan.md](./v0.2-implementation-plan.md) | v0.2 实施计划 |
| [v0.2-world-perception.md](./v0.2-world-perception.md) | v0.2 世界感知设计 |

### v0.2.1 - 主动意识细化

| 文档 | 说明 |
|------|------|
| [v0.2.1/implementation-plan.md](./v0.2.1/implementation-plan.md) | v0.2.1 实施计划 |
| [v0.2.1/implementation-status.md](./v0.2.1/implementation-status.md) | v0.2.1 实现状态 ✅ |
| [v0.2.1/detailed-design.md](./v0.2.1/detailed-design.md) | v0.2.1 详细设计 |
| [v0.2.1/architecture.html](./v0.2.1/architecture.html) | 架构图（HTML） |
| [v0.2.1/claude-code-task.md](./v0.2.1/claude-code-task.md) | Claude Code 任务清单 |

---

## 🔧 问题修复文档

### Session 同步问题

| 文档 | 说明 | 状态 |
|------|------|------|
| [fix-session-sync.md](./fix-session-sync.md) | Session 不同步修复方案 | ✅ 已修复 |
| [session-expired-handling.md](./session-expired-handling.md) | Session 过期处理 | ✅ 已实现 |
| [session-sync-fix-plan.md](./session-sync-fix-plan.md) | Session 同步修复计划 | 📝 存档 |
| [session-sync-fallback-plan.md](./session-sync-fallback-plan.md) | Session 同步降级方案 | 📝 存档 |
| [session-sync-implementation.md](./session-sync-implementation.md) | Session 同步实现细节 | 📝 存档 |

---

## 📊 v0.2.1 功能实现状态

### ✅ 已完成功能

| 功能 | 说明 |
|------|------|
| 情绪连续性 | VA 模型、情绪演化、心跳集成 |
| 时间窗口决策 | 时间权重、多维度决策公式 |
| 念头系统增强 | 类型分类、Hindsight 存储 |
| 延迟发送队列 | 队列存储、重新评估 |

### 🚧 待实现功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 世界状态 | World State 事件系统 | 中 |
| 每日种子 | Daily Seed 自动生成日程 | 中 |
| 情绪可视化 | 情绪趋势图表 | 低 |
| 单元测试 | 核心逻辑测试覆盖 | 中 |

---

## 🎨 前端页面

| 页面 | 路由 | 说明 |
|------|------|------|
| Dashboard | `/` | 监控面板 |
| Sessions | `/sessions` | Session 列表 |
| SessionDetail | `/sessions/:id` | Session 详情 |
| Messages | `/messages` | 消息管理 |
| Config | `/config` | 配置管理 |
| PassiveConsciousness | `/passive-consciousness` | 被动意识 |
| ActiveConsciousness | `/active-consciousness` | 主动意识 |
| CronJobs | `/cron-jobs` | 定时任务 |
| TaskLogs | `/task-logs` | 任务日志 |
| SystemLogs | `/system-logs` | 系统日志 |
| Test | `/test` | 测试工具 |
| ApiKeyTest | `/key-test` | API Key 测试 |

---

## 🔗 相关链接

- [Hermes Agent](https://github.com/UniGood/hermes-agent) - 主系统
- [Hermes_Soul_patch](https://github.com/gejifeng/Hermes_Soul_patch) - 参考项目
- [Hindsight](https://github.com/UniGood/hindsight) - 记忆系统

---

**最后更新**：2026-06-18
