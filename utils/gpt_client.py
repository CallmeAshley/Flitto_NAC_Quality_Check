import openai
import os
import json
from typing import List, Tuple

# 환경 변수로부터 키 로딩
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_gpt(messages: List[dict], model="gpt-4o", temperature=0.0) -> Tuple[str | list, dict]:
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        reply = response["choices"][0]["message"]["content"].strip()
        usage = response["usage"]

        if reply.startswith("["):
            try:
                return json.loads(reply), usage
            except json.JSONDecodeError:
                return [], usage

        return reply, usage

    except Exception as e:
        print(f"ChatGPT API 오류 발생: {e}")
        return "error", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
