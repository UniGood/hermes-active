# Task: Design Tokens 地基（前端颜色收编）

## STRICT RULES
- 只改 `frontend/src/` 下的文件：新建 `frontend/src/styles/tokens.css`，修改含颜色硬编码的 vue/js/css 文件（App.vue、ActiveConsciousness.vue、CronJobs.vue、Dashboard.vue、Layout.vue 等 18 个，用 grep 定位）。
- Do NOT touch: `backend/**`、`vite.config.js`、`package.json`、`.env`、任何测试文件。
- Do NOT run git commands. Do NOT 盲 sed 全局替换（会误伤渐变），逐文件 grep 定位后替换。
- 注释用中文。cwd = 项目根。

## Context
hermes-active 前端（Vue3+Naive UI）。155 行颜色硬编码散落 18 个文件。建 Design Tokens 统一。色值取自设计规格：凯莉色 #FF6B4A。

## Steps
1. 新建 `frontend/src/styles/tokens.css`：
```css
/* 设计变量（凯莉色情感层 + 技术底座） */
:root {
  --kelly: #FF6B4A;
  --kelly-soft: rgba(255, 107, 74, 0.15);
  --bg-base: #0E1116;
  --bg-card: #161B22;
  --text-primary: #E6EDF3;
  --text-secondary: #8B949E;
  --border: #21262D;
  --ok: #3FB950;
  --warn: #D29922;
  --err: #F85149;
}
```
在全局样式入口导入（`main.js` 或 App.vue 样式引入处，与现有全局样式同处）。
2. 批量收编（映射规则）：
- 橙系主色（#FF6B4A、#FF7849、#ff6a00 等珊瑚橙）→ `var(--kelly)`；橙色透明底 → `var(--kelly-soft)`
- 白/亮白文字（#fff、#ffffff、#E6EDF3、#f5f5f5）→ `var(--text-primary)`（白底上的深色文字保持原样）
- 灰文字（#999、#8B949E、#aaa、#666）→ `var(--text-secondary)`
- 深底（#0E1116、#0d1117、#0a0e14）→ `var(--bg-base)`；卡底（#161B22、#1a1f26）→ `var(--bg-card)`；边框（#21262D、#30363d）→ `var(--border)`
- 状态色（#F85149/#ff4d4f→`--err`、#3FB950/#52c41a→`--ok`、#D29922/#faad14→`--warn`）
- **不迁**：渐变 stops 里的 VA 三色功能色序列（效价红→橙→绿、唤醒蓝→橙→红、社交灰→橙→紫）、孤立特殊色
3. 验证（全部要过）：
```bash
cd /home/ubuntu/.hermes/hermes-active/frontend && npm run build   # 必须 ✓ built
grep -rn "#FF6B4A\|#0E1116\|#161B22\|#21262D\|#E6EDF3\|#8B949E" src --include=*.vue --include=*.js | grep -v tokens.css | wc -l   # 目标 <10
```

## After making changes
输出改动摘要（tokens.css + 每文件替换行数）。不跑 git。
