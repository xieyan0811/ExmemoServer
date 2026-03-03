from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 从环境变量获取数据库连接串，依据现有的 PostgreSQL 配置
PG_HOST = os.getenv("PGSQL_HOST", "192.168.10.168")
PG_PORT = os.getenv("PGSQL_PORT", "5432")
PG_USER = os.getenv("PGSQL_USER", "postgres")
PG_PASSWORD = os.getenv("PGSQL_PASSWORD", "xie54yan321")
PG_DB = os.getenv("PGSQL_DB", "exmemo")

DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}")

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()

# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
