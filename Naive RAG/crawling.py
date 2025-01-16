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
'''
아직 안한 것들 
1. (개인정보)  세부 전공, 복전인지 아닌지  -- 어디있는지 모르겠음  

2. (에타- 강의평가)  돌려야함

3. (에타) -- 필수교양, 균형교양, 정보, 등이 뭔지  -- 이거는 새로 긁어와야할 듯 

-------
(졸업 교양 조건) 완료

'''
def lectureEval():
    '''
    1. 모든 강의 이름 찾기
    2. 각 강의 평가 긁어오기
    '''

    # ChromeDriver 경로 설정
    driver = webdriver.Chrome()
    try:
        driver.get("https://account.everytime.kr/login")            # 에브리타임
        ID = ""
        PW = ""

        # 로그인
        id_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='id']"))
        )
        pw_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
        )
        id_field.send_keys(ID)
        pw_field.send_keys(PW)
        time.sleep(4)
        pw_field.send_keys(Keys.RETURN)
        time.sleep(4)
        # 시간표로 이동
        timetable_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href='/timetable']"))
        )
        timetable_btn.click()

        # 학기 선택
        dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "select[id='semesters']"))
        )
        dropdown.click()
        semester = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='semesters']/option[6]"))  # 24년 2학기
        )
        semester.click()

        # 수업 목록 검색
        course_list_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li[class='button search']"))
        )
        course_list_btn.click()

        # 수업 목록 부분 스크롤 다운
        scroll_container = driver.find_element(By.CSS_SELECTOR, "div#subjects div.list")
        last_height = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
        while True:
            # 스크롤 내리기
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
            time.sleep(2)  # 스크롤 후 로딩 대기
            # 새로운 높이 확인
            new_height = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
            if new_height == last_height:  # 스크롤이 끝에 도달했으면 종료
                break
            last_height = new_height

            break # to stop early

        # 모든 수업 찾기
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        bold_texts = soup.find_all("td", class_="bold")
        lectures = {td.get_text(strip=True): [] for td in bold_texts}

        # 강의실로 이동
        lecture_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href='/lecture']"))
        )
        lecture_btn.click()

        # 강의평가 크롤링
        count = 0   # to check
        for lecture in lectures.keys():
            count += 1
            print(count,"/",len(lectures.keys()), "지금 찾는 강의: ", lecture)    # to check

            search_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search']"))
            )

            for i in range(5):      # 비워지지 않았는데 바로 써지는 경우 방지
                search_btn.clear()
                time.sleep(0.2)

            search_btn.send_keys(lecture)   # 입력
            search_btn.send_keys(Keys.RETURN)
            time.sleep(1)

            # 교수님만 다른 같은 강의들
            same_courses = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.lectures a span.highlight"))
            )
            for i in range(len(same_courses)):
                try:
                    # DOM 무효화 방지
                    same_courses = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.lectures a div.name"))
                    )
                    element = same_courses[i]
                    element_txt = element.text

                    # 강의 이름이 다를 시, 무시 (강의 이름 포함될 시 고려)
                    if lecture != element_txt:
                        continue

                    element.click()
                    time.sleep(1)

                    # 페이지 파싱
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")

                    # 교수명, 평점, 평가 추출
                    professor_section = soup.find("section", class_="info")
                    professor_name = "미정 / 미정(전임)"
                    if professor_section:
                        professor_elements = professor_section.find_all("div", class_="item")
                        if len(professor_elements) >= 2:
                            professor_span = professor_elements[1].find("span")
                            if professor_span:
                                professor_name = professor_span.get_text(strip=True)
                    rate = "미평가"
                    review_section = soup.find("section", class_="review")
                    if review_section:
                        rating_div = review_section.find("div", class_="rating")
                        if rating_div:
                            title_div = rating_div.find("div", class_="title")
                            if title_div:
                                rate_span = title_div.find("span", class_="average")
                                if rate_span:
                                    rate = rate_span.get_text(strip=True)
                    details = soup.select("div.text")
                    details = [span.get_text(strip=True).replace('\n', ' ') for span in
                               details] if details else "미평가"

                    # 정보 하나라도 없을 시, 담지 않음
                    if not (professor_name == '미정 / 미정(전임)' or professor_name == '미정(전임)' or professor_name == '강사(미정)'or professor_name == '미정' or rate == '미평가' or details == '미평가'):
                        evaluation = "".join(f"교수명: {professor_name}; 평점: {rate} / 5.00; 평가: {details}")
                        print(evaluation)  # to check
                        lectures[lecture].append(evaluation)

                    driver.back()  # 뒤로 가기
                    time.sleep(1)

                except StaleElementReferenceException:  # 요소 무효화 시 다시 시도
                    print("StaleElementReferenceException 발생, 재시도")
                    continue

            driver.refresh()  # 성공적으로 처리


    finally:
        # 브라우저 닫기
        driver.quit()
        save_to_md("lectures_eval.md","list_in_dictionary", lectures)


def personalInfo(ID, PW):
    # ChromeDriver 경로 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 창 없이 실행
    driver = webdriver.Chrome(options = chrome_options)

    stu_info = {}   # 개인 정보
    stu_yr = None   # 추가적으로 저장할 정보
    try:
        driver.get("https://klas.kw.ac.kr/")  # 광운대학교

        # 로그인
        id_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[id='loginId']"))
        )
        pw_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[id='loginPwd']"))
        )
        id_field.send_keys(ID)
        pw_field.send_keys(PW)
        pw_field.send_keys(Keys.RETURN)
        time.sleep(3)

        # KLAS 수강 / 성적조회 사이트
        driver.get("https://klas.kw.ac.kr/std/cps/inqire/AtnlcScreStdPage.do")
        time.sleep(1)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        info = soup.find("div", class_="tablelistbox")

        # 학생 정보 - 나에 대한 정보 추가하자
        stu_categories = ["나의 학과/학부", "내 학번", "내 이름", "나의 학적상황"]
        stu_elements = info.find("table", class_="tablegw").find("tbody").find("tr").find_all("td")
        for i, stu_element in enumerate(stu_elements[1:5]):

            value = stu_element.get_text(strip=True)
            if stu_categories[i] == "내 학번":
                stu_yr = value[:4]  # 2020
                stu_info["나의 입학 년도"] = f"{stu_yr}년도 신입생"
            stu_info[stu_categories[i]] = value

        # 취득 학점
        cre_categories = ["나의 전공 학점", "나의 교양 학점", "나의 기타 학점", "나의 총 학점"]
        credit_element = info.find_all("table", class_="tablegw")[2].find("tbody").find_all("td")
        for i, credit in enumerate (credit_element[8:12]):
            value = credit.get_text(strip=True).split('(')[0]
            stu_info[cre_categories[i]] = value

        # 수강한 과목들
        courses_taken = set()
        semesters = info.find_all("table", class_="AType")
        for semester in semesters:
            semester = semester.find("tbody")
            courses = semester.find_all("tr")
            for course in courses:
                course = course.find_all('td')
                course = course[1].get_text(strip=True)
                courses_taken.add(course)
        stu_info["내가 수강한 과목"] = courses_taken
        print(stu_info)

    finally:
        # 브라우저 닫기
        driver.quit()
        save_to_md("personalInfo.md","dictionary", stu_info)
        return stu_yr


def extract_years(related_year):
    # 숫자 추출
    years = list(map(int, re.findall(r'\d{4}', related_year)))

    # ~가 있는 경우 연도 범위 생성
    if len(years) == 2:
        return list(range(years[0], years[1] + 1))
    elif len(years) == 1:
        return [years[0]]
    else:
        return []

def common_curriculum():
    # 크롤링할 URL 설정
    url = "https://www.kw.ac.kr/ko/life/bachelor_info07.jsp"

    # 브라우저 User-Agent 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    major_content = soup.find("div", class_="major-contents-box")
    sections = major_content.find_all("section", class_="h3_contents-block")
    if len(sections) >= 2:
        target_section = sections[1]
        content_blocks = target_section.find_all("div", class_="contents-block-in")

        # 2016학년도 신입생부터 ~ 2024
        selected_blocks = content_blocks[7:]
        extracted_doc = []
        for block in selected_blocks:
            block_year = block.find("p", class_="square")

            # 해당 년도
            related_years = []
            if block_year:
                related_year = block_year.get_text(strip=True)
                related_years = extract_years(related_year)
                print(related_years)


            # 교양 설명
            for inner_div in block.find_all("div"):
                if inner_div.get("style") != "margin-top:1em;" and "table-scroll-box" not in inner_div.get("class", []):
                    p_tag = inner_div.find("p")
                    if p_tag:
                        for br in p_tag.find_all("br"):
                            br.replace_with("\n")
                        text = p_tag.get_text(separator=" ", strip=False)
                        text = re.sub(r"(\xa0\s*){2,}", "- ", text)  # 2개 이상 NBSP → 하나의 '-'
                        lines = text.split('\n')

                        # 리스트 요소를 다시 '\n'을 추가하면서 하나의 문자열로 결합
                        formatted_lines = []
                        first_line = True  # 첫 번째 줄인지 확인하는 플래그

                        for line in lines:
                            line = line.strip()
                            if line:
                                if not first_line and "-" not in line:
                                    formatted_lines.append("")  # 빈 줄 추가 (줄바꿈)

                                formatted_lines.append(line)
                                first_line = False  # 첫 번째 줄 체크 완료

                        # 최종 문자열 생성
                        formatted_text = "\n".join(formatted_lines)
                        liberal_arts = formatted_text.strip()

            # 학점 테이블
            tables = block.find_all("div", class_=lambda x: x and "table-scroll-box" in x)
            if len(tables) >= 2:
                selected_table = tables[1]
                credits_table = []    # 최종 학점 테이블 2차원 배열로

                thead = selected_table.find("thead")    # 테이블의 첫 줄
                if thead:
                    header_row = []  # 최종 헤더
                    first_row_values = []  # 첫 번째 tr의 텍스트 값 저장
                    rowspans = []
                    trs = thead.find_all("tr")
                    # 첫 번째 tr 처리
                    for th in trs[0].find_all("th"):
                        colspan = int(th.get("colspan", 1))
                        rowspan = int(th.get("rowspan", 1))
                        first_row_values.extend([th.get_text(strip=True)] * colspan)
                        rowspans.extend([rowspan] * colspan)

                    # 만약 두 번째 tr이 존재하면 처리
                    if len(trs) > 1:
                        second_row_values = []
                        for th in trs[1].find_all("th"):
                            colspan = int(th.get("colspan", 1))
                            second_row_values.extend([th.get_text(strip=True)] * colspan)

                        # rowspans를 기반으로 header_row 채우기
                        for i, rowspan in enumerate(rowspans):
                            if rowspan == 2:
                                # 첫 번째 tr의 값 사용
                                header_row.append(first_row_values[i])
                            elif rowspan == 1:
                                # 두 번째 tr의 값 사용
                                header_row.append(second_row_values.pop(0))
                    else:
                        header_row = first_row_values
                credits_table.append(header_row)
                cols_num = len(header_row)

                tbody = selected_table.find("tbody")    # 테이블의 내용
                if tbody:
                    rows = tbody.find_all("tr")
                    rows_num = len(rows)
                    body_table = [[-1] * cols_num for _ in range(rows_num)]

                    for row_idx, row in enumerate(rows):
                        col_idx = 0  # 현재 열 위치
                        for cell in row.find_all("td"):
                            # 이미 채워진 칸이면 다음 빈 칸으로 이동
                            while col_idx < cols_num and body_table[row_idx][col_idx] != -1:
                                col_idx += 1

                            cell_text = cell.get_text(strip=True)
                            colspan = int(cell.get("colspan", 1))
                            rowspan = int(cell.get("rowspan", 1))

                            for i in range(rowspan):
                                for j in range(colspan):
                                    body_table[row_idx + i][col_idx + j] = cell_text

                    credits_table.extend(body_table)

            for year in related_years:
                block_info = f"## {year}학년도 신입생만 해당. 졸업하기 위한 교양 정보:\n{liberal_arts}\n\n## {year}학년도 신입생만 해당. 졸업하기 위한 학점 정보:\n{credits_table}\n\n"
                extracted_doc.append(block_info)

    for i in extracted_doc: # to check
        print(i)

    save_to_md("common_curriculum.md", "str_in_list", extracted_doc)


def save_to_md(filename, data_type, data):
    with open(filename, "w", encoding="utf-8") as file:
        # 강의 평가 저장
        if data_type == "list_in_dictionary":
            for key, value_list in data.items():
                file.write(f"## '{key}'에 대한 강의 평가:\n")
                if value_list:
                    for value in value_list:
                        file.write(f"- {value}\n")
                else:
                    file.write("- 평가가 없습니다.")
                file.write("\n")

        elif data_type == "dictionary":
            for key, value in data.items():
                file.write(f"- {key}: {value}\n")

        elif data_type == "str_in_list":
            for i in data:
                file.write(i)

        else:
            raise ValueError("지원하지 않는 데이터 타입입니다.")



def test_log_in():
    # 세션 유지
    session = requests.Session()

    # Network 탭에서 찾은 실제 로그인 URL
    login_url = "https://klas.kw.ac.kr/usr/cmn/login/LoginConfirm.do"

    # 로그인 정보 (Network 탭에서 확인)
    login_data = {
        "username": "2020203068",
        "password": "yoojong20!"
    }

    # Headers에서 찾은 Referer 값 추가
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://klas.kw.ac.kr/usr/cmn/login/LoginForm.do"  # 로그인 페이지 URL
    }

    # 로그인 요청
    response = session.post(login_url, data=login_data, headers=headers)


    if response.text:
        print("로그인 성공!")

        # 로그인 후 크롤링할 페이지
        target_url = "https://example.com/dashboard"
        response = session.get(target_url)


if __name__ == "__main__":
    
    lectureEval()    # 강의 평가
    #personalInfo("","") # 학생 정보
    #common_curriculum()
    
    #test_log_in() -- personalInfo 를 더 빨리 가져오도록 시도

