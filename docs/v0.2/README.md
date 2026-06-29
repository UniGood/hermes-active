# v0.2 意识系统设计文档

> 自主意识模块 — 独立页面、独立 LLM、跨 session 想法生成

---

## 两条路径

| | 路径 A：被动意识 (v0.2.2) | 路径 B：主动意识 (v0.2.1) |
|---|---|---|
| **触发** | 用户消息到达 | 心跳计时器 |
| **机制** | Hermes 插件注入 system 消息 | 独立异步发送 |
| **用户感知** | 凯莉回复中自然融入话题 | 凯莉主动发消息 |
| **核心依赖** | hermes-active-hook（pre_llm_call） | message_service（异步发送） |
| **状态** | 🚧 开发中 | ✅ 已完成 |

---

## 核心理念

- **情绪 = VA 模型**（Valence/Arousal/Social Need，由时间演化 + LLM 评估驱动）
- **想法生成 = 跨 session 提取 + Hindsight 记忆 + LLM 生成**（三步流程）
- **聊天热度 = count ÷ hours**（消息密度，不是简单数量）
- **决策 = 规则评分**（不用 LLM，所有阈值从配置读取）
- **所有参数可配置**（不硬编码任何阈值）

---

## 文档索引

### 核心设计

| 文档 | 说明 |
|------|------|
| [consciousness-design.md](./consciousness-design.md) | 意识系统核心设计 — 完整闭环、三步想法生成、22 个配置参数 |
| [active-consciousness-design.md](./active-consciousness-design.md) | 主动意识设计 — 心跳触发、消息发送 |
| [consciousness-path-a.md](./consciousness-path-a.md) | 路径 A：被动意识 — pre_llm_call 注入、标记格式 |

### 被动意识 (v0.2.2)

| 文档 | 说明 |
|------|------|
| [passive-consciousness-design.md](./passive-consciousness-design.md) | 被动意识设计 — 上下文注入、配置参数、API 接口 |
| [passive-consciousness-plugin-plan.md](./passive-consciousness-plugin-plan.md) | 被动意识插件计划 — Hermes 插件集成方案 |

### 任务清单

| 文档 | 说明 |
|------|------|
| [phase2-task.md](./phase2-task.md) | Phase 2 任务清单 |
| [phase2-task-v2.md](./phase2-task-v2.md) | Phase 2 任务清单 v2 |

---

## 相关文档

- [v0.2.1 实现状态](../v0.2.1/implementation-status.md) — 主动意识已完成的功能清单
- [v0.2.1 架构与流程](../v0.2.1/architecture-and-flow.md) — 主动意识详细架构

---

**最后更新**：2026-06-19
