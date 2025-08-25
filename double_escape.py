#!/usr/bin/env python3
import os
import json
from glob import glob
from typing import Dict, Any, List

BASE_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2_json"
# 점검 대상 키 (필요하면 추가)
TARGET_KEYS = ["text", "trans"]

# “더블 이스케이프” 의심 패턴들
# 주의: 단순 존재만으로 결론내리지 않고, 아래 로직에서
# “실제 제어문자 부재 + 백슬래시 시퀀스 존재”일 때만 의심으로 판단합니다.
ESCAPE_SEQUENCES = ["\\r\\n", "\\n", "\\r", "\\t", "\\\""]

def iter_json_files(base_dir: str) -> List[str]:
    """하위 모든 폴더의 .json 파일 경로 리스트."""
    pattern = os.path.join(base_dir, "**", "*.json")
    return glob(pattern, recursive=True)

def scan_value(v: str) -> Dict[str, Any]:
    """
    문자열 v에 대해 더블 이스케이프 의심 여부 및 상세 카운트 반환.
    의심 기준:
      - 실제 제어문자(예: '\n', '\t')가 전혀 없고
      - 백슬래시 시퀀스(예: '\\n', '\\t')가 하나 이상 존재
    """
    # 실제 제어문자 존재 여부
    has_real_newline = ("\n" in v) or ("\r\n" in v) or ("\r" in v)
    has_real_tab = ("\t" in v)

    # 리터럴 백슬래시 시퀀스 존재 여부와 카운트
    counts = {seq: v.count(seq) for seq in ESCAPE_SEQUENCES}
    has_literal_sequences = any(counts[seq] > 0 for seq in counts)

    suspected = (not has_real_newline) and (not has_real_tab) and has_literal_sequences

    return {
        "suspected": suspected,
        "has_real_newline": has_real_newline,
        "has_real_tab": has_real_tab,
        "literal_counts": counts
    }

def main() -> None:
    json_files = iter_json_files(BASE_DIR)
    total = len(json_files)
    scanned = 0

    results = []   # 파일별 상세 결과
    flagged = 0    # 의심 파일 수(최소 1개 필드가 suspected=True)

    print(f"🔎 Scanning {total} JSON files under: {BASE_DIR}\n")

    for fp in json_files:
        scanned += 1
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️  Skip (invalid JSON): {fp} | {e}")
            continue

        if not isinstance(data, dict):
            continue

        file_report = {"file": fp, "fields": {}}
        file_suspected = False

        for key in TARGET_KEYS:
            val = data.get(key)
            if isinstance(val, str):
                r = scan_value(val)
                file_report["fields"][key] = r
                if r["suspected"]:
                    file_suspected = True
            else:
                file_report["fields"][key] = {"suspected": False, "note": "not a string"}

        if file_suspected:
            flagged += 1
            print(f"🚩 Suspected double-escape: {fp} "
                  f"→ keys: {', '.join([k for k,v in file_report['fields'].items() if isinstance(v, dict) and v.get('suspected')])}")

        results.append(file_report)

    # 요약
    summary = {
        "base_dir": BASE_DIR,
        "total_files": total,
        "scanned_files": scanned,
        "flagged_files": flagged
    }

    # 리포트 저장 (읽기 편하게 indent)
    report_path = os.path.join(BASE_DIR, "double_escape_scan_report.json")
    out = {"summary": summary, "details": results}
    with open(report_path, "w", encoding="utf-8") as wf:
        json.dump(out, wf, ensure_ascii=False, indent=2)

    # 콘솔 요약
    print("\n📊 Summary")
    print(f"- Scanned files : {scanned}")
    print(f"- Flagged files : {flagged}")
    print(f"- Report        : {report_path}")

if __name__ == "__main__":
    main()
