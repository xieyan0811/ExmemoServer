"""
auth_manager.py
───────────────
FastAPI Users 业务层：
  - Pydantic Schema（UserRead / UserCreate / UserUpdate）
  - UserManager（注册/登录回调、重置密码密钥）
  - JWT 认证后端（Bearer Transport + JWTStrategy）
  - fastapi_users 核心对象
  - current_active_user 依赖（在受保护接口中使用）
"""

import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from auth_users import User, get_user_db

load_dotenv()

# ── 密钥 & 过期时间（生产环境请在 .env 中使用安全随机字符串）────
SECRET = os.getenv("JWT_SECRET", "please-change-this-in-production")
# JWT 令牌有效期（秒），默认 7 天
JWT_LIFETIME = int(os.getenv("JWT_LIFETIME_SECONDS", str(3600 * 24 * 7)))


# ── Pydantic Schemas ─────────────────────────────────────────────
class UserRead(schemas.BaseUser[uuid.UUID]):
    """注册/查询时返回给客户端的用户信息（不含密码哈希）"""
    pass


class UserCreate(schemas.BaseUserCreate):
    """注册时客户端提交的字段：email + password"""
    pass


class UserUpdate(schemas.BaseUserUpdate):
    """修改用户信息时客户端可提交的字段"""
    pass


# ── UserManager ──────────────────────────────────────────────────
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ):
        print(f"[Auth] ✅ 注册成功: {user.email}  (id={user.id})")

    async def on_after_login(
        self, user: User, request: Optional[Request] = None, response=None
    ):
        print(f"[Auth] 🔑 用户登录: {user.email}  (id={user.id})")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        # TODO: 接入邮件服务后在此发送重置密码邮件
        print(f"[Auth] 🔒 忘记密码: {user.email}  重置 token={token}")

    async def on_after_reset_password(
        self, user: User, request: Optional[Request] = None
    ):
        print(f"[Auth] ✅ 密码已重置: {user.email}")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# ── 认证后端（Bearer JWT）────────────────────────────────────────
# 客户端需在请求头中携带：Authorization: Bearer <access_token>
bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=JWT_LIFETIME)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# ── FastAPIUsers 核心对象 ─────────────────────────────────────────
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# 在受保护的路由中使用：user: User = Depends(current_active_user)
current_active_user = fastapi_users.current_user(active=True)

# 可选鉴权：有 JWT Token 时解析用户，无 Token 时返回 None
# 用于同时兼容新端（JWT）和旧端（user_id 查询参数）的接口
optional_current_user = fastapi_users.current_user(optional=True)
