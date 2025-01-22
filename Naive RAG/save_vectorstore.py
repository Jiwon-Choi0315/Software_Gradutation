from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.utils import DistanceStrategy


'''
split 하나만 하는 경우 split config 없애자~~~~~~~~

'''

# 하나만 빠르게 로드하고 싶을 때
def test_file():
    test_file = "md/grads/major/software/degree.md"
    split_configs = {
        "md/grads/major/software/degree.md": {
            "separators": ["##"],
            "chunk_size": 500,
            "chunk_overlap": 0
        }
    }

    # 문서 로드
    test_doc = {}
    loader = TextLoader(test_file, encoding="utf-8")
    doc = loader.load()

    # split 설정
    config = split_configs.get(test_file)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
        separators=config["separators"]
    )
    splits = splitter.split_documents(doc)

    metadata_ids = ['grads', 'eval', 'food', 'info']  # for big category
    if test_file == 'md/big_category.md':  # big category metadata
        for idx, chunk in enumerate(splits):
            metadata_id = metadata_ids[idx]
            chunk.metadata = {'id': metadata_id}

    if test_file == 'md/grads/major/majors.md':  # majors metadata
        for idx, chunk in enumerate(splits):
            metadata_id = idx
            chunk.metadata = {'id': metadata_id}

    print("splits 길이:", len(splits))
    for s in splits:
        print("--------------------------------------------------------")
        print(s)
        print()


    test_doc[test_file] = splits

    embeddings_model = HuggingFaceEmbeddings(  # 768 차원
        model_name='jhgan/ko-sroberta-nli',
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True},
    )

    # md_files 처음꺼만 vectorstore 저장
    for key, value in test_doc.items():
        vectorstore = FAISS.from_documents(value,
                                           embedding=embeddings_model,
                                           distance_strategy=DistanceStrategy.COSINE)
        # FAISS 벡터 저장소 저장하기
        address = f'./db/{key[3:-3]}'
        vectorstore.save_local(address)



def load_files():
    # Load
    md_files = [
        # 큰 카테고리
        "md/big_category.md",  # 큰 카테고리 (split 4개)

        # 졸업 카테고리 경우
        "md/grads/liberalArts.md",  # 필수, 균형 교양 (split 1개)
        "md/grads/common_curriculum.md",  # 교양 정보 (split 9개)  - 학년 별로 구분
        # "md/grads/personalInfo.md",        # 개인 정보 (split 1개)

        # 졸업 - 전공
        "md/grads/major/majors.md",  # 전공 총 36개 (split 36개)
        "md/grads/major/software/both.md",  # 소프트웨어   - 공통        (split 1개)
        "md/grads/major/software/degree.md",  # - 공학/일반    (split 2개)

        # 강의 평가 카테고리 경우
        "md/eval/lectures_eval.md"  # 강의 평가 (split 608개)    - 강의 별로 구분
    ]
    return md_files

def split_files(md_files):
    # 파일마다 다르게 Split
    split_configs = {
        # 큰 카테고리 -------------------------------------------------------
        "md/big_category.md": {  # 큰 카테고리
            "separators": ["-"],
            "chunk_size": 10,
            "chunk_overlap": 0
        },

        # 졸업 --------------------------------------------------------------
        "md/grads/common_curriculum.md": {  # 교양 정보
            "separators": ["##"],
            "chunk_size": 800,
            "chunk_overlap": 0
        },
        "md/grads/liberalArts.md": {  # 필수,균형 교양
            "separators": ["-"],
            "chunk_size": 2100,
            "chunk_overlap": 0
        },
        "md/grads/personalInfo.md": {  # 개인 정보 (원래는 없어야 함)
            "separators": ["-"],
            "chunk_size": 670,
            "chunk_overlap": 0
        },

        # 졸업 - 전공 ------------------------------------------------------
        "md/grads/major/majors.md": {  # 전공 선택
            "separators": ["\n\n"],
            "chunk_size": 10,
            "chunk_overlap": 0
        },
        "md/grads/major/software/both.md": {  # 소프트웨어학과   - 공통
            "separators": ["\n"],
            "chunk_size": 950,
            "chunk_overlap": 0
        },
        "md/grads/major/software/degree.md": {  # - 공학/일반
            "separators": ["##"],
            "chunk_size": 500,
            "chunk_overlap": 0
        },

        # 수업 평가 ----------------------------------------------------------
        "md/eval/lectures_eval.md": {  # 수업평가
            "separators": ["##", "\n\n"],
            "chunk_size": 500,
            "chunk_overlap": 50
        }
    }
    docs = {}  # 전체 문서
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

        metadata_ids = ['grads', 'eval', 'food', 'info']  # for big category
        if file_path == 'md/big_category.md':  # big category metadata
            for idx, chunk in enumerate(splits):
                metadata_id = metadata_ids[idx]
                chunk.metadata = {'id': metadata_id}
        if file_path == 'md/grads/major/majors.md':  # majors metadata
            for idx, chunk in enumerate(splits):
                metadata_id = idx
                chunk.metadata = {'id': metadata_id}

        print("file: ", file_path, "split: ", len(splits))

        docs[file_path] = splits

    return docs

def embedding_save_files(docs):
    embeddings_model = HuggingFaceEmbeddings(  # 768 차원
        model_name='jhgan/ko-sroberta-nli',
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True},
    )

    # 각 md 파일 마다 vectorstore 만들기
    for key, value in docs.items():
        vectorstore = FAISS.from_documents(value, embedding=embeddings_model, distance_strategy=DistanceStrategy.COSINE)
        # FAISS 벡터 저장소 저장하기
        address = f'./db/{key[3:-3]}'
        vectorstore.save_local(address)


if __name__ == '__main__':

    # test_file()    # 하나만 빠르게 하고 싶을 떄

    md_files = load_files()
    docs = split_files(md_files)
    embedding_save_files(docs)


