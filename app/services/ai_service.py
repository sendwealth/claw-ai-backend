"""
AI 服务
对接 Zhipu AI API，提供对话生成能力
"""

from typing import List, Optional, Dict, Any
from zhipuai import ZhipuAI
import json
import time

from app.core.config import settings


class AIService:
    """AI 服务类"""

    def __init__(self):
        """初始化 AI 服务"""
        self.client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
        self.model = settings.ZHIPUAI_MODEL

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        生成对话

        Args:
            messages: 对话历史列表
            system_prompt: 系统提示词
            temperature: 温度参数（0-1）
            max_tokens: 最大 Token 数量

        Returns:
            dict: 包含响应内容、Token 数量、成本等信息
        """
        # 构建消息列表
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        # 调用 Zhipu AI API
        try:
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            end_time = time.time()

            # 解析响应
            content = response.choices[0].message.content
            tokens = {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
            }

            # 计算成本（估算）
            cost = self._calculate_cost(tokens["total"])

            return {
                "success": True,
                "content": content,
                "tokens": tokens,
                "cost": cost,
                "response_time": end_time - start_time,
                "model": self.model,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": None,
                "tokens": None,
                "cost": None,
            }

    def _calculate_cost(self, total_tokens: int) -> float:
        """
        计算 AI 调用成本

        Args:
            total_tokens: 总 Token 数量

        Returns:
            float: 成本（单位：元）
        """
        # Zhipu AI GLM-4 定价（估算）
        # 每 1000 tokens 约 ¥0.02
        cost_per_1k_tokens = 0.02
        return round(total_tokens * cost_per_1k_tokens / 1000, 4)

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ):
        """
        流式对话（用于实时显示）

        Args:
            messages: 对话历史列表
            system_prompt: 系统提示词

        Yields:
            str: 流式响应内容
        """
        # 构建消息列表
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        # 调用流式 API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                stream=True,
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error: {str(e)}"

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 Token 数量

        Args:
            text: 输入文本

        Returns:
            int: 估算的 Token 数量
        """
        # 粗略估算：中文字符约 1 token，英文单词约 0.75 token
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        return int(chinese_chars + other_chars * 0.75)


# 创建全局 AI 服务实例
ai_service = AIService()
