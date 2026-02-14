#!/bin/bash

################################################################################
# CLAW.AI - 数据备份脚本
# 功能：自动备份 PostgreSQL 数据库、Redis、Milvus 数据
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
BACKUP_DIR="$BACKUP_ROOT_DIR/daily/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 日志文件
LOG_FILE="$PROJECT_DIR/logs/backup-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

# 保留天数
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# 加密密钥（可选）
ENCRYPT_KEY="${BACKUP_ENCRYPT_KEY:-}"

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

    if ! docker ps &> /dev/null; then
        log_error "Docker 未运行"
        exit 1
    fi

    log_success "Docker 运行正常"
}

# ====================
# 备份函数
# ====================

backup_postgres() {
    log_info "备份 PostgreSQL 数据库..."

    local backup_file="$BACKUP_DIR/postgres-${POSTGRES_DB}.sql.gz"

    # 检查容器是否运行
    if ! docker ps | grep -q claw_ai_postgres; then
        log_error "PostgreSQL 容器未运行"
        return 1
    fi

    # 执行备份
    docker exec claw_ai_postgres pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "$backup_file"

    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_success "PostgreSQL 备份完成: $backup_file ($size)"
    else
        log_error "PostgreSQL 备份失败"
        return 1
    fi
}

backup_redis() {
    log_info "备份 Redis 数据..."

    local backup_file="$BACKUP_DIR/redis-dump.rdb"

    # 检查容器是否运行
    if ! docker ps | grep -q claw_ai_redis; then
        log_error "Redis 容器未运行"
        return 1
    fi

    # 复制 RDB 文件
    docker cp claw_ai_redis:/data/dump.rdb "$backup_file"

    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_success "Redis 备份完成: $backup_file ($size)"
    else
        log_warning "Redis 备份失败，可能没有持久化数据"
    fi
}

backup_milvus() {
    log_info "备份 Milvus 数据..."

    local milvus_backup_dir="$BACKUP_DIR/milvus"
    mkdir -p "$milvus_backup_dir"

    # 检查容器是否运行
    if ! docker ps | grep -q claw_ai_milvus; then
        log_error "Milvus 容器未运行"
        return 1
    fi

    # 备份 etcd 数据
    if docker ps | grep -q claw_ai_etcd; then
        docker cp claw_ai_etcd:/etcd "$milvus_backup_dir/"
        log_info "已备份 Milvus etcd 数据"
    fi

    # 备份 MinIO 数据
    if docker ps | grep -q claw_ai_minio; then
        docker cp claw_ai_minio:/minio_data "$milvus_backup_dir/"
        log_info "已备份 Milvus MinIO 数据"
    fi

    local size=$(du -sh "$milvus_backup_dir" | cut -f1)
    log_success "Milvus 备份完成: $milvus_backup_dir ($size)"
}

backup_uploads() {
    log_info "备份上传文件..."

    local uploads_dir="$PROJECT_DIR/uploads"
    local backup_file="$BACKUP_DIR/uploads.tar.gz"

    if [ -d "$uploads_dir" ] && [ "$(ls -A "$uploads_dir" 2>/dev/null)" ]; then
        tar -czf "$backup_file" -C "$uploads_dir" . 2>/dev/null

        if [ $? -eq 0 ]; then
            local size=$(du -h "$backup_file" | cut -f1)
            log_success "上传文件备份完成: $backup_file ($size)"
        else
            log_warning "上传文件备份失败"
        fi
    else
        log_warning "没有上传文件需要备份"
    fi
}

backup_config() {
    log_info "备份配置文件..."

    local config_backup_dir="$BACKUP_DIR/config"
    mkdir -p "$config_backup_dir"

    # 备份环境配置
    cp "$ENV_FILE" "$config_backup_dir/"

    # 备份 Nginx 配置
    if [ -f "nginx/nginx.conf" ]; then
        cp "nginx/nginx.conf" "$config_backup_dir/"
    fi

    # 备份 Docker Compose 配置
    cp "$COMPOSE_FILE" "$config_backup_dir/"

    log_success "配置文件备份完成"
}

# ====================
# 加密函数
# ====================

encrypt_backup() {
    if [ -z "$ENCRYPT_KEY" ]; then
        log_info "未设置加密密钥，跳过加密"
        return 0
    fi

    log_info "加密备份数据..."

    local encrypted_file="$BACKUP_DIR/backup.tar.gz.enc"
    tar -czf - "$BACKUP_DIR" | openssl enc -aes-256-cbc -salt -pbkdf2 -k "$ENCRYPT_KEY" -out "$encrypted_file"

    if [ $? -eq 0 ]; then
        # 删除原始文件（可选）
        # rm -rf "$BACKUP_DIR"/*
        log_success "备份数据已加密: $encrypted_file"
    else
        log_error "加密失败"
        return 1
    fi
}

# ====================
# 上传函数（可选）
# ====================

upload_to_s3() {
    if [ -z "${S3_BUCKET:-}" ]; then
        log_info "未配置 S3，跳过上传"
        return 0
    fi

    log_info "上传备份到 S3..."

    local s3_path="s3://${S3_BUCKET}/claw-ai-backups/$(date +%Y%m%d)/"

    # 使用 AWS CLI 上传
    if command -v aws &> /dev/null; then
        aws s3 sync "$BACKUP_DIR" "$s3_path" --quiet
        log_success "备份已上传到 S3"
    else
        log_warning "AWS CLI 未安装，无法上传到 S3"
    fi
}

upload_to_ftp() {
    if [ -z "${FTP_HOST:-}" ]; then
        log_info "未配置 FTP，跳过上传"
        return 0
    fi

    log_info "上传备份到 FTP..."

    if command -v lftp &> /dev/null; then
        lftp -u "${FTP_USER},${FTP_PASSWORD}" "${FTP_HOST}" \
            -e "mirror -R $BACKUP_DIR /backups/claw-ai/$(date +%Y%m%d); quit"
        log_success "备份已上传到 FTP"
    else
        log_warning "lftp 未安装，无法上传到 FTP"
    fi
}

# ====================
# 清理函数
# ====================

cleanup_old_backups() {
    log_info "清理旧备份（保留 $RETENTION_DAYS 天）..."

    local daily_dir="$BACKUP_ROOT_DIR/daily"
    local weekly_dir="$BACKUP_ROOT_DIR/weekly"
    local monthly_dir="$BACKUP_ROOT_DIR/monthly"

    # 清理每日备份
    if [ -d "$daily_dir" ]; then
        find "$daily_dir" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
        log_info "已清理超过 $RETENTION_DAYS 天的每日备份"
    fi

    # 保留每周备份（每周一）
    if [ "$(date +%u)" -eq 1 ]; then
        mkdir -p "$weekly_dir"
        cp -r "$BACKUP_DIR" "$weekly_dir/$(date +%Y%m%d)"
        find "$weekly_dir" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true
        log_info "已创建并清理每周备份"
    fi

    # 保留每月备份（每月第一天）
    if [ "$(date +%d)" -eq 01 ]; then
        mkdir -p "$monthly_dir"
        cp -r "$BACKUP_DIR" "$monthly_dir/$(date +%Y%m%d)"
        find "$monthly_dir" -type d -mtime +365 -exec rm -rf {} + 2>/dev/null || true
        log_info "已创建并清理每月备份"
    fi

    log_success "备份清理完成"
}

# ====================
# 通知函数
# ====================

send_notification() {
    if [ -z "${WEBHOOK_URL:-}" ]; then
        return 0
    fi

    log_info "发送备份通知..."

    local status=$1
    local message="CLAW.AI 数据库备份: $status"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"$message\",
            \"timestamp\": \"$timestamp\",
            \"backup_dir\": \"$BACKUP_DIR\",
            \"status\": \"$status\"
        }" &>/dev/null || true

    log_info "通知已发送"
}

# ====================
# 验证函数
# ====================

verify_backup() {
    log_info "验证备份完整性..."

    local failed=0

    # 验证 PostgreSQL 备份
    if [ -f "$BACKUP_DIR/postgres-${POSTGRES_DB}.sql.gz" ]; then
        if gzip -t "$BACKUP_DIR/postgres-${POSTGRES_DB}.sql.gz" 2>/dev/null; then
            log_success "PostgreSQL 备份验证通过"
        else
            log_error "PostgreSQL 备份已损坏"
            failed=1
        fi
    fi

    # 验证 Redis 备份
    if [ -f "$BACKUP_DIR/redis-dump.rdb" ]; then
        log_success "Redis 备份验证通过"
    fi

    if [ $failed -eq 0 ]; then
        log_success "备份验证通过"
    else
        log_error "备份验证失败"
        return 1
    fi
}

# ====================
# 恢复函数
# ====================

restore_backup() {
    local backup_dir="$1"

    log_info "从备份恢复: $backup_dir"

    if [ ! -d "$backup_dir" ]; then
        log_error "备份目录不存在: $backup_dir"
        exit 1
    fi

    # 恢复 PostgreSQL
    if [ -f "$backup_dir/postgres-${POSTGRES_DB}.sql.gz" ]; then
        log_info "恢复 PostgreSQL 数据库..."
        gunzip < "$backup_dir/postgres-${POSTGRES_DB}.sql.gz" | \
            docker exec -i claw_ai_postgres psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"
        log_success "PostgreSQL 恢复完成"
    fi

    # 恢复 Redis
    if [ -f "$backup_dir/redis-dump.rdb" ]; then
        log_info "恢复 Redis 数据..."
        docker cp "$backup_dir/redis-dump.rdb" claw_ai_redis:/data/dump.rdb
        docker exec claw_ai_redis redis-cli SHUTDOWN NOSAVE
        docker-compose -f "$COMPOSE_FILE" restart redis
        log_success "Redis 恢复完成"
    fi

    log_success "备份恢复完成"
}

# ====================
# 主流程
# ====================

main() {
    echo ""
    echo "========================================"
    echo "  CLAW.AI 数据备份脚本"
    echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""

    # 解析命令行参数
    BACKUP_MODE="full"
    RESTORE_FROM=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --restore)
                RESTORE_FROM="$2"
                shift 2
                ;;
            --db-only)
                BACKUP_MODE="db"
                shift
                ;;
            --no-upload)
                NO_UPLOAD=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --restore <backup_dir>  从指定备份恢复"
                echo "  --db-only               仅备份数据库"
                echo "  --no-upload             跳过远程上传"
                echo "  --help                  显示帮助信息"
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

    # 恢复模式
    if [ -n "$RESTORE_FROM" ]; then
        restore_backup "$RESTORE_FROM"
        exit 0
    fi

    # 备份模式
    log_info "开始备份（模式: $BACKUP_MODE）..."

    if [ "$BACKUP_MODE" = "full" ] || [ "$BACKUP_MODE" = "db" ]; then
        backup_postgres
    fi

    if [ "$BACKUP_MODE" = "full" ]; then
        backup_redis
        backup_milvus
        backup_uploads
    fi

    backup_config
    verify_backup

    if [ -z "${NO_UPLOAD:-}" ]; then
        upload_to_s3
        upload_to_ftp
    fi

    cleanup_old_backups

    echo ""
    echo "========================================"
    echo "  备份完成！"
    echo "========================================"
    echo ""
    log_success "备份目录: $BACKUP_DIR"
    log_success "备份日志: $LOG_FILE"
    echo ""

    # 发送通知
    send_notification "success"
}

# 执行主流程
main "$@"
