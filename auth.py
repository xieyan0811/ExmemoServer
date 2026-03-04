import os
from fastapi import HTTPException, Form, Query
from dotenv import load_dotenv

load_dotenv()

def verify_token(token: str = Form(...)):
    """
    统一的token验证函数（用于Form数据）
    """
    expected_token = os.getenv("API_TOKEN", "800811")
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True

def verify_token_query(token: str = Query(...)):
    """
    URL查询参数的token验证函数
    """
    expected_token = os.getenv("API_TOKEN", "800811")
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True
