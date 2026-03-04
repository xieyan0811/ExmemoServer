import os
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from openai import OpenAI
from dotenv import load_dotenv
from auth import verify_token

load_dotenv()

router = APIRouter(prefix="/asr", tags=["asr"])

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        base_url = os.getenv("OPENAI_BASE_URL") or None
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=base_url)
    return _client


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), _: bool = Depends(verify_token)):
    """
    接收音频文件，调用 OpenAI Whisper API 进行语音识别，返回识别文字。

    - 请求：multipart/form-data，字段名 file（音频文件）和 token（验证令牌）
    - 返回：{"text": "识别出的文字"}
    """
    suffix = os.path.splitext(file.filename or "audio")[1] or ".m4a"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcript = get_client().audio.transcriptions.create(
                model=os.getenv("ASR_MODEL", "whisper-1"),
                file=audio_file,
            )
        return {"text": transcript.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
