import os

# 생성할 폴더 구조 정의
folders = [
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/output",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rules",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/prompt_builder",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/policy_docs",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/outputs",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/agent",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/mcp",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/utils"
]

# 생성할 파일 정의 (빈 파일 또는 기본 템플릿용)
files = [
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rules/formats.json",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/prompt_builder/build_prompt.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/autorag_config.yaml",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/autorag_runner.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/agent/langgraph_fsm.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/agent/step_date_check.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/agent/step_number_check.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/agent/utils.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/mcp/promptfoo.yaml",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/mcp/test_cases.json",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/mcp/eval.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/utils/gpt_client.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/main.py",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/requirements.txt",
    "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/.env"
]

# 폴더 생성
for folder in folders:
    os.makedirs(folder, exist_ok=True)

# 파일 생성
for file_path in files:
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("")  # 필요시 템플릿 내용을 여기에 추가 가능

print("폴더 및 파일 구조가 생성되었습니다.")
