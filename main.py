import os
import json
from prompt_builder.build_prompt import build_prompt_from_json
from rag_module.rag_searcher import query_policy
from utils.gpt_client import call_gpt
from time import time

INPUT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input/"
OUTPUT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output/"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for fname in os.listdir(INPUT_DIR):
        if not fname.endswith(".json"):
            continue

        input_path = os.path.join(INPUT_DIR, fname)
        output_path = os.path.join(OUTPUT_DIR, fname)

        with open(input_path, "r", encoding="utf-8") as f:
            sample = json.load(f)

        # RAG로 해당 target 언어의 정책 검색
        context = query_policy(language=sample["target"], 
                               query = f"Formatting rules for {sample['target']}")  # Query는 placeholder

        # Prompt 구성
        messages = build_prompt_from_json(sample, context)

        # GPT API 호출
        response = call_gpt(messages, temperature=0)
    

        # 결과 저장 (텍스트 파일)
        with open(output_path[:-4]+'txt', "w", encoding="utf-8") as f:
            f.write(f"[원문: {sample['source']}]\n")
            f.write(f"{sample['text']}\n\n")
            f.write(f"[번역문: {sample['target']}]\n")
            f.write(f"{sample['trans']}\n\n")
            f.write("[GPT 분석 결과]\n")
            f.write(response.strip() + "\n")

        print(f"저장 완료: {output_path[:-4]+'txt'}")

if __name__ == "__main__":
    
    start = time()
    main()
    end = time()
    print(f'총 소요시간: {end-start}')
