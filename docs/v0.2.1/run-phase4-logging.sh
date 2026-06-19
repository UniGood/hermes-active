#!/bin/bash
# v0.2.1 Phase 4 监控日志入库任务执行脚本

cd /home/ubuntu/.hermes/hermes-active

# 读取任务文件
TASK=$(cat docs/v0.2.1/phase4-logging-task.md)

# 启动 Claude Code，设置 max effort
claude -p "$TASK" \
  --effort max \
  --dangerously-skip-permissions \
  --max-turns 30 \
  --allowedTools "Read,Write,Edit,Bash" \
  --output-format json \
  > docs/v0.2.1/phase4-logging-result.json 2>docs/v0.2.1/phase4-logging-error.log

echo "=== DONE ==="
