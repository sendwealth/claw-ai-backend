"""
数据库初始化脚本
创建初始数据和测试用户
"""

from app.db import SessionLocal, engine
from app.models import User
from app.utils.security import get_password_hash


def init_db():
    """初始化数据库"""
    print("🚀 开始初始化数据库...")

    # 创建所有表
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 检查是否已有用户
        existing_user = db.query(User).filter(User.email == "admin@openspark.online").first()

        if not existing_user:
            # 创建管理员用户
            admin_user = User(
                email="admin@openspark.online",
                password_hash=get_password_hash("admin123456"),  # 默认密码，请尽快修改
                name="Admin",
                role="admin",
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)
            print("✅ 管理员用户创建完成")
        else:
            print("ℹ️  管理员用户已存在")

        # 创建测试用户
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(
                email="test@example.com",
                password_hash=get_password_hash("test123456"),
                name="Test User",
                role="user",
                is_active=True,
                is_verified=True,
            )
            db.add(test_user)
            print("✅ 测试用户创建完成")
        else:
            print("ℹ️  测试用户已存在")

        # 提交更改
        db.commit()
        print("✅ 数据库初始化完成")

        # 显示用户信息
        print("\n" + "=" * 50)
        print("📋 用户信息")
        print("=" * 50)
        print(f"📧 管理员邮箱: admin@openspark.online")
        print(f"🔑 管理员密码: admin123456 (请尽快修改)")
        print(f"📧 测试邮箱: test@example.com")
        print(f"🔑 测试密码: test123456")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
