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

'''
1. common_curriculum.md 도 나누기 가능? 2020 인문, 자연, 공학 이렇게 있는데 3개로 나누는거

2. md에 <tag>

3. 표를 2차원 배열에 넣었는데 이것도 쪼갤까? 

'''

def format_docs(docs):
    return '\n\n'.join([d.page_content for d in docs])

def get_save_personal_info(stu_id, stu_pw, embeddings_model):

    #stu_info = crawling.personalInfo(stu_id, stu_pw)
    #print("stu_info: ", stu_info)     #[입학 년도, 학과/학부, 나의 학위 과정]
    stu_info = ['2020년도 신입생', '소프트웨어학부 소프트웨어전공', '공학']

    # Load
    loader = TextLoader("md/grads/personalInfo.md", encoding="utf-8")
    stu_doc = loader.load()

    # embedding
    vectorstore = FAISS.from_documents(stu_doc, embedding=embeddings_model, distance_strategy=DistanceStrategy.COSINE)

    # FAISS 벡터 저장소 저장하기
    address = './db/grads/personalInfo'
    vectorstore.save_local(address)

    return stu_info

def load_vectorstore(embeddings_model):
    vec_big_category = FAISS.load_local(            # BIG CATEGORY
        './db/big_category',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)
    vec_grads_common = FAISS.load_local(            # [grads]
        './db/grads/common_curriculum',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)
    vec_grads_liberal = FAISS.load_local(
        './db/grads/liberalArts',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)
    vec_grads_personal = FAISS.load_local(
        './db/grads/personalInfo',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)
    vec_grads_major = FAISS.load_local(             # grads/major
        './db/grads/major/majors',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)

    majors_idx = [[] for i in range(36)]
    vec_grads_major_sw_both = FAISS.load_local(     # software
        './db/grads/major/software/both',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)
    vec_grads_major_sw_degree = FAISS.load_local(
        './db/grads/major/software/degree',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)
    majors_idx[7].append(vec_grads_major_sw_both)
    majors_idx[7].append(vec_grads_major_sw_degree)  # 추가 방식을 좀 더 효율적으로 하고 싶음

    vec_eval_lectures = FAISS.load_local(           # [eval]
        './db/eval/lectures_eval',
        embeddings_model,
        distance_strategy=DistanceStrategy.COSINE,
        allow_dangerous_deserialization=True)

    # 요약
    big_category = vec_big_category
    grads = [vec_grads_common, vec_grads_liberal, vec_grads_personal, vec_grads_major, majors_idx]
    eval = [vec_eval_lectures]
    food = []
    info = []
    return [big_category, grads, eval, food, info]


if __name__ == '__main__':
    # 기본 세팅
    os.environ["USER_AGENT"] = os.getenv("USER_AGENT", "MyPythonApp")
    dotenv_path = r"C:\Users\user\PycharmProjects\pythonProject\env.env"
    if load_dotenv(dotenv_path):
        print("env 파일이 성공적으로 로드되었습니다.")
    logging.langsmith("Graduation Project")  # LangSmith 추적 설정
    embeddings_model = HuggingFaceEmbeddings(  # 768 차원
        model_name='jhgan/ko-sroberta-nli',
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True},
    )

    # 개인 정보
    stu_id = '2020203068'
    stu_pw = 'yoojong20!'
    stu_info = get_save_personal_info(stu_id, stu_pw, embeddings_model)

    # 모든 vectorstore 로드 -------------------------------------------------------------
    '''
    1) 처음 시작할 때 한방에 다 로드        (벡터 스토어 개많아 질 것 같아서 걱정됨)
    2) 해당 카테고리에 해당되는 부분만 로드
    '''
    db_vectorstore = load_vectorstore(embeddings_model)

    # 질문 ------------------------------------------------------------------------------
    #query = '내가 졸업하기 위해 아직 이수하지 않은 과목이 있어?'                 # 답) 필요한 정보는 다 있지만 잘 대답을 못함 (tag로 변형 필요할 듯)
    #query = '나의 세부전공이 인공지능전공인데 혹시 꼭 들어야하는 과목들이 뭐지?'     # 답) 과목들은 알려주는데 중 3개만 들어도 된다는 얘기를 안해 -> 표를 잘 이해못하는듯
    query = '영어 관련 수업을 듣고 싶은데 어떤 영어 수업들이 있지?'

    # 질문 vs big_category  ------------------------------------------------------------
    retriever = db_vectorstore[0].as_retriever(
        search_type='mmr',
        search_kwargs={'k': 1, 'lambda_mult': 0.5}  # 하나만
    )
    chosen_category = retriever.invoke(query)

    # 해당 category vs 질문  -----------------------------------------------------------------
    selected_docs = []
    match chosen_category[0].metadata.get('id'):
        case 'grads':
            print("졸업 카테고리----------------------------")
            print("질문: ", query)

            focused, majors_idx = db_vectorstore[1][0:-1], db_vectorstore[1][-1]

            vec_major= []   # 전공에 대한 vectorstore 담겨질 곳
            for idx, current in enumerate(focused):
                retriever = current.as_retriever(
                    search_type='mmr',
                    search_kwargs={'k': 1, 'lambda_mult': 0.5}  # 하나만
                )

                if idx == 0:    # 교양 안내 (입학 년도 선택)
                    chosen_doc = retriever.invoke(stu_info[0])  # stu_info[0] = 입학 년도

                elif idx == 3:  # 전공 선택 (사용자 전공 선택)
                    chosen_doc = retriever.invoke(stu_info[1])  # stu_info[1] = 학과/학부
                    print("사용자 학과 체크: ", chosen_doc[0].page_content, "\n")
                    vec_major = majors_idx[int(chosen_doc[0].metadata.get('id'))]
                    focused.extend(vec_major)
                    continue
                elif current in vec_major:  # 전공 (학위 과정 선택)
                    chosen_doc = retriever.invoke(stu_info[2])   # stu_info[2] = 학위과정  (klas에 학위과정 없는 사람도 있음, 이 경우 생각 안함)

                else:   # 선택지 없을 때
                    chosen_doc = retriever.invoke(query)

                selected_docs.extend(chosen_doc)

            print("chunk 잘 가져오는지 확인")
            for i in selected_docs:
                print(i.metadata, "-------------------------------------------------------------------------")
                print(i.page_content)
                print()


            #exit(0)

            # 개인 정보 & 일반 문서
            personal_info_docs = [doc for doc in selected_docs if doc.metadata.get('source') == 'md/grads/personalInfo.md']
            general_info_docs = [doc for doc in selected_docs if doc.metadata.get('source') != 'md/grads/personalInfo.md']

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
                max_tokens=1000,
            )

            # Chain
            chain = prompt | llm | StrOutputParser()

            # Run
            response = chain.invoke({
                'personal_info': personal_info_text,
                'general_info': general_info_text,
                'question': query})
            print("답변: -----------------------------------------------------------")
            print(response)

        case 'eval':
            print("강의 평가 카테고리")
            focused = db_vectorstore[2]
            for idx, current in enumerate(focused):
                retriever = current.as_retriever(
                    search_type='mmr',
                    search_kwargs={'k': 5, 'lambda_mult': 0.5}  # 5개 가져오도록
                )
                chosen_doc = retriever.invoke(query)        # 유사한 청크 가져옴
                selected_docs.extend(chosen_doc)

            print("chunk 잘 가져오는지 확인")
            for i in selected_docs:
                print(i.metadata, "-------------------------------------------------------------------------")
                print(i.page_content)
                print()

        case 'food':
            print("음식 카테고리")

        case 'info':
            print("정보 카테고리")

        case _:
            print("카테고리 없음")
            exit(-1)






