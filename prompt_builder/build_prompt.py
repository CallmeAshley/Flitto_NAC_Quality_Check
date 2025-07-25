import os
import json

SYSTEM_PROMPT_PATH = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/prompt_builder/prompts/system.txt"
USER_PROMPT_PATH = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/prompt_builder/prompts/user.txt"

def build_prompt_from_json(sample: dict, rag_context: str) -> list:
    """
    JSON 입력(sample)으로부터 system/user 프롬프트를 생성하는 함수
    Args:
        sample: {
            "source": "french",
            "target": "korean",
            "text": "22 octobre 2023",
            "trans": "2023년 10월 22일"
        }
    Returns:
        [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
    """

    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()

    with open(USER_PROMPT_PATH, "r", encoding="utf-8") as f:
        user_prompt_template = f.read().strip()

    user_prompt = user_prompt_template.format(
        source=sample["source"],
        target=sample["target"],
        text=sample["text"],
        trans=sample["trans"],
        context=rag_context
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]