# Passive Consciousness Plugin Installation Guide

## Quick Install (Automated)

Use the hermes CLI tool for one-click installation:

```bash
hermes plugins enable passive-consciousness
```

## Manual Installation

### 1. Verify Plugin Files

```bash
# Check plugin directory
ls -la ~/.hermes/plugins/passive-consciousness/

# If not exists, copy from hermes-active
mkdir -p ~/.hermes/plugins/passive-consciousness/
cp -r ~/.hermes/hermes-active/plugins/passive-consciousness/* ~/.hermes/plugins/passive-consciousness/
```

### 2. Enable Plugin

Edit `~/.hermes/config.yaml`:

```yaml
plugins:
  disabled: []
  enabled:
    - agnes-ai
    - passive-consciousness  # Add this line
```

### 3. Start Backend Service

```bash
cd ~/.hermes/hermes-active/backend
python main.py
```

### 4. Configure Plugin

Access Web UI: `http://localhost:5173` → Passive Consciousness page

## Verify Installation

```bash
# Check plugin status
hermes plugins list | grep passive

# Check backend service
curl http://localhost:18720/api/passive-consciousness/status

# Test context injection
curl -X POST http://localhost:18720/api/passive-consciousness/test/context
```

## Features

The plugin automatically injects the following context when user messages arrive:

- 🎭 Emotional state (intensity and label)
- 🔥 Chat heat (message density in last hour)
- 💕 Longing score (based on last message time)
- 🌤 Weather info (optional, requires API Key)
- 📖 Hindsight memories (optional)
- 💭 Reflection (optional)

## Configuration

| Config | Description | Default |
|--------|-------------|---------|
| `enabled` | Master switch | `false` |
| `platforms.enabled` | Enable platform filtering | `false` |
| `platforms.whitelist` | Enabled platforms list | `["weixin"]` |
| `weather.enabled` | Enable weather perception | `false` |
| `weather.provider` | Weather service provider | `qweather` |
| `weather.city` | Query city | `北京` |

## Troubleshooting

### Plugin Not Loading

```bash
# Check if plugin is enabled
hermes plugins list

# Check backend service
curl http://localhost:18720/api/passive-consciousness/config
```

### Context Injection Failed

```bash
# View logs
tail -f ~/.hermes/logs/hermes.log | grep passive_consciousness

# Test full flow
curl -X POST http://localhost:18720/api/passive-consciousness/test/context
```

## Uninstall

```bash
hermes plugins disable passive-consciousness
```

## Detailed Documentation

See: [docs/plugin-installation.md](./docs/plugin-installation.md)
