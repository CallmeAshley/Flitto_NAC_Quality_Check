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

SAVE_RAW_RESPONSES = False
PRESERVE_EMPTY_LINES = True

ROOT_INPUT = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2_json"
ROOT_OUTPUT = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output_content"

TARGET_FOLDERS = [
    "NAC_2435_ar-en_HTL_412_250318_172556",
    "NAC_2585_en-uk_HTL_383_250318_172533",
]

PROMPT_PRICE_PER_1K = 0.005
COMPLETION_PRICE_PER_1K = 0.025

grand_usage = {"semantic": defaultdict(int)}

# 이모지 판별 정규식
EMOJI_BASE = (
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "\U0001F170-\U0001F251"
)
SKIN_TONE = "\U0001F3FB-\U0001F3FF"
ZWJ = "\u200D"
VS16 = "\uFE0F"

EMOJI_PATTERN = f"[{EMOJI_BASE}](?:[{VS16}]|[{SKIN_TONE}]|{ZWJ}[{EMOJI_BASE}])*"
EMOJI_REGEX = re.compile(EMOJI_PATTERN)

def has_emoji(text: str) -> bool:
    return bool(text and EMOJI_REGEX.search(text))

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
    if isinstance(x, bool): return x
    if isinstance(x, str):
        v = x.strip().lower()
        if v in ("true", "yes", "y", "1"): return True
        if v in ("false", "no", "n", "0"): return False
    return default

def _list(x):
    return x if isinstance(x, list) else []

def _pick_next_translation(res: dict, fallback: str) -> str:
    sugs = res.get("suggestions")
    if isinstance(sugs, list):
        for s in sugs:
            if isinstance(s, str) and s.strip():
                return s.strip()
    return fallback

def process_file(file_path: str, semantic_dir: str):
    filename = os.path.basename(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    source = data.get("source")
    target = data.get("target")
    text = data.get("text", "")
    trans = data.get("trans", "")

    src_lines = text.splitlines()
    trn_lines = trans.splitlines()
    max_len = max(len(src_lines), len(trn_lines))

    sem_prompt_tokens = 0
    sem_completion_tokens = 0
    semantic_issues_accum = []
    total_calls_made = 0

    final_lines = []
    changed_lines = []

    for i in range(max_len):
        src_line = src_lines[i].strip() if i < len(src_lines) else ""
        trn_line_original = trn_lines[i].strip() if i < len(trn_lines) else ""

        if not src_line and not trn_line_original:
            if PRESERVE_EMPTY_LINES:
                final_lines.append("")
            continue

        current_trn = trn_line_original

        # Emoji check
        if has_emoji(src_line) or has_emoji(current_trn):
            sys1, usr1 = build_emoji_check_prompt(src_line, current_trn)
            res1_raw, usage1 = ask_gpt([sys1, usr1])
            sem_prompt_tokens += usage1.get("prompt_tokens", 0)
            sem_completion_tokens += usage1.get("completion_tokens", 0)
            total_calls_made += 1
            res_emoji = normalize_gpt_json(res1_raw)
            current_trn = _pick_next_translation(res_emoji, current_trn)
        else:
            res_emoji = {"emoji_issue": False, "reasons": [], "suggestions": []}

        # Missing content check
        sys2, usr2 = build_missing_check_prompt(src_line, current_trn)
        res2_raw, usage2 = ask_gpt([sys2, usr2])
        sem_prompt_tokens += usage2.get("prompt_tokens", 0)
        sem_completion_tokens += usage2.get("completion_tokens", 0)
        total_calls_made += 1
        res_missing = normalize_gpt_json(res2_raw)
        current_trn = _pick_next_translation(res_missing, current_trn)

        # Faithfulness check
        sys3, usr3 = build_addition_check_prompt(src_line, current_trn)
        res3_raw, usage3 = ask_gpt([sys3, usr3])
        sem_prompt_tokens += usage3.get("prompt_tokens", 0)
        sem_completion_tokens += usage3.get("completion_tokens", 0)
        total_calls_made += 1
        res_addition = normalize_gpt_json(res3_raw)
        current_trn = _pick_next_translation(res_addition, current_trn)

        emoji_issue = _b(res_emoji.get("emoji_issue"), False)
        missing_issue = _b(res_missing.get("missing_content"), False)
        faith_issue = _b(res_addition.get("faithfulness_issue"), False)

        final_lines.append(current_trn)
        if current_trn != trn_line_original:
            changed_lines.append(i + 1)

        if emoji_issue or missing_issue or faith_issue:
            issue_item = {
                "line_no": i + 1,
                "source_line": src_line,
                "trans_line": trn_line_original,
                "final_trans_line": current_trn,
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

    final_translation = "\n".join(final_lines)

    semantic_payload = {
        "source": source,
        "target": target,
        "file": filename,
        "summary": {
            "total_lines": max_len,
            "issue_lines": len(semantic_issues_accum),
        },
        "issues": semantic_issues_accum,
        "revised": final_translation,
        "final_summary": {
            "changed_line_count": len(changed_lines),
            "changed_lines": changed_lines,
        },
        "usage": {
            "prompt_tokens": sem_prompt_tokens,
            "completion_tokens": sem_completion_tokens,
            "total_tokens": sem_prompt_tokens + sem_completion_tokens,
            "cost_usd": round(usd_cost(sem_prompt_tokens, sem_completion_tokens), 4),
            "calls_made": total_calls_made,
            "calls_per_line": "2~3 (emoji conditional, chained by suggestions)",
        }
    }

    os.makedirs(semantic_dir, exist_ok=True)
    semantic_outpath = os.path.join(semantic_dir, filename)
    with open(semantic_outpath, "w", encoding="utf-8") as f:
        json.dump(semantic_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ Processed: {filename}")
    rel_path = os.path.relpath(semantic_outpath, os.path.dirname(semantic_dir))
    print(f"   - semantic  → {rel_path}  (issues: {len(semantic_issues_accum)})")

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
            "changed_line_count": len(changed_lines),
        }
    }

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
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "token_usage_log.json"), "w", encoding="utf-8") as f:
        json.dump(log_dict, f, ensure_ascii=False, indent=2)

def safe_pick_10_numeric_jsons(input_folder: str):
    candidates = []
    for p in glob(os.path.join(input_folder, "*.json")):
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            idx = int(name)
            candidates.append((idx, p))
        except ValueError:
            print(f"⚠️  Skipped (non-numeric filename): {p}")
    candidates.sort(key=lambda t: t[0])
    return [p for _, p in candidates[:10]]

if __name__ == "__main__":
    ss = time()
    for folder_name in TARGET_FOLDERS:
        input_folder = os.path.join(ROOT_INPUT, folder_name)
        output_base = os.path.join(ROOT_OUTPUT, folder_name)
        semantic_dir = os.path.join(output_base, "semantic")
        os.makedirs(semantic_dir, exist_ok=True)

        if not os.path.isdir(input_folder):
            print(f"❌ 입력 폴더 없음: {input_folder}")
            continue

        json_files = safe_pick_10_numeric_jsons(input_folder)
        if not json_files:
            print(f"❌ 처리할 JSON이 없습니다: {input_folder}")
            continue

        print(f"\n📂 Folder: {folder_name}")
        print(f"   Input : {input_folder}")
        print(f"   Output: {semantic_dir}")
        folder_usage_log_sem = {}

        for fp in json_files:
            s = time()
            usage = process_file(fp, semantic_dir)
            sem_u = usage["semantic"]
            folder_usage_log_sem[usage["filename"]] = sem_u
            e = time()
            sem_cost = usd_cost(sem_u["prompt_tokens"], sem_u["completion_tokens"])
            print(f"⌛ 처리 시간: {e - s:.2f}s")
            print(f"💵 {usage['filename']}  semantic ${sem_cost:.4f}\n")

        write_usage_log(folder_usage_log_sem, semantic_dir)

    sem_prompt = grand_usage["semantic"]["prompt_tokens"]
    sem_comp = grand_usage["semantic"]["completion_tokens"]
    sem_total = grand_usage["semantic"]["total_tokens"]
    sem_cost_grand = usd_cost(sem_prompt, sem_comp)

    print("\n📊 총 토큰 사용량 (SEMANTIC, ALL FOLDERS):")
    print(f"- Prompt:     {sem_prompt}")
    print(f"- Completion: {sem_comp}")
    print(f"- Total:      {sem_total}")
    print(f"💰 총 요금:   ${sem_cost_grand:.4f}")

    ee = time()
    print(f"\n모든 시스템 작동 시간: {ee - ss:.2f}s")
