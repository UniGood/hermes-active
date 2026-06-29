# Hermes Active 文档索引

> 项目文档统一入口

---

## 📚 核心文档

| 文档 | 说明 |
|------|------|
| [README.md](../README.md) | 项目说明 |
| [CLAUDE.md](../CLAUDE.md) | Claude Code 指南 |
| [deployment.md](./deployment.md) | 部署指南 |

---

## 🎯 版本设计文档

### v0.1 - 基础版本（已完成）

| 文档 | 说明 |
|------|------|
| [design-v0.1.md](./design-v0.1.md) | v0.1 设计文档 — 基础架构、双数据库、JWT 认证、定时任务 |

### v0.2 - 意识系统总览

| 文档 | 说明 |
|------|------|
| [design-v0.2.md](./design-v0.2.md) | v.2 设计愿景 — 从"触发式存在"到"持续式存在" |
| [v0.2-implementation-plan.md](./v0.2-implementation-plan.md) | v0.2 整体实施计划 |
| [v0.2-world-perception.md](./v0.2-world-perception.md) | 世界感知设计（待实现） |

### v0.2.1 - 主动意识（当前版本）

| 文档 | 说明 |
|------|------|
| [v0.2.1/architecture-and-flow.md](./v0.2.1/architecture-and-flow.md) | 架构与执行流程、Hindsight 双 Bank 设计 |
| [v0.2.1/active-consciousness-send-conditions.md](./v0.2.1/active-consciousness-send-conditions.md) | **发送消息条件详解** — 决策公式、阈值、保护机制 |
| [v0.2.1/thought-enhanced-design.md](./v0.2.1/thought-enhanced-design.md) | 念头增强机制 — 循环增强、天气集成、旧念头去重 |
| [v0.2.1/implementation-status.md](./v0.2.1/implementation-status.md) | 实现状态总结 — 已完成/待完成清单 |
| [v0.2.1/detailed-design.md](./v0.2.1/detailed-design.md) | 详细设计文档 |
| [v0.2.1/implementation-plan.md](./v0.2.1/implementation-plan.md) | v0.2.1 实施计划 |

### v0.2.2 - 被动意识（开发中）

| 文档 | 说明 |
|------|------|
| [v0.2/passive-consciousness-design.md](./v0.2/passive-consciousness-design.md) | 被动意识设计 — 上下文注入、配置参数、API 接口 |
| [v0.2/passive-consciousness-plugin-plan.md](./v0.2/passive-consciousness-plugin-plan.md) | 被动意识插件计划 — Hermes 插件集成方案 |
| [v0.2/consciousness-path-a.md](./v0.2/consciousness-path-a.md) | 路径 A：被动意识 — pre_llm_call 注入机制 |

### v0.2 通用设计

| 文档 | 说明 |
|------|------|
| [v0.2/consciousness-design.md](./v0.2/consciousness-design.md) | 意识系统核心设计 — 想法生成、决策引擎 |
| [v0.2/active-consciousness-design.md](./v0.2/active-consciousness-design.md) | 主动意识设计 — 心跳触发、消息发送 |
| [v0.2/phase2-task.md](./v0.2/phase2-task.md) | Phase 2 任务清单 |
| [v0.2/phase2-task-v2.md](./v0.2/phase2-task-v2.md) | Phase 2 任务清单 v2 |

---

## 📊 功能模块

### 主动意识 (v0.2.1) ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 情绪连续性 | ✅ | VA 模型、情绪演化、心跳集成 |
| 时间窗口决策 | ✅ | 时间权重、多维度决策公式 |
| 念头系统增强 | ✅ | 类型分类、Hindsight 存储 |
| 延迟发送队列 | ✅ | 队列存储、重新评估 |
| 增强念头生成 | ✅ | 天气集成、旧念头去重 |

### 被动意识 (v0.2.2) 🚧

| 功能 | 状态 | 说明 |
|------|------|------|
| 配置管理 | ✅ | get_config / update_config |
| 状态查询 | ✅ | 想念分数、聊天热度、情绪值 |
| Hindsight 集成 | ✅ | Recall / Reflect 测试 |
| 天气感知 | ✅ | 高德地图 API |
| 上下文注入 | 🚧 | 用户消息时自动注入到系统提示词 |

---

## 📁 文档结构

```
docs/
├── README.md                          # 本文件
├── deployment.md                      # 部署指南
├── design-v0.1.md                     # v0.1 设计文档
├── design-v0.2.md                     # v0.2 设计愿景
├── v0.2-implementation-plan.md        # v0.2 实施计划
├── v0.2-world-perception.md           # 世界感知设计
├── v0.2/                              # v0.2 意识系统设计
│   ├── README.md
│   ├── consciousness-design.md
│   ├── active-consciousness-design.md
│   ├── consciousness-path-a.md
│   ├── passive-consciousness-design.md
│   ├── passive-consciousness-plugin-plan.md
│   ├── phase2-task.md
│   └── phase2-task-v2.md
├── v0.2.1/                            # 主动意识详细设计
│   ├── architecture-and-flow.md
│   ├── thought-enhanced-design.md
│   ├── implementation-status.md
│   ├── detailed-design.md
│   ├── implementation-plan.md
│   └── architecture.html
└── archive/                           # 历史文档
    ├── FIX_TASK.md
    ├── design-v0.2-brainstorm.md
    ├── fix-session-sync.md
    ├── session-expired-handling.md
    ├── session-sync-fix-plan.md
    ├── session-sync-fallback-plan.md
    └── session-sync-implementation.md
```

---

## 🔗 相关链接

- [Hermes Agent](https://github.com/UniGood/hermes-agent) — 主系统
- [Hindsight](https://github.com/UniGood/hindsight) — 记忆系统

---

**最后更新**：2026-06-19
**当前版本**：v0.2.1（主动意识）/ v0.2.2（被动意识开发中）
