from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from asr.transcribe import router as asr_router
from llm.organize import router as llm_router
from record.process import router as record_router
from database import engine, get_db
from auth import verify_token
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
def upload_note(title: str, text: str, db: Session = Depends(get_db), _: bool = Depends(verify_token)):
    """
    第一步短期产出测试：全新的上传 API，用于接收 ExRecord 文本并直传 PostgreSQL 库。
    """
    import logging
    try:
        from datetime import datetime
        addr = f"record_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        # 主记录 (block_id = 0)，原本应为摘要，我们先简单截断前文
        entry_main = models.StoreEntry(
            title=title,
            raw=text[:200],  # 截断部分作为临时摘要
            etype="record",
            source="exrecord",
            atype="subjective", # 先写死，后续从认证系统获取
            ctype="工作思考", # 先写死，后续从认证系统获取
            addr=addr, # 先写死，后续从认证系统获取
            user_id='谢彦', # 先写死，后续从认证系统获取
            block_id=0,
            created_time=datetime.utcnow()
        )
        
        # 正文记录 (block_id = 1)，用于前端读取完整内容
        entry_content = models.StoreEntry(
            title=title,
            raw=text,
            etype="record",
            source="exrecord",
            atype="subjective",
            ctype="工作思考",
            addr=addr,
            user_id='谢彦',
            block_id=1,
            created_time=datetime.utcnow()
        )

        db.add(entry_main)
        db.add(entry_content)
        db.commit()
        db.refresh(entry_main)
        return {"status": "success", "id": entry_main.idx, "title": entry_main.title}
    except Exception as e:
        db.rollback()
        logging.error(f"Error in upload_note: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
