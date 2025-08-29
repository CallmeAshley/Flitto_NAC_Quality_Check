# prompt_cache.py
import hashlib
from typing import Optional, Tuple
from utils.file_utils import load_guideline

# ===== 내부 캐시 =====
_guideline_text_cache = {}   # (target, category) -> str (원문 그대로, 가공 금지)
_system_prefix_cache = {}    # cache_key -> str (고정 system 접두사)

def _hash_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ⚠️ 캐시 안정성을 위해 문자열/개행/스페이싱 절대 임의 변경 금지
_SYSTEM_RULES_BLOCK = (
    "You are a localization format validator AI.\n"
    "Your task is to check whether the translated sentence conforms to the following locale-specific guideline.\n"
    "If the sentence violates the guideline, suggest a corrected version.\n"
    "If no changes are needed, return the original sentence.\n"
    "You will also receive the source sentence to help you understand the context and intended meaning of the translated sentence.\n"
    "Do not remove or modify any numbering, bullets, or structural markers in the sentence such as: a), 1., (1), •, '- ', ➔, →, *, <, > , [, ], .., :, ; #, !, -, >, ] , etc. These elements must be preserved exactly as they appear in the source sentence.\n"
    "These elements must be preserved exactly as they appear. \n"
    "Do not change the meaning or add explanations. Return only the revised sentence.\n"
    "Do not omit, rephrase, or summarize any semantically meaningful component of the original translation, including but not limited to modifiers, qualifiers, references, or ownership indicators.\n"
    "All content must be preserved as-is unless it clearly violates locale formatting or results in unnaturalness in the target language.\n"
    "**Context-Aware Formatting Principle**\n"
    "**LLM must always consider the grammatical and semantic context of the sentence before applying guidelines.**\n"
    "Even when a formatting rule in the guideline is clearly defined, it must not override the natural word order or fluency of the target language.\n"
    "If the formatting rule in the guideline creates an unnatural expression in the target language, adjust the position or structure accordingly while preserving the original meaning and locale format type.\n"
    "Important: The revised sentence must be exactly the same as the original translated sentence, except for the parts where locale formatting has been corrected\n"
    "If the translated sentence contains any emojis like ✅, ❌, ❗, ❓, ✔️, never delete or move them from their original position.\n"
    "Preserve commonly accepted market abbreviations such as K, M, B (e.g., $600K, 1M €) if they are contextually appropriate and clear.\n"
    "Do not modify the ending punctuation of the sentence.\n"
    "If the source sentence ends with a colon (:), comma (,), ellipsis (..), regular space, or any other non-period character, preserve it as-is.\n"
)

def _get_guideline_text(target: str, category: str) -> Optional[str]:
    key = (target, category)
    if key in _guideline_text_cache:
        return _guideline_text_cache[key]
    text = load_guideline(target, category)
    if not text:
        return None
    _guideline_text_cache[key] = text  # 가공 금지
    return text

def _build_system_prefix(target: str, category: str, guideline_text: str) -> str:
    # 개행/스페이싱 고정
    return (
        f"[LOCALE]\n{target} / {category}\n\n"
        "[GUIDELINE]\n"
        f"{guideline_text}\n\n"
        "[INSTRUCTIONS]\n"
        f"{_SYSTEM_RULES_BLOCK}"
    )

def _get_system_prefix(target: str, category: str) -> Optional[str]:
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

def build_check_messages_cached(
    sentence: str,
    source_text: str,
    target: str,
    category: str
) -> Optional[Tuple[dict, dict]]:
    """
    - system: 언어×카테고리×가이드라인 포함(캐시 대상)
    - user: 매번 달라지는 Source/Translated만
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
    return system_msg, user_msg
