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


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_y] = root_x  # Merge y's root into x's root


# 예전 과목 이름 추가
def update_dictionary(dictionary, synonym_mapping):
    for key, name_set in dictionary.items():
        for name in list(name_set):
            if name in synonym_mapping:
                name_set.update(synonym_mapping[name])
    return dictionary





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

    curriculum_summary = dict() # 2025_1 학기 균형 영역
    synonym_mapping = dict()    # 동의어 이름이 속한 동의어 집합을 매핑하는 사전 생성


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

        if md == '2025_1_grad_curriculum_p101_103.md':
            check = ['과학과기술', '인간과철학','사회와경제','예술과체육','언어와표현','글로벌문화와제2외국어','대학실용영어','수리와자연']
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


        if md == '2025_1_grad_course_name_history.md':
            uf = UnionFind()
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    # Check if the line starts with | followed by a digit (to skip headers and separators)
                    if not line.startswith('|') or len(line) < 2 or not line[1].isdigit():
                        continue
                    parts = line.split('|')
                    # Extract 과목명(A) and 기수강 과목명(B), which are in the 2nd and 4th columns respectively
                    if len(parts) < 5:
                        continue
                    subject_a = parts[2].strip()
                    subject_b = parts[4].strip()
                    if subject_a and subject_b:  # Ensure both are non-empty
                        uf.union(subject_a, subject_b)

            # Group all subjects by their root parent
            groups = {}
            for subject in uf.parent.keys():
                root = uf.find(subject)
                if root not in groups:
                    groups[root] = set()
                groups[root].add(subject)


            for syn_set in list(groups.values()):
                for syn in syn_set:
                    synonym_mapping[syn] = syn_set

        if md == '2025_1_grad_engineer_subj_p45_49.md':
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            result = dict()
            lines = markdown_content.splitlines()

            body = ''
            for line in lines:
                line = line.strip()
                # 테이블 행이 아닌 경우 건너뛰기
                if not line.startswith("|"):
                    continue

                cells = [cell.strip() for cell in line.strip("|").split("|")]
                match = re.search(r'\((\d{4})', cells[0])

                if match:
                    if body:
                        result[key_year] = body
                    key_year = int(match.group(1))
                    body = ''

                if len(line.strip('|').split('|')) !=5:
                    continue

                body += line
                body += '\n'

            result[key_year] = body # 마지막


            # 없는 연도 추가
            for current_year in range(min(result.keys()), max(result.keys())+1):
                if current_year in result.keys():
                    key_year = current_year
                else:
                    result[current_year] = result[key_year]

            # key 이름 수정
            for old_key, value in sorted(result.items()):
                new_key = f'{old_key}학년도 신입학자 (공학 필수과목)'
                result[new_key] = result.pop(old_key)



            save_to_md('upload/Graduation/ProgramEngineering/2025_1_grad_engineer_subj_p45_49.md', 'dictionary', result)
        if md == '2025_1_grad_engineer_msi_p50_73.md':
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            md_dict = {}
            current_department = None
            current_year = None
            current_content = []

            # 연도 패턴 정규표현식 (예: |2025 학년도...)
            year_pattern = re.compile(r'^\|\s*(\d{4})\s*학년도')

            for line in markdown_content.split('\n'):
                stripped_line = line.strip()

                # 학과 헤더 감지
                if line.startswith('# '):
                    if current_department and current_year:
                        md_dict[f"{current_department}_{current_year}"] = '\n'.join(current_content)
                        current_content = []
                    current_department = line[2:].strip()
                    current_year = None

                # 연도 헤더 감지
                elif year_pattern.match(stripped_line):
                    if current_department is None:
                        continue  # 학과 없이 연도가 나오는 경우 무시

                    year_match = year_pattern.search(stripped_line)
                    year = year_match.group(1)

                    if current_year:
                        md_dict[f"{current_department}_{current_year}"] = '\n'.join(current_content)
                        current_content = []

                    current_year = year
                    current_content.append(line.rstrip())

                # 일반 라인 처리
                else:
                    if current_department and current_year:
                        current_content.append(line.rstrip())

            # 마지막으로 처리 중이던 내용 저장
            if current_department and current_year:
                md_dict[f"{current_department}_{current_year}"] = '\n'.join(current_content)


            # 필요없는 부분 버리기
            for key, value in md_dict.items():
                key_year = int(key.split('_')[1])
                lines = value.split('\n')
                tot_values = ''
                for line in lines:
                    cells = [cell.strip() for cell in line.strip('|').split('|')]
                    if len(cells)>1 and key_year >= 2024:
                        cells = cells[:5]
                    elif len(cells) >1:
                        cells = cells[:4]
                    else:
                        continue

                    for idx, cell in enumerate(cells):  # 1,2 과목 나누기
                        if '1,2' in cell:
                            sub_1 = cell.replace('1,2', '1')
                            sub_2 = cell.replace('1,2', '2')
                            cells[idx] = f'{sub_1}, {sub_2}'

                    current_values = "|" + "|".join(cells) + "|\n"
                    tot_values += current_values
                md_dict[key] = tot_values

            # 없는 연도 채우기
            majors = set()
            for key in md_dict.keys():
                major, _ = key.rsplit('_', 1)
                majors.add(major)

            for major in majors:
                for year in range(2016, 2025 + 1):
                    key_current = f"{major}_{year}"
                    if key_current not in md_dict:
                        # 현재 연도보다 작거나 같은 연도 중 가장 가까운(큰) 연도를 찾음.
                        for y in range(year, 2015, -1):  # year부터 2016까지 역순으로 검색
                            key_candidate = f"{major}_{y}"
                            if key_candidate in md_dict:
                                md_dict[key_current] = md_dict[key_candidate]
                                break

            save_to_md('upload/Graduation/ProgramEngineering/2025_1_grad_engineer_msi_p50_73.md', 'dictionary', md_dict)

        if md == '2025_1_grad_majors.md':
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()
            with open('upload/Graduation/Major/' + md, "w", encoding="utf-8") as file:
                file.write(markdown_content)

    curriculum_summary = update_dictionary(curriculum_summary, synonym_mapping) # kw_chat_bot.py에서 고려: 3,4학점 과목만 인정됨(체육실기,음악실기,미술실기과목은 3학점이더라도 균형교양과목에서 제외)
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

        elif data_type == 'list':
            for i in data:
                file.write(f'{i}\n')

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




