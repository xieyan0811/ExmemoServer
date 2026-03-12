from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import StoreEntry
from pydantic import BaseModel, UUID4
from datetime import datetime
from . import crud
from .storage import storage_engine
from auth_manager import current_active_user, optional_current_user
from auth_users import User
import io

router = APIRouter(
    prefix="/dataforge",
    tags=["dataforge"]
)


class NoteCreate(BaseModel):
    title: str
    content: str
    user_id: str = None
    etype: str = "note"
    addr: str = None
    meta_data: dict = None
    source: str = None
    atype: str = None
    ctype: str = None
    status: str = None


class NoteUpdate(BaseModel):
    title: str = None
    content: str = None
    meta_data: dict = None


class NoteResponse(BaseModel):
    idx: UUID4
    title: Optional[str] = None
    etype: Optional[str] = None
    content: Optional[str] = None
    meta_data: Optional[dict] = None
    path: Optional[str] = None
    # 用户可见的显示路径/名称（与 path 区分：path 是 MinIO 内部路径，addr 是对外展示路径）
    addr: Optional[str] = None
    source: Optional[str] = None
    ctype: Optional[str] = None
    atype: Optional[str] = None
    status: Optional[str] = None
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.post("/data/", response_model=NoteResponse)
def create_note(
    note: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_active_user),
):
    addr = note.addr or f"{note.etype}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    db_node = crud.create_note(
        db=db,
        title=note.title,
        content=note.content,
        user_id=user.email,
        etype=note.etype,
        meta_data=note.meta_data,
        source=note.source,
        atype=note.atype,
        ctype=note.ctype,
        status=note.status,
        addr=addr
    )
    # Return with content
    response = NoteResponse.from_orm(db_node)
    response.content = note.content 
    return response

@router.get("/data/{idx}", response_model=NoteResponse)
def read_note(idx: str, db: Session = Depends(get_db)):
    db_node = crud.get_node(db, idx=idx)
    if db_node is None:
        raise HTTPException(status_code=404, detail="Note not found")
        
    response = NoteResponse.from_orm(db_node)
    
    # Fetch content from Minio if possible, else from legacy raw
    if db_node.path:
        content = storage_engine.get_markdown(db_node.path)
        if content is not None:
            response.content = content
    elif db_node.raw:
        response.content = db_node.raw
            
    return response

@router.put("/data/{idx}", response_model=NoteResponse)
def update_note(idx: str, note: NoteUpdate, db: Session = Depends(get_db)):
    db_node = crud.update_note(
        db,
        idx=idx,
        title=note.title,
        content=note.content,
        meta_data=note.meta_data
    )
    if db_node is None:
        raise HTTPException(status_code=404, detail="Note not found")
        
    response = NoteResponse.from_orm(db_node)
    
    # Reload content
    if note.content:
        response.content = note.content
    elif db_node.path:
        response.content = storage_engine.get_markdown(db_node.path)
    elif db_node.raw:
        response.content = db_node.raw
        
    return response

@router.delete("/data/{idx}")
def delete_note(idx: str, hard: bool = False, db: Session = Depends(get_db)):
    success = crud.delete_node(db, idx, hard_delete=hard)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Success"}

@router.get("/data/", response_model=List[NoteResponse])
def list_notes(
    skip: int = 0,
    limit: int = 100,
    # ── 向下兼容：旧客户端可直接传 user_id 参数 ──
    # ── 新客户端携带 JWT Token，user_id 参数可省略 ───
    user_id: Optional[str] = None,
    etype: Optional[str] = None,
    ctype: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(optional_current_user),
):
    # JWT 优先；没有 JWT 则 fallback 到 user_id 查询参数
    effective_user_id = user.email if user is not None else user_id
    if not effective_user_id:
        raise HTTPException(status_code=401, detail="未登录或未提供 user_id")

    # 解析日期字符串
    parsed_start = None
    parsed_end = None
    try:
        if start_date:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")

    nodes = crud.get_nodes(
        db,
        skip=skip,
        limit=limit,
        user_id=effective_user_id,
        etype=etype,
        ctype=ctype,
        status=status,
        keyword=search,
        start_date=parsed_start,
        end_date=parsed_end,
    )
    responses = []
    for n in nodes:
        resp = NoteResponse.from_orm(n)
        if n.raw:
            resp.content = n.raw[:200]
        responses.append(resp)
    return responses


@router.get("/data/{idx}/download")
def download_file(idx: str, db: Session = Depends(get_db)):
    """
    下载文件原始内容。
    - 有 MinIO path：从对象存储流式返回原文件
    - 无 path 但有 raw 文本：作为纯文本文件返回（兼容旧 record 数据）
    """
    db_node = crud.get_node(db, idx=idx)
    if db_node is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    if db_node.path:
        file_data = storage_engine.get_file(db_node.path)
        if file_data is None:
            raise HTTPException(status_code=404, detail="File not found in storage")

        filename = db_node.title or db_node.path.rsplit("/", 1)[-1]
        content_type = "application/octet-stream"
        if db_node.meta_data and "content_type" in db_node.meta_data:
            content_type = db_node.meta_data["content_type"]

        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    elif db_node.raw:
        # 兼容旧系统中直接存 raw 字段的 record 类型
        filename = (db_node.title or db_node.addr or "content") + ".txt"
        return StreamingResponse(
            io.BytesIO(db_node.raw.encode("utf-8")),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    raise HTTPException(status_code=404, detail="No content available for this entry")


@router.get("/data/{idx}/presigned-url")
def get_presigned_url(
    idx: str,
    expires: int = Query(default=3600, ge=60, le=604800, description="链接有效期（秒），60~604800"),
    db: Session = Depends(get_db),
):
    """
    获取 MinIO 预签名临时下载 URL。
    客户端收到 URL 后可直接向 MinIO 发起 GET 请求下载大文件，
    无需经过 ExmemoServer 中转，节省服务器带宽。
    """
    db_node = crud.get_node(db, idx=idx)
    if db_node is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    if not db_node.path:
        raise HTTPException(status_code=404, detail="No file path associated with this entry")

    url = storage_engine.get_presigned_url(db_node.path, expires_seconds=expires)
    return {"url": url, "expires_in": expires, "path": db_node.path}


@router.post("/upload/", response_model=NoteResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """
    上传任意文件。
    - 需要在请求头中携带 Authorization: Bearer <token>
    - 文件保存至 MinIO，元信息写入数据库
    - user_id 自动取当前登录用户的邮箱
    """
    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="上传的文件为空")

    filename = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"

    entry = crud.create_file_entry(
        db=db,
        filename=filename,
        file_data=file_data,
        user_id=user.email,
        content_type=content_type,
        source="upload",
    )
    response = NoteResponse.from_orm(entry)
    return response
