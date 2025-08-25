import os

exceptions_text = """
[Exceptions]

- Do not apply the formatting rules to numbers that are part of:
  - telephone numbers
  - addresses
  - identification codes
  - or clearly unordered lists of numbers with no separators

- If the numbers or formats (e.g., 10:00, 12/31, $15) appear to be part of such non-linguistic constructs based on the sentence context, do not apply localization guidelines.

- Always consider the context of the original sentence before making changes.
"""

BASE_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/policy_docs_new_after"
CATEGORIES = ["currency.txt", "date.txt", "numeric.txt", "time.txt"]

# 순회하면서 예외 문구 추가
for locale in os.listdir(BASE_DIR):
    locale_dir = os.path.join(BASE_DIR, locale)
    if not os.path.isdir(locale_dir):
        continue

    for cat in CATEGORIES:
        file_path = os.path.join(locale_dir, cat)
        if not os.path.exists(file_path):
            continue

        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n" + exceptions_text.strip() + "\n")

        print(f"Appended to: {file_path}")
