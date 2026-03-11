from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import StoreEntry
from pydantic import BaseModel, UUID4
from . import crud
from .storage import storage_engine
from datetime import datetime
from auth_manager import current_active_user
from auth_users import User

router = APIRouter(
    prefix="/dataforge",
    tags=["dataforge"]
)

class NoteCreate(BaseModel):
    title: str
    content: str
    user_id: str = None
    etype: str = "note"
    meta_data: dict = None
    source: str = None
    atype: str = None
    ctype: str = None

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
    
    class Config:
        from_attributes = True

@router.post("/notes/", response_model=NoteResponse)
def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    addr = f"{note.etype}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    db_node = crud.create_note(
        db=db,
        title=note.title,
        content=note.content,
        user_id=note.user_id,
        etype=note.etype,
        meta_data=note.meta_data,
        source=note.source,
        atype=note.atype,
        ctype=note.ctype,
        addr=addr
    )
    # Return with content
    response = NoteResponse.from_orm(db_node)
    response.content = note.content 
    return response

@router.get("/notes/{idx}", response_model=NoteResponse)
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

@router.put("/notes/{idx}", response_model=NoteResponse)
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

@router.delete("/notes/{idx}")
def delete_note(idx: str, hard: bool = False, db: Session = Depends(get_db)):
    success = crud.delete_node(db, idx, hard_delete=hard)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Success"}

@router.get("/notes/", response_model=List[NoteResponse])
def list_notes(skip: int = 0, limit: int = 100, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    nodes = crud.get_nodes(db, skip=skip, limit=limit, user_id=user_id)
    responses = []
    for n in nodes:
        resp = NoteResponse.from_orm(n)
        # It's an expensive operation to read from minio for list, but fallback logic can remain.
        # Actually for list, we shouldn't read full content if it slows down. We'll read raw or leave it None depending on needs.
        if n.raw:
             resp.content = n.raw[:200]
        responses.append(resp)
    return responses


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
