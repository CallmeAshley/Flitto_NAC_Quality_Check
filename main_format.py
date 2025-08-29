import os
import json
import random
from glob import glob
from collections import defaultdict
from time import time

from utils.gpt_client import ask_gpt
from prompt_builder.prompt_cache import (
    build_category_messages,        # 카테고리 감지(접두사 캐시)
    build_check_messages_cached,    # 검수(접두사 캐시)
)

# =========================
# 경로/모델/단가 설정
# =========================
INPUT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2_json"
OUTPUT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 사용 모델 (비용 계산/토큰 계측에서 활용)
MODEL_NAME = "gpt-4o"  # 또는 "gpt-5"

# 1토큰 단가 (per-token)
RATES = {
    "gpt-4o": {"input": 0.00000250, "cached": 0.00000125,  "output": 0.00001000},
    "gpt-5":  {"input": 0.00000125, "cached": 0.000000125, "output": 0.00001000},
}

total_usage = defaultdict(int)  # 전체 합산

def process_file(filepath: str, parent_folder: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    source = data["source"]
    target = data["target"]     # 타깃 로케일 (예: "ko-KR")
    text = data["text"]
    trans = data["trans"]

    source_sentences = text.splitlines()
    trans_sentences = trans.splitlines()
    checked_sentences = []
    checked_detail = []

    # 파일 단위 토큰 누적(캐시/비캐시/출력 분리)
    file_cached_prompt_tokens = 0
    file_non_cached_prompt_tokens = 0
    file_output_tokens = 0

    # Step: Format Check (줄 단위)
    for i, sentence in enumerate(trans_sentences):
        original_sentence = sentence.strip()

        # 대응하는 source 문장 추출 (fallback 포함)
        if len(source_sentences) == len(trans_sentences):
            source_for_line = source_sentences[i].strip()
        else:
            source_for_line = text  # fallback: 전체 사용

        # 빈 줄은 그대로 보존
        if not original_sentence:
            checked_sentences.append(sentence)
            checked_detail.append({
                "original": sentence,
                "revised": sentence,
                "violated": False,
                "categories": []
            })
            continue

        # 1) 카테고리 감지 (system 고정 → cached input)
        sys_msg, usr_msg, meta = build_category_messages(original_sentence, model=MODEL_NAME)
        categories, usage = ask_gpt([sys_msg, usr_msg], model=MODEL_NAME)

        file_cached_prompt_tokens     += meta["cached_input_tokens"]
        file_non_cached_prompt_tokens += meta["non_cached_input_tokens"]
        file_output_tokens            += usage.get("completion_tokens", 0)

        revised = original_sentence

        if not categories or categories == "error" or categories == []:
            checked_sentences.append(revised)
            checked_detail.append({
                "source_text": source_for_line,
                "original": sentence,
                "revised": revised,
                "violated": False,
                "categories": []
            })
            continue

        # 2) 카테고리별 포맷 검수 (guideline을 system 접두사로 → 76개 캐시 활용)
        for category in categories:
            built = build_check_messages_cached(
                revised, source_for_line, target, category, model=MODEL_NAME
            )
            if not built:
                continue  # 해당 카테고리 guideline 없으면 스킵
            sys_msg2, usr_msg2, meta2 = built

            revised_result, usage = ask_gpt([sys_msg2, usr_msg2], model=MODEL_NAME)

            file_cached_prompt_tokens     += meta2["cached_input_tokens"]
            file_non_cached_prompt_tokens += meta2["non_cached_input_tokens"]
            file_output_tokens            += usage.get("completion_tokens", 0)

            if isinstance(revised_result, str) and revised_result != "error":
                revised = revised_result.strip()

        violated_flag = (original_sentence != revised)

        checked_sentences.append(revised)
        checked_detail.append({
            "source_text": source_for_line,
            "original": sentence,
            "revised": revised,
            "violated": violated_flag,
            "categories": categories
        })

    filename = os.path.basename(filepath)

    output_data = {
        "source": source,
        "target": target,
        "text": text,
        "original_trans": trans,
        "checked_trans": "\n".join(checked_sentences),
        "checked_sentences": checked_detail
    }

    os.makedirs(os.path.join(OUTPUT_DIR, parent_folder), exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, parent_folder, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Processed: {parent_folder}/{filename}")

    # 파일 비용 계산 (per 1k tokens 환산)
    rate = RATES[MODEL_NAME]
    file_input_cost = (file_non_cached_prompt_tokens / 1000.0) * rate["input"] \
                    + (file_cached_prompt_tokens     / 1000.0) * rate["cached"]
    file_output_cost = (file_output_tokens / 1000.0) * rate["output"]
    file_total_cost  = file_input_cost + file_output_cost

    return {
        "filename": filename,
        "cached_prompt_tokens": file_cached_prompt_tokens,
        "non_cached_prompt_tokens": file_non_cached_prompt_tokens,
        "completion_tokens": file_output_tokens,
        "input_cost_usd": round(file_input_cost, 6),
        "output_cost_usd": round(file_output_cost, 6),
        "total_cost_usd": round(file_total_cost, 6),
        # 레거시 호환/총합
        "total_tokens": file_cached_prompt_tokens + file_non_cached_prompt_tokens + file_output_tokens,
    }

if __name__ == "__main__":
    random.seed(111)
    ss = time()
    folders = glob(os.path.join(INPUT_DIR, "*"))

    folder_logs = {}  # 폴더별 로그 파일 저장용

    for folder_path in folders:
        if not os.path.isdir(folder_path):
            continue

        folder_name = os.path.basename(folder_path)
        json_files = glob(os.path.join(folder_path, "*.json"))
        json_files = random.sample(json_files, min(50, len(json_files)))

        folder_usage_log = {}

        # 폴더 단위 누적
        folder_cached_prompt_tokens = 0
        folder_non_cached_prompt_tokens = 0
        folder_completion_tokens = 0

        for file_path in json_files:
            s_time = time()
            usage = process_file(file_path, folder_name)

            folder_usage_log[usage["filename"]] = usage

            # 폴더 누적
            folder_cached_prompt_tokens     += usage["cached_prompt_tokens"]
            folder_non_cached_prompt_tokens += usage["non_cached_prompt_tokens"]
            folder_completion_tokens        += usage["completion_tokens"]

            # 전체 누적
            total_usage["cached_prompt_tokens"]     += usage["cached_prompt_tokens"]
            total_usage["non_cached_prompt_tokens"] += usage["non_cached_prompt_tokens"]
            total_usage["completion_tokens"]        += usage["completion_tokens"]
            total_usage["total_tokens"]             += usage["total_tokens"]

            e_time = time()
            print(f"⌛ 하나의 Payload 처리 시간: {e_time - s_time:.2f}s")
            print(f"💵 {usage['filename']} 비용(USD): {usage['total_cost_usd']:.6f}\n")

        # 폴더 비용 계산
        rate = RATES[MODEL_NAME]
        folder_input_cost = (folder_non_cached_prompt_tokens / 1000.0) * rate["input"] \
                          + (folder_cached_prompt_tokens     / 1000.0) * rate["cached"]
        folder_output_cost = (folder_completion_tokens / 1000.0) * rate["output"]
        folder_total_cost  = folder_input_cost + folder_output_cost

        folder_usage_log["_summary"] = {
            "cached_prompt_tokens": folder_cached_prompt_tokens,
            "non_cached_prompt_tokens": folder_non_cached_prompt_tokens,
            "completion_tokens": folder_completion_tokens,
            "input_cost_usd": round(folder_input_cost, 6),
            "output_cost_usd": round(folder_output_cost, 6),
            "total_cost_usd": round(folder_total_cost, 6),
            "total_tokens": folder_cached_prompt_tokens + folder_non_cached_prompt_tokens + folder_completion_tokens,
        }

        folder_output_path = os.path.join(OUTPUT_DIR, folder_name, "token_usage_log.json")
        os.makedirs(os.path.join(OUTPUT_DIR, folder_name), exist_ok=True)
        with open(folder_output_path, "w", encoding="utf-8") as f:
            json.dump(folder_usage_log, f, indent=2, ensure_ascii=False)

    # 전체 비용 계산
    rate = RATES[MODEL_NAME]
    prompt_cost  = (total_usage["non_cached_prompt_tokens"] / 1000.0) * rate["input"] \
                 + (total_usage["cached_prompt_tokens"]     / 1000.0) * rate["cached"]
    completion_cost = (total_usage["completion_tokens"] / 1000.0) * rate["output"]
    total_cost = prompt_cost + completion_cost

    print(f"\n📊총 토큰 사용량: {total_usage['total_tokens']}")
    print(f"- Cached input tokens:     {total_usage['cached_prompt_tokens']}")
    print(f"- Non-cached input tokens: {total_usage['non_cached_prompt_tokens']}")
    print(f"- Output tokens:           {total_usage['completion_tokens']}")
    print(f"💰 총 요금(USD): {total_cost:.6f}")

    ee = time()
    print(f"모든 시스템 작동 시간: {ee - ss:.2f}s")
