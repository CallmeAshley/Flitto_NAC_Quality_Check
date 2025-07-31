# utils/file_utils.py
import os

def load_guideline(locale: str, category: str) -> str:
    """
    Load the guideline txt file content for a specific locale and category.
    Example: locale='fr_FR', category='currency'
    → loads: rag_module/policy_docs_new_after/fr_FR/currency.txt
    """
    base_dir = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/policy_docs_new_after"
    file_path = os.path.join(base_dir, locale, f"{category}.txt")

    if not os.path.exists(file_path):
        print(f"가이드라인 파일이 존재하지 않습니다: {file_path}")
        return ""

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
