# hermes-active v0.2 设计文档

> 自主意识模块 — 独立页面、独立 LLM、跨 session 想法生成

## 文档索引

| 文档 | 内容 |
|------|------|
| [consciousness-design.md](consciousness-design.md) | **核心设计**：完整闭环、三步想法生成、22 个配置参数 |
| [consciousness-path-a.md](consciousness-path-a.md) | **路径 A：被动意识** — pre_llm_call 注入、标记格式 |

## 两条路径

| | 路径 A：被动意识 | 路径 B：主动意识 |
|---|---|---|
| **触发** | 用户消息到达 | 心跳计时器 |
| **机制** | Hermes 插件注入 system 消息 | 独立异步发送 |
| **用户感知** | 凯莉回复中自然融入话题 | 凯莉主动发消息 |
| **核心依赖** | hermes-active-hook（pre_llm_call） | message_service（异步发送） |

## 核心理念

- **情绪 = 想念分数**（0-1 浮点数，由空白时长驱动）
- **想法生成 = 跨 session 提取 + Hindsight 记忆 + LLM 生成**（三步流程）
- **聊天热度 = count ÷ hours**（消息密度，不是简单数量）
- **情绪值 = LLM 判断**（聊工作 0.1 vs 聊情感 0.8）
- **决策 = 规则评分**（不用 LLM，所有阈值从配置读取）
- **所有参数可配置**（不硬编码任何阈值）
