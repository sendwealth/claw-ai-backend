"""
数据库性能基准测试

测试目标：
1. 测试索引对查询性能的影响
2. 测试连接池性能
3. 测试常见查询模式的性能
4. 生成性能报告

运行方式：
    pytest tests/test_db_performance.py -v
    pytest tests/test_db_performance.py::TestDBPerformance::test_index_performance -v
"""

import pytest
import time
import statistics
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import engine, get_db, get_db_pool_status
from app.models import User, Conversation, Message, Document, KnowledgeBase


class TestDBPerformance:
    """数据库性能测试类"""

    @pytest.fixture
    def db(self):
        """
        获取数据库会话

        使用 pytest fixture 管理数据库会话生命周期
        """
        with get_db() as db:
            yield db

    @pytest.fixture(autouse=True)
    def setup_test_data(self, db: Session):
        """
        自动为每个测试创建测试数据

        创建足够的测试数据以进行有意义的性能测试
        """
        # 创建用户
        users = []
        for i in range(10):
            user = User(
                email=f"test{i}@example.com",
                password_hash="test_hash",
                name=f"Test User {i}"
            )
            db.add(user)
            users.append(user)

        db.flush()

        # 创建知识库
        knowledge_bases = []
        for user in users:
            for j in range(2):
                kb = KnowledgeBase(
                    user_id=user.id,
                    name=f"KB {j} for User {user.id}",
                    description=f"Test knowledge base {j}"
                )
                db.add(kb)
                knowledge_bases.append(kb)

        db.flush()

        # 创建对话
        conversations = []
        for user in users:
            for k in range(20):
                conv = Conversation(
                    user_id=user.id,
                    title=f"Conversation {k}"
                )
                db.add(conv)
                conversations.append(conv)

        db.flush()

        # 创建消息
        messages = []
        for conv in conversations[:50]:  # 为部分对话添加消息
            for m in range(50):
                msg = Message(
                    conversation_id=conv.id,
                    role="user" if m % 2 == 0 else "assistant",
                    content=f"Message {m} in conversation {conv.id}"
                )
                db.add(msg)
                messages.append(msg)

        db.flush()

        # 创建文档
        documents = []
        for kb in knowledge_bases[:10]:  # 为部分知识库添加文档
            for d in range(30):
                doc = Document(
                    knowledge_base_id=kb.id,
                    title=f"Document {d}",
                    content=f"Test content for document {d}"
                )
                db.add(doc)
                documents.append(doc)

        db.commit()

        yield

        # 清理测试数据
        db.query(Message).delete()
        db.query(Document).delete()
        db.query(Conversation).delete()
        db.query(KnowledgeBase).delete()
        db.query(User).delete()
        db.commit()

    def _measure_query_time(self, db: Session, query_func, iterations: int = 10) -> Dict[str, Any]:
        """
        测量查询执行时间

        Args:
            db: 数据库会话
            query_func: 要测试的查询函数
            iterations: 测试迭代次数

        Returns:
            dict: 包含性能统计信息的字典
        """
        times = []

        for _ in range(iterations):
            start = time.time()
            result = query_func(db)
            end = time.time()
            times.append(end - start)

        return {
            "min_time": min(times),
            "max_time": max(times),
            "avg_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "total_time": sum(times),
            "iterations": iterations
        }

    def test_index_performance_conversations(self, db: Session):
        """
        测试 conversations 表索引性能

        测试场景：
        1. 按 user_id 查询对话
        2. 按 user_id + created_at 排序查询
        3. 按时间范围查询
        """
        print("\n=== 测试 conversations 表索引性能 ===")

        # 测试 1：按 user_id 查询
        def query_by_user_id(db: Session):
            return db.query(Conversation).filter(
                Conversation.user_id == 1
            ).all()

        result = self._measure_query_time(db, query_by_user_id, 20)
        print(f"按 user_id 查询 (100 条):")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        print(f"  最小时间: {result['min_time']*1000:.2f}ms")
        print(f"  最大时间: {result['max_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.1, "按 user_id 查询性能未达标"

        # 测试 2：按 user_id + created_at 排序
        def query_sorted(db: Session):
            return db.query(Conversation).filter(
                Conversation.user_id == 1
            ).order_by(Conversation.created_at.desc()).all()

        result = self._measure_query_time(db, query_sorted, 20)
        print(f"\n按 user_id + created_at 排序:")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.15, "排序查询性能未达标"

        # 测试 3：时间范围查询
        def query_by_time_range(db: Session):
            return db.query(Conversation).filter(
                Conversation.user_id == 1
            ).order_by(Conversation.created_at.desc()).limit(10).all()

        result = self._measure_query_time(db, query_by_time_range, 20)
        print(f"\n时间范围查询 (limit 10):")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.1, "时间范围查询性能未达标"

    def test_index_performance_messages(self, db: Session):
        """
        测试 messages 表索引性能

        测试场景：
        1. 按 conversation_id 查询消息
        2. 按 conversation_id + created_at 排序查询
        3. 分页查询消息
        """
        print("\n=== 测试 messages 表索引性能 ===")

        # 测试 1：按 conversation_id 查询
        def query_by_conv_id(db: Session):
            return db.query(Message).filter(
                Message.conversation_id == 1
            ).all()

        result = self._measure_query_time(db, query_by_conv_id, 20)
        print(f"按 conversation_id 查询 (50 条):")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.1, "按 conversation_id 查询性能未达标"

        # 测试 2：按 conversation_id + created_at 排序
        def query_sorted(db: Session):
            return db.query(Message).filter(
                Message.conversation_id == 1
            ).order_by(Message.created_at.asc()).all()

        result = self._measure_query_time(db, query_sorted, 20)
        print(f"\n按 conversation_id + created_at 排序:")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.15, "排序查询性能未达标"

        # 测试 3：分页查询
        def query_paginated(db: Session):
            return db.query(Message).filter(
                Message.conversation_id == 1
            ).order_by(Message.created_at.desc()).offset(20).limit(10).all()

        result = self._measure_query_time(db, query_paginated, 20)
        print(f"\n分页查询 (offset 20, limit 10):")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.1, "分页查询性能未达标"

    def test_index_performance_documents(self, db: Session):
        """
        测试 documents 表索引性能

        测试场景：
        1. 按 knowledge_base_id 查询文档
        2. 按 knowledge_base_id + created_at 排序
        3. 时间范围查询
        """
        print("\n=== 测试 documents 表索引性能 ===")

        # 测试 1：按 knowledge_base_id 查询
        def query_by_kb_id(db: Session):
            return db.query(Document).filter(
                Document.knowledge_base_id == 1
            ).all()

        result = self._measure_query_time(db, query_by_kb_id, 20)
        print(f"按 knowledge_base_id 查询 (30 条):")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.1, "按 knowledge_base_id 查询性能未达标"

        # 测试 2：按 knowledge_base_id + created_at 排序
        def query_sorted(db: Session):
            return db.query(Document).filter(
                Document.knowledge_base_id == 1
            ).order_by(Document.created_at.desc()).all()

        result = self._measure_query_time(db, query_sorted, 20)
        print(f"\n按 knowledge_base_id + created_at 排序:")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.15, "排序查询性能未达标"

    def test_connection_pool_performance(self):
        """
        测试连接池性能

        测试场景：
        1. 并发连接获取
        2. 连接回收
        3. 连接池状态监控
        """
        print("\n=== 测试连接池性能 ===")

        # 获取初始连接池状态
        initial_status = get_db_pool_status()
        print(f"初始连接池状态: {initial_status}")

        # 测试并发连接获取
        def get_connection():
            start = time.time()
            with get_db() as db:
                db.execute(text("SELECT 1"))
            end = time.time()
            return end - start

        times = []
        for _ in range(50):
            times.append(get_connection())

        print(f"\n50 次连接获取:")
        print(f"  平均时间: {statistics.mean(times)*1000:.2f}ms")
        print(f"  最小时间: {min(times)*1000:.2f}ms")
        print(f"  最大时间: {max(times)*1000:.2f}ms")

        # 获取最终连接池状态
        final_status = get_db_pool_status()
        print(f"\n最终连接池状态: {final_status}")

        # 验证连接池正常工作
        assert final_status['status'] == 'healthy', "连接池状态异常"

    def test_query_complexity(self, db: Session):
        """
        测试复杂查询性能

        测试场景：
        1. 多表连接查询
        2. 聚合查询
        3. 复杂条件查询
        """
        print("\n=== 测试复杂查询性能 ===")

        # 测试 1：多表连接查询
        def query_join(db: Session):
            return db.query(
                Conversation.id,
                Conversation.title,
                User.name,
                User.email
            ).join(
                User, Conversation.user_id == User.id
            ).filter(
                User.id == 1
            ).all()

        result = self._measure_query_time(db, query_join, 10)
        print(f"多表连接查询:")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.2, "多表连接查询性能未达标"

        # 测试 2：聚合查询
        def query_aggregate(db: Session):
            return db.query(
                Conversation.user_id,
                func.count(Conversation.id).label('conversation_count')
            ).group_by(
                Conversation.user_id
            ).all()

        from sqlalchemy import func
        result = self._measure_query_time(db, query_aggregate, 10)
        print(f"\n聚合查询:")
        print(f"  平均时间: {result['avg_time']*1000:.2f}ms")
        assert result['avg_time'] < 0.2, "聚合查询性能未达标"


if __name__ == "__main__":
    """
    直接运行此文件进行性能测试
    """
    pytest.main([__file__, "-v", "-s"])
