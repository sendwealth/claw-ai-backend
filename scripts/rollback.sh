#!/bin/bash

################################################################################
# CLAW.AI - 回滚脚本
# 功能：将系统回滚到之前的稳定版本
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

# 备份目录
BACKUP_ROOT_DIR="$PROJECT_DIR/backups"

# 日志文件
LOG_FILE="$PROJECT_DIR/logs/rollback-$(date +%Y%m%d-%H%M%S).log"
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

    log_success "环境检查通过"
}

check_docker() {
    log_info "检查 Docker 状态..."

    if ! docker ps &> /dev/null; then
        log_error "Docker 未运行"
        exit 1
    fi

    log_success "Docker 运行正常"
}

# ====================
# 备份列表函数
# ====================

list_backups() {
    echo ""
    echo "========================================"
    echo "  可用的备份列表"
    echo "========================================"
    echo ""

    # 按时间排序列出备份
    local backups=$(find "$BACKUP_ROOT_DIR" -maxdepth 2 -type d -name "20*" | sort -r)

    if [ -z "$backups" ]; then
        log_error "没有找到可用的备份"
        exit 1
    fi

    local index=1
    for backup in $backups; do
        local backup_name=$(basename "$backup")
        local backup_path=$(dirname "$backup")

        # 计算备份大小
        local size=$(du -sh "$backup" 2>/dev/null | cut -f1)

        # 显示备份信息
        if [ "$backup_path" = "$BACKUP_ROOT_DIR/daily" ]; then
            echo "  [$index] $backup_name (每日备份, 大小: $size)"
        elif [ "$backup_path" = "$BACKUP_ROOT_DIR/weekly" ]; then
            echo "  [$index] $backup_name (每周备份, 大小: $size)"
        elif [ "$backup_path" = "$BACKUP_ROOT_DIR/monthly" ]; then
            echo "  [$index] $backup_name (每月备份, 大小: $size)"
        else
            echo "  [$index] $backup_name (大小: $size)"
        fi

        index=$((index + 1))
    done

    echo ""
}

select_backup() {
    local backup_index="$1"
    local backup_dir

    backup_dir=$(find "$BACKUP_ROOT_DIR" -maxdepth 2 -type d -name "20*" | sort -r | sed -n "${backup_index}p")

    if [ -z "$backup_dir" ]; then
        log_error "无效的备份索引: $backup_index"
        exit 1
    fi

    echo "$backup_dir"
}

# ====================
# 快照函数
# ====================

take_snapshot() {
    log_info "创建当前系统快照..."

    local snapshot_dir="$BACKUP_ROOT_DIR/pre-rollback-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$snapshot_dir"

    # 保存当前配置
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$snapshot_dir/"
    fi

    if [ -f "nginx/nginx.conf" ]; then
        cp "nginx/nginx.conf" "$snapshot_dir/"
    fi

    # 保存当前镜像标签
    docker images --format "{{.Repository}}:{{.Tag}}" | grep "claw" > "$snapshot_dir/images.txt"

    log_success "系统快照已创建: $snapshot_dir"
    echo "$snapshot_dir"
}

# ====================
# 回滚函数
# ====================

rollback_services() {
    local backup_dir="$1"

    log_info "回滚服务..."

    # 停止所有服务
    log_info "停止所有服务..."
    docker-compose -f "$COMPOSE_FILE" down

    # 恢复配置文件
    log_info "恢复配置文件..."
    if [ -f "$backup_dir/config/.env.prod" ]; then
        cp "$backup_dir/config/.env.prod" "$ENV_FILE"
        log_success "环境配置已恢复"
    fi

    if [ -f "$backup_dir/config/nginx.conf" ]; then
        cp "$backup_dir/config/nginx.conf" "nginx/nginx.conf"
        log_success "Nginx 配置已恢复"
    fi

    # 恢复 Docker Compose 配置
    if [ -f "$backup_dir/config/docker-compose.prod.yml" ]; then
        cp "$backup_dir/config/docker-compose.prod.yml" "$COMPOSE_FILE"
        log_success "Docker Compose 配置已恢复"
    fi

    # 启动服务
    log_info "启动服务..."
    docker-compose -f "$COMPOSE_FILE" up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    log_success "服务已回滚"
}

rollback_database() {
    local backup_dir="$1"

    log_info "回滚数据库..."

    # 加载环境变量
    source "$ENV_FILE"

    # 检查备份文件
    local db_backup="$backup_dir/postgres-${POSTGRES_DB:-claw_ai}.sql.gz"

    if [ ! -f "$db_backup" ]; then
        log_error "数据库备份文件不存在: $db_backup"
        return 1
    fi

    # 检查容器是否运行
    if ! docker ps | grep -q claw_ai_postgres; then
        log_error "PostgreSQL 容器未运行"
        return 1
    fi

    # 恢复数据库
    log_info "恢复数据库内容..."
    gunzip < "$db_backup" | \
        docker exec -i claw_ai_postgres psql -U "${POSTGRES_USER:-claw_ai}" "${POSTGRES_DB:-claw_ai}"

    if [ $? -eq 0 ]; then
        log_success "数据库回滚完成"
    else
        log_error "数据库回滚失败"
        return 1
    fi
}

rollback_redis() {
    local backup_dir="$1"

    log_info "回滚 Redis..."

    # 检查备份文件
    local redis_backup="$backup_dir/redis-dump.rdb"

    if [ ! -f "$redis_backup" ]; then
        log_warning "Redis 备份文件不存在，跳过 Redis 回滚"
        return 0
    fi

    # 检查容器是否运行
    if ! docker ps | grep -q claw_ai_redis; then
        log_error "Redis 容器未运行"
        return 1
    fi

    # 停止 Redis
    log_info "停止 Redis 服务..."
    docker exec claw_ai_redis redis-cli SHUTDOWN NOSAVE

    # 恢复 RDB 文件
    log_info "恢复 Redis 数据..."
    docker cp "$redis_backup" claw_ai_redis:/data/dump.rdb

    # 启动 Redis
    docker-compose -f "$COMPOSE_FILE" start redis

    # 等待 Redis 启动
    sleep 5

    log_success "Redis 回滚完成"
}

rollback_milvus() {
    local backup_dir="$1"

    log_info "回滚 Milvus..."

    local milvus_backup="$backup_dir/milvus"

    if [ ! -d "$milvus_backup" ]; then
        log_warning "Milvus 备份不存在，跳过 Milvus 回滚"
        return 0
    fi

    # 恢复 etcd 数据
    if [ -d "$milvus_backup/etcd" ] && docker ps | grep -q claw_ai_etcd; then
        log_info "恢复 Milvus etcd 数据..."
        docker-compose -f "$COMPOSE_FILE" stop etcd
        docker run --rm -v clawd_etcd_data:/etcd \
            -v "$milvus_backup/etcd":/backup \
            alpine sh -c "rm -rf /etcd/* && cp -a /backup/. /etcd/"
        docker-compose -f "$COMPOSE_FILE" start etcd
        sleep 5
        log_success "Milvus etcd 数据已恢复"
    fi

    # 恢复 MinIO 数据
    if [ -d "$milvus_backup/minio_data" ] && docker ps | grep -q claw_ai_minio; then
        log_info "恢复 Milvus MinIO 数据..."
        docker-compose -f "$COMPOSE_FILE" stop minio
        docker run --rm -v clawd_minio_data:/minio_data \
            -v "$milvus_backup/minio_data":/backup \
            alpine sh -c "rm -rf /minio_data/* && cp -a /backup/. /minio_data/"
        docker-compose -f "$COMPOSE_FILE" start minio
        sleep 5
        log_success "Milvus MinIO 数据已恢复"
    fi

    log_success "Milvus 回滚完成"
}

rollback_uploads() {
    local backup_dir="$1"

    log_info "回滚上传文件..."

    local uploads_backup="$backup_dir/uploads.tar.gz"

    if [ ! -f "$uploads_backup" ]; then
        log_warning "上传文件备份不存在，跳过上传文件回滚"
        return 0
    fi

    # 备份当前上传文件
    local current_uploads="$PROJECT_DIR/uploads"
    local backup_uploads="$BACKUP_ROOT_DIR/current-uploads-$(date +%Y%m%d-%H%M%S)"

    if [ -d "$current_uploads" ]; then
        mv "$current_uploads" "$backup_uploads"
    fi

    # 恢复上传文件
    mkdir -p "$current_uploads"
    tar -xzf "$uploads_backup" -C "$current_uploads"

    log_success "上传文件回滚完成"
    log_info "原上传文件已备份到: $backup_uploads"
}

# ====================
# 验证函数
# ====================

verify_rollback() {
    log_info "验证回滚结果..."

    local failed=0

    # 检查 PostgreSQL
    if docker ps | grep -q claw_ai_postgres; then
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready &>/dev/null; then
            log_success "PostgreSQL 运行正常"
        else
            log_error "PostgreSQL 未正常运行"
            failed=1
        fi
    fi

    # 检查 Redis
    if docker ps | grep -q claw_ai_redis; then
        if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping &>/dev/null; then
            log_success "Redis 运行正常"
        else
            log_error "Redis 未正常运行"
            failed=1
        fi
    fi

    # 检查后端服务
    if docker ps | grep -q claw_ai_backend; then
        if curl -f -s http://localhost:8000/health &>/dev/null; then
            log_success "后端服务运行正常"
        else
            log_error "后端服务未正常运行"
            failed=1
        fi
    fi

    if [ $failed -eq 0 ]; then
        log_success "回滚验证通过"
    else
        log_error "回滚验证失败，请检查服务状态"
        return 1
    fi
}

# ====================
# 通知函数
# ====================

send_notification() {
    local status="$1"
    local backup_dir="$2"

    if [ -z "${WEBHOOK_URL:-}" ]; then
        return 0
    fi

    log_info "发送回滚通知..."

    local message="CLAW.AI 系统回滚: $status"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"$message\",
            \"timestamp\": \"$timestamp\",
            \"backup_dir\": \"$backup_dir\",
            \"status\": \"$status\"
        }" &>/dev/null || true

    log_info "通知已发送"
}

# ====================
# 主流程
# ====================

main() {
    echo ""
    echo "========================================"
    echo "  CLAW.AI 系统回滚脚本"
    echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""
    echo "⚠️  警告：此操作将回滚系统到之前的备份状态"
    echo "⚠️  当前系统状态将被覆盖"
    echo ""

    # 解析命令行参数
    BACKUP_DIR=""
    SKIP_DB=false
    SKIP_REDIS=false
    SKIP_MILVUS=false
    SKIP_UPLOADS=false
    AUTO_CONFIRM=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --list)
                list_backups
                exit 0
                ;;
            --skip-db)
                SKIP_DB=true
                shift
                ;;
            --skip-redis)
                SKIP_REDIS=true
                shift
                ;;
            --skip-milvus)
                SKIP_MILVUS=true
                shift
                ;;
            --skip-uploads)
                SKIP_UPLOADS=true
                shift
                ;;
            -y|--yes)
                AUTO_CONFIRM=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --backup <dir>         使用指定的备份目录"
                echo "  --list                 列出所有可用备份"
                echo "  --skip-db              跳过数据库回滚"
                echo "  --skip-redis           跳过 Redis 回滚"
                echo "  --skip-milvus          跳过 Milvus 回滚"
                echo "  --skip-uploads         跳过上传文件回滚"
                echo "  -y, --yes              自动确认回滚（跳过提示）"
                echo "  --help                 显示帮助信息"
                echo ""
                echo "示例:"
                echo "  $0 --list                    # 列出可用备份"
                echo "  $0 --backup 1 -y             # 使用第一个备份自动回滚"
                echo "  $0 --backup ./backups/1      # 使用指定目录回滚"
                exit 0
                ;;
            *)
                # 尝试解析为备份索引
                if [[ "$1" =~ ^[0-9]+$ ]]; then
                    BACKUP_DIR=$(select_backup "$1")
                    shift
                else
                    echo "未知选项: $1"
                    echo "使用 --help 查看帮助信息"
                    exit 1
                fi
                ;;
        esac
    done

    # 检查环境
    check_env
    check_docker

    # 如果没有指定备份目录，列出备份供选择
    if [ -z "$BACKUP_DIR" ]; then
        list_backups
        read -p "请选择要回滚的备份编号: " backup_index
        BACKUP_DIR=$(select_backup "$backup_index")
    fi

    # 验证备份目录
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "备份目录不存在: $BACKUP_DIR"
        exit 1
    fi

    echo ""
    log_info "将使用备份: $BACKUP_DIR"
    echo ""

    # 确认回滚
    if [ "$AUTO_CONFIRM" = false ]; then
        read -p "确认要回滚吗？此操作不可逆 (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "回滚已取消"
            exit 0
        fi
    fi

    # 创建当前系统快照
    snapshot_dir=$(take_snapshot)

    # 执行回滚
    echo ""
    log_info "开始回滚..."
    echo ""

    # 回滚服务（配置）
    rollback_services "$BACKUP_DIR"

    # 回滚数据库
    if [ "$SKIP_DB" = false ]; then
        rollback_database "$BACKUP_DIR" || true
    else
        log_warning "跳过数据库回滚"
    fi

    # 回滚 Redis
    if [ "$SKIP_REDIS" = false ]; then
        rollback_redis "$BACKUP_DIR" || true
    else
        log_warning "跳过 Redis 回滚"
    fi

    # 回滚 Milvus
    if [ "$SKIP_MILVUS" = false ]; then
        rollback_milvus "$BACKUP_DIR" || true
    else
        log_warning "跳过 Milvus 回滚"
    fi

    # 回滚上传文件
    if [ "$SKIP_UPLOADS" = false ]; then
        rollback_uploads "$BACKUP_DIR" || true
    else
        log_warning "跳过上传文件回滚"
    fi

    # 验证回滚结果
    echo ""
    verify_rollback || true

    echo ""
    echo "========================================"
    echo "  回滚完成！"
    echo "========================================"
    echo ""
    log_success "系统已回滚到备份: $BACKUP_DIR"
    log_info "当前系统快照: $snapshot_dir"
    log_info "回滚日志: $LOG_FILE"
    echo ""
    log_info "如需重新部署，请运行: bash scripts/deploy.sh"
    log_info "如需回滚到当前状态，请使用快照: $snapshot_dir"
    echo ""

    # 发送通知
    send_notification "success" "$BACKUP_DIR"
}

# 执行主流程
main "$@"
