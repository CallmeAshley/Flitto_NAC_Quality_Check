# prompt_builder/prompt_cache.py
from __future__ import annotations
import hashlib
from typing import Optional, Tuple, Dict, List, Any

# 가이드라인 로드
from utils.file_utils import load_guideline
# 프롬프트 상수 (고정 system 블록)
from prompt_builder.build_prompt import (
    SYSTEM_CATEGORY_BLOCK,  # 카테고리 감지용 고정 system
    SYSTEM_RULES_BLOCK,     # 포맷 검수 공통 규칙
)

# =========================
# 토큰 카운트 유틸 (tiktoken 우선, 없으면 폴백)
# =========================
try:
    import tiktoken
except Exception:
    tiktoken = None  # 폴백 사용

_MODEL_TO_ENCODING = {
    "gpt-4o": "o200k_base",
    "gpt-5": "cl100k_base"
}

def _get_encoding_name(model: str) -> str:
    if tiktoken is None:
        return "fallback"
    try:
        # 모델명을 직접 인식하면 그대로 사용
        tiktoken.encoding_for_model(model)
        return model
    except Exception:
        return _MODEL_TO_ENCODING.get(model, "cl100k_base")

def _count_tokens(text: str, model: str) -> int:
    if not text:
        return 0
    if tiktoken is None:
        # 매우 보수적인 폴백(공백 단위 근사) — 비용 추정용
        return max(1, len(text.split()))
    enc_name = _get_encoding_name(model)
    try:
        enc = tiktoken.encoding_for_model(enc_name)
    except Exception:
        enc = tiktoken.get_encoding(enc_name)
    return len(enc.encode(text))

def _split_and_count_cached_non_cached(messages: List[Dict[str, Any]], model: str) -> Dict[str, int]:
    """
    설계상: system = 전부 cached input, user/assistant = non-cached input
    """
    cached = 0
    non_cached = 0
    for m in messages:
        n = _count_tokens(m.get("content", "") or "", model)
        if m.get("role") == "system":
            cached += n
        else:
            non_cached += n
    return {
        "cached_input_tokens": cached,
        "non_cached_input_tokens": non_cached,
    }

# =========================
# 내부 캐시
# =========================
_guideline_text_cache: dict[tuple[str, str], str] = {}  # (target, category) -> guideline text (가공 금지)
_system_prefix_cache: dict[str, str] = {}               # cache_key -> system prefix string

def _hash_text(s: str) -> str:
    """가이드라인 본문 그대로 해시. 1자라도 바뀌면 캐시 키가 달라짐."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def _get_guideline_text(target: str, category: str) -> Optional[str]:
    """
    (target, category) 기준 가이드라인 텍스트 1회 로드 후 그대로 보관.
    ⚠ 개행/스페이싱/유니코드 정규화 등 가공 금지 (캐시 안정성).
    """
    key = (target, category)
    if key in _guideline_text_cache:
        return _guideline_text_cache[key]
    text = load_guideline(target, category)
    if not text:
        return None
    _guideline_text_cache[key] = text
    return text

def _build_system_prefix(target: str, category: str, guideline_text: str) -> str:
    """
    OpenAI cached input이 붙도록 '항상 동일한' system 접두사 조립.
    헤더/개행/스페이싱 절대 변경 금지.
    """
    return (
        f"[LOCALE]\n{target} / {category}\n\n"
        "[GUIDELINE]\n"
        f"{guideline_text}\n\n"
        "[INSTRUCTIONS]\n"
        f"{SYSTEM_RULES_BLOCK}"
    )

def _get_system_prefix(target: str, category: str) -> Optional[str]:
    """
    (target, category, guideline_hash)로 접두사 조회/생성.
    guideline 미존재 시 None.
    """
    guideline_text = _get_guideline_text(target, category)
    if not guideline_text:
        return None

    ghash = _hash_text(guideline_text)
    cache_key = f"{target}::{category}::{ghash}"
    if cache_key in _system_prefix_cache:
        return _system_prefix_cache[cache_key]

    prefix = _build_system_prefix(target, category, guideline_text)
    _system_prefix_cache[cache_key] = prefix
    return prefix

# =========================
# 메시지 빌더 (카테고리 감지 / 포맷 검수)
# =========================
def build_category_messages(
    sentence: str,
    model: str = "gpt-4o",
) -> Tuple[dict, dict, Dict[str, int]]:
    """
    카테고리 감지 메시지 (캐시 친화)
    - system: SYSTEM_CATEGORY_BLOCK (고정 → cached input)
    - user: 문장만 포함 (변동 → non-cached input)
    """
    system_msg = {"role": "system", "content": SYSTEM_CATEGORY_BLOCK}
    user_msg = {"role": "user", "content": f"Translated sentence: {sentence}\n\nWhich categories apply?"}
    meta = _split_and_count_cached_non_cached([system_msg, user_msg], model)
    return system_msg, user_msg, meta

def build_check_messages_cached(
    sentence: str,
    source_text: str,
    target: str,
    category: str,
    model: str = "gpt-4o",
) -> Optional[Tuple[dict, dict, Dict[str, int]]]:
    """
    포맷 검수 메시지 (캐시 친화)
    - system: [LOCALE] + [GUIDELINE] + [INSTRUCTIONS(=SYSTEM_RULES_BLOCK)]  → cached input
    - user  : Source/Translated/출력 cue                                   → non-cached input
    """
    system_prefix = _get_system_prefix(target, category)
    if not system_prefix:
        return None

    system_msg = {"role": "system", "content": system_prefix}
    user_msg = {
        "role": "user",
        "content": (
            "Source sentence:\n"
            f"{source_text.strip()}\n\n"
            "Translated sentence:\n"
            f"{sentence.strip()}\n\n"
            "Revised translation:"
        ),
    }
    meta = _split_and_count_cached_non_cached([system_msg, user_msg], model)
    return system_msg, user_msg, meta
