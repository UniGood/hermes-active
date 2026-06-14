# hermes-active 部署文档

## Session 同步扩展（2026-06-14）

### 问题描述

hermes-active 和 Gateway 的 SessionStore 各自独立运行，导致：
- hermes-active 创建的 session 写入 state.db 和 sessions.json
- Gateway 的 SessionStore 只加载 sessions.json 一次，不会自动同步
- 用户发消息时，Gateway 创建新 session，主动消息和用户消息分散到不同 session

### 解决方案

在 Gateway 中安装 session fallback 扩展，当内存中找不到 session 时，自动从 state.db 加载。

### 修改的文件

| 文件 | 改动 |
|------|------|
| `extensions/session_reload.py` | 新建，session fallback 扩展 |
| `extensions/__init__.py` | 新建，包初始化 |
| `hermes_state.py` | 添加 `get_latest_session_by_source()` 方法 |
| `gateway/run.py` | 初始化时安装扩展（单行导入） |

### 工作原理

```
Gateway 启动
    ↓
SessionStore 初始化
    ↓
install_session_fallback() 注入 fallback 逻辑
    ↓
用户发消息 → get_or_create_session()
    ↓
内存 _entries 找不到 session
    ↓
fallback → state.db.get_latest_session_by_source()
    ↓
找到 → 加载到内存 → 使用同一 session ✅
没找到 → 创建新 session（正常逻辑）
```

### 验证方法

```bash
# 1. 检查扩展文件存在
ls -la ~/.hermes/hermes-agent/extensions/

# 2. 检查 Python 语法
python3 -c "import py_compile; py_compile.compile('$HOME/.hermes/hermes-agent/extensions/session_reload.py', doraise=True)"

# 3. 检查 Gateway 日志中的 fallback 安装
grep "session_fallback" ~/.hermes/logs/gateway.log

# 4. 测试 session 同步
# 发送主动消息后，检查 session 是否一致
```

### 回滚方法

如果需要回滚：
1. 删除 `gateway/run.py` 中的扩展导入代码（4行）
2. 重启 Gateway

```bash
# 找到并删除以下代码块：
#         # 安装 session fallback：从 state.db 加载 session
#         try:
#             from extensions.session_reload import install_session_fallback
#             install_session_fallback(self.session_store)
#         except Exception as e:
#             logger.warning("Session fallback 安装失败: %s", e)
```

### 注意事项

1. **不修改 Hermes 核心代码**：扩展通过 monkey-patch 方式注入，不改变原有逻辑
2. **向后兼容**：fallback 只在内存找不到时触发，不影响正常流程
3. **性能影响**：只在首次找不到 session 时查一次 state.db，之后从内存读取
4. **日志记录**：fallback 触发时会记录日志，便于排查问题
