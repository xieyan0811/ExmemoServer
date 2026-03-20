from contextlib import asynccontextmanager
 
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from asr.transcribe import router as asr_router
from llm.complete import router as llm_router
from record.process import router as record_router
from dataforge.router import router as dataforge_router
from dataforge import crud
from database import get_db
import models          # noqa: F401 – 注册 StoreEntry 到 Base.metadata
import auth_users      # noqa: F401 – 注册 User 到 Base.metadata
from auth_users import engine_async, User
from auth_manager import (
    auth_backend,
    fastapi_users,
    current_active_user,
    UserRead,
    UserCreate,
    UserUpdate,
)
from database import Base
from pydantic import BaseModel
import datetime


class NoteRequest(BaseModel):
    title: str
    text: str


# ── 生命周期：服务启动时确保所有表存在（幂等操作）───────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine_async.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="ExmemoServer", version="0.1.0", lifespan=lifespan)

# ── 用户认证路由 ─────────────────────────────────────────────────
# POST /auth/jwt/login    → 登录，返回 access_token（表单格式）
# POST /auth/jwt/logout   → 登出
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# POST /auth/register     → 注册新用户（JSON: email + password）
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# POST /auth/forgot-password  → 触发重置密码流程
# POST /auth/reset-password   → 提交新密码 + 重置 token
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# GET  /users/me          → 获取当前用户信息
# PATCH /users/me         → 修改当前用户信息
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# ── 业务路由（保持不变）─────────────────────────────────────────
app.include_router(asr_router)
app.include_router(llm_router)
app.include_router(record_router)
app.include_router(dataforge_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/entry/data")
def upload_note(
    body: NoteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    接收 ExRecord 文本并直传 PostgreSQL 和 Minio。
    需要 JWT 登录态，请求头携带 Authorization: Bearer <access_token>。
    """
    import logging
    try:
        from datetime import datetime
        title = body.title
        text = body.text
        addr = f"record_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Now use the new dataforge crud which handles Minio Markdown storage automatically 
        # as well as the old double-block (0 and 1) storage to stay compatible.
        entry_main = crud.create_note(
            db=db,
            title=title,
            content=text,
            user_id=user.email,
            etype="record",
            source="exrecord",
            atype="subjective",
            ctype="工作思考",
            addr=addr
        )
        
        return {"status": "success", "id": str(entry_main.idx), "title": entry_main.title}
    except Exception as e:
        db.rollback()
        logging.error(f"Error in upload_note: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
