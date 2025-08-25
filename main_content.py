# main.py
import os
import re
import json
from glob import glob
from collections import defaultdict
from time import time

from prompt_builder.build_prompt import (
    build_emoji_check_prompt,
    build_missing_check_prompt,
    build_addition_check_prompt,
)
from utils.gpt_client import ask_gpt

# ============ 설정 ============
# 원문 모델 응답(raw_response) 저장 여부 토글
SAVE_RAW_RESPONSES = False

# ============ 고정 입력/출력 경로 ============
INPUT_FOLDER = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2_json/NAC_2425_ko-en_HTL_405_250318_172641"

OUTPUT_BASE = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output_content/NAC_2425_ko-en_HTL_405_250318_172641"
SEMANTIC_DIR = os.path.join(OUTPUT_BASE, "semantic")
os.makedirs(SEMANTIC_DIR, exist_ok=True)

# ============ 비용 테이블 ============
PROMPT_PRICE_PER_1K = 0.005
COMPLETION_PRICE_PER_1K = 0.025

grand_usage = {
    "semantic": defaultdict(int),
}

# Discrete emoji ranges only (no giant bridging ranges!)
EMOJI_BASE = (
    "\U0001F1E6-\U0001F1FF"  # Regional indicator letters (flags)
    "\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F700-\U0001F77F"  # (optional) Alchemical Symbols
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
    "\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Extended-A
    "\u2600-\u26FF"          # Misc symbols
    "\u2700-\u27BF"          # Dingbats
    "\U0001F170-\U0001F251"  # Enclosed Alphanumeric Supplement (emoji subset)
)
SKIN_TONE = "\U0001F3FB-\U0001F3FF"
ZWJ = "\u200D"
VS16 = "\uFE0F"

EMOJI_PATTERN = (
    f"[{EMOJI_BASE}]"
    f"(?:[{VS16}]|[{SKIN_TONE}]|{ZWJ}[{EMOJI_BASE}])*"
)
EMOJI_REGEX = re.compile(EMOJI_PATTERN)

def has_emoji(text: str) -> bool:
    if not text:
        return False
    return bool(EMOJI_REGEX.search(text))

def usd_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens / 1000 * PROMPT_PRICE_PER_1K) + \
           (completion_tokens / 1000 * COMPLETION_PRICE_PER_1K)

def normalize_gpt_json(raw):
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    s = raw.strip()

    if s.startswith("```"):
        # ```json ... ``` 형태 제거
        s = s.strip("`")
        parts = s.split("\n", 1)
        if parts and parts[0].lower().startswith("json"):
            s = parts[1] if len(parts) > 1 else ""

    if "{" in s and "}" in s:
        s = s[s.find("{"):s.rfind("}")+1]

    try:
        return json.loads(s)
    except Exception:
        return {}

def _b(x, default=False):
    # 문자열 "true"/"false" 안전 캐스팅
    if isinstance(x, bool): return x
    if isinstance(x, str):
        v = x.strip().lower()
        if v in ("true", "yes", "y", "1"): return True
        if v in ("false", "no", "n", "0"): return False
    return default

def _list(x):
    return x if isinstance(x, list) else []

def _pick_next_translation(res: dict, fallback: str) -> str:
    """
    If 'suggestions' contains a non-empty string, use it; else keep fallback.
    """
    sugs = res.get("suggestions")
    if isinstance(sugs, list):
        for s in sugs:
            if isinstance(s, str):
                s2 = s.strip()
                if s2:
                    return s2
    return fallback

def is_issue_combined(emoji_res, miss_res, add_res) -> bool:
    return _b(emoji_res.get("emoji_issue")) or \
           _b(miss_res.get("missing_content")) or \
           _b(add_res.get("faithfulness_issue"))

def process_file(file_path: str):
    filename = os.path.basename(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    source = data.get("source")
    target = data.get("target")
    text = data.get("text", "")
    trans = data.get("trans", "")

    # ===== 줄 단위 분할 =====
    src_lines = text.splitlines()
    trn_lines = trans.splitlines()
    max_len = max(len(src_lines), len(trn_lines))

    # 파일별 토큰 집계
    sem_prompt_tokens = 0
    sem_completion_tokens = 0

    semantic_issues_accum = []
    total_calls_made = 0  # 라인별 호출 수 합계(이모지 없는 라인은 2회만)

    for i in range(max_len):
        src_line = src_lines[i].strip() if i < len(src_lines) else ""
        trn_line_original = trn_lines[i].strip() if i < len(trn_lines) else ""

        # 둘 다 빈 줄이면 스킵
        if not src_line and not trn_line_original:
            continue

        # 체이닝을 위한 현재 번역문(초기값은 원래 번역문)
        current_trn = trn_line_original

        # --- (조건부) 1) Emoji check: suggestions가 있으면 갱신 ---
        if has_emoji(src_line) or has_emoji(current_trn):
            sys1, usr1 = build_emoji_check_prompt(src_line, current_trn)
            res1_raw, usage1 = ask_gpt([sys1, usr1])
            sem_prompt_tokens += usage1.get("prompt_tokens", 0)
            sem_completion_tokens += usage1.get("completion_tokens", 0)
            total_calls_made += 1
            res_emoji = normalize_gpt_json(res1_raw)
            current_trn = _pick_next_translation(res_emoji, current_trn)
        else:
            # 이모지 없음: 호출 스킵, 기본값
            res_emoji = {"emoji_issue": False, "reasons": [], "suggestions": []}

        # --- 2) Missing content check: (이전 단계 결과가 반영된 current_trn 입력) ---
        sys2, usr2 = build_missing_check_prompt(src_line, current_trn)
        res2_raw, usage2 = ask_gpt([sys2, usr2])
        sem_prompt_tokens += usage2.get("prompt_tokens", 0)
        sem_completion_tokens += usage2.get("completion_tokens", 0)
        total_calls_made += 1
        res_missing = normalize_gpt_json(res2_raw)
        current_trn = _pick_next_translation(res_missing, current_trn)

        # --- 3) Added/altered content (faithfulness) check: current_trn 입력 ---
        sys3, usr3 = build_addition_check_prompt(src_line, current_trn)
        res3_raw, usage3 = ask_gpt([sys3, usr3])
        sem_prompt_tokens += usage3.get("prompt_tokens", 0)
        sem_completion_tokens += usage3.get("completion_tokens", 0)
        total_calls_made += 1
        res_addition = normalize_gpt_json(res3_raw)
        current_trn = _pick_next_translation(res_addition, current_trn)

        # --- 이슈 여부 플래그 ---
        emoji_issue = _b(res_emoji.get("emoji_issue"), False)
        missing_issue = _b(res_missing.get("missing_content"), False)
        faith_issue = _b(res_addition.get("faithfulness_issue"), False)

        # --- 이슈 라인만 기록 (요청: 최종 한 개의 suggestions만 유지 = addition 단계) ---
        if emoji_issue or missing_issue or faith_issue:
            issue_item = {
                "line_no": i + 1,
                "source_line": src_line,
                "trans_line": trn_line_original,
                "final_trans_line": current_trn,  # 모든 단계 반영 후 최종 확정본
                "result": {
                    "emoji_issue": emoji_issue,
                    "emoji_reasons": _list(res_emoji.get("reasons")),
                    "missing_content": missing_issue,
                    "missing_spans": _list(res_missing.get("missing_spans")),
                    "missing_reasons": _list(res_missing.get("reasons")),
                    "faithfulness_issue": faith_issue,
                    "faithfulness_type": res_addition.get("faithfulness_type", "none"),
                    "added_spans": _list(res_addition.get("added_spans")),
                    "faithfulness_reasons": _list(res_addition.get("reasons")),
                    # ★ 최종 하나의 suggestions만 유지 (addition 단계)
                    "suggestions": _list(res_addition.get("suggestions")),
                }
            }

            if SAVE_RAW_RESPONSES: 
                issue_item["raw"] = {
                    "emoji": res_emoji,
                    "missing": res_missing,
                    "addition": res_addition,
                }

            semantic_issues_accum.append(issue_item)

    # 파일 단위 Semantic 출력 페이로드
    semantic_payload = {
        "source": source,
        "target": target,
        "file": filename,
        "summary": {
            "total_lines": max_len,
            "issue_lines": len(semantic_issues_accum),
        },
        "issues": semantic_issues_accum,
        "usage": {
            "prompt_tokens": sem_prompt_tokens,
            "completion_tokens": sem_completion_tokens,
            "total_tokens": sem_prompt_tokens + sem_completion_tokens,
            "cost_usd": round(usd_cost(sem_prompt_tokens, sem_completion_tokens), 4),
            "calls_made": total_calls_made,     # 이모지 없으면 2회, 있으면 3회
            "calls_per_line": "2~3 (emoji conditional, chained by suggestions)",
        }
    }

    semantic_outpath = os.path.join(SEMANTIC_DIR, filename)
    with open(semantic_outpath, "w", encoding="utf-8") as f:
        json.dump(semantic_payload, f, ensure_ascii=False, indent=2)

    # 콘솔 로그
    print(f"✅ Processed: {filename}")
    print(f"   - semantic  → {os.path.relpath(semantic_outpath, OUTPUT_BASE)}  (issues: {len(semantic_issues_accum)})")

    # 총계 집계
    grand_usage["semantic"]["prompt_tokens"] += sem_prompt_tokens
    grand_usage["semantic"]["completion_tokens"] += sem_completion_tokens
    grand_usage["semantic"]["total_tokens"] += (sem_prompt_tokens + sem_completion_tokens)

    return {
        "filename": filename,
        "semantic": {
            "prompt_tokens": sem_prompt_tokens,
            "completion_tokens": sem_completion_tokens,
            "total_tokens": sem_prompt_tokens + sem_completion_tokens,
            "calls_made": total_calls_made,
        }
    }

if __name__ == "__main__":
    ss = time()

    # 파일명 숫자 기준 오름차순 정렬, 상위 10개만 선택
    json_files = glob(os.path.join(INPUT_FOLDER, "*.json"))
    json_files = sorted(
        json_files,
        key=lambda p: int(os.path.splitext(os.path.basename(p))[0])
    )[:10]

    folder_usage_log_sem = {}

    for fp in json_files:
        s = time()
        usage = process_file(fp)

        sem_u = usage["semantic"]
        folder_usage_log_sem[usage["filename"]] = sem_u

        e = time()
        sem_cost = usd_cost(sem_u["prompt_tokens"], sem_u["completion_tokens"])
        print(f"⌛ 처리 시간: {e - s:.2f}s")
        print(f"💵 {usage['filename']}  semantic ${sem_cost:.4f}\n")

    # 폴더(=고정 경로) 요약 로그 저장
    def write_usage_log(log_dict, out_dir):
        prompt_tokens = sum(v["prompt_tokens"] for v in log_dict.values())
        completion_tokens = sum(v["completion_tokens"] for v in log_dict.values())
        total_tokens = prompt_tokens + completion_tokens
        cost_total = usd_cost(prompt_tokens, completion_tokens)
        calls_made_total = sum(v.get("calls_made", 0) for v in log_dict.values())
        log_dict["_summary"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_total, 4),
            "calls_made": calls_made_total,
        }
        with open(os.path.join(out_dir, "token_usage_log.json"), "w", encoding="utf-8") as f:
            json.dump(log_dict, f, ensure_ascii=False, indent=2)

    write_usage_log(folder_usage_log_sem, SEMANTIC_DIR)

    # 전체 요약 콘솔
    sem_prompt = grand_usage["semantic"]["prompt_tokens"]
    sem_comp = grand_usage["semantic"]["completion_tokens"]
    sem_total = grand_usage["semantic"]["total_tokens"]
    sem_cost_grand = usd_cost(sem_prompt, sem_comp)

    print("\n📊 총 토큰 사용량 (SEMANTIC):")
    print(f"- Prompt:     {sem_prompt}")
    print(f"- Completion: {sem_comp}")
    print(f"- Total:      {sem_total}")
    print(f"💰 총 요금:   ${sem_cost_grand:.4f}")

    ee = time()
    print(f"\n모든 시스템 작동 시간: {ee - ss:.2f}s")
