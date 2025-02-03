from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.utils import DistanceStrategy

import re
import os

# 하나만 빠르게 save하고 싶을 때
def test_file():
    split_configs = {
        # Graduation
        '2025_1_grad_requirement_p19_29_credits.md': {
            "separators": ['\n# '],
            "chunk_size": 500,
            "chunk_overlap": 0
        },
        '2025_1_grad_requirement_p19_29_liberal_arts.md': {
            "separators": ['\n# '],
            "chunk_size": 500,
            "chunk_overlap": 0
        }
    }
    default_config = {
        "separators": [],  # No separators
        "chunk_size": None,  # Entire document
        "chunk_overlap": 0  # No overlap
    }

    test_file = "upload\\Graduation\\2025_1_grad_requirement_p19_29_credits.md"

    # 문서 로드
    test_doc = {}
    loader = TextLoader(test_file, encoding="utf-8")
    doc = loader.load()


    # split 설정
    config = split_configs.get(test_file.split('\\')[-1], default_config)
    if config["separators"] or config["chunk_size"] is not None:  # split 하는 경우
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            separators=config["separators"]
        )
        splits = splitter.split_documents(doc)



        if test_file == 'md/grads/major/majors.md':  # majors metadata
            for idx, chunk in enumerate(splits):
                metadata_id = idx
                chunk.metadata = {'id': metadata_id}

    else:
        splits = doc

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
        # FAISS 벡터 저장소 저장하기
        address = f'db\\{key[7:-3]}'
        vectorstore = FAISS.from_documents(value, embedding=embeddings_model, distance_strategy=DistanceStrategy.COSINE)
        vectorstore.save_local(address)



def find_md_files():

    md_files = []
    for root, dirs, files in os.walk('upload'):
        if root == 'upload':  # 최상위 'upload' 폴더는 건너뜀
            continue
        for file_name in files:
            if file_name.endswith('.md'):
                md_files.append(os.path.join(root, file_name))
    print("찾은 md 파일들:", md_files)

    return md_files



def split_files(md_files):
    # 파일마다 다르게 Split
    split_configs = {
        # Graduation
        '2025_1_grad_requirement_p19_29_credits.md': {
            "separators": ['\n# '],
            "chunk_size": 500,
            "chunk_overlap": 0
        },
        '2025_1_grad_requirement_p19_29_liberal_arts.md': {
            "separators": ['\n# '],
            "chunk_size": 500,
            "chunk_overlap": 0
        }
    }
    default_config = {
        "separators": [],  # No separators
        "chunk_size": None,  # Entire document
        "chunk_overlap": 0  # No overlap
    }

    docs = {}  # 전체 문서
    for file in md_files:
        # 문서 로드
        loader = TextLoader(file, encoding="utf-8")
        doc = loader.load()

        # split 설정
        config = split_configs.get(file.split('\\')[-1], default_config)

        if config["separators"] or config["chunk_size"] is not None:    # split 하는 경우
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=config["chunk_size"],
                chunk_overlap=config["chunk_overlap"],
                separators=config["separators"]
            )
            splits = splitter.split_documents(doc)

            '''
            # split 출력 
            if file.split('\\')[-1] == '2025_1_grad_requirement_p19_29_credits.md':
                print("splits len: ", len(splits))
                for idx, split in enumerate(splits):
                    print(idx + 1,"번째: ", split)
                    print()
    
                exit(0)
            '''

            # metadata 추가하고 싶다면
            if file == '':  # majors metadata
                for idx, chunk in enumerate(splits):
                    metadata_id = idx
                    chunk.metadata = {'id': metadata_id}

        else:
            splits = doc

        print("file: ", file, "split: ", len(splits))
        docs[file] = splits

    return docs

def embedding_save_files(docs):
    embeddings_model = HuggingFaceEmbeddings(  # 768 차원
        model_name='jhgan/ko-sroberta-nli',
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True},
    )
    # 각 md 파일 마다 vectorstore 만들기
    for key, value in docs.items():
        # FAISS 벡터 저장소 저장하기
        address = f'db\\{key[7:-3]}'
        vectorstore = FAISS.from_documents(value, embedding=embeddings_model, distance_strategy=DistanceStrategy.COSINE)
        vectorstore.save_local(address)


if __name__ == '__main__':

    #test_file()    # 하나만 빠르게 하고 싶을 떄


    md_files = find_md_files()  # md파일 찾기

    docs = split_files(md_files)
    embedding_save_files(docs)

