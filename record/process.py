import json
import os
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/record", tags=["record"])

_client: OpenAI | None = None

ORGANIZE_PROMPT = """\
你是一个笔记整理助手。用户会给你一段语音识别出的原始文字，内容可能包含口语化表达、重复词、语气词等。
请你完成以下工作：
1. 将原文整理成通顺的书面文字，去除语气词和明显的冗余重复
2. 提炼一个简短的标题（不超过 20 字）
3. 仅以 JSON 格式返回，结构为：{"title": "...", "content": "..."}
不要输出任何 JSON 以外的内容。\
"""


def get_client() -> OpenAI:
    global _client
    if _client is None:
        base_url = os.getenv("OPENAI_BASE_URL") or None
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=base_url)
    return _client


class ProcessResponse(BaseModel):
    raw_text: str
    title: str
    content: str


@router.post("/process", response_model=ProcessResponse)
async def process(file: UploadFile = File(...)):
    """
    接收音频文件，内部串联 ASR → LLM，一次返回全部结果。

    - 请求：multipart/form-data，字段名 file，支持 m4a、mp3、wav 等格式
    - 返回：{"text": "原始识别文字", "title": "标题", "content": "整理后正文"}
    """
    suffix = os.path.splitext(file.filename or "audio")[1] or ".m4a"
    tmp_path = None
    try:
        # Step 1: ASR
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcript = get_client().audio.transcriptions.create(
                model=os.getenv("ASR_MODEL", "whisper-1"),
                file=audio_file,
            )
        raw_text = transcript.text

        # Step 2: LLM organize
        response = get_client().chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": ORGANIZE_PROMPT},
                {"role": "user", "content": raw_text},
            ],
        )
        result = json.loads(response.choices[0].message.content)
        return ProcessResponse(
            raw_text=raw_text,
            title=result["title"],
            content=result["content"],
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"LLM 返回格式解析失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
