#!/bin/bash

# CLAW.AI - 企业级部署脚本
# OpenSpark 智能科技

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
APP_NAME="CLAW.AI"
APP_VERSION="1.0.0"
APP_DIR="/opt/claw-ai"
REPO_URL="https://github.com/sendwealth/claw-ai-backend.git"
COMPOSE_FILE="$APP_DIR/docker-compose.prod.yml"
ENV_FILE="$APP_DIR/.env"
BACKUP_DIR="/opt/claw-ai-backup"
LOG_DIR="$APP_DIR/logs"

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo "========================================="
    echo "  $1"
    echo "========================================="
    echo ""
}

# 检查权限
check_permission() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "此脚本需要 root 权限运行"
        exit 1
    fi
}

# 安装 Docker
install_docker() {
    print_header "安装 Docker 和 Docker Compose"

    if ! command -v docker &> /dev/null; then
        print_info "安装 Docker..."
        curl -fsSL https://get.docker.com | sh
        print_info "启动 Docker..."
        systemctl start docker
        systemctl enable docker
        print_info "✅ Docker 安装完成"
    else
        print_info "Docker 已安装，跳过"
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_info "安装 Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        print_info "✅ Docker Compose 安装完成"
    else
        print_info "Docker Compose 已安装，跳过"
    fi
}

# 创建目录结构
create_directories() {
    print_header "创建目录结构"

    mkdir -p "$APP_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$APP_DIR/nginx/ssl"
    mkdir -p "$APP_DIR/nginx/logs"

    print_info "✅ 目录结构创建完成"
}

# 克隆代码
clone_code() {
    print_header "克隆/更新代码"

    if [ -d "$APP_DIR/.git" ]; then
        print_info "更新代码..."
        cd "$APP_DIR"
        git pull origin master
    else
        print_info "克隆代码..."
        rm -rf "$APP_DIR"
        git clone "$REPO_URL" "$APP_DIR"
        cd "$APP_DIR"
    fi

    print_info "✅ 代码克隆完成"
}

# 配置环境变量
configure_env() {
    print_header "配置环境变量"

    if [ ! -f "$ENV_FILE" ]; then
        print_info "创建 .env 文件..."
        cp "$APP_DIR/.env.example" "$ENV_FILE"

        # 生成随机密钥
        SECRET_KEY=$(openssl rand -hex 32)
        POSTGRES_PASSWORD=$(openssl rand -hex 16)
        REDIS_PASSWORD=$(openssl rand -hex 16)

        # 更新 .env 文件
        sed -i "s/your-secret-key-here-change-in-production/$SECRET_KEY/" "$ENV_FILE"
        sed -i "s/password/$POSTGRES_PASSWORD/" "$ENV_FILE"
        sed -i "s/password/$REDIS_PASSWORD/" "$ENV_FILE"

        print_warn "⚠️  请编辑 .env 文件并配置以下变量："
        print_warn "   文件位置: $ENV_FILE"
        print_warn ""
        print_warn "   必须配置："
        print_warn "   - ZHIPUAI_API_KEY (智谱 AI API Key)"
        print_warn "   - PINECONE_API_KEY (Pinecone API Key)"
        print_warn ""
        print_warn "   编辑命令: nano $ENV_FILE"
        print_warn ""
        read -p "按 Enter 继续..."

        print_info "✅ .env 文件创建完成"
    else
        print_info ".env 文件已存在，跳过"
    fi
}

# 配置 SSL 证书
configure_ssl() {
    print_header "配置 SSL 证书"

    if [ ! -f "$APP_DIR/nginx/ssl/fullchain.pem" ]; then
        print_warn "SSL 证书不存在"
        print_warn "请将 SSL 证书文件放到: $APP_DIR/nginx/ssl/"
        print_warn "需要的文件:"
        print_warn "  - fullchain.pem (证书链)"
        print_warn "  - privkey.pem (私钥)"
        print_warn ""
        print_warn "如果不配置 SSL，请修改 nginx/nginx.conf 使用 HTTP"
    else
        print_info "✅ SSL 证书已配置"
    fi
}

# 构建镜像
build_images() {
    print_header "构建 Docker 镜像"

    cd "$APP_DIR"
    docker-compose -f "$COMPOSE_FILE" build

    print_info "✅ 镜像构建完成"
}

# 启动服务
start_services() {
    print_header "启动服务"

    cd "$APP_DIR"
    docker-compose -f "$COMPOSE_FILE" up -d

    print_info "✅ 服务启动完成"

    # 等待服务启动
    print_info "等待服务启动..."
    sleep 10

    # 检查服务状态
    print_header "服务状态"
    docker-compose -f "$COMPOSE_FILE" ps
}

# 停止服务
stop_services() {
    print_header "停止服务"

    cd "$APP_DIR"
    docker-compose -f "$COMPOSE_FILE" down

    print_info "✅ 服务已停止"
}

# 备份数据库
backup_database() {
    print_header "备份数据库"

    BACKUP_FILE="$BACKUP_DIR/postgres_backup_$(date +%Y%m%d_%H%M%S).sql"

    docker exec claw_ai_postgres pg_dump -U claw_ai -d claw_ai > "$BACKUP_FILE"

    # 压缩备份
    gzip "$BACKUP_FILE"

    print_info "✅ 数据库备份完成: ${BACKUP_FILE}.gz"

    # 清理 30 天前的备份
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
}

# 查看日志
view_logs() {
    print_info "查看日志 (Ctrl+C 退出)"
    cd "$APP_DIR"
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# 健康检查
health_check() {
    print_header "健康检查"

    # 检查服务是否运行
    print_info "检查服务状态..."
    docker-compose -f "$COMPOSE_FILE" ps

    # 测试 API
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_info "✅ API 健康检查通过"
    else
        print_error "❌ API 健康检查失败"
    fi

    # 测试数据库连接
    if docker exec claw_ai_postgres pg_isready -U claw_ai > /dev/null 2>&1; then
        print_info "✅ 数据库连接正常"
    else
        print_error "❌ 数据库连接失败"
    fi

    # 测试 Redis
    if docker exec claw_ai_redis redis-cli ping > /dev/null 2>&1; then
        print_info "✅ Redis 连接正常"
    else
        print_error "❌ Redis 连接失败"
    fi
}

# 显示帮助
show_help() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  install     - 安装 Docker 和部署应用"
    echo "  start      - 启动服务"
    echo "  stop       - 停止服务"
    echo "  restart    - 重启服务"
    echo "  logs       - 查看日志"
    echo "  status     - 查看服务状态"
    echo "  backup     - 备份数据库"
    echo "  health     - 健康检查"
    echo "  update     - 更新代码并重启"
    echo "  help       - 显示帮助信息"
    echo ""
}

# 主函数
main() {
    check_permission

    case "${1:-help}" in
        install)
            install_docker
            create_directories
            clone_code
            configure_env
            configure_ssl
            build_images
            start_services
            print_info ""
            print_info "🎉 部署完成！"
            print_info ""
            print_info "📱 访问地址："
            print_info "   - API: http://111.229.40.25:8000"
            print_info "   - 文档: http://111.229.40.25:8000/docs"
            print_info "   - HTTPS: https://openspark.online"
            print_info ""
            print_info "📊 查看状态: $0 status"
            print_info "📜 查看日志: $0 logs"
            print_info "💚 健康检查: $0 health"
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            start_services
            ;;
        logs)
            view_logs
            ;;
        status)
            docker-compose -f "$COMPOSE_FILE" ps
            health_check
            ;;
        backup)
            backup_database
            ;;
        health)
            health_check
            ;;
        update)
            print_info "更新代码..."
            clone_code
            print_info "重启服务..."
            restart
            ;;
        help|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
