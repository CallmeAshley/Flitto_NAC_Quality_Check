import os
import glob

# A 폴더 경로 (엑셀 파일이 존재하는 곳)
a_folder_path = '/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2'

# B 폴더 경로 (폴더를 생성할 대상 경로)
b_folder_path = '/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2_json'

# A 폴더의 모든 엑셀 파일 리스트 가져오기
excel_files = glob.glob(os.path.join(a_folder_path, '*.xlsx'))

# 각 엑셀 파일명으로 B 폴더 내에 새 폴더 생성
for file_path in excel_files:
    # 파일명만 추출 (확장자 제외)
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # 만들 폴더 경로
    new_folder_path = os.path.join(b_folder_path, file_name)
    
    # 폴더가 없으면 생성
    if not os.path.exists(new_folder_path):
        os.makedirs(new_folder_path)
        print(f'생성됨: {new_folder_path}')
    else:
        print(f'이미 존재함: {new_folder_path}')
