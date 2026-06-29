# Deployment Guide

## Overview

This directory contains deployment files for Hermes Active.

## Contents

```
deployment/
├── README.md                          # This file
├── systemd/
│   └── hermes-active-backend.service  # Systemd user service
└── hermes-agent-patches/
    └── session_fallback.py            # Gateway session sync extension
```

## Quick Start

### 1. Systemd Service

```bash
# Copy service file
mkdir -p ~/.config/systemd/user/
cp systemd/hermes-active-backend.service ~/.config/systemd/user/

# Edit paths in the service file
vi ~/.config/systemd/user/hermes-active-backend.service

# Enable and start
systemctl --user daemon-reload
systemctl --user enable hermes-active-backend.service
systemctl --user start hermes-active-backend.service
```

### 2. Gateway Session Sync

The `session_fallback.py` extension is **already included in the default Hermes Agent installation** at `~/.hermes/hermes-agent/gateway/extensions/session_fallback.py`.

Only copy it manually if you're using a custom/forked Hermes Agent that doesn't include it:

```bash
cp hermes-agent-patches/session_fallback.py ~/.hermes/hermes-agent/gateway/extensions/
```

Then ensure this code exists in `gateway/run.py` (around line 2178):

```python
from gateway.extensions.session_fallback import install_fallback
_SessionStore = install_fallback(SessionStore)
```

## Prerequisites

| Component | Required | Notes |
|-----------|----------|-------|
| Python 3.12+ | ✅ | Hermes Agent's venv recommended |
| Node.js 18+ | ✅ | Frontend build only |
| Hermes Agent | ✅ | Must be installed at `~/.hermes/hermes-agent/` |
| Hindsight | Optional | For memory features (Recall/Reflect) |
| Amap API Key | Optional | For weather perception |

## Directory Layout After Deployment

```
~/.hermes/
├── hermes-agent/           # Hermes Agent (existing installation)
│   ├── venv/               # Python virtual environment
│   ├── agent/
│   │   ├── auxiliary_client.py   # LLM calls (imported by hermes-active)
│   │   └── prompt_builder.py     # Soul/persona loading
│   ├── hermes_state.py           # SessionDB (imported by hermes-active)
│   └── gateway/
│       └── extensions/
│           └── session_fallback.py  # Session sync extension
│
├── hermes-active/          # This project
│   ├── backend/            # FastAPI backend
│   ├── frontend/           # Vue 3 frontend (built)
│   ├── data/
│   │   └── active.db       # Active database (auto-created)
│   ├── deployment/         # This directory
│   └── docs/               # Documentation
│
├── state.db                # Hermes Agent's state database (read by hermes-active)
├── SOUL.md                 # Soul/persona definition
├── MEMORY.md               # Memory file
├── .env                    # Environment variables (API keys)
└── config.yaml             # Hermes Agent configuration
```

## Verification

After deployment, verify everything works:

```bash
# 1. Backend health check
curl http://localhost:18720/health
# Expected: {"status":"ok","version":"0.1.0"}

# 2. Systemd service status
systemctl --user status hermes-active-backend.service

# 3. Backend logs
tail -f ~/.hermes/hermes-active/data/backend.log

# 4. Database exists
ls -la ~/.hermes/hermes-active/data/active.db

# 5. Frontend accessible
# Open http://localhost:18720 in browser
# Login: admin / admin
```

## Troubleshooting

### Port 18720 already in use

```bash
fuser -k 18720/tcp
systemctl --user restart hermes-active-backend.service
```

### API returns HTML instead of JSON

This means an old process is running. Kill it and restart:

```bash
fuser 18720/tcp  # Get PID
cat /proc/PID/cwd/main.py  # Verify it's hermes-active
fuser -k 18720/tcp
systemctl --user restart hermes-active-backend.service
```

### Cannot import hermes-agent modules

Ensure the Python path is correct. The backend's `main.py` adds `~/.hermes/hermes-agent` to `sys.path`. If using a separate venv, make sure it can access hermes-agent modules.

### Gateway doesn't see proactive messages

Check that `session_fallback` is installed:

```bash
grep -n "session_fallback\|install_fallback" ~/.hermes/hermes-agent/gateway/run.py
# Should show 2 lines (import + activation)
```
