import os
import re

# 기준 디렉토리: locale별 하위 폴더들을 포함한 상위 경로
root_dir = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/policy_docs_new_after"

# 섹션 키워드와 파일명 접미사 매핑
sections = {
    "Numeric Format": "numeric",
    "Currency Format": "currency",
    "Date Format": "date",
    "Time Format": "time"
}
section_header_pattern = re.compile(r"^\[(.+?)\]")

# 루트 디렉토리 아래 모든 하위 폴더 순회
for dirpath, _, filenames in os.walk(root_dir):
    for filename in filenames:
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(dirpath, filename)
        base_name = os.path.splitext(filename)[0]

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        current_section = None
        section_contents = {v: [] for v in sections.values()}

        for line in lines:
            match = section_header_pattern.match(line.strip())
            if match:
                header = match.group(1)
                matched = False
                for section_title, suffix in sections.items():
                    if header.startswith(section_title):
                        current_section = suffix
                        section_contents[current_section].append(line)
                        matched = True
                        break
                if not matched:
                    current_section = None  # 다른 섹션은 무시
            elif current_section:
                section_contents[current_section].append(line)

        # 동일 폴더 내에 분리된 파일 저장
        for suffix, content in section_contents.items():
            if content:
                new_filename = f"{suffix}.txt"
                out_path = os.path.join(dirpath, new_filename)
                with open(out_path, "w", encoding="utf-8") as out_file:
                    out_file.writelines(content)
