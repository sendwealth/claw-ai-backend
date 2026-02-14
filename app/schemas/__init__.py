"""Schemas package"""

from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    Token,
    TokenData,
    LoginRequest,
    RegisterRequest,
    SubscriptionUpdate,
    SubscriptionResponse,
    MessageResponse as UserMessageResponse,
)

from app.schemas.conversation import (
    ConversationBase,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetailResponse,
    MessageBase,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
)

from app.schemas.knowledge import (
    KnowledgeBaseBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseDetailResponse,
    DocumentBase,
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
)

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "Token",
    "TokenData",
    "LoginRequest",
    "RegisterRequest",
    "SubscriptionUpdate",
    "SubscriptionResponse",
    "UserMessageResponse",
    # Conversation
    "ConversationBase",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationDetailResponse",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "MessageListResponse",
    # Knowledge
    "KnowledgeBaseBase",
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "KnowledgeBaseResponse",
    "KnowledgeBaseDetailResponse",
    "DocumentBase",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentListResponse",
]
