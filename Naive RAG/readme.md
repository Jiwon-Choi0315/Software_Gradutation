## Naive RAG 방식 
- Dense Vector만 사용 (추후에 **Hybrid Rag** 로 바뀔 예정)
- 현재 llm 모델은 chatgpt 4o (추후에 deepseek와 비교 예정)


## 간단한 소개
- 광운대학교 학생을 위한 챗봇
- 대답 가능 분야 (졸업, 음식, 강의평가, 학사정보)
- **졸업:** 학생의 klas 아이디와 비번을 입력받아서 크롤링을 통해 개인정보 긁어옴 -> 개인정보를 졸업조건과 비교야하여 충족 여부 알려줌
- **음식:** 학교 주변 음식 추천해줌
- **강의평가:** 에브리타임에 있는 강의평가를 바탕으로 강의 추천 또는 평가 알려줌
- **학사정보:** 글로벌인재트랙인증제 충족 여부 등


## 간단한 코드 설명
- **vectorstore를 저장하기 위해:** 'upload' 폴더생성하여 필요한 md파일 올리기 -> create_md_files.py 실행 -> save_vectorstore.py 실행
- **광운대 챗봇:** kw_chat_bot.py 실행 (단, vectorstore가 존재해야함) 


## 구조



### **create_md_files.py**
- 'upload'폴더에 있는 md 파일을 읽어 카테고리 별로 파일 생성하여 (필요하다면 해당 md 파일을 수정하여) 분류  


### **crawling.py**
- 크롤링 관련 모든 코드들 (현재: **학생 klas 개인정보**, **에타 강의평**)


### **save_vectorstore.py**
- **create_md_files.py**에서 카테고리별 분류한 md파일들을 split하여 FAISS vectorstore에 저장함.
- split 필요없는 것(하나의 chunk)은 FAISS에 저장 안함, 필요시 md파일 부름 


### **kw_chat_bot.py**
- klas 아이디와 비번으로 개인정보를 긁어와 저장되어 있는 vectorstore 의 정보를 통해 사용자의 질문에 대한 답변 생성





