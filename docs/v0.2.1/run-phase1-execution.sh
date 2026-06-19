#!/bin/bash
# v0.2.1 Phase 1 执行脚本

cd /home/ubuntu/.hermes/hermes-active

# 读取任务文件
TASK=$(cat docs/v0.2.1/phase1-execution-task.md)

# 启动 Claude Code，设置 max effort
claude -p "$TASK" \
  --effort max \
  --dangerously-skip-permissions \
  --max-turns 40 \
  --allowedTools "Read,Write,Edit,Bash" \
  --output-format json \
  > docs/v0.2.1/phase1-execution-result.json 2>docs/v0.2.1/phase1-execution-error.log

echo "=== DONE ==="
