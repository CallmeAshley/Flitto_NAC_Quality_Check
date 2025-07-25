import os
import openai
from dotenv import load_dotenv

# .env에서 API 키 불러오기
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def call_gpt(messages, model="gpt-4o", temperature=0.0):
    """
    GPT API 호출 함수

    Args:
        messages (list): [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        model (str): 사용할 모델명 (기본값: gpt-4o)
        temperature (float): 창의성 조절 (기본값: 0.0, 검수 작업에 적절)

    Returns:
        str: GPT의 응답 텍스트
    """

    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return response["choices"][0]["message"]["content"]

