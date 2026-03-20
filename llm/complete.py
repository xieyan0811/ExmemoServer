import os

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/llm", tags=["llm"])

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        base_url = os.getenv("OPENAI_BASE_URL") or None
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=base_url)
    return _client


class CompleteRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    token: str


class CompleteResponse(BaseModel):
    text: str


@router.post("/complete", response_model=CompleteResponse)
async def complete(req: CompleteRequest):
    """
    通用 LLM 接口，客户端传入完整的 system_prompt 和 user_prompt，服务端只负责转发并返回文本结果。

    - 请求：{"system_prompt": "...", "user_prompt": "...", "token": "验证令牌"}
    - 返回：{"text": "LLM 原始文本结果"}
    """
    expected_token = os.getenv("API_TOKEN", "800811")
    if req.token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        response = get_client().chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.user_prompt},
            ],
        )
        text = response.choices[0].message.content or ""
        return CompleteResponse(text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
