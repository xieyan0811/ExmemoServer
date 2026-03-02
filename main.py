from fastapi import FastAPI
from asr.transcribe import router as asr_router
from llm.organize import router as llm_router
from record.process import router as record_router

app = FastAPI(title="ExmemoServer", version="0.1.0")

app.include_router(asr_router)
app.include_router(llm_router)
app.include_router(record_router)


@app.get("/health")
def health():
    return {"status": "ok"}
