import os
import json
import re
from glob import glob
from collections import defaultdict

# 검사할 루트 디렉토리 (여러 폴더 포함)
ROOT_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output2"

# 숫자 정렬 기준 함수
def extract_number(filename):
    match = re.search(r"\d+", filename)
    return int(match.group()) if match else float("inf")

# 폴더 내 JSON 파일 분석 함수
def analyze_folder(folder_path):
    folder_name = os.path.basename(os.path.normpath(folder_path))
    json_files = glob(os.path.join(folder_path, "*.json"))

    files_with_true = []
    files_with_semantic_issues = []
    category_counter = defaultdict(int)

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                # ✅ 형식 검수 위반 분석
                violated_sentences = []
                for sentence in data.get("checked_sentences", []):
                    if sentence.get("violated") is True:
                        violated_sentences.append({
                            "original": sentence.get("original", ""),
                            "revised": sentence.get("revised", ""),
                            "categories": sentence.get("categories", [])
                        })
                        for cat in sentence.get("categories", []):
                            category_counter[cat] += 1

                if violated_sentences:
                    files_with_true.append({
                        "filename": os.path.basename(file_path),
                        "violated_count": len(violated_sentences),
                        "violated_sentences": violated_sentences
                    })

                # ✅ semantic_issues 분석
                semantic = data.get("semantic_issues", {})
                if (
                    semantic.get("emoji_issue") is True
                    or semantic.get("missing_content") is True
                    or semantic.get("faithfulness_issue") is True
                    or semantic.get("faithfulness_type") in ("mild", "severe")
                    or semantic.get("parenthesis_issue") is True
                ):
                    files_with_semantic_issues.append({
                        "filename": os.path.basename(file_path),
                        "semantic_issues": semantic
                    })

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    files_with_true.sort(key=lambda x: extract_number(x["filename"]))
    files_with_semantic_issues.sort(key=lambda x: extract_number(x["filename"]))

    result = {
        "folder_name": folder_name,
        "total_files": len(json_files),
        "files_with_true_count": len(files_with_true),
        "files_with_true": files_with_true,
        "category_statistics": dict(sorted(category_counter.items())),
        "files_with_semantic_issues_count": len(files_with_semantic_issues),
        "files_with_semantic_issues": files_with_semantic_issues
    }

    return result

# 전체 폴더 순회
folder_paths = [os.path.join(ROOT_DIR, d) for d in os.listdir(ROOT_DIR)
                if os.path.isdir(os.path.join(ROOT_DIR, d))]

total_results = []

for folder_path in folder_paths:
    result = analyze_folder(folder_path)
    total_results.append(result)

    # 폴더별 개별 결과 저장
    output_path = os.path.join(ROOT_DIR, f"{result['folder_name']}_result_summary.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

# 전체 요약본 저장
total_output_path = os.path.join(ROOT_DIR, "total_summary.json")
with open(total_output_path, "w", encoding="utf-8") as f:
    json.dump(total_results, f, indent=2, ensure_ascii=False)

# 출력
print(json.dumps(total_results, indent=2, ensure_ascii=False))
