#!/bin/bash

################################################################################
# CLAW.AI 测试执行脚本
#
# 用途: 自动化执行项目的所有测试（单元测试、集成测试、覆盖率测试等）
# 使用方法: ./scripts/run-tests.sh [选项]
#
# 选项:
#   -u, --unit          只运行单元测试
#   -i, --integration   只运行集成测试
#   -e, --e2e           只运行 E2E 测试
#   -c, --coverage      生成覆盖率报告
#   -v, --verbose       详细输出
#   -h, --help          显示帮助信息
#
# 示例:
#   ./scripts/run-tests.sh                    # 运行所有测试
#   ./scripts/run-tests.sh -u                 # 只运行单元测试
#   ./scripts/run-tests.sh -c                 # 运行所有测试并生成覆盖率报告
#   ./scripts/run-tests.sh -u -c -v           # 运行单元测试，生成覆盖率报告，详细输出
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 配置
BACKEND_DIR="$PROJECT_ROOT"
FRONTEND_DIR="$PROJECT_ROOT/../claw-ai-frontend"
TEST_REPORT_DIR="$PROJECT_ROOT/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 标志
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_E2E=false
RUN_COVERAGE=false
VERBOSE=false

# 函数: 打印信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# 函数: 打印成功
print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 函数: 打印警告
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 函数: 打印错误
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数: 打印分隔线
print_separator() {
    echo "================================================================================"
}

# 函数: 显示帮助
show_help() {
    cat << EOF
CLAW.AI 测试执行脚本

用途: 自动化执行项目的所有测试

用法: $0 [选项]

选项:
  -u, --unit          只运行单元测试
  -i, --integration   只运行集成测试
  -e, --e2e           只运行 E2E 测试
  -c, --coverage      生成覆盖率报告
  -v, --verbose       详细输出
  -h, --help          显示帮助信息

示例:
  $0                    # 运行所有测试
  $0 -u                 # 只运行单元测试
  $0 -c                 # 运行所有测试并生成覆盖率报告
  $0 -u -c -v           # 运行单元测试，生成覆盖率报告，详细输出

EOF
}

# 函数: 解析参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--unit)
                RUN_UNIT=true
                RUN_INTEGRATION=false
                RUN_E2E=false
                shift
                ;;
            -i|--integration)
                RUN_UNIT=false
                RUN_INTEGRATION=true
                RUN_E2E=false
                shift
                ;;
            -e|--e2e)
                RUN_UNIT=false
                RUN_INTEGRATION=false
                RUN_E2E=true
                shift
                ;;
            -c|--coverage)
                RUN_COVERAGE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 函数: 创建测试报告目录
create_report_dir() {
    if [ ! -d "$TEST_REPORT_DIR" ]; then
        mkdir -p "$TEST_REPORT_DIR"
        print_info "创建测试报告目录: $TEST_REPORT_DIR"
    fi
}

# 函数: 检查依赖
check_dependencies() {
    print_info "检查依赖..."

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装"
        exit 1
    fi
    print_success "Python 3: $(python3 --version)"

    # 检查 pytest
    if ! python3 -m pytest --version &> /dev/null; then
        print_error "pytest 未安装"
        exit 1
    fi
    print_success "pytest: $(python3 -m pytest --version)"

    # 检查 Node.js（前端测试）
    if [ -d "$FRONTEND_DIR" ]; then
        if ! command -v node &> /dev/null; then
            print_warning "Node.js 未安装，跳过前端测试"
        else
            print_success "Node.js: $(node --version)"
        fi
    fi

    # 检查 Docker（集成测试）
    if ! command -v docker &> /dev/null; then
        print_warning "Docker 未安装，集成测试可能无法运行"
    else
        print_success "Docker: $(docker --version)"
    fi
}

# 函数: 运行后端单元测试
run_backend_unit_tests() {
    print_separator
    print_info "运行后端单元测试..."
    print_separator

    local coverage_args=""
    if [ "$RUN_COVERAGE" = true ]; then
        coverage_args="--cov=app --cov-report=html --cov-report=term --cov-report=xml"
    fi

    local verbose_args=""
    if [ "$VERBOSE" = true ]; then
        verbose_args="-v -s"
    fi

    cd "$BACKEND_DIR"

    python3 -m pytest tests/ \
        $coverage_args \
        $verbose_args \
        --tb=short \
        --maxfail=5 \
        --durations=10 \
        -m "not integration and not e2e" \
        || {
            print_error "后端单元测试失败"
            return 1
        }

    print_success "后端单元测试完成"

    # 如果生成覆盖率报告
    if [ "$RUN_COVERAGE" = true ]; then
        local coverage_report="$BACKEND_DIR/htmlcov/index.html"
        if [ -f "$coverage_report" ]; then
            print_info "覆盖率报告: file://$coverage_report"
        fi
    fi
}

# 函数: 运行后端集成测试
run_backend_integration_tests() {
    print_separator
    print_info "运行后端集成测试..."
    print_separator

    local coverage_args=""
    if [ "$RUN_COVERAGE" = true ]; then
        coverage_args="--cov=app --cov-report=html --cov-report=term --cov-report=xml"
    fi

    local verbose_args=""
    if [ "$VERBOSE" = true ]; then
        verbose_args="-v -s"
    fi

    cd "$BACKEND_DIR"

    # 检查测试环境是否运行
    if ! docker ps | grep -q "postgres\|redis"; then
        print_warning "测试环境未运行，尝试启动..."
        docker-compose -f docker-compose.staging.yml up -d postgres redis
        sleep 10
    fi

    python3 -m pytest tests/ \
        $coverage_args \
        $verbose_args \
        --tb=short \
        --maxfail=5 \
        --durations=10 \
        -m "integration" \
        || {
        print_error "后端集成测试失败"
        return 1
    }

    print_success "后端集成测试完成"

    # 如果生成覆盖率报告
    if [ "$RUN_COVERAGE" = true ]; then
        local coverage_report="$BACKEND_DIR/htmlcov/index.html"
        if [ -f "$coverage_report" ]; then
            print_info "覆盖率报告: file://$coverage_report"
        fi
    fi
}

# 函数: 运行前端单元测试
run_frontend_unit_tests() {
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_warning "前端目录不存在: $FRONTEND_DIR"
        return 0
    fi

    print_separator
    print_info "运行前端单元测试..."
    print_separator

    cd "$FRONTEND_DIR"

    # 检查依赖是否安装
    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install || {
            print_error "安装前端依赖失败"
            return 1
        }
    fi

    # 运行测试
    if [ "$RUN_COVERAGE" = true ]; then
        npm run test -- --coverage || {
            print_error "前端单元测试失败"
            return 1
        }
    else
        npm run test || {
            print_error "前端单元测试失败"
            return 1
        }
    fi

    print_success "前端单元测试完成"
}

# 函数: 运行 E2E 测试
run_e2e_tests() {
    print_separator
    print_info "运行 E2E 测试..."
    print_separator

    cd "$BACKEND_DIR"

    # 检查 E2E 测试环境
    if ! docker ps | grep -q "postgres\|redis\|milvus"; then
        print_warning "E2E 测试环境未运行，尝试启动..."
        docker-compose -f docker-compose.staging.yml up -d
        sleep 20
    fi

    # 运行 E2E 测试
    python3 -m pytest tests/ \
        -v -s \
        --tb=short \
        --maxfail=3 \
        --durations=10 \
        -m "e2e" \
        || {
        print_error "E2E 测试失败"
        return 1
    }

    print_success "E2E 测试完成"
}

# 函数: 生成测试报告
generate_test_report() {
    print_separator
    print_info "生成测试报告..."
    print_separator

    local report_file="$TEST_REPORT_DIR/test_report_$TIMESTAMP.txt"

    cat > "$report_file" << EOF
CLAW.AI 测试报告
================================================================================

测试时间: $(date)
测试环境: $(uname -s) $(uname -m)
Python 版本: $(python3 --version)

================================================================================
测试结果
================================================================================

后端单元测试: $([ "$BACKEND_UNIT_PASS" = true ] && echo "✓ 通过" || echo "✗ 失败")
后端集成测试: $([ "$BACKEND_INTEGRATION_PASS" = true ] && echo "✓ 通过" || echo "✗ 失败")
前端单元测试: $([ "$FRONTEND_UNIT_PASS" = true ] && echo "✓ 通过" || echo "✗ 失败")
E2E 测试: $([ "$E2E_PASS" = true ] && echo "✓ 通过" || echo "✗ 失败")

================================================================================
EOF

    if [ "$RUN_COVERAGE" = true ]; then
        echo "覆盖率信息:" >> "$report_file"
        echo "" >> "$report_file"
        echo "后端覆盖率报告: file://$BACKEND_DIR/htmlcov/index.html" >> "$report_file"
        if [ -d "$FRONTEND_DIR/coverage" ]; then
            echo "前端覆盖率报告: file://$FRONTEND_DIR/coverage/index.html" >> "$report_file"
        fi
        echo "" >> "$report_file"
    fi

    print_success "测试报告生成: $report_file"
}

# 函数: 清理临时文件
cleanup() {
    print_info "清理临时文件..."
    # 删除 __pycache__
    find "$BACKEND_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$BACKEND_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    # 删除 .pytest_cache
    find "$BACKEND_DIR" -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
}

# 函数: 主函数
main() {
    print_separator
    print_info "CLAW.AI 测试执行脚本"
    print_info "开始时间: $(date)"
    print_separator

    # 解析参数
    parse_args "$@"

    # 创建报告目录
    create_report_dir

    # 检查依赖
    check_dependencies

    # 初始化测试结果
    BACKEND_UNIT_PASS=true
    BACKEND_INTEGRATION_PASS=true
    FRONTEND_UNIT_PASS=true
    E2E_PASS=true

    # 运行测试
    if [ "$RUN_UNIT" = true ]; then
        run_backend_unit_tests || BACKEND_UNIT_PASS=false
        if [ -d "$FRONTEND_DIR" ]; then
            run_frontend_unit_tests || FRONTEND_UNIT_PASS=false
        fi
    fi

    if [ "$RUN_INTEGRATION" = true ]; then
        run_backend_integration_tests || BACKEND_INTEGRATION_PASS=false
    fi

    if [ "$RUN_E2E" = true ]; then
        run_e2e_tests || E2E_PASS=false
    fi

    # 生成测试报告
    generate_test_report

    # 清理临时文件
    cleanup

    # 输出结果
    print_separator
    print_info "测试总结"
    print_separator

    local all_passed=true
    if [ "$BACKEND_UNIT_PASS" = false ]; then
        print_error "后端单元测试失败"
        all_passed=false
    fi
    if [ "$BACKEND_INTEGRATION_PASS" = false ]; then
        print_error "后端集成测试失败"
        all_passed=false
    fi
    if [ "$FRONTEND_UNIT_PASS" = false ]; then
        print_error "前端单元测试失败"
        all_passed=false
    fi
    if [ "$E2E_PASS" = false ]; then
        print_error "E2E 测试失败"
        all_passed=false
    fi

    print_separator
    print_info "结束时间: $(date)"
    print_separator

    if [ "$all_passed" = true ]; then
        print_success "所有测试通过！"
        exit 0
    else
        print_error "部分测试失败！"
        exit 1
    fi
}

# 运行主函数
main "$@"
