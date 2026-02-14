#!/bin/bash

################################################################################
# CLAW.AI - 数据库迁移脚本
# 功能：执行数据库迁移、种子数据导入等
################################################################################

set -e
set -u

# ====================
# 配置变量
# ====================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目路径
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 配置文件
ENV_FILE=".env.prod"
COMPOSE_FILE="docker-compose.prod.yml"

# 日志文件
LOG_FILE="$PROJECT_DIR/logs/migrate-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

# ====================
# 日志函数
# ====================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

# ====================
# 检查函数
# ====================

check_env() {
    log_info "检查环境..."

    if [ ! -f "$ENV_FILE" ]; then
        log_error "环境配置文件 $ENV_FILE 不存在"
        exit 1
    fi

    # 加载环境变量
    source "$ENV_FILE"

    if [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
        log_error "数据库配置不完整"
        exit 1
    fi

    log_success "环境检查通过"
}

check_docker() {
    log_info "检查 Docker 状态..."

    if ! docker ps | grep -q claw_ai_postgres; then
        log_error "PostgreSQL 容器未运行"
        exit 1
    fi

    log_success "Docker 运行正常"
}

wait_for_db() {
    log_info "等待数据库就绪..."

    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker exec claw_ai_postgres pg_isready -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" &>/dev/null; then
            log_success "数据库已就绪"
            return 0
        fi
        attempt=$((attempt + 1))
        log_info "等待数据库... ($attempt/$max_attempts)"
        sleep 2
    done

    log_error "数据库未能在预期时间内就绪"
    exit 1
}

# ====================
# 数据库操作函数
# ====================

create_database() {
    log_info "检查数据库是否存在..."

    local db_exists=$(docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB:-claw_ai}'" 2>/dev/null || echo "")

    if [ "$db_exists" != "1" ]; then
        log_info "创建数据库 ${POSTGRES_DB:-claw_ai}..."
        docker exec claw_ai_postgres createdb -U "${POSTGRES_USER:-claw_ai}" "${POSTGRES_DB:-claw_ai}"
        log_success "数据库创建成功"
    else
        log_info "数据库已存在"
    fi
}

create_extensions() {
    log_info "创建数据库扩展..."

    local extensions=("uuid-ossp" "pg_trgm" "vector")

    for ext in "${extensions[@]}"; do
        docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" -c "CREATE EXTENSION IF NOT EXISTS \"$ext\";" 2>/dev/null || true
        log_info "扩展 $ext 已安装"
    done

    log_success "数据库扩展创建完成"
}

run_init_script() {
    local init_script="$PROJECT_DIR/scripts/init-db.sql"

    if [ ! -f "$init_script" ]; then
        log_warning "初始化脚本不存在: $init_script"
        return 0
    fi

    log_info "运行数据库初始化脚本..."

    docker exec -i claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" < "$init_script"

    log_success "初始化脚本执行完成"
}

run_alembic_migration() {
    log_info "运行 Alembic 数据库迁移..."

    # 检查 alembic.ini 是否存在
    if [ ! -f "$PROJECT_DIR/alembic.ini" ]; then
        log_warning "未找到 Alembic 配置文件，跳过 Alembic 迁移"
        return 0
    fi

    # 在后端容器中运行迁移
    if docker ps | grep -q claw_ai_backend; then
        docker exec claw_ai_backend alembic upgrade head

        if [ $? -eq 0 ]; then
            log_success "Alembic 迁移完成"
        else
            log_error "Alembic 迁移失败"
            return 1
        fi
    else
        log_warning "后端容器未运行，跳过 Alembic 迁移"
    fi
}

run_sql_migration() {
    local migration_dir="$PROJECT_DIR/migrations"

    if [ ! -d "$migration_dir" ]; then
        log_info "未找到迁移目录: $migration_dir"
        return 0
    fi

    log_info "运行 SQL 迁移脚本..."

    # 创建迁移记录表
    docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" -c "
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    " &>/dev/null || true

    # 按文件名排序执行迁移
    for migration_file in "$migration_dir"/*.sql; do
        if [ -f "$migration_file" ]; then
            local version=$(basename "$migration_file" .sql)

            # 检查是否已执行
            local applied=$(docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" -tAc "SELECT 1 FROM schema_migrations WHERE version='$version'" 2>/dev/null || echo "")

            if [ "$applied" = "1" ]; then
                log_info "迁移 $version 已执行，跳过"
                continue
            fi

            log_info "执行迁移: $version"
            docker exec -i claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" < "$migration_file"

            if [ $? -eq 0 ]; then
                # 记录迁移
                docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" -c "INSERT INTO schema_migrations (version) VALUES ('$version');" &>/dev/null || true
                log_success "迁移 $version 执行成功"
            else
                log_error "迁移 $version 执行失败"
                return 1
            fi
        fi
    done

    log_success "SQL 迁移完成"
}

import_seed_data() {
    local seed_dir="$PROJECT_DIR/seeds"

    if [ ! -d "$seed_dir" ]; then
        log_info "未找到种子数据目录: $seed_dir"
        return 0
    fi

    log_info "导入种子数据..."

    for seed_file in "$seed_dir"/*.sql; do
        if [ -f "$seed_file" ]; then
            local name=$(basename "$seed_file" .sql)
            log_info "导入种子数据: $name"

            docker exec -i claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" < "$seed_file"

            if [ $? -eq 0 ]; then
                log_success "种子数据 $name 导入成功"
            else
                log_warning "种子数据 $name 导入失败"
            fi
        fi
    done

    log_success "种子数据导入完成"
}

# ====================
# 验证函数
# ====================

verify_migration() {
    log_info "验证迁移结果..."

    # 检查关键表是否存在
    local tables=("users" "knowledge_base" "conversations" "messages")
    local failed=0

    for table in "${tables[@]}"; do
        local exists=$(docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='$table'" 2>/dev/null || echo "")

        if [ "$exists" = "1" ]; then
            log_info "表 $table 存在"
        else
            log_warning "表 $table 不存在"
            failed=1
        fi
    done

    if [ $failed -eq 0 ]; then
        log_success "迁移验证通过"
    else
        log_warning "部分表不存在，可能需要运行完整的应用迁移"
    fi
}

show_migration_status() {
    log_info "数据库迁移状态..."

    # 显示迁移记录
    docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" -c "
        SELECT version, applied_at
        FROM schema_migrations
        ORDER BY applied_at;
    " 2>/dev/null || log_warning "无法获取迁移记录"

    # 显示表列表
    docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d "${POSTGRES_DB:-claw_ai}" -c "\dt" 2>/dev/null || true
}

# ====================
# 回滚函数
# ====================

rollback_migration() {
    local version="$1"

    log_info "回滚到版本: $version"

    # Alembic 回滚
    if [ -f "$PROJECT_DIR/alembic.ini" ] && docker ps | grep -q claw_ai_backend; then
        docker exec claw_ai_backend alembic downgrade "$version"

        if [ $? -eq 0 ]; then
            log_success "Alembic 回滚完成"
        else
            log_error "Alembic 回滚失败"
            return 1
        fi
    else
        log_warning "无法执行回滚，请手动处理"
    fi
}

# ====================
# 主流程
# ====================

main() {
    echo ""
    echo "========================================"
    echo "  CLAW.AI 数据库迁移脚本"
    echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""

    # 解析命令行参数
    ACTION="migrate"
    VERSION=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --init)
                ACTION="init"
                shift
                ;;
            --seed)
                ACTION="seed"
                shift
                ;;
            --status)
                ACTION="status"
                shift
                ;;
            --rollback)
                ACTION="rollback"
                VERSION="$2"
                shift 2
                ;;
            --fresh)
                ACTION="fresh"
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --init              初始化数据库（创建数据库、扩展）"
                echo "  --seed              导入种子数据"
                echo "  --status            显示迁移状态"
                echo "  --rollback <ver>    回滚到指定版本"
                echo "  --fresh             重新初始化数据库（危险！）"
                echo "  --help              显示帮助信息"
                echo ""
                echo "示例:"
                echo "  $0                  # 执行迁移"
                echo "  $0 --init           # 初始化数据库"
                echo "  $0 --seed           # 导入种子数据"
                echo "  $0 --fresh          # 重新初始化（删除所有数据）"
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                echo "使用 --help 查看帮助信息"
                exit 1
                ;;
        esac
    done

    check_env
    check_docker
    wait_for_db

    case "$ACTION" in
        init)
            create_database
            create_extensions
            run_init_script
            ;;
        seed)
            import_seed_data
            ;;
        status)
            show_migration_status
            ;;
        rollback)
            rollback_migration "$VERSION"
            ;;
        fresh)
            log_warning "⚠️  此操作将删除所有数据！"
            read -p "确认继续？(yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                docker exec claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB:-claw_ai};"
                create_database
                create_extensions
                run_init_script
                import_seed_data
                run_alembic_migration
                run_sql_migration
                verify_migration
            else
                log_info "操作已取消"
            fi
            ;;
        migrate)
            create_database
            create_extensions
            run_init_script
            run_alembic_migration
            run_sql_migration
            import_seed_data
            verify_migration
            ;;
    esac

    echo ""
    echo "========================================"
    echo "  迁移完成！"
    echo "========================================"
    echo ""
    log_success "数据库迁移已完成"
    log_info "迁移日志: $LOG_FILE"
    echo ""
}

# 执行主流程
main "$@"
