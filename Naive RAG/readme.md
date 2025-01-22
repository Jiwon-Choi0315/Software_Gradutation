## Naive RAG 방식 
- Dense Vector만 사용

## 순서

- 1. crawling.py

광운대 정보 크롤링하여 md파일에 저장 

- 2. save_vectorstore.py

저장된 md파일 임베딩 후, 저장

- 3. test.py

임베딩된 vectorstore + (klas 개인정보 크롤링 통해 가져온 데이터) 를 가지고 챗봇 답변 제공 


