#!/bin/bash

################################################################################
# CLAW.AI - 生产环境部署脚本
# 功能：自动化部署生产环境，包括 SSL 证书配置、服务启动等
################################################################################

set -e  # 遇到错误立即退出
set -u  # 使用未定义变量时报错

# ====================
# 配置变量
# ====================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 日志文件
LOG_FILE="$PROJECT_DIR/logs/deploy-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

# 配置文件
ENV_FILE=".env.prod"
COMPOSE_FILE="docker-compose.prod.yml"

# 域名配置（从环境变量读取，或使用默认值）
DOMAIN="${DEPLOY_DOMAIN:-claw-ai.com}"
ADMIN_EMAIL="${DEPLOY_EMAIL:-admin@claw-ai.com}"

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

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_warning "此脚本需要 root 权限运行，请使用 sudo"
        return 1
    fi
    return 0
}

check_docker() {
    log_info "检查 Docker 安装状态..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    log_success "Docker 和 Docker Compose 已安装"
}

check_env_file() {
    log_info "检查环境配置文件..."
    if [ ! -f "$ENV_FILE" ]; then
        log_error "环境配置文件 $ENV_FILE 不存在"
        log_info "请从模板创建：cp .env.prod.example $ENV_FILE"
        log_info "然后编辑配置：vim $ENV_FILE"
        exit 1
    fi

    # 检查关键配置项
    if grep -q "your_secure_password_here_change_this" "$ENV_FILE"; then
        log_error "检测到未修改的默认密码，请修改 $ENV_FILE 中的敏感配置"
        exit 1
    fi

    log_success "环境配置文件检查通过"
}

check_domain() {
    log_info "检查域名 $DOMAIN 的 DNS 配置..."

    # 检查域名是否指向当前服务器
    local server_ip=$(curl -s ifconfig.me)
    local domain_ip=$(dig +short "$DOMAIN" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1)

    if [ -z "$domain_ip" ]; then
        log_warning "无法解析域名 $DOMAIN，请确保 DNS 配置正确"
        read -p "是否继续部署？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    elif [ "$domain_ip" != "$server_ip" ]; then
        log_warning "域名 $DOMAIN 解析的 IP ($domain_ip) 与当前服务器 IP ($server_ip) 不匹配"
        read -p "是否继续部署？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_success "域名 DNS 配置正确 ($domain_ip)"
    fi
}

# ====================
# 备份函数
# ====================

backup_existing() {
    log_info "备份现有配置和数据..."

    local backup_dir="$PROJECT_DIR/backups/pre-deploy-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"

    # 备份环境配置
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$backup_dir/"
        log_info "已备份环境配置"
    fi

    # 备份 Nginx 配置
    if [ -f "nginx/nginx.conf" ]; then
        cp "nginx/nginx.conf" "$backup_dir/"
        log_info "已备份 Nginx 配置"
    fi

    # 备份数据库（如果容器在运行）
    if docker ps | grep -q claw_ai_postgres; then
        docker exec claw_ai_postgres pg_dump -U "${POSTGRES_USER:-claw_ai}" "${POSTGRES_DB:-claw_ai}" \
            > "$backup_dir/database.sql" 2>/dev/null || true
        log_info "已备份数据库"
    fi

    log_success "备份完成：$backup_dir"
}

# ====================
# SSL 证书函数
# ====================

setup_ssl() {
    log_info "设置 SSL 证书..."

    # 检查是否已有证书
    if [ -d "nginx/ssl" ] && [ -f "nginx/ssl/fullchain.pem" ]; then
        log_warning "SSL 证书已存在，跳过证书申请"
        return 0
    fi

    # 创建 SSL 目录
    mkdir -p nginx/ssl

    # 安装 certbot
    if ! command -v certbot &> /dev/null; then
        log_info "安装 certbot..."
        apt-get update
        apt-get install -y certbot
    fi

    # 检查 Nginx 是否在运行
    if docker ps | grep -q claw_ai_nginx; then
        log_info "停止 Nginx 容器..."
        docker-compose -f "$COMPOSE_FILE" stop nginx
    fi

    # 申请证书（使用 standalone 模式）
    log_info "申请 Let's Encrypt SSL 证书..."
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email "$ADMIN_EMAIL" \
        -d "$DOMAIN" \
        --force-renewal

    if [ $? -eq 0 ]; then
        # 复制证书到项目目录
        cp /etc/letsencrypt/live/"$DOMAIN"/fullchain.pem nginx/ssl/
        cp /etc/letsencrypt/live/"$DOMAIN"/privkey.pem nginx/ssl/
        chmod 644 nginx/ssl/*.pem

        log_success "SSL 证书申请成功"
    else
        log_error "SSL 证书申请失败"
        log_warning "将使用自签名证书继续部署..."
        generate_self_signed_cert
    fi

    # 设置自动续期
    setup_cert_renewal
}

generate_self_signed_cert() {
    log_info "生成自签名证书..."
    mkdir -p nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem \
        -out nginx/ssl/fullchain.pem \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=CLAW.AI/CN=$DOMAIN"
    chmod 644 nginx/ssl/*.pem
}

setup_cert_renewal() {
    log_info "设置 SSL 证书自动续期..."

    local renew_script="$PROJECT_DIR/scripts/renew-ssl.sh"
    cat > "$renew_script" << 'EOF'
#!/bin/bash
# SSL 证书自动续期脚本

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="${DEPLOY_DOMAIN:-claw-ai.com}"

# 续期证书
certbot renew --quiet

# 复制新证书
cp /etc/letsencrypt/live/"$DOMAIN"/fullchain.pem "$PROJECT_DIR/nginx/ssl/"
cp /etc/letsencrypt/live/"$DOMAIN"/privkey.pem "$PROJECT_DIR/nginx/ssl/"

# 重载 Nginx
cd "$PROJECT_DIR"
docker-compose -f docker-compose.prod.yml exec -T nginx nginx -s reload
EOF

    chmod +x "$renew_script"

    # 添加到 crontab（每天凌晨 3 点检查）
    (crontab -l 2>/dev/null | grep -v "renew-ssl.sh"; echo "0 3 * * * $renew_script >> $PROJECT_DIR/logs/renew-ssl.log 2>&1") | crontab -

    log_success "SSL 证书自动续期已配置"
}

# ====================
# 部署函数
# ====================

deploy_services() {
    log_info "开始部署服务..."

    # 拉取最新镜像
    log_info "拉取最新 Docker 镜像..."
    docker-compose -f "$COMPOSE_FILE" pull

    # 构建镜像
    log_info "构建 Docker 镜像..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache

    # 停止旧容器
    log_info "停止旧容器..."
    docker-compose -f "$COMPOSE_FILE" down

    # 启动服务
    log_info "启动服务..."
    docker-compose -f "$COMPOSE_FILE" up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    # 检查服务状态
    check_services

    log_success "服务部署完成"
}

check_services() {
    log_info "检查服务状态..."

    local failed_services=()

    # 检查关键服务
    local services=("postgres" "redis" "claw-ai-backend" "nginx" "milvus-standalone")

    for service in "${services[@]}"; do
        if ! docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            failed_services+=("$service")
            log_error "服务 $service 未正常运行"
        else
            log_success "服务 $service 运行正常"
        fi
    done

    if [ ${#failed_services[@]} -gt 0 ]; then
        log_error "以下服务启动失败：${failed_services[*]}"
        log_info "查看日志：docker-compose -f $COMPOSE_FILE logs"
        exit 1
    fi
}

run_migrations() {
    log_info "运行数据库迁移..."

    # 等待数据库就绪
    log_info "等待数据库就绪..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "${POSTGRES_USER:-claw_ai}" &>/dev/null; then
            break
        fi
        attempt=$((attempt + 1))
        log_info "等待数据库... ($attempt/$max_attempts)"
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        log_error "数据库未能在预期时间内就绪"
        exit 1
    fi

    # 运行迁移脚本
    if [ -f "scripts/migrate.sh" ]; then
        bash scripts/migrate.sh
    else
        log_warning "未找到迁移脚本，跳过数据库迁移"
    fi

    log_success "数据库迁移完成"
}

# ====================
# 健康检查函数
# ====================

health_check() {
    log_info "执行健康检查..."

    # 检查 API 端点
    local api_url="https://$DOMAIN/api/health"
    local max_attempts=10
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "$api_url" > /dev/null 2>&1; then
            log_success "API 健康检查通过"
            return 0
        fi
        attempt=$((attempt + 1))
        log_info "等待 API 就绪... ($attempt/$max_attempts)"
        sleep 5
    done

    log_error "API 健康检查失败"
    log_info "查看日志：docker-compose -f $COMPOSE_FILE logs claw-ai-backend"
    return 1
}

# ====================
# 清理函数
# ====================

cleanup() {
    log_info "清理未使用的 Docker 资源..."
    docker system prune -f --volumes
    log_success "清理完成"
}

# ====================
# 主流程
# ====================

main() {
    echo ""
    echo "========================================"
    echo "  CLAW.AI 生产环境部署脚本"
    echo "  域名: $DOMAIN"
    echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""

    # 解析命令行参数
    SKIP_BACKUP=false
    SKIP_SSL=false
    SKIP_MIGRATIONS=false
    SKIP_HEALTH_CHECK=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-ssl)
                SKIP_SSL=true
                shift
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --skip-backup         跳过备份"
                echo "  --skip-ssl            跳过 SSL 证书配置"
                echo "  --skip-migrations     跳过数据库迁移"
                echo "  --skip-health-check   跳过健康检查"
                echo "  --help                显示帮助信息"
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                echo "使用 --help 查看帮助信息"
                exit 1
                ;;
        esac
    done

    # 执行部署流程
    check_docker
    check_env_file
    check_domain

    if [ "$SKIP_BACKUP" = false ]; then
        backup_existing
    fi

    if [ "$SKIP_SSL" = false ]; then
        setup_ssl
    fi

    deploy_services

    if [ "$SKIP_MIGRATIONS" = false ]; then
        run_migrations
    fi

    if [ "$SKIP_HEALTH_CHECK" = false ]; then
        health_check
    fi

    cleanup

    echo ""
    echo "========================================"
    echo "  部署完成！"
    echo "========================================"
    echo ""
    log_success "服务已成功部署"
    log_info "访问地址: https://$DOMAIN"
    log_info "Grafana 监控: https://$DOMAIN/grafana"
    log_info "Flower 任务监控: https://$DOMAIN/flower"
    log_info ""
    log_info "查看服务状态: docker-compose -f $COMPOSE_FILE ps"
    log_info "查看服务日志: docker-compose -f $COMPOSE_FILE logs -f"
    log_info ""
    log_info "部署日志: $LOG_FILE"
    echo ""
}

# 执行主流程
main "$@"
