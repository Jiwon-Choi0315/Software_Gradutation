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

''' 
인제니움학부대학? 이건 과없음?!?!?

복전이라면 KLAS 형식 다르게 생길거 같은데 어떻게 생긴지를 알아야함 

'''

# eval 카테고리 ----------------------------------
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
        save_to_md("eval/lectures_eval.md","list_in_dictionary", lectures)

# grads 카테고리 ---------------------------------
def personalInfo(ID, PW):
    # ChromeDriver 경로 설정
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # 창 없이 실행
    driver = webdriver.Chrome(options = chrome_options)

    stu_info = {}   # 개인 정보

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

        # 프로그램 학위과정 (없을 수도 있음) --- 만약 없다면 [1] [2] 이런식으로 하면 안될 거 같아 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!111
        grad_element = info.find_all("table", class_="tablegw")[1].find("tbody").find("td")
        if grad_element:
            grad_process = grad_element.get_text(strip=True)
            stu_info["나의 학위 과정"] = grad_process

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
        save_to_md("grads/personalInfo.md","dictionary", stu_info)


        return [stu_info['나의 입학 년도'], stu_info['나의 학과/학부'], stu_info['나의 학위 과정']]


def liberalArt():
    driver = webdriver.Chrome()
    liberal_arts_info = {}

    try:
        time.sleep(2)
        driver.get("https://account.everytime.kr/login")  # 에브리타임
        ID = "choiyoojong0906"
        PW = "thousand0908"

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
        time.sleep(3)

        focused_area = ['정보영역', '과학과기술', '인간과철학','사회와경제','글로벌문화와제2외국어','예술과체육','수리와자연(수학)','수리와자연(물리)','수리와자연(화학)','수리와자연(생물)']
        idx = 0
        hidden_area = '수리와자연'
        hidden_courses = []
        liberal_num = 1
        while len(focused_area) != 0:   # focused_area 없어질 때까지
            # 전공/영역: 전체 버튼
            course_categories = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span[class='key']"))
            )
            course_categories.click()
            time.sleep(2)

            # 교양 버튼 누르기: 처음만 누르면 됨
            if idx ==0:
                liberalArts_btn = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li[class='parent folded']"))
                )
                liberalArts_btn.click()  # 눌러서 이제 parent unfolded로 됨
                time.sleep(2)


            parent_ul = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul[class='category']"))
            )
            child_elements = parent_ul.find_elements(By.CLASS_NAME, "child")
            current = child_elements[idx]
            area = current.text

            current.click()
            time.sleep(2)

            # 관심 영역인 경우
            if area in focused_area:
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
                # 수업 찾기
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                bold_texts = soup.find_all("td", class_="bold")
                courses = {td.get_text(strip=True) for td in bold_texts}

                if hidden_area in area:     # 수리와 자연인 경우
                    hidden_courses.extend(list(courses))
                    focused_area.remove(area)
                    continue

                part = "필수" if area == "정보영역" else "균형"
                if part =="필수":
                    updated_area = f"필수교양, {area}"             # 정보영역 에서 영역을 빼야하나? ? ? ?!?!?!?
                else:
                    updated_area = f"제{liberal_num} {part}교양, {area}"
                    liberal_num += 1
                liberal_arts_info[updated_area] = list(courses)
                # 담은건 제거
                focused_area.remove(area)

            idx += 1

        updated_hidden_area = f"제{liberal_num} 균형교양, {hidden_area}"       # 수리와자연
        liberal_arts_info[updated_hidden_area] = hidden_courses
        print(liberal_arts_info)

    finally:
        driver.quit()
        save_to_md("grads/liberalArts.md", "dictionary", liberal_arts_info)
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
                block_info = f"## [{year}학년도 신입생만 해당.  {year}교양 정보]:\n{liberal_arts}\n\n[{year}학년도 신입생만 해당. {year}학점 정보]:\n{credits_table}"
                extracted_doc.append(block_info)

    for i in extracted_doc: # to check
        print(i)

    save_to_md("grads/common_curriculum.md", "str_in_list", extracted_doc)

def majors():
    # 크롤링할 URL 설정
    url = "https://www.kw.ac.kr/ko/univ/glance.jsp"
    # 브라우저 User-Agent 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    info = soup.find("div", class_="major-contents-box")

    result_majors = []
    if info:
        colleges = info.find_all("div", class_="college-univ")
        for college in colleges:
            names = [major.get_text(strip=True) for major in college.find_all('li')]
            result_majors.extend(names)

    print(result_majors)
    save_to_md("grads/major/majors.md", "str_in_list", result_majors)



def major_software():
    def major_software_both():
        # 크롤링할 URL 설정
        url = "https://cs.kw.ac.kr/program/requirement.php?admin_mode=read&no=2235&make=&search=&page=1&site_type=3"
        # 브라우저 User-Agent 설정
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        info = soup.find('td', class_='view_td')

        word_info = info.find_all('p')
        if len(word_info) >=6:
            # title
            title = word_info[4].get_text(strip=True)
            print("title", title)
            # body
            body = word_info[5].get_text(strip=True)
            print("body", body)

        # detail (table)
        table_element = info.find("table", class_="MsoNormalTable").find('tbody')

        if table_element:
            rows = table_element.find_all('tr')
            max_cols = sum(int(col.get("colspan", 1)) for col in rows[0].find_all('td')) if rows else 0
            result_table = [[None] * max_cols for _ in range(len(rows))]

            for row_idx, row in enumerate(rows):
                cols = row.find_all('td')
                col_idx = 0

                for col in cols:
                    while col_idx < max_cols and result_table[row_idx][col_idx] is not None:    # 채워져있으면 패스
                        col_idx += 1

                    # 현재 셀 처리
                    '''
                    if col.find('b'):  # <b> 태그가 있는 경우
                        text = " ".join([b.get_text(strip=True) for b in col.find_all('b')])  # 모든 <b> 텍스트 결합
                    else:  # <p> 태그 기준 텍스트 추출
                        text = ", ".join([p.get_text(strip=True) for p in col.find_all('p')])
                    # 텍스트 클린업: (숫자) 패턴 제거
                    text = clean_text(text)
                    '''
                    text = " ".join([b.get_text(strip=True) for b in col])  # 모든 <b> 텍스트 결합
                    text = clean_text(text)

                    colspan = int(col.get("colspan", 1))
                    rowspan = int(col.get("rowspan", 1))

                    # 셀 텍스트를 colspan 및 rowspan 적용
                    for i in range(rowspan):  # rowspan만큼 반복
                        for j in range(colspan):  # colspan만큼 반복
                            result_table[row_idx + i][col_idx + j] = text

                    # colspan만큼 인덱스 이동
                    col_idx += colspan

            for i in result_table:
                print(i)
            print()
            print()

        # md 파일에 저장하자!
        final_info = f"##{title}\n{body}\n{result_table}"
        save_to_md("grads/major/software/both.md", "string", final_info)

    # 공학이랑 일반 한 md에 넣어야함.
    def major_software_degree():
        # 공학
        url = "https://cs.kw.ac.kr/program/requirement.php?admin_mode=read&no=2235&make=&search=&page=1&site_type=3"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, allow_redirects=False)

        soup = BeautifulSoup(response.text, "html.parser")
        table_element = soup.find_all("table", class_="MsoNormalTable")[1].find('tbody')

        if table_element:
            rows = table_element.find_all('tr')
            max_cols = sum(int(col.get("colspan", 1)) for col in rows[0].find_all('td')) if rows else 0
            engineer_table = [[None] * max_cols for _ in range(len(rows))]

            for row_idx, row in enumerate(rows):
                cols = row.find_all('td')
                col_idx = 0

                for col in cols:
                    while col_idx < max_cols and engineer_table[row_idx][col_idx] is not None:  # 채워져있으면 패스
                        col_idx += 1

                    # 현재 셀 처리
                    text = " ".join([b.get_text(strip=True) for b in col])  # 모든 <b> 텍스트 결합
                    #text = clean_text(text)

                    colspan = int(col.get("colspan", 1))
                    rowspan = int(col.get("rowspan", 1))

                    # 셀 텍스트를 colspan 및 rowspan 적용
                    for i in range(rowspan):  # rowspan만큼 반복
                        for j in range(colspan):  # colspan만큼 반복
                            engineer_table[row_idx + i][col_idx + j] = text

                    # colspan만큼 인덱스 이동
                    col_idx += colspan

            print("공학 인증")
            for i in engineer_table:
                print(i)
            print()
            print()

        # 일반
        url = "https://cs.kw.ac.kr/program/requirement.php?admin_mode=read&no=2241&make=&search=&page=1&site_type=3"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        table_element = soup.find_all("table", class_="MsoNormalTable")[1].find('tbody')

        if table_element:
            rows = table_element.find_all('tr')
            max_cols = sum(int(col.get("colspan", 1)) for col in rows[0].find_all('td')) if rows else 0
            general_table = [[None] * max_cols for _ in range(len(rows))]

            for row_idx, row in enumerate(rows):
                cols = row.find_all('td')
                col_idx = 0

                for col in cols:
                    while col_idx < max_cols and general_table[row_idx][col_idx] is not None:  # 채워져있으면 패스
                        col_idx += 1

                    # 현재 셀 처리
                    text = " ".join([b.get_text(strip=True) for b in col])  # 모든 <b> 텍스트 결합
                    # text = clean_text(text)

                    colspan = int(col.get("colspan", 1))
                    rowspan = int(col.get("rowspan", 1))

                    # 셀 텍스트를 colspan 및 rowspan 적용
                    for i in range(rowspan):  # rowspan만큼 반복
                        for j in range(colspan):  # colspan만큼 반복
                            general_table[row_idx + i][col_idx + j] = text

                    # colspan만큼 인덱스 이동
                    col_idx += colspan

            print("일반")
            for i in general_table:
                print(i)
            print()
            print()

            final_info = f"##공학프로그램\n{engineer_table}\n\n##일반프로그램\n{general_table}"
            save_to_md("grads/major/software/degree.md", "string", final_info)

    #major_software_both()
    major_software_degree()




# 기타 함수
def extract_years(related_year):
    '''
    ex) 2020 ~ 2023  -> 2020, 2021, 2022, 2023
    '''

    # 숫자 추출
    years = list(map(int, re.findall(r'\d{4}', related_year)))

    # ~가 있는 경우 연도 범위 생성
    if len(years) == 2:
        return list(range(years[0], years[1] + 1))
    elif len(years) == 1:
        return [years[0]]
    else:
        return []
def save_to_md(filename, data_type, data):
    filename = "md/" + filename  # 파일 경로에 'md/' 추가

    # Ensure the directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
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
                file.write('\n\n')

        elif data_type == "string":
            file.write(data)

        else:
            raise ValueError("지원하지 않는 데이터 타입입니다.")

def clean_text(text):
    # (숫자 ~~~ ) 패턴 제거
    text = re.sub(r'\(\d+.*?\)', '', text)
    # '/' 뒤에 숫자가 오고 다음 숫자가 나올 때까지만 제거
    text = re.sub(r'/\d+(-\d+)?', '', text)
    return text.strip()



if __name__ == "__main__":

    # eval -------------
    lectureEval()                               # 강의 평가

    # grads ------------
    #personalInfo("","")                        # 학생 정보 (공학 인증 다시 크롤링)
    #common_curriculum()                        # 교양 안내
    #liberalArt()                               # 필수/균형 교양

    # grads/major
    #majors()                  # 인제니움학부대학? 이건 과없음?!?!?
    #major_software()                            # 전공 -소프트웨어학과

