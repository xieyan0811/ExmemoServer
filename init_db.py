"""
init_db.py
──────────
一次性初始化脚本，按顺序完成：

  1. 创建 PostgreSQL 数据库（若不存在）
  2. 启用 pgvector 扩展（供 StoreEntry.embeddings 字段使用）
  3. 通过 SQLAlchemy Base.metadata.create_all() 创建所有表
     （user_account、store_entry 等）

使用方式（在 Docker 容器或宿主机内执行一次即可）：
  python init_db.py
"""

import os
import asyncio

from dotenv import load_dotenv

load_dotenv()

# ── 读取数据库配置 ───────────────────────────────────────────────
PG_HOST = os.getenv("PGSQL_HOST", "127.0.0.1")
PG_PORT = os.getenv("PGSQL_PORT", "5432")
PG_USER = os.getenv("PGSQL_USER", "postgres")
PG_PASSWORD = os.getenv("PGSQL_PASSWORD", "")
PG_DB = os.getenv("PGSQL_DB", "exmemo_new")


# ── Step 1: 创建数据库（使用 psycopg2 连到 postgres 默认库）──────
def create_database():
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    print(f"[init_db] 连接到 postgres 默认库: {PG_HOST}:{PG_PORT}")
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (PG_DB,)
    )
    if cur.fetchone():
        print(f"[init_db] ✅ 数据库 '{PG_DB}' 已存在，跳过创建")
    else:
        cur.execute(f'CREATE DATABASE "{PG_DB}"')
        print(f"[init_db] ✅ 数据库 '{PG_DB}' 创建成功")

    cur.close()
    conn.close()


# ── Step 2 & 3: 启用 pgvector + 建表（连到目标库，使用 asyncpg）──
async def create_extensions_and_tables():
    # 延迟导入，保证此时 .env 已经加载
    from auth_users import engine_async
    # 导入所有模型，确保它们注册到 Base.metadata
    import models       # noqa: F401 – 注册 StoreEntry
    import auth_users   # noqa: F401 – 注册 User
    from database import Base

    async with engine_async.begin() as conn:
        # 启用 pgvector 扩展（StoreEntry 的 embeddings 字段依赖它）
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        print("[init_db] ✅ pgvector 扩展已就绪")

        # 创建所有表（已存在的表会被跳过）
        await conn.run_sync(Base.metadata.create_all)
        print("[init_db] ✅ 所有表创建完成")

    await engine_async.dispose()


# ── 入口 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print(f"目标数据库: {PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")
    print("=" * 50)

    create_database()
    asyncio.run(create_extensions_and_tables())

    print("=" * 50)
    print("[init_db] 🎉 初始化完成，可以启动服务了！")
    print("=" * 50)
