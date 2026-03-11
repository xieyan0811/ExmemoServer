"""
auth_users.py
─────────────
异步数据库层：定义 User 表模型及 FastAPI Users 所需的依赖注入。

使用与 database.py 相同的 Base，保证所有表可通过同一次
Base.metadata.create_all() 统一创建。
"""

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database import Base

load_dotenv()

# ── 异步数据库 URL（asyncpg 驱动）─────────────────────────────
_host = os.getenv("PGSQL_HOST", "127.0.0.1")
_port = os.getenv("PGSQL_PORT", "5432")
_user = os.getenv("PGSQL_USER", "postgres")
_pwd  = os.getenv("PGSQL_PASSWORD", "")
_db   = os.getenv("PGSQL_DB", "exmemo_new")

DATABASE_URL_ASYNC = (
    f"postgresql+asyncpg://{_user}:{_pwd}@{_host}:{_port}/{_db}"
)

engine_async = create_async_engine(DATABASE_URL_ASYNC, echo=False)
async_session_maker = async_sessionmaker(engine_async, expire_on_commit=False)


# ── 用户表模型 ─────────────────────────────────────────────────
class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    用户表。SQLAlchemyBaseUserTableUUID 已提供以下字段：
      id (UUID PK)、email、hashed_password、
      is_active、is_superuser、is_verified
    如需扩展字段（如昵称、手机号），直接在此处添加 Column。
    """
    __tablename__ = "user_account"


# ── 依赖注入 ────────────────────────────────────────────────────
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
