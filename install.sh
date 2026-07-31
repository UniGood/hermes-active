#!/bin/bash
# 被动意识插件自动化安装脚本
# Usage: bash install.sh [--enable] [--disable] [--status] [--test]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
PLUGIN_NAME="passive-consciousness"
PLUGIN_DIR="$HOME/.hermes/plugins/$PLUGIN_NAME"
HERMES_ACTIVE_DIR="$HOME/.hermes/hermes-active"
CONFIG_FILE="$HOME/.hermes/config.yaml"
BACKEND_PORT=18720

# 打印带颜色的消息
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    info "Checking dependencies..."

    # 检查 hermes 命令
    if ! command -v hermes &> /dev/null; then
        error "hermes command not found"
        exit 1
    fi

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        error "python3 not found"
        exit 1
    fi

    # 检查 pip
    if ! command -v pip3 &> /dev/null; then
        error "pip3 not found"
        exit 1
    fi

    info "Dependencies OK"
}

# 安装插件文件
install_plugin_files() {
    info "Installing plugin files..."

    # 创建插件目录
    mkdir -p "$PLUGIN_DIR"

    # 检查源目录
    SOURCE_DIR="$HERMES_ACTIVE_DIR/plugins/$PLUGIN_NAME"
    if [ ! -d "$SOURCE_DIR" ]; then
        error "Source directory not found: $SOURCE_DIR"
        exit 1
    fi

    # 复制文件
    cp -r "$SOURCE_DIR"/* "$PLUGIN_DIR/"

    # 验证文件
    if [ ! -f "$PLUGIN_DIR/__init__.py" ]; then
        error "Plugin entry file not found: $PLUGIN_DIR/__init__.py"
        exit 1
    fi

    if [ ! -f "$PLUGIN_DIR/plugin.yaml" ]; then
        error "Plugin config not found: $PLUGIN_DIR/plugin.yaml"
        exit 1
    fi

    info "Plugin files installed"
}

# 启用插件
enable_plugin() {
    info "Enabling plugin..."

    # 使用 hermes 命令启用
    hermes plugins enable "$PLUGIN_NAME" --no-tool-override 2>/dev/null || {
        warn "hermes plugins enable failed, trying manual config..."

        # 手动修改配置
        if grep -q "passive-consciousness" "$CONFIG_FILE" 2>/dev/null; then
            info "Plugin already in config"
        else
            # 添加到 enabled 列表
            sed -i '/^plugins:/,/^[^ ]/{
                /^  enabled:/,/^[^ ]/{
                    /^    - agnes-ai$/a\    - passive-consciousness
                }
            }' "$CONFIG_FILE"
        fi
    }

    info "Plugin enabled"
}

# 禁用插件
disable_plugin() {
    info "Disabling plugin..."

    hermes plugins disable "$PLUGIN_NAME" 2>/dev/null || {
        warn "hermes plugins disable failed, trying manual config..."

        # 从配置中移除
        sed -i '/passive-consciousness/d' "$CONFIG_FILE"
    }

    info "Plugin disabled"
}

# 安装 Python 依赖
install_dependencies() {
    info "Installing Python dependencies..."

    cd "$HERMES_ACTIVE_DIR/backend"
    pip3 install -r requirements.txt -q

    info "Dependencies installed"
}

# 启动后端服务
start_backend() {
    info "Starting backend service..."

    # 检查是否已在运行
    if curl -s "http://localhost:$BACKEND_PORT/api/passive-consciousness/status" > /dev/null 2>&1; then
        info "Backend already running"
        return
    fi

    # 启动服务
    cd "$HERMES_ACTIVE_DIR/backend"
    nohup python3 main.py > /tmp/hermes-active.log 2>&1 &
    sleep 3

    # 验证启动
    if curl -s "http://localhost:$BACKEND_PORT/api/passive-consciousness/status" > /dev/null 2>&1; then
        info "Backend started"
    else
        error "Backend failed to start"
        cat /tmp/hermes-active.log
        exit 1
    fi
}

# 更新数据库
update_database() {
    info "Updating database..."

    DB_FILE="$HOME/.hermes/hermes-active/data/active.db"

    if [ ! -f "$DB_FILE" ]; then
        warn "Database not found: $DB_FILE"
        return
    fi

    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cursor = conn.cursor()

# 添加新列
for col_def in [
    'ALTER TABLE passive_consciousness_logs ADD COLUMN template_id TEXT',
    'ALTER TABLE passive_consciousness_logs ADD COLUMN context_preview TEXT',
]:
    try:
        cursor.execute(col_def)
    except sqlite3.OperationalError:
        pass  # 列已存在

conn.commit()
conn.close()
print('Database updated')
" || warn "Database update failed (may not exist yet)"

    info "Database updated"
}

# 显示状态
show_status() {
    echo ""
    echo "=== Plugin Status ==="
    hermes plugins list | grep -i "passive\|consciousness" || echo "Plugin not found"

    echo ""
    echo "=== Backend Status ==="
    if curl -s "http://localhost:$BACKEND_PORT/api/passive-consciousness/status" > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is running${NC}"
    else
        echo -e "${RED}Backend is not running${NC}"
    fi

    echo ""
    echo "=== Config Status ==="
    if grep -q "passive-consciousness" "$CONFIG_FILE" 2>/dev/null; then
        echo -e "${GREEN}Plugin in config${NC}"
    else
        echo -e "${RED}Plugin not in config${NC}"
    fi
}

# 运行测试
run_tests() {
    info "Running tests..."

    # 测试后端 API
    echo ""
    echo "=== Testing Backend API ==="

    # 测试配置接口
    echo -n "Config API: "
    if curl -s "http://localhost:$BACKEND_PORT/api/passive-consciousness/config" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi

    # 测试模板接口
    echo -n "Template API: "
    if curl -s "http://localhost:$BACKEND_PORT/api/passive-consciousness/templates" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi

    # 测试天气接口
    echo -n "Weather API: "
    if curl -s "http://localhost:$BACKEND_PORT/api/passive-consciousness/weather" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi

    # 测试分析接口
    echo -n "Analysis API: "
    if curl -s "http://localhost:$BACKEND_PORT/api/passive-consciousness/analysis/stats" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi

    # 测试上下文注入
    echo ""
    echo "=== Testing Context Injection ==="
    curl -s -X POST "http://localhost:$BACKEND_PORT/api/passive-consciousness/test/context" | python3 -c "
import json, sys
data = json.load(sys.stdin)
steps = data.get('steps', [])
errors = data.get('errors', [])
context = data.get('context', '')

print(f'Steps: {len(steps)}')
for step in steps:
    status = '✅' if step.get('ok') else '❌'
    print(f'  {status} {step[\"name\"]}')

print(f'Errors: {len(errors)}')
print(f'Context length: {len(context)} chars')

if errors:
    print('\\nErrors:')
    for err in errors:
        print(f'  - {err}')

sys.exit(0 if len(errors) == 0 else 1)
"
}

# 完整安装
full_install() {
    echo "=== Passive Consciousness Plugin Installation ==="
    echo ""

    check_dependencies
    install_plugin_files
    install_dependencies
    enable_plugin
    update_database
    start_backend

    echo ""
    echo "=== Installation Complete ==="
    show_status
}

# 显示帮助
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --install     Full installation (default)"
    echo "  --enable      Enable plugin only"
    echo "  --disable     Disable plugin"
    echo "  --status      Show plugin status"
    echo "  --test        Run tests"
    echo "  --help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                    # Full installation"
    echo "  $0 --enable           # Enable plugin"
    echo "  $0 --status           # Check status"
    echo "  $0 --test             # Run tests"
}

# 主函数
main() {
    case "${1:-}" in
        --enable)
            check_dependencies
            enable_plugin
            show_status
            ;;
        --disable)
            disable_plugin
            show_status
            ;;
        --status)
            show_status
            ;;
        --test)
            run_tests
            ;;
        --help|-h)
            show_help
            ;;
        --install|"")
            full_install
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
