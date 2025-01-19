## Naive RAG 방식 
- Dense Vector만 사용

## 순서
- 1. crawling.py

학교 정보 크롤링하여 md파일에 저장 (현재: 에타 강의평가.md, 학교 교양 정보.md) 

- 2. save_vectorstore.py

저장된 md파일 불러와서 임베딩하여 vectorstore에 저장

- 3. test.py

임베딩된 vectorstore + (klas 개인정보 크롤링 통해 가져온 데이터) 를 가지고 챗봇 답변 제공 
    
## 지금 다루고 있는 정보들: 3개

- 학교 교양 정보(common_curriculum.md), 
- 에타 강의 평가(lectures_eval.md), 
- klas 개인정보 (personalInfo.md)    (test.py에서 자동 가져옴)


