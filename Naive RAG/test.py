from dotenv import load_dotenv
import os

import bs4  # 웹페이지 파싱
from langchain import hub  # 텍스트 분할, 문서 로딩, 벡터 저장, 출력 파싱
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # OpenAI의 챗봇과 임베딩
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain.prompts import ChatPromptTemplate
import crawling

from langchain_teddynote import logging

def format_docs(docs):
    return '\n\n'.join([d.page_content for d in docs])

if __name__ == '__main__':
    # personalInfo.md 저장
    stu_ID = ""
    stu_PW = "!"
    stu_yr = crawling.personalInfo(stu_ID, stu_PW)

    # Load
    loader = TextLoader("personalInfo.md", encoding="utf-8")
    documents = loader.load()

    # Split
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["-"],
        chunk_size=500,
        chunk_overlap=0
    )
    split_docs = text_splitter.split_documents(documents)

    # 사전 준비, 환경 설정 - API 키 정보 로드
    os.environ["USER_AGENT"] = os.getenv("USER_AGENT", "MyPythonApp")
    dotenv_path = r"C:\Users\user\PycharmProjects\pythonProject\env.env"
    if load_dotenv(dotenv_path):
        print("env 파일이 성공적으로 로드되었습니다.")
    else:
        print("env 파일을 찾을 수 없습니다. 경로를 다시 확인하세요.")

    # LangSmith 추적 설정
    logging.langsmith("Graduation Project")

    embeddings_model = HuggingFaceEmbeddings(  # 768 차원
        model_name='jhgan/ko-sroberta-nli',
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True},
    )

    # 벡터스토어 불러오기
    vectorstore = FAISS.load_local(
        './db/faiss',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)

    vectorstore.add_documents(split_docs)   # personalInfo.md 추가

    # Retriever: mmr 방식 (검색 결과의 관련성 & 다양성)
    retriever = vectorstore.as_retriever(
        search_type='mmr',
        search_kwargs={'k': 5, 'lambda_mult': 0.5}  # 0.5가 기본값  #0.15
    )

    query = '내가 졸업하기 위해 들어야하는 교양 정보를 알려주고 만약 듣지 않은 과목들이 있다면 무엇인지 알려줘'
    #query = '내가 졸업하기 위해 남은 학점은 어떻게 되지? 자세히 알려줘'
    #query = '소프트웨어학생이 졸업하기 위해 부전공 학점은 얼마나 채워야 하지?'
    #query = '광운인되기 수업중 어떤 교수님 수업을 들어야할지 고민이야. 추천해줘'

    new_query = f"{query} (참고로 나는 {int(stu_yr)}년도 신입생이야)"

    docs = retriever.get_relevant_documents(new_query)
    for i, doc in enumerate(docs):
        print(f"{i + 1}번째 유사한 문서:-------------------------")
        print(doc)
        print()



    # 개인 정보 & 일반 문서
    personal_info_docs = [doc for doc in docs if doc.metadata.get('source') == 'personalInfo.md']
    general_info_docs = [doc for doc in docs if doc.metadata.get('source') != 'personalInfo.md']

    # 문자열로 변환
    personal_info_text = format_docs(personal_info_docs) if personal_info_docs else "No personal info available."
    general_info_text = format_docs(general_info_docs) if general_info_docs else "No general info available."

    # Prompt: {context} 검색된 문서의 내용, {question} 사용자 쿼리
    template = '''You are an intelligent assistant tasked with analyzing both the user's personal academic records and the official requirements to provide an accurate response.

    ### User's Personal Academic Information:
    {personal_info}

    ### Official Requirements:
    {general_info}

    Carefully compare the user's academic records with the official requirements. Answer the question based only on the given data.

    #### Question:
    {question}
    '''

    prompt = ChatPromptTemplate.from_template(template)

    # Model
    llm = ChatOpenAI(
        model='gpt-4o-mini',
        temperature=0,  # 0.2~ 0.4 FAQ, 고객 지원
        max_tokens=500,
    )


    # Chain
    chain = prompt | llm | StrOutputParser()

    # Run
    response = chain.invoke({
        'personal_info': personal_info_text,
        'general_info' : general_info_text,
        'question': new_query})

    print("\n\n-----------------------------------------")
    print(response)

