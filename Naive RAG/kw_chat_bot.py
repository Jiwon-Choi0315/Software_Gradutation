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
from langchain.retrievers import BM25Retriever, EnsembleRetriever
# import crawling
from langchain_teddynote import logging
import ast
import joblib
import warnings

warnings.simplefilter("ignore", FutureWarning)

current_dir = os.path.dirname(os.path.abspath(__file__)) + "\\"

'''
1번 행 찾기를 내가 하자.
'''

def format_docs(docs):
    # return '\n\n'.join([d.page_content for d in docs])
    return docs


def get_personal_info(stu_id, stu_pw):
    stu_info_dict = crawling.personalInfo(stu_id, stu_pw)
    return stu_info_dict


class VectorStoreManager:
    def __init__(self):
        self._vectorstores = {
            "Graduation": [],
            "Course": [],
            "Food": [],
            "Academic Info": []
        }
        self._docs = {
            "Graduation": [],
            "Course": [],
            "Food": [],
            "Academic Info": []
        }
        self._embeddings_model = HuggingFaceEmbeddings(  # 768 차원
            model_name='jhgan/ko-sroberta-nli',
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
        )

    def get_vectorstores(self, category):
        if not self._vectorstores[category]:
            print(f"{category} Vectorstore 로드중")
            try:
                category_path = os.path.join(current_dir + 'db', category)
                for topic_folder in os.listdir(category_path):
                    topic_folder_path = os.path.join(category_path, topic_folder)
                    topic_vectorstore = []
                    topic_docs = []

                    for detail_folder in os.listdir(topic_folder_path):
                        detail_folder_path = os.path.join(topic_folder_path, detail_folder)

                        vectorstore = FAISS.load_local(
                            detail_folder_path,
                            self._embeddings_model,
                            distance_strategy=DistanceStrategy.COSINE,
                            allow_dangerous_deserialization=True
                        )
                        doc = joblib.load(detail_folder_path + "\\keyword.joblib")

                        topic_vectorstore.append(vectorstore)
                        topic_docs.append(doc)

                    self._vectorstores[category].append(topic_vectorstore)
                    self._docs[category].append(topic_docs)

                print(f"{category} 모든 Vectorstore 로드 완료")

                # 학생 전공 타입 물어보기
                global stu_info
                major_type = ['단일전공', '심화전공', '복수전공', '연계전공', '학생설계융합전공', '마이크로전공']
                stu_major_type = input(f"{', '.join(major_type)} 중 무엇을 하고 있나요?")
                while stu_major_type not in major_type:
                    print("다시 입력해주세요.")
                    stu_major_type = input("'단일전공', '심화전공', '복수전공', '연계전공', '학생설계융합전공', '마이크로전공' 중 무엇을 하고 있나요?)")
                stu_info['전공 타입'] = stu_major_type

            except Exception as e:
                print(f"{category} Vectorstore 로드 실패: {e}")
        else:
            print(f"{category} Vectorstore 이미 로드됨.")

        return self._vectorstores[category], self._docs[category]

class LlmManager:
    def __init__(self):
        self._llm = ChatOpenAI(
            model='gpt-4o',
            temperature=0
        )
        self._llm_type = None
        self._template = None

    def set_llm_type(self, llm_type):
        self._llm_type = llm_type

    def get_template(self):
        if self._llm_type == 'category':
            self._template = '''
                Select the category that best matches the question below. 
                The categories are: "Graduation", "Food", "Course", "Academic Info", and "None".

                1. Graduation: Questions related to requirements or conditions needed for graduation.
                2. Food: Questions related to food, such as recommendations or information.
                3. Course: Questions about course evaluations or recommendations.
                4. Academic Info: Questions about school announcements or academic-related information.
                5. None: If the question does not fit any of the above categories.

                Question: {question}
                Category Name:
                '''
        elif self._llm_type == 'summarize':
            self._template = '''
            다음 글의 핵심 내용을 유지하면서 요약해 주세요.
            
            ### 주의사항: 
            학생이 충족한 부분에 대해서는 충족되었다고 명시하고,
            학생이 충족하지 못한 부분에 대해서는 자세하게 작성해주세요. 
            
            ### 요약할 내용:
            {words}
            
            '''

        # [졸업 카테고리]
        elif self._llm_type == 'grad_credits_table':
            self._template = '''
            당신은 표에 대한 정보를 dictionary 형태로 변환하는 전문 에이전트입니다.
            학생의 개인 정보와 학점 졸업 요건 표가 주어지면, 학생에게 해당하는 행을 정확히 추출하여 딕셔너리로 반환하세요.

            ### 학생 개인 정보:
            - **전공**: {major}
            - **학번**: {stu_id}

            ### 학점 졸업 요건 표:
            {credits_table}

            ___
            ### 해당 행(row) 찾기
            - `credits_table`에서 '단과대' 열들을 확인하여 **학생의 전공 '{major}'과 일치하는 행(row)**을 찾습니다.  
            - 특정 학번에 대한 기준이 존재하는 경우, 학생의 학번에 맞는 행을 선택합니다.  
                - **학생의 학번 '{stu_id}'이 정확히 "2020학번"이면, "2020학번" 행을 선택합니다.**  
                - **학생의 학번 '{stu_id}'이 "2021학번" 이상(2021, 2022, 2023)이면, "2021학번~" 행을 선택합니다.** 
            - 적절한 행을 찾았다면, 모든 열의 이름을 key로, 해당 행의 값을 value로 매핑하세요.
            
            ### 출력
            - 열의 이름을 최대한 자세하게 반드시 하위 항목이 명시되도록 작성해주세요.
            - 추출한 딕셔너리만 출력하세요.
            - 추출을 잘할시 팁 $100 와 당근 500개를 드리겠습니다.
            '''
        elif self._llm_type == 'grad_credits':
            self._template = '''
            당신은 학생의 **학점 정보**가 졸업 요건을 충족하는지 판단하는 에이전트입니다.
            학생의 학점 정보와 졸업 요건이 담긴 딕셔너리가 주어지며, 이를 비교하여 졸업 가능 여부를 검토해야 합니다.

            ### 학생 정보:
            - **전공 유형**: {major_type} (ex: 단일 전공, 심화 전공, 복수 전공, 연계 전공 등)
            - **전공 취득 학점**: {major_credits}
            - **교양 취득 학점**: {liberal_credits}
            - **총 취득 학점**: {tot_credits}

            ### 졸업 요건 딕셔너리:
            {credits_dictionary}

            ___
            ### 학생의 정보와 dictionary를 비교
            - **총 학점:** 학생의 총 취득 학점 vs dictionary의 졸업이수학점  
            - **교양 학점:** 학생의 취득 교양 학점 vs dictionary의 교양 관련 학점 합 
            - **전공 학점:** 학생의 취득 전공 학점 vs dictionary의 학생 전공 유형에 해당하는 학점  
                _(참고: **학생 전공이 복수 전공일 경우, dictionary의 학생 전공 유형에 해당하는 학점은 복수전공 학점과 부전공 학점의 합입니다.**)_

            '''

        elif self._llm_type == 'grad_liberalArts_table':
            self._template ='''
            당신은 표에 대한 정보를 dictionary 형태로 변환하는 전문 에이전트입니다.
            교양 이수 체계 표가 주어지면, 해당하는 행을 정확히 추출하여 딕셔너리로 반환하세요.

            ### 교양 이수 체계 표:
            {liberalArts_table}

            ___
            ### 교양 조건 딕셔너리 구성 지침
            -   **key: '필수교양'** 
                **value:** '필수교양'행에 기재된 조건을 요약합니다. _(참고: 학점에 대한 정보는 제외)_
            -   **key: '균형교양'**  
                **value:** '균형교양' 행의 마지막 열에 해당하는 조건을 요약합니다. _(참고: 학점 관련 정보는 제외)_
    
            ### 출력 요건
            - 추출한 딕셔너리만 출력하세요.
            - 추출을 잘할시 팁 $100 와 당근 500개를 드리겠습니다.
            '''
        elif self._llm_type == 'grad_liberalArts':
            self._template = '''
            당신은 학생의 수강 정보가 교양 졸업 요건(필수교양과 균형교양)을 충족하는지 평가하는 에이전트입니다.
            아래 제공된 **학생 정보**와 **교양 이수 체계 딕셔너리**를 참고하여, 학생이 교양 졸업 요건을 만족하는지 판단하세요.
            
            ### [입력 데이터]
            
            **학생 정보**
            - **학번**: {stu_id}
            - **수강 정보**: {intersection_summary}
            
            **교양 이수 체계 딕셔너리**
            {table_info}
            
            ___
            ### [평가 항목]
            1. **필수교양 평가**
            - 딕셔너리의 '필수교양' 항목과 수강 정보의 '필수교양'을 비교합니다.
            - 해당 영역의 요건이 충족되었는지 여부를 출력하세요.
            
            2. **균형교양 평가**
            - 딕셔너리에서 제시된 '균형교양' 항목들을 출력합니다.
            - **특별 조건**: 학번{stu_id}이 2024, 2025가 아닐 경우, 수강 정보의 '균형영역: 수리와자연'은 평가 대상에서 제외합니다.
            - 각 균형교양 영역에 대해, 수강 정보에서 과목 이수 여부를 확인하고 이수한 과목의 수를 집계합니다.
            - 총 포함된 균형교양 영역의 수와 이수한 과목의 총 개수를 출력하세요.
       
            3. **최종 결론**  
            - 위의 평가 결과를 종합하여, 학생이 전체 교양 졸업 요건(필수교양 및 균형교양)을 충족하는지 최종 결론을 내려주세요.
            '''

        elif self._llm_type == 'grad_engineer_subj_table':
            self._template = '''
            당신은 표에서 정보를 추출하는 전문 에이전트입니다.
            주어진 공학인증 표에서 학생 정보와 관련된 행을 정확히 찾아 필요한 데이터를 추출하세요.
            
            ### 학생 정보:
            - 학부/학과: {major}
            
            ### 공학인증 표:
            {engineer_table}

            ___
            ### 출력 지침
            1. 학생 전공{major}과 일치하는 행을 찾습니다.
            2. 해당 행에서 **마지막 '전공' 열의 값**을 추출합니다.
            
            추출한 내용:  
            '''
        elif self._llm_type == 'grad_engineer_subj':
            self._template = '''
            당신은 학생이 공학 필수 과목을 이수했는지 검토하는 에이전트입니다.
            아래 **공학 필수 과목**과 **학생 수강 과목**을 바탕으로 필수 과목 이수 여부를 판단하세요.

            ### [입력 데이터]

            **공학 필수 과목**
            {required_sbj}

            **학생 수강 과목**
            {attended_sbj}
            
            '''

        elif self._llm_type == 'grad_engineer_msi_table':
            self._template = '''
            당신은 공학 인증 기준표를 분석하고 핵심 정보를 요약하는 전문가입니다. 아래 지침에 따라 표의 내용을 정확히 분류해 주세요.
            
            ### 주의사항:
            "택1" 표기 주의: 해당 그룹 내 한 과목만 선택하여 필수 이수라는 의미
            **일반 과목: 필수 표시 없음**, 추가로 이수 가능한 과목 (학점 채우기 용)

            ### 처리 방법:
            표의 각 행을 순차적으로 분석합니다.
            학점 조건이 영역별인지 전체 총괄인지 어느 영역에서 몇학점을 이수해야하는지 명시합니다. 
            과목명, 필수 여부, 택1을 확인합니다.   
            3개 영역 중 해당하는 영역에 분류하고, 필수/일반 과목으로 구분합니다.
                        
            ### 공학인증 표:
            {msi_table}
            
            ### 출력 형식:
            [수학, 기초과학, 전산학(공학기초)] 또는 [수학, 기초과학] 영역에서 총 몇학점 이수 
            
            수학 영역
            - 수학 영역 최소 몇학점 이수
            - 필수 과목:
            - 일반 과목:
            
            기초과학 영역
            - 기초과학 영역 최소 몇학점 이수
            - 필수 과목:
            - 일반 과목:
            
            전산학(공학기초) 영역
            - 전산학(공학기초) 영역 최소 몇학점 이수
            - 필수 과목:
            - 일반 과목:
            
            '''
        elif self._llm_type == 'grad_engineer_msi':
            self._template = '''
            당신은 학생이 공학 msi 학점이 채워졌는지 검토하는 에이전트입니다.
            아래 **msi 정보**와 **학생 수강 과목**을 바탕으로 충족 여부를 판단하세요.
            
            ### [주의사항]
            각 과목에 대한 학점 정보는 학생 수강 과목에서 알 수 있습니다.
            
            ### [입력 데이터]

            **msi 정보**
            {msi_info}

            **학생 수강 과목**
            {attended_sbj}
            

            '''

        return self._template

    def get_chain(self):
        template = self.get_template()
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self._llm | StrOutputParser()
        return chain

class MdManager:
    def __init__(self):
        self._file_path = None

    def set_path(self, file_path):
        self._file_path = file_path

    def get_dictionary(self):
        with open(self._file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
            result = dict()
            for line in markdown_content.splitlines():
                if line.startswith('#'):
                    current_section = line.lstrip('#').strip()  # '#' 제거 후 제목 추출
                    result[current_section] = None
                else:
                    result[current_section] = ast.literal_eval(line)
        return result

if __name__ == '__main__':
    # 기본 세팅
    #os.environ["USER_AGENT"] = os.getenv("USER_AGENT", "MyPythonApp")       # 이부분 이상함
    dotenv_path = current_dir + r"\\.env"
    if load_dotenv(dotenv_path):
        print("env 파일이 성공적으로 로드되었습니다.")
    logging.langsmith("Graduation Project")  # LangSmith 추적 설정


    # vectorstore, LLM 관리자
    vec_manager = VectorStoreManager()
    llm_manager = LlmManager()
    md_manager = MdManager()

    # 개인 정보
    #stu_info = get_personal_info('', '')
    stu_info = {'학부/학과': '소프트웨어학부 소프트웨어전공', '입학 년도': '2020년도 신입학자', '학번': '2020203068', '이름': '최유종', '학적상황': '4학년 재학', '학위 과정': '공학 프로그램', '전공 학점': '63', '교양 학점': '61', '기타 학점': '8', '총 학점': '132', '수강한 과목': {('리눅스활용실습', '2'), ('데이터통신', '3'), ('중국어HSK연습', '3'), ('산학협력캡스톤설계1', '3'), ('인공지능', '3'), ('기계학습', '3'), ('빅데이터언어', '3'), ('운영체제', '3'), ('사회봉사1', '1'), ('융합적사고와글쓰기', '3'), ('객체지향프로그래밍', '3'), ('고급프로그래밍', '3'), ('파이썬프로그래밍기초', '3'), ('알고리즘', '3'), ('시스템소프트웨어', '3'), ('C프로그래밍', '3'), ('심화전공실습', '3'), ('이산구조', '3'), ('공학설계입문', '3'), ('컴퓨터비전', '3'), ('응용소프트웨어실습', '3'), ('영어회화', '3'), ('참빛설계V', '2'), ('영어베스트셀러읽기', '3'), ('축구', '2'), ('대학수학및연습1', '3'), ('선형대수학', '3'), ('초급중국어1', '3'), ('자료구조실습', '2'), ('딥러닝실습', '2'), ('디지털논리', '3'), ('대학영어', '3'), ('자료구조', '3'), ('공학수학1', '3'), ('TED로배우는영어', '3'), ('대학수학및연습2', '3'), ('고급C프로그래밍및설계', '3'), ('데이터베이스', '3'), ('컴퓨터구조', '3'), ('중급영어회화', '3'), ('비즈니스영어', '3'), ('초급중국어2', '3'), ('광운인되기', '1'), ('컴퓨팅사고', '3'), ('빅데이터처리및응용', '3'), ('국제회의영어', '3'), ('소프트웨어공학', '3')}}


    # 질문 ------------------------------------------------------------------------------여기부터 계속 반복
    query = '내가 졸업하기 위해 아직 이수하지 않은 과목이 있어?'
    print("질문: ", query)

    # 카테고리 gpt ------------------------------------------------------------
    llm_manager.set_llm_type('category')
    chain = llm_manager.get_chain()
    response = chain.invoke({'question': query})
    # print("gpt가 선택한 카테고리: ----------------------------------")
    # print(response)

    #response = 'Graduation'

    # 해당 category vs 질문  -----------------------------------------------------------------
    match response:
        case 'Graduation':
            # print("졸업 카테고리----------------------------")

            grad_vecs, grad_docs = vec_manager.get_vectorstores("Graduation")  # 졸업 처음 방문할 때, 졸업 vectorstore 로드 및 학생 전공 타입 물어봄,
            # 참고: grad_vecs = [[학점], [교양], [전공], [공학]]      (현재: [[학점],[교양],[공학] )

            for idx, vecs in enumerate(grad_vecs, start = 1):
                # 1. 학점
                if idx == 1:
                    retriever = vecs[0].as_retriever(
                        search_type='mmr',
                        search_kwargs={'k': 3, 'lambda_mult': 0.5}  # 하나만
                    )

                    Kretriever = BM25Retriever.from_documents(grad_docs[idx-1][0])
                    Kretriever.k = 3

                    Eretriever = EnsembleRetriever(
                        retrievers = [retriever, Kretriever],
                        weights = [0.8, 0.2]
                    )

                    chosen_doc = Eretriever.invoke(stu_info["입학 년도"])  # 사용자 신입학 연도 가져오기    2020

                    # print("chosen doc: ", chosen_doc[0]) # 여러개가 나옴
                    chosen_text = format_docs(chosen_doc[0])

                    llm_manager.set_llm_type('grad_credits_table')  # 학점 표 이해 gpt
                    chain = llm_manager.get_chain()
                    table_dict = chain.invoke({
                        'major': stu_info['학부/학과'],
                        # 'major': '공과대학 건축학과',

                        'stu_id': f"{stu_info['학번'][:4]}학번",
                        # 'stu_id': f"2025학번",

                        'credits_table': chosen_text})

                    # print("\n표 gpt가 추출한 행: -------------------------------------------------------------------")
                    # print(table_dict)

                    llm_manager.set_llm_type('grad_credits')  # 학점 gpt
                    chain = llm_manager.get_chain()
                    credit_gpt_response = chain.invoke({
                        'major_type': stu_info['전공 타입'],  # stu_info 에 존재하지 않음 (klas어디에 있는지 모르겠음)
                        'major_credits': stu_info['전공 학점'],
                        'liberal_credits': stu_info['교양 학점'],
                        'extra_credits': stu_info['기타 학점'],
                        'tot_credits': stu_info['총 학점'],

                        'credits_dictionary': table_dict})

                    print("학점 gpt 답변:-------------------------------------------------------------------")
                    print(credit_gpt_response)


                # 2. 교양 gpt
                elif idx == 2:
                    # 교양 균형 영역
                    md_manager.set_path(current_dir + 'upload\\Graduation\\LiberalArts\\curriculum_summary.md')
                    curriculum_summary= md_manager.get_dictionary()

                    excluded_subj = {'체육실기', '음악실기', '미술실기'}
                    filtered_courses = {
                        course_name
                        for course_name, credit in stu_info['수강한 과목']
                        if course_name == '광운인되기' or (int(credit) >= 3 and course_name not in excluded_subj)
                    }

                    intersection_summary = {
                        '필수영역': '광운인되기' if '광운인되기' in filtered_courses else None,
                        **{
                            f'균형영역: {section}': list(courses & filtered_courses) or None
                            for section, courses in curriculum_summary.items()
                        }
                    }

                    # print("겹치는 영역: -----")
                    # for key, value in intersection_summary.items():
                    #     print(key, value)

                    retriever = vecs[0].as_retriever(
                        search_type='mmr',
                        search_kwargs={'k': 3, 'lambda_mult': 0.5}  # 하나만
                    )

                    Kretriever = BM25Retriever.from_documents(grad_docs[idx-1][0])
                    Kretriever.k = 3

                    Eretriever = EnsembleRetriever(
                        retrievers = [retriever, Kretriever],
                        weights = [0.8, 0.2]
                    )

                    chosen_doc = Eretriever.invoke(stu_info["입학 년도"])  # 사용자 신입학 연도 가져오기


                    # print("chosen doc: ", chosen_doc)
                    chosen_text = format_docs(chosen_doc[0])

                    llm_manager.set_llm_type('grad_liberalArts_table')  # 교양이수체계 표 이해 gpt-----------------------
                    chain = llm_manager.get_chain()
                    table_dict = chain.invoke({'liberalArts_table': chosen_text})
                    # print("\n표 gpt가 추출한 행: -------------------------------------------------------------------")
                    # print(table_dict)

                    llm_manager.set_llm_type('grad_liberalArts')  # 교양 gpt
                    chain = llm_manager.get_chain()
                    liberalArts_gpt_response = chain.invoke({
                        'table_info': table_dict,
                        'stu_id': f"{stu_info['학번'][:4]}",
                        #'stu_id': f"2025",
                        'intersection_summary': intersection_summary,
                    })

                    print("교양 gpt 답변:-------------------------------------------------------------------")
                    print(liberalArts_gpt_response)


                # 3. 전공 gpt


                # 4. 공학 인증 gpt (기초교양)
                elif idx ==3:   # idx == 4
                    if stu_info['학위 과정'] == '공학 프로그램':
                        # 1. MSI 학점 확인
                        retriever = vecs[0].as_retriever(
                            search_type='mmr',
                            search_kwargs={'k': 3, 'lambda_mult': 0.5}  # 하나만
                        )

                        Kretriever = BM25Retriever.from_documents(grad_docs[idx-1][0])
                        Kretriever.k = 3

                        Eretriever = EnsembleRetriever(
                            retrievers = [retriever, Kretriever],
                            weights = [0.8, 0.2]
                        )

                        chosen_doc = Eretriever.invoke(f'# {stu_info["학부/학과"]}_{stu_info["입학 년도"][:4]}')

                        # print("chosen doc: ", chosen_doc)
                        chosen_text = format_docs(chosen_doc[0])


                        llm_manager.set_llm_type('grad_engineer_msi_table')  # 표 이해 gpt
                        chain = llm_manager.get_chain()
                        table_info = chain.invoke({
                            'msi_table': chosen_text})

                        # print("\n표 gpt가 추출한 행: -------------------------------------------------------------------")
                        # print(table_info)

                        llm_manager.set_llm_type('grad_engineer_msi')  # 표 이해 gpt
                        chain = llm_manager.get_chain()
                        engineer_msi_response = chain.invoke({
                            'msi_info': table_info,
                            'attended_sbj': stu_info['수강한 과목'] })

                        print("\n공학 msi gpt: -------------------------------")
                        print(engineer_msi_response)

                        # 2. 공학필수 과목
                        retriever = vecs[1].as_retriever(
                            search_type='mmr',
                            search_kwargs={'k': 3, 'lambda_mult': 0.5}
                        )

                        Kretriever = BM25Retriever.from_documents(grad_docs[idx-1][1])
                        Kretriever.k = 3

                        Eretriever = EnsembleRetriever(
                            retrievers = [retriever, Kretriever],
                            weights = [0.8, 0.2]
                        )

                        chosen_doc = Eretriever.invoke(stu_info["입학 년도"])
                        # print("chosen doc: ", chosen_doc)
                        chosen_text = format_docs(chosen_doc[0])

                        llm_manager.set_llm_type('grad_engineer_subj_table')  # 표 이해 gpt
                        chain = llm_manager.get_chain()
                        table_info = chain.invoke({
                            'major': stu_info['학부/학과'],
                            #'major': '공과대학 환경공학과',
                            'engineer_table': chosen_text})

                        # print("\n표 gpt가 추출한 행: -------------------------------------------------------------------")
                        # print(table_info)

                        llm_manager.set_llm_type('grad_engineer_subj')  # 공학 필수 과목 gpt
                        chain = llm_manager.get_chain()
                        engineer_subj_response = chain.invoke({
                            'attended_sbj': {course[0] for course in stu_info['수강한 과목']},
                            'required_sbj': table_info})
                        print("\n공학 필수 과목 gpt: -------------------------------")
                        print(engineer_subj_response)


                        ''' 
                        words = '\n\n'.join([engineer_msi_response, engineer_subj_response])
                        llm_manager.set_llm_type('summarize')  # 요약 gpt
                        chain = llm_manager.get_chain()

                        summary = chain.invoke({
                            'words': words})
                        print("\n요약 gpt: -----------------------------------------")
                        print(summary)
                        '''


        case 'Food':
            print("음식 평가 카테고리")

        case 'Course':
            print("강의 카테고리")

        case 'Academic Info':
            print("정보 카테고리")

        case 'None':
            print("카테고리 없음")

    exit(0)


