from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from asr.transcribe import router as asr_router
from llm.organize import router as llm_router
from record.process import router as record_router
from dataforge.router import router as dataforge_router
from dataforge import crud
from database import engine, get_db
from auth import verify_token_query
import models
from pydantic import BaseModel
import datetime

class NoteRequest(BaseModel):
    title: str
    text: str

app = FastAPI(title="ExmemoServer", version="0.1.0")

app.include_router(asr_router)
app.include_router(llm_router)
app.include_router(record_router)
app.include_router(dataforge_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/entry/data")
def upload_note(body: NoteRequest, db: Session = Depends(get_db), _: bool = Depends(verify_token_query)):
    """
    第一步短期产出测试：全新的上传 API，用于接收 ExRecord 文本并直传 PostgreSQL 和 Minio 库。
    支持GET和POST两种方式，token通过查询参数传递。
    """
    import logging
    try:
        from datetime import datetime
        title = body.title
        text = body.text
        addr = f"record_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Now use the new dataforge crud which handles Minio Markdown storage automatically 
        # as well as the old double-block (0 and 1) storage to stay compatible.
        entry_main = crud.create_note(
            db=db,
            title=title,
            content=text,
            user_id="谢彦",
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
