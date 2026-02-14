"""
数据库监控脚本

功能：
1. 查看连接池状态
2. 分析慢查询
3. 检查索引使用情况
4. 生成性能报告

使用方式：
    python scripts/monitor_db.py --pool
    python scripts/monitor_db.py --slow-queries
    python scripts/monitor_db.py --index-usage
    python scripts/monitor_db.py --report
"""

import argparse
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, '/home/wuying/clawd/claw-ai-backend')

from app.db.database import engine, get_db_pool_status
from sqlalchemy import text


def show_pool_status():
    """显示连接池状态"""
    print("\n" + "="*60)
    print("数据库连接池状态")
    print("="*60)

    status = get_db_pool_status()

    print(f"\n连接池配置:")
    print(f"  Pool Size: {status['pool_size']}")
    print(f"  Max Overflow: {status['max_overflow']}")
    print(f"  Pool Timeout: {status['pool_timeout']}s")

    print(f"\n当前状态:")
    print(f"  已借出连接: {status['checked_out']}")
    print(f"  溢出连接: {status['overflow']}")
    print(f"  已归还连接: {status['checked_in']}")
    print(f"  状态: {status['status']}")

    # 计算利用率
    total_connections = status['pool_size'] + status['max_overflow']
    utilization = (status['checked_out'] / total_connections) * 100
    print(f"\n  连接池利用率: {utilization:.1f}%")

    if utilization > 80:
        print(f"  ⚠️  警告：连接池利用率过高（>80%）")
    elif utilization > 60:
        print(f"  ⚠️  提示：连接池利用率较高（>60%）")
    else:
        print(f"  ✅ 连接池状态良好")

    print("="*60 + "\n")


def show_slow_queries():
    """显示慢查询"""
    print("\n" + "="*60)
    print("慢查询分析")
    print("="*60)

    with engine.connect() as conn:
        # 查询最近 1 小时内执行时间超过 1 秒的查询
        result = conn.execute(text("""
            SELECT
                query,
                calls,
                total_time,
                mean_time,
                max_time
            FROM pg_stat_statements
            WHERE mean_time > 1000  -- 超过 1 秒
            ORDER BY mean_time DESC
            LIMIT 10;
        """))

        rows = result.fetchall()

        if not rows:
            print("\n✅ 没有慢查询记录")
        else:
            print(f"\n找到 {len(rows)} 个慢查询：\n")
            for i, row in enumerate(rows, 1):
                print(f"{i}. 查询:")
                print(f"   SQL: {row[0][:100]}...")
                print(f"   调用次数: {row[1]}")
                print(f"   总时间: {row[2]:.2f}ms")
                print(f"   平均时间: {row[3]:.2f}ms")
                print(f"   最大时间: {row[4]:.2f}ms")
                print()

    print("="*60 + "\n")


def show_index_usage():
    """显示索引使用情况"""
    print("\n" + "="*60)
    print("索引使用情况")
    print("="*60)

    with engine.connect() as conn:
        # 查询索引使用统计
        result = conn.execute(text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan as index_scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY idx_scan ASC;
        """))

        rows = result.fetchall()

        if not rows:
            print("\n没有找到索引")
        else:
            print(f"\n共 {len(rows)} 个索引：\n")

            # 分类显示
            unused = [row for row in rows if row[3] == 0]
            low_usage = [row for row in rows if 0 < row[3] < 100]
            high_usage = [row for row in rows if row[3] >= 100]

            if unused:
                print(f"⚠️  未使用的索引 ({len(unused)} 个):")
                for row in unused:
                    print(f"   - {row[1]}.{row[2]} (大小: {row[6]})")
                print()

            if low_usage:
                print(f"⚠️  低使用率索引 ({len(low_usage)} 个):")
                for row in low_usage:
                    print(f"   - {row[1]}.{row[2]} (扫描: {row[3]} 次, 大小: {row[6]})")
                print()

            if high_usage:
                print(f"✅ 高使用率索引 ({len(high_usage)} 个):")
                for row in high_usage[:10]:  # 只显示前 10 个
                    print(f"   - {row[1]}.{row[2]} (扫描: {row[3]} 次, 大小: {row[6]})")
                print()

    print("="*60 + "\n")


def show_index_sizes():
    """显示索引大小"""
    print("\n" + "="*60)
    print("索引大小统计")
    print("="*60)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY pg_relation_size(indexrelid) DESC;
        """))

        rows = result.fetchall()

        print(f"\n{'表名':<20} {'索引名':<40} {'大小':<10}")
        print("-" * 70)

        for row in rows:
            print(f"{row[0]:<20} {row[1]:<40} {row[2]:<10}")

    print("="*60 + "\n")


def show_table_sizes():
    """显示表大小"""
    print("\n" + "="*60)
    print("表大小统计")
    print("="*60)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """))

        rows = result.fetchall()

        print(f"\n{'表名':<20} {'总大小':<10} {'数据大小':<10} {'索引大小':<10}")
        print("-" * 50)

        for row in rows:
            print(f"{row[1]:<20} {row[2]:<10} {row[3]:<10} {row[4]:<10}")

    print("="*60 + "\n")


def generate_report():
    """生成完整的性能报告"""
    print("\n" + "="*60)
    print("数据库性能报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    show_pool_status()
    show_table_sizes()
    show_index_sizes()
    show_index_usage()

    print("\n报告生成完成！")
    print("="*60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据库监控工具')
    parser.add_argument('--pool', action='store_true', help='显示连接池状态')
    parser.add_argument('--slow-queries', action='store_true', help='显示慢查询')
    parser.add_argument('--index-usage', action='store_true', help='显示索引使用情况')
    parser.add_argument('--index-sizes', action='store_true', help='显示索引大小')
    parser.add_argument('--table-sizes', action='store_true', help='显示表大小')
    parser.add_argument('--report', action='store_true', help='生成完整报告')

    args = parser.parse_args()

    # 如果没有指定任何参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # 执行相应的命令
    if args.pool:
        show_pool_status()
    if args.slow_queries:
        show_slow_queries()
    if args.index_usage:
        show_index_usage()
    if args.index_sizes:
        show_index_sizes()
    if args.table_sizes:
        show_table_sizes()
    if args.report:
        generate_report()


if __name__ == "__main__":
    main()
