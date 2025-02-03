from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import requests
from selenium.common.exceptions import StaleElementReferenceException
import re
from selenium.webdriver.chrome.options import Options
import os
from selenium.common.exceptions import TimeoutException


def make_folders():
    # upload 폴더
    upload_path = "upload"
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)

    # upload 폴더 안에 생성할 하위 폴더 리스트
    subfolders = ["Graduation", "Food", "Course", "Academic Info"]  # 카테고리
    for folder in subfolders:
        subfolder_path = os.path.join(upload_path, folder)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)

        if folder == "Graduation":
            graduation_subfolders = ["Credits", "LiberalArts", "Major", "ProgramEngineering"] # 졸업 하위 폴더
            for sub in graduation_subfolders:
                subfolder_path = os.path.join(upload_path, "Graduation", sub)
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path)

def modify_md():
    # upload 된 파일들
    raw_mds = [f for f in os.listdir('upload') if
               f.endswith('.md') and os.path.isfile(os.path.join('upload', f))]

    curriculum_summary = dict()
    for md in raw_mds:
        file_path = os.path.join('upload', md)
        if md == '2025_1_grad_requirement_p19_29.md':
            out_split_1 = []
            out_split_2 = []
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            # 신입학 년도별 split
            admission_years = re.split(r'(?=^# )', markdown_content, flags=re.MULTILINE)
            for admission_year in admission_years:
                lines = admission_year.splitlines()

                topic = lines[0]  # 첫 줄은 큰 주제
                body = "\n".join(line.strip() for line in lines[1:] if line.strip())
                subtopics = re.split(r'(?=^## )', body, flags=re.MULTILINE)  # 소주제 분리
                subtopics = [sub for sub in subtopics if sub.strip()]  # 빈 요소 제거

                years = list(map(int, re.findall(r'\d{4}', topic)))  # 큰 주제의 신입학 해당 년도
                if len(years) > 1:
                    years = list(sorted(range(years[0], years[1] + 1), reverse=True))   # ex) '2020~2023' -> [2020, 2021, 2022, 2023]

                for year in years:
                    topic = f'\n# {year}학년도 신입학자\n'

                    for i, subtopic in enumerate(subtopics, start = 1):
                        if i==1:
                            out_split_1.extend([topic, subtopic, '\n'])
                        elif i==2:
                            out_split_2.extend([topic, subtopic, '\n'])

            # 결과를 파일로 저장
            name_1 = '2025_1_grad_requirement_p19_29_credits.md'
            name_2 = '2025_1_grad_requirement_p19_29_liberal_arts.md'
            with open('upload/Graduation/Credits/' + name_1 , "w", encoding="utf-8") as file1:
                file1.writelines(out_split_1)
            with open('upload/Graduation/LiberalArts/' + name_2, "w", encoding="utf-8") as file2:
                file2.writelines(out_split_2)


        if 'curriculum' in md:
            check = ['과학과기술', '인간과철학','사회와경제','예술과체육','언어와표현','글로벌문화와제2외국어','대학실용영어','수리와자연','융합적사고와글쓰기', '실용영어']
            pattern = re.compile(r'(.+?)(?=\([VL]\d+\))\([VL]\d+\)')

            with open(file_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            lines = markdown_content.splitlines()
            current_key = None

            for line in lines:
                line = line.strip()
                # 테이블 행이 아닌 경우 건너뛰기
                if not line.startswith("|"):
                    continue

                cells = [cell.strip() for cell in line.strip("|").split("|")]

                if cells[0]:
                    current_key = cells[0]

                if current_key not in check:
                    continue

                if current_key not in curriculum_summary:
                    curriculum_summary[current_key] = set()

                for cell in cells[1:]:
                    if cell:
                        subjects = [s.strip() for s in pattern.findall(cell)]
                        for subj in subjects:
                            subj = subj.strip()
                            if '1,2' in subj:
                                curriculum_summary[current_key].add(f'{subj[:-3]}1')
                                curriculum_summary[current_key].add(f'{subj[:-3]}2')
                            elif ',' in subj:
                                curriculum_summary[current_key].add(subj.replace(',',''))
                            else:
                                curriculum_summary[current_key].add(subj)

    # 영역 합치기 및 제거
    curriculum_summary['언어와표현'].update(curriculum_summary['융합적사고와글쓰기'])
    curriculum_summary['대학실용영어'].update(curriculum_summary['실용영어'])
    for key in ['융합적사고와글쓰기', '실용영어']:
        curriculum_summary.pop(key, None)

    # 고려 x: 3,4학점 과목만 인정됨(체육실기,음악실기,미술실기과목은 3학점이더라도 균형교양과목에서 제외)
    for key, value in curriculum_summary.items():
        print(key, value)
    save_to_md('upload/Graduation/LiberalArts/curriculum_summary.md', 'dictionary', curriculum_summary)

def save_to_md(filename, data_type, data):

    # Ensure the directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as file:
        # 강의 평가 저장
        if data_type == "list_in_dictionary":
            for key, value_list in data.items():
                file.write(f"## <'{key}'에 대한 강의 평가>\n")
                if value_list:
                    for value in value_list:
                        file.write(f"- {value}\n")
                else:
                    file.write("- 평가가 없습니다.\n")
                file.write(f"</'{key}'에 대한 강의 평가>\n\n")


        elif data_type == "dictionary":
            for key, value in data.items():
                file.write(f"# {key}\n{value}\n")

        elif data_type == "str_in_list":
            for i in data:
                file.write(i)
                file.write('\n\n')

        elif data_type == "string":
            file.write(data)

        else:
            raise ValueError("지원하지 않는 데이터 타입입니다.")


if __name__ == "__main__":

    make_folders()  # 기본 세팅
    modify_md()




