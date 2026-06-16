#!/bin/bash
# v0.2.1 设计方案深度审查脚本

cd /home/ubuntu/.hermes/hermes-active

# 读取任务文件
TASK=$(cat docs/v0.2.1/design-review-task.md)

# 启动 Claude Code，设置 max effort
claude -p "$TASK" \
  --effort max \
  --dangerously-skip-permissions \
  --max-turns 50 \
  --output-format json \
  > docs/v0.2.1/design-review-result.json 2>docs/v0.2.1/design-review-error.log

echo "=== DONE ==="
