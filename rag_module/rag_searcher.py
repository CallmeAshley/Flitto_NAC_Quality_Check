from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
import os
from dotenv import load_dotenv
import openai
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 벡터 DB 경로 및 임베딩 모델 정의
PERSIST_DIR = "/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/vector_store/"
embedding = OpenAIEmbeddings()

# 벡터 DB 로드
vectordb = Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding)

def query_policy(language: str, query: str, top_k: int = 2) -> str:
    """
    특정 target 언어의 정책 문서에서 query에 가장 유사한 내용을 검색합니다.
    """
    results = vectordb.similarity_search(query, k=top_k, filter={"target": language})
    
    if results:
        return results[0].page_content
    else:
        return "관련 정책 문서를 찾을 수 없습니다."

# # 테스트 예시
# if __name__ == "__main__":
#     example = {
#         "source": "portuguese",
#         "target": "english",
#         "text": "28/10 to 02/11",
#         "trans": "de 28/10 a 2/11"
#     }

#     query = f"""In the sentence \"{example['trans']}\", does the date format conform to the translation policy for '{example['target']}' language?"""
#     answer = query_policy(example["target"], query)
#     print("\n검색 결과:\n", answer)
