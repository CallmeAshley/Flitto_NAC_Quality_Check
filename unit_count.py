import os
import json
import re
from glob import glob

# 상위 경로
BASE_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output2"

# 두 개의 중국어 전용 폴더
HANZI_FOLDERS = {
    "NAC_2411_zh-CN-en_HTL_367_250318_172742",
    "LP.sys.test.longcontext.112024.zh_TW-en_US.83741c.v3.HT_nac"
}

# 결과 저장 파일 이름
SUMMARY_FILENAME = "word_count_summary.json"

# 모든 하위 폴더 (파일 제외)
all_subfolders = [
    f for f in os.listdir(BASE_DIR)
    if os.path.isdir(os.path.join(BASE_DIR, f))
]

print(f"✅ 전체 대상 폴더 수: {len(all_subfolders)}개\n")

# 총합 카운터
total_space_split_count = 0
total_hanzi_count = 0

# 각 폴더 처리
for folder in all_subfolders:
    folder_path = os.path.join(BASE_DIR, folder)
    json_files = glob(os.path.join(folder_path, "*.json"))

    word_counts = {}
    folder_total_count = 0

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ JSON 로딩 실패: {json_file} - {e}")
            continue

        if "text" not in data:
            continue

        text = data["text"]
        filename = os.path.basename(json_file)

        # 🌐 중국어 폴더: 한자 수 계산
        if folder in HANZI_FOLDERS:
            cleaned_text = re.sub(r"\[redacted_name\]", "", text)
            hanzi = re.findall(r"[\u3400-\u4DBF\u4E00-\u9FFF]", cleaned_text)
            count = len(hanzi)
            total_hanzi_count += count
        # 🌍 기타 폴더: 공백 기준 단어 수 계산
        else:
            count = len(text.split())
            total_space_split_count += count

        word_counts[filename] = count
        folder_total_count += count

    word_counts["TOTAL_COUNT"] = folder_total_count

    # 결과 저장
    output_path = os.path.join(folder_path, SUMMARY_FILENAME)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(word_counts, f, indent=2, ensure_ascii=False)

    print(f"📁 {folder}: 총 {folder_total_count}개 → {SUMMARY_FILENAME} 저장 완료")

# ✅ 최종 요약 출력
print("\n📊 전체 단어 수 요약:")
print(f"- 공백 기준 단어 수 (25개 일반 폴더): {total_space_split_count:,}개")
print(f"- 한자 기준 단어 수 (2개 중국어 폴더): {total_hanzi_count:,}자")
print(f"🧮 총합: {total_space_split_count + total_hanzi_count:,}개")
