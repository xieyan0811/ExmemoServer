from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import StoreEntry
import uuid
import datetime
import hashlib
from typing import Optional, List, Dict, Any
from .storage import storage_engine

def get_node(db: Session, idx: str) -> Optional[StoreEntry]:
    return db.query(StoreEntry).filter(StoreEntry.idx == idx, StoreEntry.is_deleted == False, StoreEntry.block_id == 1).first()

def get_nodes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: str = None,
    etype: str = None,
    ctype: str = None,
    status: str = None,
    keyword: str = None,
    start_date: datetime.datetime = None,
    end_date: datetime.datetime = None,
) -> List[StoreEntry]:
    query = db.query(StoreEntry).filter(StoreEntry.is_deleted == False, StoreEntry.block_id == 1)
    if user_id:
        query = query.filter(StoreEntry.user_id == user_id)
    if etype:
        query = query.filter(StoreEntry.etype == etype)
    if ctype:
        query = query.filter(StoreEntry.ctype == ctype)
    if status:
        query = query.filter(StoreEntry.status == status)
    if keyword:
        query = query.filter(
            or_(
                StoreEntry.title.ilike(f"%{keyword}%"),
                StoreEntry.raw.ilike(f"%{keyword}%"),
            )
        )
    if start_date:
        query = query.filter(StoreEntry.created_time >= start_date)
    if end_date:
        query = query.filter(StoreEntry.created_time <= end_date)
    return query.order_by(StoreEntry.created_time.desc()).offset(skip).limit(limit).all()

def calc_md5(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()

def create_note(db: Session, title: str, content: str, user_id: str = None, etype: str = "note", meta_data: dict = None, source: str = None, atype: str = None, ctype: str = None, status: str = None, addr: str = None) -> StoreEntry:
    node_idx = uuid.uuid4()
    
    # Generate storage path: type/year/month/uuid.md
    now = datetime.datetime.utcnow()
    path = f"{etype}/{now.year}/{now.month:02d}/{node_idx}.md"
    
    # Save to Minio
    storage_engine.put_markdown(path, content)
    md5_hash = calc_md5(content.encode('utf-8'))
    
    # To keep compatibility, we write the exact same two records:
    # 1. Main entry (block_id=0): raw holds the abstract/summary (we truncate content)
    entry_main = StoreEntry(
        idx=node_idx,
        user_id=user_id,
        title=title,
        raw=content[:200], # truncated as temp abstract
        meta_data=meta_data or {},
        etype=etype,
        source=source,
        atype=atype,
        ctype=ctype,
        status=status,
        addr=addr,
        path=path,  # ExmemoServer only: store the minio path
        md5=md5_hash,
        block_id=0,
        created_time=now
    )
    
    # 2. Content entry (block_id=1): raw holds the full text
    entry_content = StoreEntry(
        idx=node_idx,
        user_id=user_id,
        title=title,
        raw=content,
        meta_data=meta_data or {},
        etype=etype,
        source=source,
        atype=atype,
        ctype=ctype,
        status=status,
        addr=addr,
        path=path,
        md5=md5_hash,
        block_id=1,
        created_time=now
    )
    
    db.add(entry_main)
    db.add(entry_content)
    db.commit()
    db.refresh(entry_main)
    return entry_main

def update_note(db: Session, idx: str, title: Optional[str] = None, content: Optional[str] = None, meta_data: Optional[dict] = None) -> Optional[StoreEntry]:
    # Update both block 0 and block 1
    db_node_0 = db.query(StoreEntry).filter(StoreEntry.idx == idx, StoreEntry.block_id == 0).first()
    db_node_1 = db.query(StoreEntry).filter(StoreEntry.idx == idx, StoreEntry.block_id == 1).first()
    
    if not db_node_0 and not db_node_1:
        return None
        
    nodes = [n for n in [db_node_0, db_node_1] if n]
        
    for node in nodes:
        if title is not None:
            node.title = title
            
        if meta_data is not None:
            current_meta = dict(node.meta_data) if node.meta_data else {}
            current_meta.update(meta_data)
            node.meta_data = current_meta
            
        if content is not None:
            if not node.path:
                now = node.created_time or datetime.datetime.utcnow()
                node.path = f"{node.etype}/{now.year}/{now.month:02d}/{node.idx}.md"
            node.md5 = calc_md5(content.encode('utf-8'))
            if node.block_id == 1:
                node.raw = content
            elif node.block_id == 0:
                node.raw = content[:200]
                
        node.updated_time = datetime.datetime.utcnow()

    # Save to minio only once
    if content is not None and len(nodes) > 0:
        path = nodes[0].path
        storage_engine.put_markdown(path, content)
        
    db.commit()
    if db_node_0:
        db.refresh(db_node_0)
    return db_node_0 or db_node_1

def delete_node(db: Session, idx: str, hard_delete: bool = False):
    nodes = db.query(StoreEntry).filter(StoreEntry.idx == idx).all()
    if not nodes:
        return False
        
    if hard_delete:
        if nodes[0].path:
            storage_engine.delete_file(nodes[0].path)
        for node in nodes:
            db.delete(node)
    else:
        for node in nodes:
            node.is_deleted = True
        
    db.commit()
    return True


def create_file_entry(
    db: Session,
    filename: str,
    file_data: bytes,
    user_id: str,
    content_type: str = "application/octet-stream",
    source: str = "upload",
) -> StoreEntry:
    """将上传的二进制文件存到 MinIO，并在数据库中创建对应的 StoreEntry。
    与 create_note 保持一致，同时写入 block_id=0（主记录/摘要）和 block_id=1（内容记录），
    保证旧系统（Django/exmemo）仍可正常读取。
    """
    node_idx = uuid.uuid4()
    now = datetime.datetime.utcnow()

    # 提取扩展名，拼装 MinIO 存储路径
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    path = f"upload/{now.year}/{now.month:02d}/{node_idx}.{ext}"

    storage_engine.put_file(path, file_data, content_type)
    md5_hash = calc_md5(file_data)
    meta = {"filename": filename, "content_type": content_type, "size": len(file_data)}

    common = dict(
        idx=node_idx,
        user_id=user_id,
        title=filename,
        raw=None,
        meta_data=meta,
        etype="file",
        source=source,
        atype=None,
        ctype=None,
        addr=filename,
        path=path,
        md5=md5_hash,
        created_time=now,
    )

    # block_id=0：主记录（旧系统列表/树视图读的是这条）
    entry_main = StoreEntry(**common, block_id=0)
    # block_id=1：内容记录（新系统 get_node / get_nodes 读的是这条）
    entry_content = StoreEntry(**common, block_id=1)

    db.add(entry_main)
    db.add(entry_content)
    db.commit()
    db.refresh(entry_main)
    return entry_main
