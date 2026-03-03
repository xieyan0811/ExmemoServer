from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from asr.transcribe import router as asr_router
from llm.organize import router as llm_router
from record.process import router as record_router
from database import engine, get_db
import models

# 如果数据库不存表，初始化表结构（由于是连接现有库，可省，但留做保险）
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExmemoServer", version="0.1.0")

app.include_router(asr_router)
app.include_router(llm_router)
app.include_router(record_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/entry/data")
def upload_note(title: str, text: str, db: Session = Depends(get_db)):
    """
    第一步短期产出测试：全新的上传 API，用于接收 ExRecord 文本并直传 PostgreSQL 库。
    """
    import logging
    try:
        from datetime import datetime
        addr = f"record_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        new_entry = models.StoreEntry(
            title=title,
            raw=text,
            etype="record",
            source="exrecord",
            atype="subjective", # 先写死，后续从认证系统获取
            ctype="工作思考", # 先写死，后续从认证系统获取
            addr=addr, # 先写死，后续从认证系统获取
            user_id='谢彦', # 先写死，后续从认证系统获取
            created_time=datetime.utcnow()
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return {"status": "success", "id": new_entry.idx, "title": new_entry.title}
    except Exception as e:
        db.rollback()
        logging.error(f"Error in upload_note: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
