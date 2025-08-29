# token_utils.py
from __future__ import annotations
from typing import List, Dict, Any
import tiktoken

_MODEL_TO_ENCODING = {
    "gpt-4o": "o200k_base",         
    "gpt-5": "cl100k_base"
}

def _get_encoding_name(model: str) -> str:
    # tiktoken이 직접 모델명을 인식하면 그걸 사용하고,
    # 아니면 우리가 정의한 매핑 → 마지막엔 cl100k_base로 안전 fallback
    try:
        tiktoken.encoding_for_model(model)
        return model
    except KeyError:
        pass
    return _MODEL_TO_ENCODING.get(model, "cl100k_base")

def count_tokens(text: str, model: str) -> int:
    enc_name = _get_encoding_name(model)
    try:
        enc = tiktoken.encoding_for_model(enc_name)
    except KeyError:
        enc = tiktoken.get_encoding(enc_name)
    return len(enc.encode(text))

def count_message_tokens(messages: List[Dict[str, Any]], model: str) -> int:
    """
    OpenAI Chat 포맷: [{'role': 'system'|'user'|'assistant', 'content': '...'}, ...]
    단순 합산(메타 토큰 가산은 무시 — 비용 추정엔 충분히 정확)
    """
    total = 0
    for m in messages:
        total += count_tokens(m.get("content", "") or "", model)
    return total

def split_and_count_cached_non_cached(messages: List[Dict[str, Any]], model: str) -> Dict[str, int]:
    """
    system 메시지를 '전부 cached input', user/assistant를 'non-cached input'으로 가정해 분리 계측.
    (우리 설계상 system=고정접두사, user=변동이므로 합리적)
    """
    cached = 0
    non_cached = 0
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "") or ""
        n = count_tokens(content, model)
        if role == "system":
            cached += n
        elif role in ("user", "assistant"):
            non_cached += n
        else:
            non_cached += n  # 혹시 모르는 커스텀 role은 비캐시로 처리
    return {
        "cached_input_tokens": cached,
        "non_cached_input_tokens": non_cached
    }
