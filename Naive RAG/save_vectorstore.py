from dotenv import load_dotenv
import os
from langchain_teddynote import logging
import bs4  # 웹페이지 파싱
from langchain import hub   # 텍스트 분할, 문서 로딩, 벡터 저장, 출력 파싱
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings   # OpenAI의 챗봇과 임베딩
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.utils import DistanceStrategy



if __name__ == '__main__':

    # Load
    md_files = [
        "common_curriculum.md",     # 학년별 교양 및 학점 정보 (10개)
        "lectures_eval.md"          # 강의 평가 (608개)
    ]

    # 파일마다 다르게 Split
    split_configs = {
        "common_curriculum.md": {
            "separators": ["##", "\n\n"],
            "chunk_size": 800,
            "chunk_overlap": 100
        },
        "lectures_eval.md": {
            "separators": ["##", "\n\n"],
            "chunk_size": 500,
            "chunk_overlap": 50
        }
    }

    docs = []  # 전체 문서
    for file_path in md_files:
        # 문서 로드
        loader = TextLoader(file_path, encoding="utf-8")
        doc = loader.load()

        # split 설정
        config = split_configs.get(file_path)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            separators=config["separators"]
        )
        splits = splitter.split_documents(doc)
        print("splits 길이:", len(splits))

        '''
        # split 보고 싶다면
        for s in splits:
            print("--------------------------------------------------------")
            print(s)
            print()
        exit(0)
        '''

        docs.extend(splits)

    embeddings_model = HuggingFaceEmbeddings(       # 768 차원
        model_name='jhgan/ko-sroberta-nli',
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True},
    )


    vectorstore = FAISS.from_documents(docs,
                                       embedding = embeddings_model,
                                       distance_strategy = DistanceStrategy.COSINE)

    # FAISS 벡터 저장소 저장하기
    vectorstore.save_local('./db/faiss')

    
