## Naive RAG 방식 
- Dense Vector만 사용


## 바뀐점
- gpt가 답하고 그 답이 gpt한테 넘어감
- **학생 개인정보**를 vectorstore로 저장 하지 않고, 긁으면 바로 사용 가능 하도록 바꿈
- split하지 않아도 되는 vector라면 (즉, 하나 vectorstore에서 전체 vectorstore를 가져오는 경우) vectorstore로 저장하지 않음. 바로 md를 가져옴. 즉, 로드 및 비교하는 불필요한 과정이 없어짐.
- 한번에 vectorstore를 로드하지 않고 질문이 카테고리에 처음 들어갔을 때 해당 카테고리와 관련된 vectorstore들만 로드함.  


## 코드 설명
- **실행 순서:** upload 폴더생성 -> 폴더 안에 필요한 md파일 올리기 -> create_md_files.py -> save_vectorstore.py -> kw_chat_bot.py 

- **create_md_files.py**


'upload'폴더에 있는 md 파일을 읽어 카테고리 별로 (필요하다면 해당 md 파일을 수정하여) 분류한다.  


'upload'폴더에 필요한 md파일: (2025 1학기 전체 수강신청 자료집의 부분들, 2021 1,2학기 ~ 2025 1학기까지의 교양 균형 영역들 표시된 과목들) 


- **crawling.py**


크롤링 관련 모든 코드들 (현재: **학생 개인정보**, **에타 강의평**)


- **save_vectorstore.py**


**create_md_files.py**에서 카테고리별 분류한 md파일들을 vectorstore로 저장함. 


- **kw_chat_bot.py**


개인정보를 긁어오는데 아이디 비번 입력해야함, 챗봇


## 구조


질문 -> **카테고리 gpt** (졸업, 음식, 강의평가, 학사정보)


### **졸업 카테고리**


번호 순으로 진행, 각 번호들에 대한 답변은 **요약 gpt**로 들어가 최종 답변 할 것임.


1. 학점
- **표 이해 gpt** -> **학점 gpt** -> 학점관련 답변


2. 교양
- **표 이해 gpt** -> **교양 gpt** -> 교양 (필수,균형) 관련 답변


3. 전공
- 아직 안함


4. 공학인증
- 진행 중

__
학점, 교양, 전공, 공학 답변 -> **요약 gpt** -> 최종 답변

### **음식 카테고리**

