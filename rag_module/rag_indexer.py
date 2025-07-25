import os
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from dotenv import load_dotenv
import openai
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def index_policy_documents(
    docs_path="/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/policy_docs/",
    persist_dir="/mnt/c/Users/Flitto/Documents/NAC/LLM검수/Advanced/rag_module/vector_store/",
    chunk_size=3000,
    chunk_overlap=50
):
    print("정책 문서를 불러오는 중...")
    documents = []

    for fname in os.listdir(docs_path):
        if fname.endswith(".txt"):
            lang = fname.replace(".txt", "")
            loader = TextLoader(os.path.join(docs_path, fname), encoding="utf-8")
            loaded_docs = loader.load()
            for doc in loaded_docs:
                doc.metadata["target"] = lang
            documents.extend(loaded_docs)

    print(f"총 {len(documents)}개의 문서 로드 완료.")

    print("문서 청킹 중...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    split_docs = splitter.split_documents(documents)
    print(f"총 {len(split_docs)}개의 청크 생성 완료.")

    print("임베딩 및 벡터 DB 저장 중...")
    embedding = OpenAIEmbeddings()
    vectordb = Chroma.from_documents(split_docs, embedding, persist_directory=persist_dir)

    vectordb.persist()
    print(f"벡터 저장 완료: {persist_dir}")


if __name__ == "__main__":
    index_policy_documents()
