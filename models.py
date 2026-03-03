import uuid
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import datetime
from database import Base

class StoreEntry(Base):
    __tablename__ = 'store_entry'

    idx = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=True)

    embeddings = Column(Vector(dim=None), nullable=True)
    emb_model = Column(String(64), nullable=True)
    block_id = Column(Integer, default=0)
    raw = Column(Text, nullable=True)
    
    title = Column(String(256), nullable=True)
    meta_data = Column("meta", JSON, default=dict) # SQLAlchemy 中 meta 是保留字，采用 mapping

    etype = Column(String(30), default="note")
    atype = Column(String(32), nullable=True)
    ctype = Column(String(64), nullable=True)
    status = Column(String(64), default="init")
    source = Column(String(32), nullable=True)
    access_level = Column(Integer, default=-1)

    addr = Column(String(400), nullable=True)
    path = Column(String(400), nullable=True)
    md5 = Column(String(200), nullable=True)

    is_deleted = Column(Boolean, default=False)
    created_time = Column(DateTime, default=datetime.datetime.utcnow)
    updated_time = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
