# Hermes Agent 修改文件

hermes-active 需要对 hermes-agent 做以下修改（来自 3 个 git commit）。

## 文件清单

| 文件 | 改动量 | 说明 |
|------|--------|------|
| `gateway/extensions/__init__.py` | 新建空文件 | Python 包初始化 |
| `gateway/extensions/session_fallback.py` | 新建 151 行 | Session 回退：Gateway 内存找不到 session 时自动查 state.db |
| `gateway/run.py` | 改 3 行 | 在 `GatewayRunner.__init__()` 中激活 session_fallback |
| `hermes_state.py` | 新增 24 行 | `SessionDB.get_active_session_by_source()` 方法 |

## Git Commit 记录

```
630013152 feat: session fallback — Gateway 内存找不到 session 时自动查 state.db
5818415b9 fix: session_fallback 对比 state.db session_id，防止外部修改后内存不同步
70052b0e4 fix: session_fallback 只对比 session_id，让 _should_reset 处理过期逻辑
```

## 本目录文件说明

```
hermes-agent-patches/
├── __init__.py              # gateway/extensions/__init__.py（直接复制）
├── session_fallback.py      # gateway/extensions/session_fallback.py（直接复制）
├── run.py.patch             # gateway/run.py 改动说明（手动改 3 行）
├── hermes_state.py.patch    # hermes_state.py 改动说明（手动新增 24 行方法）
└── README.md                # 本文件
```

## 应用方法

```bash
cd ~/.hermes/hermes-agent

# 1. 复制新文件
mkdir -p gateway/extensions
cp hermes-agent-patches/__init__.py gateway/extensions/
cp hermes-agent-patches/session_fallback.py gateway/extensions/

# 2. 修改 gateway/run.py（约第 1939 行）
#    在 GatewayRunner.__init__() 中找到：
#        self.session_store = SessionStore(
#    改为：
#        from gateway.extensions.session_fallback import install_fallback
#        _SessionStore = install_fallback(SessionStore)
#        self.session_store = _SessionStore(

# 3. 修改 hermes_state.py
#    在 SessionDB 类的 resolve_session_id() 方法之前，
#    插入 get_active_session_by_source() 方法（详见 hermes_state.py.patch）

# 4. 验证
grep "install_fallback" gateway/run.py
grep "get_active_session_by_source" hermes_state.py
ls gateway/extensions/session_fallback.py
```
