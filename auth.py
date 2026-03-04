import os
from fastapi import HTTPException, Form
from dotenv import load_dotenv

load_dotenv()

def verify_token(token: str = Form(...)):
    """
    统一的token验证函数
    """
    expected_token = os.getenv("API_TOKEN", "800811")
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True
