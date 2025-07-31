import os
import json
from glob import glob
from collections import defaultdict
from time import time
from prompt_builder.build_prompt import build_category_prompt, build_check_prompt
from utils.gpt_client import ask_gpt
from utils.file_utils import load_guideline

INPUT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2_json"
OUTPUT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output2"
TOKEN_LOG_PATH = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output2/token_usage_log.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

total_usage = defaultdict(int)
file_usage_log = {}

def process_file(filepath: str, parent_folder: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    source = data["source"]
    target = data["target"]
    text = data["text"]
    trans = data["trans"]

    sentences = trans.splitlines()
    checked_sentences = []
    checked_detail = []

    file_prompt_tokens = 0
    file_completion_tokens = 0

    for sentence in sentences:
        if not sentence.strip():
            checked_sentences.append(sentence)
            checked_detail.append({
                "original": sentence,
                "revised": sentence,
                "violated": False,
                "categories": []
            })
            continue

        sys_msg, usr_msg = build_category_prompt(sentence)
        categories, usage = ask_gpt([sys_msg, usr_msg])
        file_prompt_tokens += usage["prompt_tokens"]
        file_completion_tokens += usage["completion_tokens"]

        if not categories or categories == "error" or categories == []:
            checked_sentences.append(sentence)
            checked_detail.append({
                "original": sentence,
                "revised": sentence,
                "violated": False,
                "categories": []
            })
            continue

        revised = sentence
        revised_once = False

        for category in categories:
            guideline = load_guideline(target, category)
            if not guideline:
                continue

            sys_msg, usr_msg = build_check_prompt(revised, guideline, source)
            revised_result, usage = ask_gpt([sys_msg, usr_msg])
            file_prompt_tokens += usage["prompt_tokens"]
            file_completion_tokens += usage["completion_tokens"]

            if isinstance(revised_result, str) and revised_result != "error":
                if revised_result.strip() != revised.strip():
                    revised = revised_result.strip()
                    revised_once = True

        checked_sentences.append(revised)
        checked_detail.append({
            "original": sentence,
            "revised": revised,
            "violated": revised_once,
            "categories": categories
        })

    file_total_tokens = file_prompt_tokens + file_completion_tokens
    filename = os.path.basename(filepath)
    file_usage_log[filename] = {
        "prompt_tokens": file_prompt_tokens,
        "completion_tokens": file_completion_tokens,
        "total_tokens": file_total_tokens
    }

    total_usage["prompt_tokens"] += file_prompt_tokens
    total_usage["completion_tokens"] += file_completion_tokens
    total_usage["total_tokens"] += file_total_tokens

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

if __name__ == "__main__":
    # 토큰당 요금
    prompt_price = 0.005  # per 1k
    completion_price = 0.015
    
    ss = time()
    folders = glob(os.path.join(INPUT_DIR, "*"))
    for folder_path in folders:
        if not os.path.isdir(folder_path):
            continue

        folder_name = os.path.basename(folder_path)
        json_files = glob(os.path.join(folder_path, "*.json"))
        json_files.sort()

        for file_path in json_files:
            s_time = time()
            process_file(file_path, folder_name)

            # 파일 단위 사용량
            filename = os.path.basename(file_path)
            file_tokens = file_usage_log.get(filename, {})
            file_prompt_tokens = file_tokens.get("prompt_tokens", 0)
            file_completion_tokens = file_tokens.get("completion_tokens", 0)
            
            # 파일 요금 계산
            file_cost = (file_prompt_tokens / 1000 * prompt_price) + (file_completion_tokens / 1000 * completion_price)
            
            e_time = time()
            print(f"⌛ 하나의 Payload 처리 시간: {e_time-s_time:.2f}s")
            print(f"💵 {filename} 요금: ${file_cost:.4f}\n")
            

    prompt_cost = total_usage["prompt_tokens"] / 1000 * prompt_price
    completion_cost = total_usage["completion_tokens"] / 1000 * completion_price
    total_cost = prompt_cost + completion_cost

    print(f"\n📊총 토큰 사용량: {total_usage['total_tokens']}")
    print(f"- Prompt tokens:     {total_usage['prompt_tokens']}")
    print(f"- Completion tokens: {total_usage['completion_tokens']}")
    print(f"💰 총 요금: ${total_cost:.4f}")

    with open(TOKEN_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(file_usage_log, f, indent=2)

    ee = time()
    print(f"모든 시스템 작동 시간: {ee-ss}s")
    
    