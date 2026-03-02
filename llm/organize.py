import json
import os

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/llm", tags=["llm"])

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


class OrganizeRequest(BaseModel):
    text: str


class OrganizeResponse(BaseModel):
    title: str
    content: str


@router.post("/organize", response_model=OrganizeResponse)
async def organize(req: OrganizeRequest):
    """
    接收语音识别的原始文字，用 LLM 整理成标题 + 正文后返回。

    - 请求：{"text": "原始识别文字"}
    - 返回：{"title": "标题", "content": "整理后的正文"}
    """
    try:
        response = get_client().chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": ORGANIZE_PROMPT},
                {"role": "user", "content": req.text},
            ],
        )
        result = json.loads(response.choices[0].message.content)
        return OrganizeResponse(**result)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"LLM 返回格式解析失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
