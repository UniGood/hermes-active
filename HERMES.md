# Hermes Active — Superpowers 引导文件

> 本文件由 superpowers-zh 安装器自动生成，供 Hermes Agent 在会话开始时加载。

## 项目概述

Hermes Active 是 Hermes Agent 的主动会话管理系统，提供 Web UI 界面管理消息、监控状态、配置定时任务等。

- **后端**: FastAPI (端口 18720)
- **前端**: Vue 3 + Naive UI (端口 5173)
- **数据库**: state.db (只读) + active.db (读写)

## 工具映射

技能中引用的 Claude Code 工具名称对应 Hermes Agent 的等价工具：

| 技能中引用 | Hermes Agent 工具 |
|-----------|------------------|
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `patch` |
| `Bash` | `terminal` |
| `Grep` / `Glob` | `search_files` |
| `Skill` | `skill_view` |
| `Task`（子智能体） | `delegate_task` |
| `WebSearch` | `web_search` |
| `WebFetch` | `web_extract` |
| `TodoWrite` | `todo` |

## 可用 Superpowers 技能

### 核心工作流
- **brainstorming** — 创建功能前先探索意图和设计
- **writing-plans** — 编写实现计划
- **executing-plans** — 按计划执行任务
- **test-driven-development** — TDD 红绿重构
- **systematic-debugging** — 四阶段根因调试
- **verification-before-completion** — 完成前必须验证

### 代码质量
- **requesting-code-review** — 请求代码审查
- **receiving-code-review** — 处理审查反馈
- **finishing-a-development-branch** — 分支收尾

### 中文专属
- **chinese-code-review** — 中文 review 话术
- **chinese-commit-conventions** — 中文 commit 规范
- **chinese-documentation** — 中文排版规范
- **chinese-git-workflow** — 国内 Git 平台配置

### 高级技能
- **dispatching-parallel-agents** — 并行派发任务
- **subagent-driven-development** — 子智能体驱动开发
- **writing-skills** — 创建和验证技能
- **mcp-builder** — MCP 服务器构建
- **workflow-runner** — 运行 YAML 工作流
- **using-git-worktrees** — Git worktree 隔离开发

## 核心规则

1. **先思考再动手** — 创建功能前使用 `brainstorming`
2. **先测试再写代码** — 使用 `test-driven-development`
3. **先排查再修复** — 使用 `systematic-debugging`
4. **先验证再宣称完成** — 使用 `verification-before-completion`
5. **技能优先** — 如果有 1% 可能性某个技能适用，就必须加载它

## 加载技能

```bash
# 浏览所有可用技能
skills_list

# 加载某个技能的完整内容
skill_view("brainstorming")

# 查看技能的引用文件
skill_view("using-superpowers", "references/hermes-tools.md")
```
