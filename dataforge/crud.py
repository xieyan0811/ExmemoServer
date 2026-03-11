from sqlalchemy.orm import Session
from models import StoreEntry
import uuid
import datetime
import hashlib
from typing import Optional, List, Dict, Any
from .storage import storage_engine

def get_node(db: Session, idx: str) -> Optional[StoreEntry]:
    return db.query(StoreEntry).filter(StoreEntry.idx == idx, StoreEntry.is_deleted == False, StoreEntry.block_id == 1).first()

def get_nodes(db: Session, skip: int = 0, limit: int = 100, user_id: str = None) -> List[StoreEntry]:
    query = db.query(StoreEntry).filter(StoreEntry.is_deleted == False, StoreEntry.block_id == 1)
    if user_id:
        query = query.filter(StoreEntry.user_id == user_id)
    return query.order_by(StoreEntry.created_time.desc()).offset(skip).limit(limit).all()

def calc_md5(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()

def create_note(db: Session, title: str, content: str, user_id: str = None, etype: str = "note", meta_data: dict = None, source: str = None, atype: str = None, ctype: str = None, addr: str = None) -> StoreEntry:
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
