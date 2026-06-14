# hermes-active v0.2 设计文档

> 从「触发式存在」到「持续式存在」

## 文档索引

| 文档 | 内容 |
|------|------|
| [consciousness-design.md](consciousness-design.md) | **核心设计**：闭环架构、想法生成流程（跨 session + Hindsight）、决策引擎、配置设计、实施计划 |
| [consciousness-config-design.md](consciousness-config-design.md) | **配置卡片设计**：UI 布局、参数清单、API 设计、测试按钮 |

## 核心理念

- **情绪 = 上次的想法**（自然语言，不是浮点数）
- **想法生成 = 跨 session 提取 + Hindsight 记忆 + LLM 生成**（三步流程）
- **决策 = 规则评分**（不用 LLM，所有阈值从配置读取）
- **所有参数可配置**（不硬编码任何阈值）
