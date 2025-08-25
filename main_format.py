import os
import json
import random
from glob import glob
from collections import defaultdict
from time import time

from prompt_builder.build_prompt import build_category_prompt, build_check_prompt
from utils.gpt_client import ask_gpt
from utils.file_utils import load_guideline

INPUT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2_json"
OUTPUT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output2"

os.makedirs(OUTPUT_DIR, exist_ok=True)

total_usage = defaultdict(int)

def process_file(filepath: str, parent_folder: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    source = data["source"]
    target = data["target"]
    text = data["text"]
    trans = data["trans"]

    source_sentences = text.splitlines()
    trans_sentences = trans.splitlines()
    checked_sentences = []
    checked_detail = []

    file_prompt_tokens = 0
    file_completion_tokens = 0

    # 🧠 Step: Format Check (줄 단위)
    for i, sentence in enumerate(trans_sentences):
        original_sentence = sentence.strip()

        # ✅ 대응하는 source 문장 추출
        if len(source_sentences) == len(trans_sentences):
            source_for_line = source_sentences[i].strip()
        else:
            source_for_line = text  # fallback: 전체 사용

        if not original_sentence:
            checked_sentences.append(sentence)
            checked_detail.append({
                "original": sentence,
                "revised": sentence,
                "violated": False,
                "categories": []
            })
            continue

        # Category 분류
        sys_msg, usr_msg = build_category_prompt(original_sentence)
        categories, usage = ask_gpt([sys_msg, usr_msg])
        file_prompt_tokens += usage["prompt_tokens"]
        file_completion_tokens += usage["completion_tokens"]

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

        # Format 검수
        for category in categories:
            guideline = load_guideline(target, category)
            if not guideline:
                continue

            sys_msg, usr_msg = build_check_prompt(revised, guideline, source_for_line)
            revised_result, usage = ask_gpt([sys_msg, usr_msg])
            file_prompt_tokens += usage["prompt_tokens"]
            file_completion_tokens += usage["completion_tokens"]

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

    return {
        "filename": filename,
        "prompt_tokens": file_prompt_tokens,
        "completion_tokens": file_completion_tokens,
        "total_tokens": file_prompt_tokens + file_completion_tokens
    }

if __name__ == "__main__":
    prompt_price = 0.005  # per 1k tokens
    completion_price = 0.025

    random.seed(111)
    ss = time()
    folders = glob(os.path.join(INPUT_DIR, "*"))
    for folder_path in folders:
        if not os.path.isdir(folder_path):
            continue

        folder_name = os.path.basename(folder_path)
        json_files = glob(os.path.join(folder_path, "*.json"))
        json_files = random.sample(json_files, min(50, len(json_files)))

        folder_usage_log = {}

        for file_path in json_files:
            s_time = time()
            usage = process_file(file_path, folder_name)

            file_cost = (usage["prompt_tokens"] / 1000 * prompt_price) + \
                        (usage["completion_tokens"] / 1000 * completion_price)

            folder_usage_log[usage["filename"]] = usage

            total_usage["prompt_tokens"] += usage["prompt_tokens"]
            total_usage["completion_tokens"] += usage["completion_tokens"]
            total_usage["total_tokens"] += usage["total_tokens"]

            e_time = time()
            print(f"⌛ 하나의 Payload 처리 시간: {e_time - s_time:.2f}s")
            print(f"💵 {usage['filename']} 요금: ${file_cost:.4f}\n")

        folder_prompt_tokens = sum(v["prompt_tokens"] for v in folder_usage_log.values())
        folder_completion_tokens = sum(v["completion_tokens"] for v in folder_usage_log.values())
        folder_total_tokens = folder_prompt_tokens + folder_completion_tokens
        folder_cost = (folder_prompt_tokens / 1000 * prompt_price) + (folder_completion_tokens / 1000 * completion_price)

        folder_usage_log["_summary"] = {
            "prompt_tokens": folder_prompt_tokens,
            "completion_tokens": folder_completion_tokens,
            "total_tokens": folder_total_tokens,
            "cost_usd": round(folder_cost, 4)
        }

        folder_output_path = os.path.join(OUTPUT_DIR, folder_name, "token_usage_log.json")
        with open(folder_output_path, "w", encoding="utf-8") as f:
            json.dump(folder_usage_log, f, indent=2, ensure_ascii=False)

    prompt_cost = total_usage["prompt_tokens"] / 1000 * prompt_price
    completion_cost = total_usage["completion_tokens"] / 1000 * completion_price
    total_cost = prompt_cost + completion_cost

    print(f"\n📊총 토큰 사용량: {total_usage['total_tokens']}")
    print(f"- Prompt tokens:     {total_usage['prompt_tokens']}")
    print(f"- Completion tokens: {total_usage['completion_tokens']}")
    print(f"💰 총 요금: ${total_cost:.4f}")

    ee = time()
    print(f"모든 시스템 작동 시간: {ee - ss:.2f}s")
