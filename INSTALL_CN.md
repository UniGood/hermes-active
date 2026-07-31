# 被动意识插件安装指南

## 快速安装（自动化）

使用 hermes 命令行工具一键安装：

```bash
hermes plugins enable passive-consciousness
```

## 手动安装

### 1. 确认插件文件

```bash
# 检查插件目录
ls -la ~/.hermes/plugins/passive-consciousness/

# 如果不存在，从 hermes-active 复制
mkdir -p ~/.hermes/plugins/passive-consciousness/
cp -r ~/.hermes/hermes-active/plugins/passive-consciousness/* ~/.hermes/plugins/passive-consciousness/
```

### 2. 启用插件

编辑 `~/.hermes/config.yaml`：

```yaml
plugins:
  disabled: []
  enabled:
    - agnes-ai
    - passive-consciousness  # 添加这一行
```

### 3. 启动后端服务

```bash
cd ~/.hermes/hermes-active/backend
python main.py
```

### 4. 配置插件

访问 Web UI：`http://localhost:5173` → 被动意识页面

## 验证安装

```bash
# 检查插件状态
hermes plugins list | grep passive

# 检查后端服务
curl http://localhost:18720/api/passive-consciousness/status

# 测试上下文注入
curl -X POST http://localhost:18720/api/passive-consciousness/test/context
```

## 功能说明

插件会在用户消息到达时自动注入以下上下文：

- 🎭 情绪状态（强度和标签）
- 🔥 聊天热度（近 1 小时消息密度）
- 💕 想念程度（基于最后消息时间）
- 🌤 天气信息（可选，需配置 API Key）
- 📖 Hindsight 记忆（可选）
- 💭 综合反思（可选）

## 配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `enabled` | 总开关 | `false` |
| `platforms.enabled` | 启用平台过滤 | `false` |
| `platforms.whitelist` | 启用的平台列表 | `["weixin"]` |
| `weather.enabled` | 启用天气感知 | `false` |
| `weather.provider` | 天气服务提供商 | `qweather` |
| `weather.city` | 查询城市 | `北京` |

## 故障排除

### 插件未加载

```bash
# 检查插件是否启用
hermes plugins list

# 检查后端服务
curl http://localhost:18720/api/passive-consciousness/config
```

### 上下文注入失败

```bash
# 查看日志
tail -f ~/.hermes/logs/hermes.log | grep passive_consciousness

# 测试完整流程
curl -X POST http://localhost:18720/api/passive-consciousness/test/context
```

## 卸载

```bash
hermes plugins disable passive-consciousness
```

## 详细文档

参见：[docs/plugin-installation.md](./docs/plugin-installation.md)
