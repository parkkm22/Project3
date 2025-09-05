import streamlit as st
import re
import requests
import json
import pandas as pd
import google.generativeai as genai

# 페이지 설정
st.set_page_config(
    page_title="AI 공사관리 에이전트",
    page_icon="✨",
)

# --- CONSTANTS & API SETUP ---
# Gemini API 설정
GENAI_API_KEY = "AIzaSyAdLLTvgfKadJCsYgUX0ZeuCCboS8aOVSQ"
try:
    genai.configure(api_key=GENAI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel("models/gemini-2.5-flash-preview-05-20")
    AI_AVAILABLE = True
except Exception as e:
    st.error(f"❌ Gemini AI 초기화 실패: {str(e)}")
    AI_AVAILABLE = False

# --- SESSION STATE ---
def initialize_report_session_state():
    """페이지 1의 세션 상태를 초기화합니다."""
    if 'PROMPT_PAGE1' not in st.session_state:
        st.session_state.PROMPT_PAGE1 = """
# INSTRUCTION
1. `USER TEXT`에 입력된 여러 작업 계획을 취합하여, 아래 규칙에 따라 **하나의 보고서 본문(MAIN SET)**을 마크다운 코드블럭으로 생성하세요.
2. **자동 검증 결과(QA-CHECKLIST)**를 마크다운 표(Table)로 생성합니다.

# OUTPUT 
## 1. MAIN SET (보고서 본문)
1.  보고서 통합 및 헤더
-   `USER TEXT 1~3`을 하나의 보고서로 통합합니다. (보고서 내 `1)`, `(1)`과 같은 계층 구조는 원문 그대로 유지)
-   본문 첫 줄에는 `"신안산선 4-1공구(포스코이앤씨)"`를, 다음 줄에는 원문에서 가장 빠른 날짜를 `####년 ##월 ##일(#) 작업계획보고` 형식으로 표기합니다.

2.  본문 정렬 및 서식
-   작업 위치 정렬 : 아래 지정된 순서로 본문을 재정렬합니다.
     `1. 본선터널(1구간)` → `2. 신풍정거장` → `3. 신풍정거장 환승통로` → `4. 본선터널(2구간)` → `5. 도림사거리정거장`

-   **'없음' 항목 처리:** `0명` 또는 `-명`으로 표기된 인원, `0대` 또는 `-대`로 표기된 장비는 해당 줄을 삭제합니다. 특정 위치에 남은 인원이나 장비가 전혀 없으면 각각 `"인원 : 없음"`, `"장비 : 없음"`으로 표기합니다.
- "지정된 5개의 작업 위치는 USER TEXT에 내용이 없더라도 보고서에 항상 포함되어야 한다. 만약 특정 위치의 작업 내용이 없다면, 해당 위치의 제목 아래에 '작업 없음'이라고 표기한다."

3.  인원/장비 표준화 및 집계
-   인원:
    -   순서: `직영반장 → 목공 → 철근공 → 연수생 → 신호수 → 그 외` 순서로 정렬하고 `/`로 구분합니다.
    -   합산: `직영`, `철근연수생`, `목공연수생` 등은 `연수생`으로 합산합니다.
-   장비:
    -   표준화: 아래 `매핑 딕셔너리`를 적용하여 장비명을 표준화하고 `/`로 구분합니다. (띄어쓰기, 대소문자, 오타 등은 유연하게 판단)
-   **총계:**
    -   보고서 하단에 `■ 총 인원`, `■ 총 장비`를 계산하여 표기합니다.
    -   **(중요)** `직영반장`은 총 인원 합산에서 제외합니다.

4.  매핑 딕셔너리 (상세)
-   인원: `목수`→`목공`, `카리프트`→`카리프트공`, `기계타설공`→`타설공`, `가시설`→`가시설공`
-   장비: `B/H08LC`→`B/H(08LC)`, `백호06LC`→`B/H(06LC)`, `25톤 카고크레인`→`카고크레인(25T)`, `5톤트럭`→`화물차(5T)`

5.  안전관리 중점 POINT
-   모든 `USER TEXT`의 안전관리 내용을 취합하여 보고서 맨 하단에 **한 번만** 작성합니다.
-   `추락, 협착, 낙하, 질식, 폭발` 5대 재해 키워드 관련 내용을 우선 추출하고, 중복을 제거하여 최대 10개까지만 나열합니다.

6. 예시

```
    신안산선 4-1공구(포스코이앤씨)
    2025년 06월 27일(금) 작업계획보고
 

    1. 본선터널(1구간)
    ■ 작업내용
    ...
    ■ 시공현황(누계/설계)
    ...
    ■ 투입현황 (주간)
    - 인원 : 목공 10명 / 철근공 8명 / 신호수 2명
    - 장비 : B/H(06LC) 1대 / 카고크레인(25T) 1대
 
    2. 신풍정거장
    1) 정거장 터널
    ■ 작업내용
    ...
    ■ 시공현황(누계/설계)
    ...
    ■ 투입현황 (주간)
    - 인원 : ...
    - 장비 : ...

    2) 주출입구 연결터널
    (1) PCB
    ■ 작업내용
    ...
    ■ 시공현황(누계/설계)
    ...
    ■ 투입현황 (주간)
    - 인원 : ...
    - 장비 : ...

    ... (보고서 본문 계속) ...

    ■ 총 인원 : 213명
    ■ 총 장비 : 29대

    ※ 안전관리 중점 POINT
    1. 추락 위험구간 안전 난간대 설치 및 확인 철저
    2. ... (최대 10개까지 나열)

```
---

## 2. QA-CHECKLIST (자동 검증 결과)
1.  **검증 항목:** 아래 기준에 따라 처리 과정의 정확성을 자체 검증합니다.
    -   **구조:** `MAIN SET`, `QA-CHECKLIST` 2개 코드블럭으로 출력되었는가?
    -   **헤더/정렬:** 보고서 제목, 날짜, 작업 위치 순서가 정확한가?
    -   **항목 처리:** `0명/0대` 항목이 규칙에 맞게 제거 또는 `"없음"`으로 표기되었는가?
    -   **데이터 집계:** 총 인원/장비가 규칙(`직영반장` 제외 등)에 따라 정확히 계산되었는가?
    -   **표준화/추출:** 매핑 딕셔너리 및 안전관리 POINT 추출 규칙이 올바르게 적용되었는가?

2.  **출력 방식:** 위 검증 과정에서 변경된 내용이 있는 경우에만, **변경 전 '원문'과 변경 후 '결과'를 화살표(→)로 명확히 비교하여 '변환 내역'란에 요약**합니다. 변경 사항이 없다면 "변경사항 없음"으로 표기합니다.
3.  **예시** (마크다운 표(Table) 렌더링)
|  점검 항목 | 기준 | 변환 내역(원문→결과) | 상태 |
| :--- | :--- | :--- | :---: |
| **데이터 집계** | 총 인원/장비 수가 정확히 계산되었는가? | 총 인원 123명, 총 장비 15대 계산 완료 | ✅ |
| **인원 표준화**| 매핑 딕셔너리 적용 | **원문**: `...카리프트 1명...`<br>**결과**: `...카리프트공 1명...`| ✅ |
| **안전관리 POINT** | 중복 없이 10개 항목으로 요약되었는가? | 5대 재해 중심으로 10개 항목 추출 완료 | ✅ |


"""
    # 페이지별 입력/출력 상태 저장
    states = {
        'project_info': '', 'today_work': '', 'issues_solutions': '',
        'generated_report': '', 'qa_log': '', 'is_editing': False,
        'report_edit_content': ''
    }
    for key, value in states.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- HELPER FUNCTIONS ---
def call_gemini_api(prompt):
    """Gemini API를 호출하는 함수"""
    if not AI_AVAILABLE:
        st.error("⚠️ Gemini AI API 키가 설정되지 않았습니다.")
        return None
    
    try:
        response = GEMINI_MODEL.generate_content(prompt)
        if response.text:
            return response.text
        else:
            st.error("❌ AI 응답이 비어있습니다.")
            return None
    except Exception as e:
        st.error(f"❌ Gemini API 호출 중 오류: {str(e)}")
        return None

def process_api_response(api_result, all_inputs):
    """API 응답을 후처리하고 QA 로그를 분리합니다."""
    # ##1 MAIN SET와 ##2 QA-CHECKLIST를 확실히 구분
    qa_log_content = ''
    
    # ##2 QA-CHECKLIST 섹션의 정확한 시작점 찾기
    qa_start = -1
    
    # 가장 정확한 패턴부터 순서대로 찾기
    exact_patterns = [
        '## 2. QA-CHECKLIST (자동 검증 결과)',
        '## 2. QA-CHECKLIST',
        '## 2.'
    ]
    
    for pattern in exact_patterns:
        qa_start = api_result.find(pattern)
        if qa_start != -1:
            print(f"✅ 정확한 패턴 '{pattern}'으로 QA-CHECKLIST 발견!")
            break
    
    # ##2를 찾지 못했다면 테이블 헤더로 찾기
    if qa_start == -1:
        table_header = '| 점검 항목 | 기준 | 변환 내역(원문→결과) | 상태 |'
        qa_start = api_result.find(table_header)
        if qa_start != -1:
            print("✅ 테이블 헤더로 QA-CHECKLIST 발견!")
    
    if qa_start != -1:
        # ##2 QA-CHECKLIST 섹션을 끝까지 추출
        qa_log_content = api_result[qa_start:].strip()
        
        # ##1 MAIN SET만 남기기 (##2 시작점 직전까지)
        api_result = api_result[:qa_start].strip()
        
        # 디버깅용 로그
        print(f"##2 QA-CHECKLIST 발견: 위치 {qa_start}")
        print(f"##2 내용 길이: {len(qa_log_content)}")
        print(f"##1 MAIN SET 내용 길이: {len(api_result)}")
        
        # Streamlit에서도 구분 정보 표시
        st.success(f"✅ ##1 MAIN SET과 ##2 QA-CHECKLIST 성공적으로 분리됨")
        st.info(f"📊 ##1 길이: {len(api_result)}, ##2 길이: {len(qa_log_content)}")
    else:
        # ##2를 찾지 못한 경우
        print("⚠️ ##2 QA-CHECKLIST를 찾을 수 없음")
        st.warning("⚠️ AI 응답에서 ##2 QA-CHECKLIST를 찾을 수 없습니다.")
        qa_log_content = '##2 QA-CHECKLIST 내용이 없습니다.'

    # ##1 MAIN SET에서 불필요한 마크업 제거
    api_result = re.sub(r'```[a-zA-Z]*\s*\n?', '', api_result)  # 시작 코드블럭 제거
    api_result = re.sub(r'```\s*$', '', api_result)  # 끝 코드블럭 제거
    api_result = re.sub(r'^\s*# MAIN SET\s*\n?', '', api_result, flags=re.IGNORECASE)
    api_result = api_result.replace('**', '')
    api_result = api_result.replace('```markdown', '')  # markdown 코드블럭 제거

    # "신안산선..." 문자열 변경
    api_result = api_result.replace('신안산선 4-1공구(포스코이앤씨)', '●신안산선 4-1공구(포스코이앤씨)')
    
    # 인원/장비 합산
    total_person = sum(int(n) for n in re.findall(r'(\d+)\s*명', all_inputs))
    total_equip = sum(int(n) for n in re.findall(r'(\d+)\s*대', all_inputs))

    final_report = re.sub(r'■ 총 인원 : .*', f'■ 총 인원 : {total_person}명', api_result)
    final_report = re.sub(r'■ 총 장비 : .*', f'■ 총 장비 : {total_equip}대', final_report)

    return final_report.strip(), qa_log_content.strip()

def format_qa_log_to_markdown(qa_log):
    """QA 로그 텍스트를 마크다운 테이블로 변환합니다."""
    if not qa_log or '없습니다' in qa_log:
        return qa_log

    # undefined 텍스트 전역 제거
    qa_log = qa_log.replace('undefined', '').strip()

    # ##2 QA-CHECKLIST 내용을 정확하게 처리
    if '## 2.' in qa_log or 'QA-CHECKLIST' in qa_log:
        # ##2 섹션의 시작점 찾기
        start_patterns = [
            '## 2. QA-CHECKLIST (자동 검증 결과)',
            '## 2. QA-CHECKLIST',
            '## 2.'
        ]
        
        start_idx = -1
        for pattern in start_patterns:
            start_idx = qa_log.find(pattern)
            if start_idx != -1:
                break
        
        if start_idx != -1:
            # QA-CHECKLIST 섹션을 끝까지 추출
            qa_section = qa_log[start_idx:].strip()
            
            # undefined 텍스트 제거
            qa_section = qa_section.replace('undefined', '').strip()
            
            # 테이블만 정확하게 추출
            lines = qa_section.split('\n')
            table_lines = []
            in_table = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('|'):
                    in_table = True
                    # undefined 텍스트 제거
                    clean_line = line.replace('undefined', '').strip()
                    table_lines.append(clean_line)
                elif in_table and line and not line.startswith('|'):
                    # 테이블이 끝났음
                    break
                elif in_table and not line:
                    # 빈 줄은 테이블의 일부로 간주 (구분선 등)
                    table_lines.append(line)
            
            # 테이블이 완성되었는지 확인 (헤더 + 구분선 + 최소 1개 행)
            if len(table_lines) >= 3:
                print("✅ ##2 QA-CHECKLIST에서 완성된 마크다운 테이블 발견!")
                print(f"테이블 행 수: {len(table_lines)}")
                # 최종 undefined 제거
                clean_table = [line.replace('undefined', '').strip() for line in table_lines]
                return '\n'.join(clean_table)
            else:
                print("⚠️ ##2 QA-CHECKLIST 테이블이 불완전함")
                print(f"수집된 행 수: {len(table_lines)}")
                # 불완전한 테이블이라도 반환 (undefined 제거)
                clean_table = [line.replace('undefined', '').strip() for line in table_lines]
                return '\n'.join(clean_table) if clean_table else qa_section
    
    # ##2를 찾지 못한 경우 원본 반환 (undefined 제거)
    print("⚠️ ##2 QA-CHECKLIST 섹션을 찾을 수 없음")
    return qa_log.replace('undefined', '').strip()

# --- UI & LOGIC ---
st.set_page_config(
    page_title="AI 일일작업보고 생성기",
    page_icon="https://raw.githubusercontent.com/primer/octicons/main/icons/note-16.svg",
    layout="wide"
)
initialize_report_session_state()

# 공통 사이드바 스타일 추가
st.markdown("""
<style>
    /* 사이드바 공통 스타일 */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA;
        border-right: 1px solid #E5E7EB;
    }
    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem;
        color: #1E3A8A;
        font-weight: 700;
        padding: 1rem 0;
    }
    /* 메인 폰트 (아이콘 충돌 방지를 위해 [class*="st-"] 선택자 제거) */
    html, body, .stTextArea, .stButton>button, .stFileUploader, .stSelectbox {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }
    /* 메인 컨테이너 */
    .main .block-container {
        padding: 2rem 2rem 5rem 2rem;
        max-width: 1000px;
    }
    
    /* PRIMARY 버튼 모던한 색상 스타일 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        padding: 8px 16px !important;
        font-size: 14px !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton > button[kind="primary"]:active {
        transform: translateY(0) !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📱SNS 일일작업계획보고 자동화")
st.write("국가철도공단/발주처 일일작업계획보고를 간편하게 생성하세요.")
st.markdown("---")

with st.container(border=True):
    st.session_state.project_info = st.text_area(
        label="본선터널(1구간), 신풍정거장", 
        value=st.session_state.project_info, 
        placeholder="위치별 작업내용을 입력하세요",
        height=150,
        key="project_info_input"
    )
    st.session_state.today_work = st.text_area(
        label="신풍 환승통로",
        value=st.session_state.today_work,
        placeholder="위치별 작업내용을 입력하세요",
        height=200,
        key="today_work_input"
    )
    st.session_state.issues_solutions = st.text_area(
        label="본선터널(2구간), 도림정거장",
        value=st.session_state.issues_solutions,
        placeholder="위치별 작업내용을 입력하세요",
        height=150,
        key="issues_solutions_input"
    )

col1, col2 = st.columns(2)
with col1:
    if st.button("📄 보고서 생성", use_container_width=True, type="primary"):
        if not all([st.session_state.project_info, st.session_state.today_work, st.session_state.issues_solutions]):
            st.warning("모든 필드를 입력해주세요.")
        else:
            with st.spinner("🤖 AI가 보고서를 생성 중입니다..."):
                user_text = (
                    f"USER TEXT 1: {st.session_state.project_info}\n"
                    f"USER TEXT 2: {st.session_state.today_work}\n"
                    f"USER TEXT 3: {st.session_state.issues_solutions}"
                )
                full_prompt = f"{st.session_state.PROMPT_PAGE1}\n\n{user_text}"
                api_result = call_gemini_api(full_prompt)

                if api_result:
                    report, qa_log = process_api_response(api_result, user_text)
                    st.session_state.generated_report = report
                    st.session_state.report_edit_content = report
                    st.session_state.qa_log = qa_log
                    st.session_state.is_editing = False
                    st.toast("✅ 보고서 생성 완료!", icon="🎉")

with col2:
    if st.button("🗑️ 초기화", use_container_width=True):
        st.session_state.project_info = ''
        st.session_state.today_work = ''
        st.session_state.issues_solutions = ''
        st.session_state.generated_report = ''
        st.session_state.qa_log = ''
        st.session_state.is_editing = False
        st.rerun()

with st.expander("⚙️ 프롬프트 수정"):
    edited_prompt = st.text_area(
        "프롬프트(지시문) 수정",
        value=st.session_state.PROMPT_PAGE1,
        height=300,
        key="prompt_edit_area"
    )
    if st.button("프롬프트 저장", key="save_prompt"):
        st.session_state.PROMPT_PAGE1 = edited_prompt
        st.toast("프롬프트가 저장되었습니다.", icon="💾")

if st.session_state.generated_report:
    st.markdown("---")
    st.subheader("📋 SNS일일작업계획보고")

    if st.session_state.is_editing:
        st.session_state.report_edit_content = st.text_area(
            "보고서 수정",
            value=st.session_state.report_edit_content,
            height=400,
            label_visibility="collapsed"
        )
        
        edit_col1, edit_col2 = st.columns(2)
        with edit_col1:
            if st.button("💾 저장", use_container_width=True, type="primary"):
                st.session_state.generated_report = st.session_state.report_edit_content
                st.session_state.is_editing = False
                st.toast("보고서가 수정되었습니다.", icon="✏️")
                st.rerun()
        with edit_col2:
            if st.button("❌ 취소", use_container_width=True):
                st.session_state.is_editing = False
                st.session_state.report_edit_content = st.session_state.generated_report
                st.rerun()
    else:
        st.text_area(
            "보고서 내용",
            value=st.session_state.generated_report,
            height=400,
            key="report_output_area",
            label_visibility="collapsed"
        )
        
        btn_col1, btn_col2, btn_col3 = st.columns([1,1,2])
        with btn_col1:
            if st.button("✏️ 수정", use_container_width=True):
                st.session_state.is_editing = True
                st.rerun()
        with btn_col2:
            if st.button("📲 작업일보 작성 자동화로 전달", use_container_width=True):
                st.session_state.report_to_transfer = st.session_state.generated_report
                st.toast("✅ 보고서 내용이 전달되었습니다. 다음 페이지에서 확인하세요.")
                st.switch_page("pages/작업일보 작성.py")
        
        with st.expander("📋 복사용 텍스트 (우측 상단 복사 버튼 클릭)", expanded=False):
            st.code(st.session_state.generated_report, language=None)

    if st.session_state.qa_log:
        st.subheader("📊 QA-Checklist(자동 검증 결과)")
        
        # 디버깅용: 원본 QA 로그 표시
        with st.expander("🔍 원본 QA 로그 (디버깅용)", expanded=False):
            st.text(st.session_state.qa_log)
        
        formatted_qa_log = format_qa_log_to_markdown(st.session_state.qa_log)
        
        # 디버깅용: 포맷된 QA 로그 표시
        with st.expander("🔍 포맷된 QA 로그 (디버깅용)", expanded=False):
            st.text(formatted_qa_log)
        
        st.markdown(formatted_qa_log, unsafe_allow_html=True)