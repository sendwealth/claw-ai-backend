"""
WebSocket 连接管理器
管理所有活跃的 WebSocket 连接
"""

from typing import Dict, List
from fastapi import WebSocket
import json


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        """初始化连接管理器"""
        # 用户 ID 到 WebSocket 连接的映射
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        """
        连接用户

        Args:
            user_id: 用户 ID
            websocket: WebSocket 连接
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        print(f"✅ 用户 {user_id} 已连接")

    def disconnect(self, user_id: int, websocket: WebSocket):
        """
        断开用户连接

        Args:
            user_id: 用户 ID
            websocket: WebSocket 连接
        """
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            # 如果用户没有其他连接，删除用户
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        print(f"🔌 用户 {user_id} 已断开")

    async def send_personal_message(self, user_id: int, message: dict):
        """
        发送消息给指定用户

        Args:
            user_id: 用户 ID
            message: 消息内容
        """
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"❌ 发送消息失败: {e}")

    async def broadcast(self, message: dict, user_ids: List[int] = None):
        """
        广播消息给所有用户

        Args:
            message: 消息内容
            user_ids: 指定用户 ID 列表，None 表示广播给所有用户
        """
        if user_ids:
            # 发送给指定用户
            for user_id in user_ids:
                await self.send_personal_message(user_id, message)
        else:
            # 广播给所有用户
            for user_id, connections in self.active_connections.items():
                for connection in connections:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        print(f"❌ 广播消息失败: {e}")

    def get_active_users(self) -> List[int]:
        """
        获取所有在线用户 ID

        Returns:
            List[int]: 在线用户 ID 列表
        """
        return list(self.active_connections.keys())

    def get_user_connection_count(self, user_id: int) -> int:
        """
        获取用户的连接数量

        Args:
            user_id: 用户 ID

        Returns:
            int: 连接数量
        """
        if user_id in self.active_connections:
            return len(self.active_connections[user_id])
        return 0


# 创建全局连接管理器实例
manager = ConnectionManager()
