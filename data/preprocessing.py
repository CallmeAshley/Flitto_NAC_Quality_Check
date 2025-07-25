import pandas as pd
import json
import glob
import os

# 엑셀 파일이 있는 폴더 경로
folder_path = '/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2' 
# 해당 경로 내의 모든 .xlsx 파일 리스트 얻기
excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))

# 파일 하나씩 불러오기
for file in excel_files:
    df = pd.read_excel(file)
    # 파일 이름 전체 추출: 'LP.sys.test.longcontext.112024.de_DE-en_US.77980w.v3.HT_nac.xlsx'
    filename_with_ext = os.path.basename(file)
    # 확장자 제거: ('파일명', '.xlsx')로 나뉨
    filename = os.path.splitext(filename_with_ext)[0]
    for i in range(len(df)):
        if df['status'][i] != 'Reported':
            SID = df['SID'][i]
            data = {
                "source": str(df['Src language'][i]),
                "target": str(df['Tgt language'][i]),
                "text": str(df['Origin'][i]),
                "trans": str(df['Translation'][i])
            }

            with open(f'/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/data/input2_json/{filename}/{SID}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
