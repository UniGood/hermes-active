# hermes-active v0.2 设计文档

> 从「触发式存在」到「持续式存在」

## 文档索引

### 🆕 推荐先看这个（精简方案，5天可交付）

| 文档 | 内容 | 字数 |
|------|------|------|
| [consciousness-design.md](consciousness-design.md) | **自主意识设计**：最小闭环、情绪=上次的想法、规则评分决策 | ~13K |

### 原始设计文档（完整版，14天方案）

| 文档 | 内容 | 字数 |
|------|------|------|
| [design-v0.2.md](design-v0.2.md) | 核心设计理念、架构总览、模块划分 | ~7K |
| [design-v0.2-brainstorm.md](design-v0.2-brainstorm.md) | 头脑风暴、逻辑闭环验证、完整数据流 | ~23K |
| [v0.2-implementation-plan.md](v0.2-implementation-plan.md) | 完整实施方案：6 Phase、42 任务、数据模型、完整代码 | ~54K |
| [v0.2-world-perception.md](v0.2-world-perception.md) | 外界感知层：高德天气 API 接入 | ~8K |

## 两个方案的关系

| | 精简方案 (consciousness-design) | 完整方案 (implementation-plan) |
|---|---|---|
| 情绪模型 | last_thought（自然语言） | 6 维浮点数（valence/arousal/...） |
| 心跳周期 | 10 分钟 | 5 分钟 |
| 想法生成 | LLM 直接读上下文 | 规则模板 + LLM 深度模式 |
| 决策 | 简单 3 因子公式 | 4 因子公式 + 延迟队列 |
| 交付时间 | 5 天 | 14 天 |
| 扩展性 | 后续可升级到完整版 | 已包含所有设计 |

**建议**：先实现精简方案，验证闭环可行后，再逐步扩展到完整版。
