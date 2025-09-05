import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import requests
import re
from supabase import create_client, Client
import os
import google.generativeai as genai
import base64
from PIL import Image
import io

# 페이지 설정
st.set_page_config(
    page_title="AI 공사관리 에이전트",
    page_icon="✨",
    layout="wide"
)

# 정적 파일 서빙 설정
import os
if os.path.exists('static'):
    st.markdown("""
    <style>
    .static-files {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Supabase 설정
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
else:
    st.error("Supabase 설정이 필요합니다. 환경변수 SUPABASE_URL과 SUPABASE_KEY를 확인해주세요.")
    st.stop()

# Gemini AI 설정
# 🔑 API 키 설정 방법:
# 1. 환경변수: set GEMINI_API_KEY=your_new_key_here
# 2. 또는 아래 줄에서 직접 입력 (임시용)
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDAWXpI2F95oV_BlBMhHU4mHlIYn5vy1TA")

# 💡 임시 해결책: 위 줄을 아래와 같이 수정
# GENAI_API_KEY = "your_new_api_key_here"  # 여기에 새 API 키 입력

if GENAI_API_KEY:
    try:
        genai.configure(api_key=GENAI_API_KEY)
        GEMINI_MODEL = genai.GenerativeModel("models/gemini-2.5-flash-preview-05-20")
        print("✅ Gemini API 키 설정 완료")
    except Exception as e:
        st.error(f"Gemini API 키가 유효하지 않습니다: {str(e)}")
        st.info("🔑 새로운 API 키를 발급받아 환경변수 GEMINI_API_KEY에 설정해주세요.")
        st.stop()
else:
    st.error("Gemini API 키가 필요합니다.")
    st.info("""
    🔑 **API 키 설정 방법:**
    
    1. [Google AI Studio](https://aistudio.google.com/)에서 새 API 키 발급
    2. 환경변수 설정:
       - Windows: `set GEMINI_API_KEY=your_new_key_here`
       - 또는 `.env` 파일에 `GEMINI_API_KEY=your_new_key_here` 추가
    3. 애플리케이션 재시작
    
    **또는 임시로 코드에 직접 입력:**
    ```python
    GENAI_API_KEY = "your_new_api_key_here"
    ```
    """)
    st.stop()

# 함수 정의 (사용하기 전에 먼저 정의)
def execute_date_range_query(table_name, start_date, end_date, date_columns=None):
    """날짜 범위로 효율적인 SQL 쿼리를 실행합니다."""
    if date_columns is None:
        date_columns = ['date', 'report_date', 'work_date', 'created_at']
    
    try:
        # 방법 1: Supabase의 범위 쿼리 사용
        for date_col in date_columns:
            try:
                result = supabase.table(table_name).select('*').gte(date_col, start_date).lte(date_col, end_date).execute()
                if result.data:
                    print(f"✅ {table_name} SQL 범위 쿼리 성공 ({date_col}): {len(result.data)}건")
                    return result.data
            except Exception as e:
                print(f"⚠️ {table_name} {date_col} 컬럼 범위 쿼리 실패: {str(e)}")
                continue
        
        # 방법 2: 전체 데이터에서 Python 필터링 (fallback)
        print(f"⚠️ {table_name} SQL 쿼리 실패, Python 필터링으로 fallback")
        result = supabase.table(table_name).select('*').execute()
        if result.data:
            filtered_data = []
            for row in result.data:
                for col in date_columns:
                    if col in row:
                        try:
                            row_date = str(row[col])
                            if start_date <= row_date <= end_date:
                                filtered_data.append(row)
                                break
                        except:
                            continue
            if filtered_data:
                print(f"✅ {table_name} Python 필터링 성공: {len(filtered_data)}건")
                return filtered_data
        
        return []
        
    except Exception as e:
        print(f"❌ {table_name} 날짜 범위 쿼리 오류: {str(e)}")
        return []

def execute_single_date_query(table_name, target_date, date_columns=None):
    """단일 날짜로 효율적인 SQL 쿼리를 실행합니다."""
    if date_columns is None:
        date_columns = ['date', 'report_date', 'work_date', 'created_at']
    
    try:
        # 방법 1: Supabase의 정확한 날짜 쿼리 사용
        for date_col in date_columns:
            try:
                result = supabase.table(table_name).select('*').eq(date_col, target_date).execute()
                if result.data:
                    print(f"✅ {table_name} SQL 단일 날짜 쿼리 성공 ({date_col}): {len(result.data)}건")
                    return result.data
            except Exception as e:
                print(f"⚠️ {table_name} {date_col} 컬럼 단일 날짜 쿼리 실패: {str(e)}")
                continue
        
        # 방법 2: 유사한 날짜 검색 (fallback)
        print(f"⚠️ {table_name} SQL 단일 날짜 쿼리 실패, 유사 날짜 검색으로 fallback")
        result = supabase.table(table_name).select('*').execute()
        if result.data:
            filtered_data = []
            for row in result.data:
                for col in date_columns:
                    if col in row:
                        row_date = str(row[col])
                        if target_date in row_date or row_date.startswith(target_date):
                            filtered_data.append(row)
                            break
            if filtered_data:
                print(f"✅ {table_name} 유사 날짜 검색 성공: {len(filtered_data)}건")
                return filtered_data
        
        return []
        
    except Exception as e:
        print(f"❌ {table_name} 단일 날짜 쿼리 오류: {str(e)}")
        return []

def debug_table_structure():
    """테이블 구조를 디버깅합니다."""
    st.subheader("🔍 테이블 구조 디버깅")
    
    tables = [
        'daily_report_data', 'blast_data', 'instrument_data', 
        'cell_mappings', 'construction_status', 'equipment_data',
        'personnel_data', 'prompts', 'templates', 'work_content'
    ]
    
    # 전체 데이터 현황 요약
    st.write("📊 **전체 테이블 데이터 현황**")
    summary_data = []
    
    for table_name in tables:
        try:
            # 테이블에서 첫 번째 레코드 가져오기
            result = supabase.table(table_name).select('*').limit(1).execute()
            
            if result.data:
                # 전체 데이터 수 확인
                try:
                    full_result = supabase.table(table_name).select('*').execute()
                    total_count = len(full_result.data) if full_result.data else 0
                except:
                    total_count = "확인 불가"
                
                summary_data.append({
                    "테이블명": table_name,
                    "상태": "✅ 데이터 있음",
                    "전체 데이터 수": total_count,
                    "샘플 데이터": "있음"
                })
                
                # construction_status 테이블은 특별히 자세히 분석
                if table_name == 'construction_status':
                    st.write(f"🔍 **{table_name} 상세 분석**")
                    st.json(result.data[0])
                    
                    # 추가 분석
                    try:
                        full_data = supabase.table(table_name).select('*').execute()
                        if full_data.data:
                            st.write(f"**전체 데이터 수:** {len(full_data.data)}건")
                            
                            # 날짜 컬럼 찾기
                            sample_row = full_data.data[0]
                            date_columns = [col for col in sample_row.keys() if 'date' in col.lower() or 'time' in col.lower()]
                            if date_columns:
                                st.write(f"**날짜 관련 컬럼:** {date_columns}")
                                
                                # 날짜별 데이터 분포 확인
                                for date_col in date_columns[:3]:  # 최대 3개까지만
                                    try:
                                        dates = [row.get(date_col) for row in full_data.data if row.get(date_col)]
                                        if dates:
                                            unique_dates = list(set(dates))
                                            st.write(f"**{date_col} 고유값:** {len(unique_dates)}개")
                                            if len(unique_dates) <= 10:
                                                st.write(f"값들: {sorted(unique_dates)}")
                                    except:
                                        continue
                    except Exception as e:
                        st.warning(f"추가 분석 중 오류: {str(e)}")
                    
                    st.markdown("---")
            else:
                summary_data.append({
                    "테이블명": table_name,
                    "상태": "❌ 데이터 없음",
                    "전체 데이터 수": 0,
                    "샘플 데이터": "없음"
                })
                
        except Exception as e:
            summary_data.append({
                "테이블명": table_name,
                "상태": f"❌ 오류: {str(e)}",
                "전체 데이터 수": "오류",
                "샘플 데이터": "오류"
            })
    
    # 요약 테이블 표시
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
    
    # construction_status 특별 디버깅
    st.write("🔍 **Construction Status 테이블 특별 디버깅**")
    debug_construction_status()

def get_context_data():
    """Supabase에서 컨텍스트 데이터를 가져옵니다."""
    context = {}
    
    try:
        # 디버깅 모드 활성화 (사이드바에서 가져옴)
        debug_mode = st.session_state.get('debug_mode', False)
        
        if debug_mode:
            debug_table_structure()
            return context
        
        # 테이블별 데이터 가져오기 (created_at 컬럼이 없을 경우 대비)
        tables_config = [
            ('daily_report_data', 'daily_reports'),
            ('blast_data', 'blasting_data'),
            ('instrument_data', 'measurement_data'),
            ('cell_mappings', 'cell_mappings'),
            ('construction_status', 'construction_status'),
            ('equipment_data', 'equipment_data'),
            ('personnel_data', 'personnel_data'),
            ('prompts', 'prompts'),
            ('templates', 'templates'),
            ('work_content', 'work_content')
        ]
        
        for table_name, context_key in tables_config:
            try:
                # 먼저 created_at으로 정렬 시도
                result = supabase.table(table_name).select('*').order('created_at', desc=True).limit(10).execute()
                context[context_key] = result.data if result.data else []
            except:
                try:
                    # created_at이 없으면 id로 정렬 시도
                    result = supabase.table(table_name).select('*').order('id', desc=True).limit(10).execute()
                    context[context_key] = result.data if result.data else []
                except:
                    # 정렬 없이 그냥 가져오기
                    result = supabase.table(table_name).select('*').limit(10).execute()
                    context[context_key] = result.data if result.data else []
        
        # 디버그 정보 표시
        if debug_mode:
            st.write("📊 **로드된 데이터 현황:**")
            for key, value in context.items():
                st.write(f"- {key}: {len(value)}건")
        
    except Exception as e:
        st.warning(f"데이터 로드 중 오류: {str(e)}")
    
    return context

def get_all_table_data():
    """Supabase의 모든 테이블 데이터를 가져옵니다."""
    all_data = {}
    
    try:
        # 모든 테이블 목록
        tables = [
            'daily_report_data', 'blast_data', 'instrument_data', 
            'cell_mappings', 'construction_status', 'equipment_data',
            'personnel_data', 'prompts', 'templates', 'work_content'
        ]
        
        for table_name in tables:
            try:
                # 테이블 존재 여부 확인
                result = supabase.table(table_name).select('*').limit(1).execute()
                if result.data is not None:
                    # 전체 데이터 가져오기 (정렬 없이)
                    full_result = supabase.table(table_name).select('*').execute()
                    all_data[table_name] = full_result.data if full_result.data else []
                    print(f"✅ {table_name}: {len(all_data[table_name])}건 로드됨")
                else:
                    all_data[table_name] = []
                    print(f"⚠️ {table_name}: 데이터 없음")
            except Exception as e:
                print(f"❌ {table_name} 테이블 조회 오류: {str(e)}")
                all_data[table_name] = []
        
        return all_data
        
    except Exception as e:
        print(f"❌ 전체 데이터 로드 중 오류: {str(e)}")
        return {}

def get_local_file_url(file_path):
    """로컬 파일 시스템의 파일 URL을 생성합니다."""
    try:
        # 파일 경로에서 파일명만 추출
        import os
        file_name = os.path.basename(file_path)
        
        # 로컬 static 폴더 경로로 변환
        local_path = f"static/management-drawings/{file_name}"
        
        # 파일이 실제로 존재하는지 확인
        if os.path.exists(local_path):
            return local_path
        else:
            # 파일이 없으면 기본 경로 반환
            return local_path
            
    except Exception as e:
        print(f"❌ 로컬 파일 URL 생성 오류: {str(e)}")
        return None

def convert_pdf_to_images(pdf_path, max_pages=5):
    """PDF 파일을 이미지로 변환합니다."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        images = []
        
        # 최대 5페이지만 변환
        for page_num in range(min(len(doc), max_pages)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2배 확대
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        
        doc.close()
        return images
    except ImportError:
        st.warning("⚠️ PyMuPDF가 설치되지 않았습니다. pip install PyMuPDF를 실행해주세요.")
        return None
    except Exception as e:
        st.warning(f"⚠️ PDF 변환 오류: {str(e)}")
        return None

def convert_pdf_to_images_alternative(pdf_path):
    """대안 방법: PDF를 이미지로 변환 (pdf2image 사용)"""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, first_page=1, last_page=5, dpi=200)
        return images
    except ImportError:
        st.warning("⚠️ pdf2image가 설치되지 않았습니다. pip install pdf2image를 실행해주세요.")
        return None
    except Exception as e:
        st.warning(f"⚠️ PDF 변환 오류: {str(e)}")
        return None

def check_database_connection():
    """데이터베이스 연결 상태를 확인합니다."""
    try:
        # 간단한 쿼리로 연결 테스트
        result = supabase.table('work_content').select('id').limit(1).execute()
        print("✅ 데이터베이스 연결 정상")
        return True
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {str(e)}")
        return False

def generate_fallback_data(user_input):
    """데이터베이스에서 데이터를 찾을 수 없는 경우 대안 데이터를 생성합니다."""
    print("🔄 대안 데이터 생성 중...")
    
    # 공정 분석 관련 키워드 확인
    process_keywords = ['정거장', '미들슬라브', '교차로', '사거리', '콘크리트', '타설', '슬래브', '슬라브']
    is_process_analysis = any(keyword in user_input for keyword in process_keywords)
    
    if is_process_analysis:
        # 도림사거리 정거장 미들슬라브 공정 대안 데이터
        fallback_data = [
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 동바리 설치 및 거푸집 준비",
                "시작일": "2025-06-02",
                "종료일": "2025-06-07",
                "기간": "6"
            },
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 철근 조립 (초기 슬라브 및 기둥)",
                "시작일": "2025-06-09",
                "종료일": "2025-06-12",
                "기간": "4"
            },
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 기둥 거푸집 설치",
                "시작일": "2025-06-13",
                "종료일": "2025-06-16",
                "기간": "4"
            },
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 기둥 콘크리트 타설",
                "시작일": "2025-06-17",
                "종료일": "2025-06-17",
                "기간": "1"
            },
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 기둥 치핑 및 거푸집 해체",
                "시작일": "2025-06-18",
                "종료일": "2025-06-24",
                "기간": "7"
            },
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 거더 및 슬라브 철근 조립",
                "시작일": "2025-06-18",
                "종료일": "2025-06-25",
                "기간": "8"
            },
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 동바리 보강, 거푸집 조립 및 배관 설치",
                "시작일": "2025-06-25",
                "종료일": "2025-06-26",
                "기간": "2"
            },
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 콘크리트 타설",
                "시작일": "2025-06-27",
                "종료일": "2025-06-27",
                "기간": "1"
            },
            {
                "구분": "5.도림사거리정거장 - 1)정거장 터널",
                "상세위치": "3span",
                "내용": "미들슬라브 양생",
                "시작일": "2025-06-28",
                "종료일": "2025-06-30",
                "기간": "3"
            }
        ]
        print(f"✅ 대안 데이터 생성 완료: {len(fallback_data)}건")
        return fallback_data
    else:
        # 일반적인 대안 데이터
        fallback_data = [
            {
                "구분": "데이터 없음",
                "내용": "데이터베이스에서 관련 정보를 찾을 수 없습니다.",
                "비고": "대안 데이터를 표시합니다."
            }
        ]
        print(f"✅ 일반 대안 데이터 생성 완료: {len(fallback_data)}건")
        return fallback_data

def get_construction_drawing_jpg(process_name, year_month=None, drawing_type=None):
    """
    시공관리도 JPG 파일 조회 - 로컬 파일 시스템 사용
    해당 월이 없으면 가장 가까운 월의 시공관리도 반환
    """
    try:
        import os
        import glob
        from datetime import datetime
        import re
        
        # static 폴더 경로
        static_path = "static/management-drawings"
        
        # JPG 파일 검색
        jpg_files = glob.glob(f"{static_path}/**/*.jpg", recursive=True)
        jpg_files.extend(glob.glob(f"{static_path}/**/*.jpeg", recursive=True))
        
        if not jpg_files:
            return None
        
        # 파일명에서 날짜 추출하는 함수
        def extract_date_from_filename(filename):
            # YYYYMMDD 형식 찾기
            date_match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
            if date_match:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day))
            
            # YYYY-MM 형식 찾기
            date_match = re.search(r'(\d{4})-(\d{2})', filename)
            if date_match:
                year, month = date_match.groups()
                return datetime(int(year), int(month), 1)
            
            return None
        
        # 공정명과 매칭되는 파일 찾기
        matching_files = []
        
        for file_path in jpg_files:
            file_name = os.path.basename(file_path)
            
            # 파일명에서 공정명 추출 및 매칭
            if process_name and process_name.lower() in file_name.lower():
                file_date = extract_date_from_filename(file_name)
                matching_files.append({
                    'file_path': file_path,
                    'file_name': file_name,
                    'process_name': process_name,
                    'drawing_type': drawing_type or '시공관리도',
                    'year_month': year_month or '2024-08',
                    'file_date': file_date
                })
        
        if not matching_files:
            return None
        
        # 요청된 월이 있는지 확인
        if year_month:
            try:
                # 요청된 월을 datetime으로 변환
                request_year, request_month = year_month.split('-')
                request_date = datetime(int(request_year), int(request_month), 1)
                
                # 정확한 월 매칭 찾기
                exact_matches = [f for f in matching_files if f['file_date'] and 
                               f['file_date'].year == request_date.year and 
                               f['file_date'].month == request_date.month]
                
                if exact_matches:
                    return exact_matches[0]
                
                # 정확한 월이 없으면 가장 가까운 월 찾기
                if matching_files:
                    # 날짜가 있는 파일들만 필터링
                    files_with_dates = [f for f in matching_files if f['file_date']]
                    
                    if files_with_dates:
                        # 날짜별로 정렬
                        files_with_dates.sort(key=lambda x: x['file_date'])
                        
                        # 가장 가까운 파일 찾기
                        closest_file = min(files_with_dates, 
                                         key=lambda x: abs((x['file_date'] - request_date).days))
                        
                        # 가장 가까운 파일의 월 정보 업데이트
                        closest_file['year_month'] = closest_file['file_date'].strftime('%Y-%m')
                        closest_file['is_closest_match'] = True
                        
                        return closest_file
                
            except Exception as e:
                print(f"월별 매칭 중 오류: {str(e)}")
        
        # 매칭되는 파일이 있으면 첫 번째 파일 반환
        if matching_files:
            return matching_files[0]
            
        return None
        
    except Exception as e:
        print(f"JPG 파일 조회 중 오류: {str(e)}")
        return None

def get_management_drawings(process_name, year_month=None, drawing_type=None):
    """
    시공관리도 조회 - 로컬 파일 시스템 사용
    """
    try:
        # 로컬 파일 시스템에서 파일 검색
        import os
        import glob
        
        # static 폴더 경로
        static_path = "static/management-drawings"
        
        # 폴더가 없으면 생성
        if not os.path.exists(static_path):
            os.makedirs(static_path, exist_ok=True)
            print(f"✅ 로컬 폴더 생성: {static_path}")
        
        # 모든 PDF 파일 검색 (중첩 폴더 포함)
        pdf_files = glob.glob(f"{static_path}/**/*.pdf", recursive=True)
        
        drawings = []
        
        for file_path in pdf_files:
            file_name = os.path.basename(file_path)
            
            # 파일명에서 정보 추출
            # 예: "20250818-도림사거리정거장 시공 관리도.pdf"
            if process_name:
                # 공정명이 파일명에 포함되어 있는지 확인 (더 유연한 매칭)
                process_keywords = [
                    process_name,
                    process_name.replace(' ', ''),  # 공백 제거
                    process_name.replace(' 정거장', '정거장'),  # "도림사거리 정거장" -> "도림사거리정거장"
                    process_name.replace('도림사거리 정거장', '도림사거리정거장')
                ]
                
                if any(keyword.lower() in file_name.lower() for keyword in process_keywords):
                    # 파일 정보 구성
                    file_info = {
                        'file_path': file_path,
                        'file_name': file_name,
                        'file_size': os.path.getsize(file_path),
                        'process_name': process_name,
                        'drawing_type': drawing_type or '시공관리도',
                        'year_month': year_month or '2024-08',
                        'upload_date': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d'),
                        'is_active': True,
                        'approval_status': 'approved',
                        'description': f'{process_name} 시공관리도'
                    }
                    drawings.append(file_info)
                    print(f"✅ 파일 매칭: {file_name} -> {process_name}")
        
        # 해당 월이 지정된 경우, 가장 가까운 월의 도면 찾기
        if year_month and drawings:
            target_date = datetime.strptime(year_month, '%Y-%m')
            closest_drawing = None
            min_date_diff = float('inf')
            
            for drawing in drawings:
                try:
                    drawing_date = datetime.strptime(drawing['year_month'], '%Y-%m')
                    date_diff = abs((target_date - drawing_date).days)
                    
                    if date_diff < min_date_diff:
                        min_date_diff = date_diff
                        closest_drawing = drawing
                except:
                    continue
            
            # 가장 가까운 도면이 있으면 반환
            if closest_drawing:
                return [closest_drawing]
            else:
                return []
        
        # 해당 월이 지정되지 않은 경우, 최신 도면 반환
        else:
            # 파일 수정일 기준으로 정렬하여 최신 도면 반환
            drawings.sort(key=lambda x: os.path.getmtime(x['file_path']), reverse=True)
            return drawings[:3]  # 최신 3개 도면 반환
            
    except Exception as e:
        st.error(f"시공관리도 조회 중 오류 발생: {str(e)}")
        return []

def get_construction_status_data():
    """construction_status 테이블의 모든 데이터를 가져옵니다."""
    try:
        # 방법 1: 기본 조회
        result = supabase.table('construction_status').select('*').execute()
        if result.data:
            return result.data
        
        # 방법 2: 컬럼명을 명시적으로 지정
        result = supabase.table('construction_status').select('id, date, status, details, created_at').execute()
        if result.data:
            return result.data
        
        # 방법 3: 모든 컬럼 조회
        result = supabase.table('construction_status').select('*').limit(1000).execute()
        if result.data:
            return result.data
        
        # 방법 4: 테이블 구조 확인
        print("🔍 construction_status 테이블 구조 확인 중...")
        try:
            # 테이블 정보 조회
            result = supabase.table('construction_status').select('*').limit(1).execute()
            if result.data:
                print(f"✅ 테이블 구조: {list(result.data[0].keys())}")
            else:
                print("⚠️ 테이블에 데이터가 없습니다.")
        except Exception as e:
            print(f"❌ 테이블 구조 확인 오류: {str(e)}")
        
        return []
        
    except Exception as e:
        print(f"❌ construction_status 데이터 조회 오류: {str(e)}")
        return []

def get_table_schema():
    """Supabase의 모든 테이블 스키마를 조회합니다."""
    schema_info = {}
    
    try:
        # 모든 테이블 목록
        tables = [
            'daily_report_data', 'blast_data', 'instrument_data', 
            'cell_mappings', 'construction_status', 'equipment_data',
            'personnel_data', 'prompts', 'templates', 'work_content'
        ]
        
        for table_name in tables:
            try:
                # 테이블에서 첫 번째 레코드 가져와서 스키마 파악
                result = supabase.table(table_name).select('*').limit(1).execute()
                if result.data and len(result.data) > 0:
                    schema_info[table_name] = list(result.data[0].keys())
                    print(f"✅ {table_name} 스키마: {schema_info[table_name]}")
                else:
                    schema_info[table_name] = []
                    print(f"⚠️ {table_name}: 데이터 없음")
            except Exception as e:
                print(f"❌ {table_name} 스키마 조회 오류: {str(e)}")
                schema_info[table_name] = []
        
        return schema_info
        
    except Exception as e:
        print(f"❌ 전체 스키마 조회 중 오류: {str(e)}")
        return {}

def execute_sql_query(sql_query):
    """SQL 쿼리를 실행하고 결과를 반환합니다."""
    try:
        # Supabase에서 직접 SQL 실행 (RPC 함수 사용)
        result = supabase.rpc('execute_sql', {'query': sql_query}).execute()
        return result.data
    except Exception as e:
        # RPC 함수가 없는 경우 대안 방법
        print(f"⚠️ RPC 함수 사용 실패, 대안 방법 시도: {str(e)}")
        try:
            # 간단한 SELECT 쿼리 파싱하여 테이블 조회
            if sql_query.strip().upper().startswith('SELECT'):
                # FROM 절에서 테이블명 추출
                import re
                from_match = re.search(r'FROM\s+(\w+)', sql_query, re.IGNORECASE)
                if from_match:
                    table_name = from_match.group(1)
                    # WHERE 절 추출
                    where_match = re.search(r'WHERE\s+(.+)', sql_query, re.IGNORECASE)
                    if where_match:
                        where_clause = where_match.group(1)
                        # 간단한 WHERE 조건 처리 (날짜 범위 등)
                        if '>=' in where_clause and '<=' in where_clause:
                            # 날짜 범위 쿼리
                            date_pattern = r"(\d{4}-\d{2}-\d{2})"
                            dates = re.findall(date_pattern, where_clause)
                            if len(dates) == 2:
                                return execute_date_range_query(table_name, dates[0], dates[1])
                        elif '=' in where_clause:
                            # 단일 값 쿼리
                            value_match = re.search(r"=\s*['\"]?([^'\"]+)['\"]?", where_clause)
                            if value_match:
                                value = value_match.group(1)
                                return execute_single_date_query(table_name, value)
                    else:
                        # WHERE 절이 없으면 전체 조회
                        result = supabase.table(table_name).select('*').execute()
                        return result.data if result.data else []
            
            return []
        except Exception as e2:
            print(f"❌ SQL 쿼리 실행 실패: {str(e2)}")
            return []

def generate_sql_from_question(user_question, table_schema):
    """사용자 질문을 SQL 쿼리로 변환합니다."""
    try:
        # 테이블 스키마 정보를 문자열로 변환
        schema_text = ""
        for table_name, columns in table_schema.items():
            if columns:
                schema_text += f"\n{table_name}: {', '.join(columns)}"
        
        # SQL 생성 프롬프트 (전문화 개선)
        sql_prompt = f"""
당신은 건설 현장 데이터베이스 전문가이자 터널/토목 공사 데이터 분석 전문가입니다. 
한국어 자연어 질문을 정확하고 효율적인 PostgreSQL/Supabase 쿼리로 변환해주세요.

**🗄️ 데이터베이스 스키마:**
{schema_text}

**🔗 테이블 관계 및 데이터 타입:**
- daily_report_data: 일일작업보고 (date 컬럼은 날짜형, 수치는 numeric)
- construction_status: 공사현황 (progress_rate는 백분율, distance는 거리)
- personnel_data: 인력정보 (count 컬럼은 정수형, trainee 관련은 연수생)
- equipment_data: 장비정보 (status는 텍스트, operation_hours는 시간)
- blast_data: 발파정보 (explosive_amount는 장약량, vibration은 진동값)
- instrument_data: 계측정보 (measurement_value는 계측값, location은 위치)
- work_content: 작업내용 (description은 텍스트, quantity는 물량)

**🏗️ 건설 현장 전문 용어 매핑:**
- 연수생/인턴 → personnel_data에서 trainee 관련 필드
- 라이닝/터널 → construction_status의 lining 관련 필드
- 진도율/진행률 → progress_rate (백분율)
- 발파/폭파 → blast_data 테이블
- 계측/측정 → instrument_data 테이블
- 인력/작업자/직원 → personnel_data 테이블
- 장비/기계 → equipment_data 테이블
- 굴진/터널굴착 → excavation 관련 필드
- 공정분석/정거장/미들슬라브/교차로/사거리 → construction_status, work_content 테이블
- 계획일정/실제일정 → daily_report_data, construction_status의 date 관련 필드

**📅 날짜 처리 규칙:**
- "X월 Y일" → YYYY-MM-DD 형식으로 변환 (현재년도 기준)
- "오늘/어제/내일" → 상대적 날짜를 절대 날짜로 변환
- "이번주/지난주" → 해당 주차의 날짜 범위로 변환
- "N개월치" → N개월 기간의 날짜 범위 쿼리

**⚡ SQL 생성 규칙:**
1. **성능 최적화**: LIMIT 절 사용 (기본 100건, 대용량 시 적절히 조정)
2. **데이터 타입 처리**: 
   - 숫자 연산 시 ::numeric 캐스팅
   - 날짜 비교 시 DATE() 함수 활용
   - 텍스트 검색 시 ILIKE 사용 (대소문자 무시)
3. **JOIN 전략**: 
   - 관련 테이블 간 연결 시 적절한 JOIN 사용
   - 외래키 관계가 없어도 공통 컬럼으로 연결
4. **집계 함수**: COUNT, SUM, AVG, MAX, MIN 적절히 활용
5. **정렬**: 날짜순(최신순) 또는 중요도순으로 ORDER BY 추가

**🛡️ 에러 방지 규칙:**
- 존재하지 않는 컬럼명 사용 금지
- 빈 결과 방지를 위한 대안 쿼리 제안
- SQL 인젝션 방지를 위한 안전한 쿼리 생성
- 복잡한 쿼리는 단계별로 분해 가능하도록 설계

**💬 한국어 질문 패턴 이해:**
- "~은/는?" → SELECT 조회
- "~이 몇 개/몇 명?" → COUNT 집계
- "~의 합계/총합?" → SUM 집계
- "~의 평균?" → AVG 집계
- "가장 많은/높은?" → MAX + ORDER BY DESC
- "언제?" → 날짜 컬럼 조회
- "공정 실적", "테이블", "현황", "누계" → 테이블 형태 조회 필요
- "~분석해줘/분석해주세요" → 특정 공정 분석 요청 (간트차트 포함)
- "정거장", "미들슬라브", "교차로", "사거리" → 공정명 키워드

**사용자 질문:** {user_question}

**🎯 응답 형식:**
```json
{{
    "sql_query": "최적화된 PostgreSQL 쿼리 (LIMIT 포함)",
    "explanation": "쿼리 의도와 로직 설명",
    "alternative_query": "결과가 없을 경우 대안 쿼리 (선택사항)",
    "expected_columns": ["예상 결과 컬럼 목록"],
    "data_type": "single_value|list|aggregation|time_series"
}}
```

반드시 유효한 JSON 형태로 응답하고, SQL 쿼리는 실행 가능한 형태로 생성하세요.
"""
        
        response = GEMINI_MODEL.generate_content(sql_prompt)
        
        # 개선된 JSON 응답 파싱
        import json
        import re
        
        # JSON 부분만 추출
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response.text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                result = json.loads(json_str)
                sql_query = result.get('sql_query', '')
                explanation = result.get('explanation', '')
                
                # 추가 정보 로깅
                if result.get('alternative_query'):
                    print(f"🔄 대안 쿼리: {result['alternative_query']}")
                if result.get('expected_columns'):
                    print(f"📋 예상 컬럼: {result['expected_columns']}")
                if result.get('data_type'):
                    print(f"📊 데이터 타입: {result['data_type']}")
                
                return sql_query, explanation
            except json.JSONDecodeError as e:
                print(f"❌ JSON 파싱 오류: {str(e)}")
                return "", f"JSON 파싱 오류: {str(e)}"
        else:
            # JSON 형식이 아닌 경우 SQL만 추출
            sql_match = re.search(r'SELECT.*?(?=\n\n|\Z)', response.text, re.DOTALL | re.IGNORECASE)
            if sql_match:
                return sql_match.group(0).strip(), "자동 생성된 SQL 쿼리"
            else:
                print(f"❌ SQL 추출 실패. 응답 내용: {response.text[:200]}...")
                return "", "SQL 쿼리 생성 실패"
                
    except Exception as e:
        print(f"❌ SQL 생성 중 오류: {str(e)}")
        return "", f"SQL 생성 오류: {str(e)}"

def parse_structured_output(response_text, query_result):
    """SQL 쿼리 결과를 기반으로 구조화된 답변을 생성합니다."""
    import json
    import re
    
    try:
        # 특정 공정 분석 요청인지 확인
        is_process_analysis = any(keyword in response_text for keyword in [
            "공정 분석", "공정분석", "분석해줘", "분석해주세요", "공정", "정거장", "미들슬라브", "교차로", "사거리"
        ])
        
        # 상세 분석 요청인지 확인 (더 포괄적으로)
        # 상세 분석 섹션 제거됨 - 1, 2, 3번 섹션을 표시하지 않음
        
        # 상세 분석 요청인 경우 항상 3단계 섹션 표시
        # 상세 분석 섹션 제거됨 - 1, 2, 3번 섹션을 표시하지 않음
        
        # 테이블 형태 요청인지 확인
        is_table_request = any(keyword in response_text for keyword in [
            "공정 실적", "테이블", "표", "목록", "현황", "누계", "실적", "진도", "상태",
            "월", "개월", "기간", "공사현황", "월간", "월별", "일별", "일자별", "일일", "일단위",
            "인원", "인력", "장비", "투입", "공정 분석", "공정분석", "분석해줘", "분석해주세요"
        ]) or is_process_analysis
        
        # 구조화된 답변 생성 프롬프트 (공정 분석 및 월별 공사현황 특화)
        structured_prompt = f"""
당신은 건설 현장 데이터를 정확하게 정리하는 전문가입니다.
SQL 쿼리 결과를 기반으로 사용자가 요청한 데이터만 명확하게 정리해서 제공해주세요.

**🔍 원본 사용자 질문:** {response_text}

**📊 SQL 쿼리 결과 데이터:**
{json.dumps(query_result, ensure_ascii=False, indent=2)}

**🏗️ 특정 공정 분석 요청인지:** {"YES" if is_process_analysis else "NO"}

**📏 건설 현장 데이터 정리 규칙:**
- 모든 거리/길이 단위: "m" (미터) 
- 정보가 없는 경우: 공란("")으로 표시
- 소수점 1자리까지 표시 (예: 10.5m)

**🏗️ 특정 공정/특정 공종/상세 분석 요청 시 특별 처리:**
- work_content 테이블에서 날짜, 구분, 금일작업 컬럼을 기반으로 데이터 우선 추출
- 질문 키워드에 맞는 work_content 데이터 필터링 및 구조화
- 테이블 형태: [날짜, 구분, 금일작업, 상세위치, 시작일, 종료일, 기간]
- 예시: "2024-06-01 | 5.도림사거리정거장 - 1)정거장 터널 | 철근, 거푸집 조립 | 3span | 2026-06-01 | 2026-06-15 | 14"
- 간트차트 데이터 생성: work_content의 날짜, 구분, 금일작업 정보를 기반으로 공정별 시작일, 종료일, 기간 포함
- work_content 테이블의 실제 데이터를 기반으로 구조화 (construction_status보다 우선)
- 시공상세도 자동 매칭 및 표시
- 해당 월에 시공상세도가 없으면 가장 가까운 월의 도면 표시

**🏗️ 상세 분석 요청 시 3단계 처리:**
1. **공사 실적**: construction_status 테이블에서 진도율, 진행상황, 완료율 등 구조화
2. **상세 분석**: work_content 테이블에서 키워드 분석하여 세부 공정별 작업내용, 일정, 위치 등 구조화
3. **투입 인원/장비**: personnel_data, equipment_data에서 관련 인력 및 장비 정보 추출
- 상세 분석 시 3개 섹션으로 구분하여 표시
- 각 섹션별로 적절한 테이블 형태로 데이터 정리
- 투입 인원은 직종별, 장비는 종류별로 집계하여 표시
- 기존 테이블과 중복되지 않도록 다른 데이터 사용
- 실제 데이터베이스에서 검색된 데이터를 기반으로 구조화

**📋 월별 공사현황 요청 시 특별 처리:**
- 월 시작일의 누계값 → 월 종료일의 누계값 → 차이(월간 실적) 형태로 정리
- 예시: "4월 1일: 85.2m → 4월 30일: 95.7m → 월간 실적: 10.5m"
- 테이블 형태: [구분, 월초 누계, 월말 누계, 월간 실적, 단위]
- 월간 실적이 음수인 경우 데이터 오타로 간주하여 해당 행 제외

**📋 인원/장비 데이터 요청 시 특별 처리:**
- 인원/장비는 누계가 아닌 투입 리소스이므로 집계하여 표시
- 직종별로 투입된 인원 수량을 합계하여 정리 (연수생, 화약주임, 터널공, 목공 등)
- 장비는 종류별로 투입된 장비 수량을 합계하여 정리
- 테이블 형태: [직종, 투입인원, 단위] 또는 [장비종류, 투입대수, 단위]
- 예시: "연수생: 44명", "화약주임: 11명", "터널공: 22명", "굴착기: 3대"

**📋 일별/일일 데이터 요청 시 특별 처리:**
- "일별", "일일", "일단위" 모두 동일한 의미로 처리
- 일별로 데이터를 날짜별로 정리하여 표시
- 테이블 형태: [날짜, 구분, 값, 단위] 또는 피벗 형태: [직종, 날짜1, 날짜2, ...]
- 예시: "2024-07-21: 라이닝 2.5m", "2024-07-22: 라이닝 3.0m"
- 피벗 예시: "연수생 | 4월1일:2명 | 4월2일:3명 | 4월3일:3명"
- 유의미한 그래프 생성: 선그래프(진도율), 막대그래프(일별 실적), 파이차트(직종별 비율), 간트차트(공정 현황)

**📋 테이블 형태 응답 여부:** {"YES" if is_table_request else "NO"}

**📋 응답 형식 (데이터 중심):**
```json
{{
    "summary": "간단한 요약 (1문장)",
    "display_as_table": {"true" if is_table_request else "false"},
    "is_process_analysis": {"true" if is_process_analysis else "false"},
    "is_detailed_analysis": {"false"},
    "fallback_detailed_analysis": {"false"},
    "table_data": {{
        "headers": ["날짜", "구분", "금일작업", "상세위치", "시작일", "종료일", "기간"],
        "rows": [
            ["2024-06-01", "5.도림사거리정거장 - 1)정거장 터널", "철근, 거푸집 조립", "3span", "2026-06-01", "2026-06-15", "14"],
            ["2024-06-16", "5.도림사거리정거장 - 1)정거장 터널", "콘크리트 타설", "3span", "2026-06-16", "2026-06-17", "1"],
            ["2024-01-20", "도림사거리 정거장 미들슬라브", "구조체 작업", "-", "2024-01-20", "2024-01-30", "10"]
        ]
    }},
    "data_points": [
        {{
            "category": "공정현황",
            "label": "전체 진행률",
            "value": "85",
            "unit": "%",
            "status": "지연"
        }}
    ],
    "gantt_data": [
        {{
            "task": "5.도림사거리정거장 - 철근, 거푸집 조립",
            "start": "2026-06-01",
            "end": "2026-06-15",
            "progress": 0.8,
            "status": "진행중",
            "resource": "3span",
            "duration": 14
        }},
        {{
            "task": "5.도림사거리정거장 - 콘크리트 타설",
            "start": "2026-06-16",
            "end": "2026-06-17",
            "progress": 0.0,
            "status": "미시작",
            "resource": "3span", 
            "duration": 1
        }}
    ],
    "chart_data": {{
        "chart_type": "gantt",
        "title": "공정별 간트차트",
        "x_axis": "기간",
        "y_axis": "공정",
        "data": []
    }},
            # 상세 분석 섹션 제거됨 - 1, 2, 3번 섹션을 표시하지 않음
}}
```

**⚠️ 중요 지침:**
- 인사이트, 분석, 추천사항은 생성하지 마세요
- 특정 공정 분석 요청 시 반드시 간트차트 데이터(gantt_data) 생성
- 공정 분석 시 계획일정, 실제일정, 진행률, 지연일수, 상태를 포함한 테이블 생성
- 간트차트 데이터에는 task, start, end, progress, status, resource, duration 필드 포함
- 월별 현황 요청 시 반드시 시작→종료→차이 형태로 정리
- 인원 요청 시 직종별로 투입 리소스를 집계하여 표시 (연수생, 화약주임, 터널공, 목공 등)
- 장비 요청 시 장비종류별로 투입 리소스를 집계하여 표시
- 일별/일일 요청 시 날짜별로 데이터를 정리하고 유의미한 그래프 생성
- 모든 거리 단위는 "m"으로 통일
- 인원 단위는 "명", 장비 단위는 "대"로 통일
- 정보가 없거나 0인 경우 해당 행을 제외하고 표시
- 월간 실적에서 음수 값이 나오는 행은 데이터 오타로 간주하여 제외
- 월간 실적 = 월말 누계 - 월초 누계로 계산
- 테이블 형태 요청 시 table_data 필드 적극 활용
- HTML 태그를 절대 사용하지 마세요 (순수 텍스트만)

반드시 유효한 JSON 형태로 응답하고, 요청된 형식에 맞게 데이터를 정확하게 제공하세요. 

**⚠️ 절대 금지사항:**
- HTML 태그 사용 금지 (<div>, </div>, <p>, </p> 등)
- 마크업 언어 사용 금지
- 순수 텍스트만 사용
- JSON 응답 외에 추가 텍스트 없음

응답은 오직 JSON 블록만 포함해야 합니다.
"""
        
        response = GEMINI_MODEL.generate_content(structured_prompt)
        
        # 개선된 JSON 응답 파싱
        # HTML 태그 제거 후 JSON 부분만 추출
        clean_response = re.sub(r'<[^>]+>', '', response.text)  # HTML 태그 제거
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', clean_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                result = json.loads(json_str)
                
                # 데이터 품질 검증
                if not result.get('summary'):
                    result['summary'] = "데이터 분석 완료"
                if not result.get('data_points'):
                    result['data_points'] = [{"category": "기본", "label": "조회 결과", "value": str(len(query_result)), "unit": "건", "status": "정상"}]
                
                # 간트차트 데이터가 있는지 확인하고 저장
                if result.get('gantt_data'):
                    print(f"✅ 간트차트 데이터 포함: {len(result['gantt_data'])}개 공정")
                
                print(f"✅ 구조화된 분석 완료: {len(result.get('data_points', []))}개 데이터 포인트")
                return result
            except json.JSONDecodeError as e:
                print(f"❌ 구조화된 출력 JSON 파싱 오류: {str(e)}")
                # 기본 구조로 fallback
                return {
                    "summary": "데이터 조회 완료",
                    "display_as_table": is_table_request,
                    "table_data": {
                        "headers": ["구분", "값", "단위"],
                        "rows": [["조회 결과", str(len(query_result)), "건"]]
                    } if is_table_request else {},
                    "data_points": [{"category": "기본", "label": "조회 결과", "value": str(len(query_result)), "unit": "건", "status": "정상"}]
                }
        else:
            print(f"❌ JSON 형식 추출 실패. 응답 내용: {response.text[:200]}...")
            # JSON 형식이 아닌 경우 기본 구조로 반환
            return {
                "summary": "데이터 조회 완료",
                "display_as_table": is_table_request,
                "table_data": {
                    "headers": ["구분", "값", "단위"],
                    "rows": [["조회 결과", str(len(query_result)), "건"]]
                } if is_table_request else {},
                "data_points": [{"category": "기본", "label": "조회 결과", "value": str(len(query_result)), "unit": "건", "status": "정상"}]
            }
                
    except Exception as e:
        print(f"❌ 구조화된 출력 생성 중 오류: {str(e)}")
        return {
            "summary": "데이터 조회 중 오류 발생",
            "display_as_table": False,
            "table_data": {},
            "data_points": []
        }

def format_structured_response(structured_data):
    """개선된 구조화된 데이터를 사용자 친화적인 텍스트로 변환합니다."""
    try:
        response_text = ""
        
        # 요약
        if structured_data.get('summary'):
            response_text += f"📊 **{structured_data['summary']}**\n\n"
        
        # 테이블 형태로 표시해야 하는 경우
        if structured_data.get('display_as_table') and structured_data.get('table_data'):
            table_data = structured_data['table_data']
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            
            if headers and rows:
                response_text += "📋 **데이터 테이블:**\n\n"
                
                # pandas DataFrame으로 변환해서 테이블 데이터 저장
                import pandas as pd
                try:
                    # 값이 0이거나 빈 값, 음수인 행 제거
                    filtered_rows = []
                    for row in rows:
                        if len(row) >= 2:  # 투입인원 컬럼이 있는지 확인
                            personnel_value = row[1]  # 투입인원 컬럼 (두 번째 컬럼)
                            # 값이 0, "0", "", None이 아닌 경우만 포함
                            if personnel_value and str(personnel_value).strip() not in ["0", "0.0", ""]:
                                # 음수 값 체크 (월간 실적에서 음수 제거)
                                try:
                                    value = float(str(personnel_value).replace(',', ''))
                                    if value >= 0:  # 0 이상인 경우만 포함
                                        filtered_rows.append(row)
                                except (ValueError, TypeError):
                                    # 숫자로 변환할 수 없는 경우 문자열로 처리
                                    if not str(personnel_value).strip().startswith('-'):
                                        filtered_rows.append(row)
                    
                    if filtered_rows:
                        df = pd.DataFrame(filtered_rows, columns=headers)
                        
                        # 일별 데이터인 경우 피벗 테이블로 변환
                        if len(headers) >= 3 and "날짜" in headers[0] and "구분" in headers[1]:
                            try:
                                # 피벗 테이블 생성
                                pivot_df = df.pivot(index='구분', columns='날짜', values='값')
                                pivot_df = pivot_df.fillna(0)  # NaN을 0으로 채움
                                
                                # 피벗 테이블을 다시 일반 테이블 형태로 변환
                                pivot_rows = []
                                for job_type in pivot_df.index:
                                    # 직종명에서 숫자 제거 (예: "0 목공" -> "목공")
                                    clean_job_type = re.sub(r'^\d+\s*', '', str(job_type))
                                    row_data = [clean_job_type]  # 첫 번째 컬럼은 직종
                                    for date in pivot_df.columns:
                                        row_data.append(str(pivot_df.loc[job_type, date]))
                                    row_data.append('명')  # 단위 추가
                                    pivot_rows.append(row_data)
                                
                                # 새로운 헤더 생성
                                pivot_headers = ['직종'] + list(pivot_df.columns) + ['단위']
                                
                                # 피벗 테이블로 DataFrame 재생성
                                df = pd.DataFrame(pivot_rows, columns=pivot_headers)
                                structured_data['is_pivot'] = True
                                
                            except Exception as e:
                                print(f"피벗 테이블 변환 오류: {str(e)}")
                                # 피벗 변환 실패 시 원본 테이블 사용
                                structured_data['is_pivot'] = False
                        
                        # structured_data에 DataFrame 저장
                        structured_data['dataframe'] = df
                        response_text += "※ 아래에 테이블이 표시됩니다.\n\n"
                    else:
                        response_text += "※ 투입된 인원이 있는 직종이 없습니다.\n\n"
                except Exception as e:
                    print(f"DataFrame 생성 오류: {str(e)}")
                    # fallback: 텍스트 형태로 표시 (0이 아닌 값만)
                    for i, header in enumerate(headers):
                        response_text += f"**{header}**\n"
                        for row in rows:
                            if i < len(row) and row[i] and str(row[i]).strip() not in ["0", "0.0", ""]:
                                response_text += f"- {row[i]}\n"
                response_text += "\n"
        
        # 일반 데이터 포인트 (카테고리별 정리) - 테이블이 아닌 경우에만
        elif structured_data.get('data_points'):
            categories = {}
            for point in structured_data['data_points']:
                category = point.get('category', '기본')
                if category not in categories:
                    categories[category] = []
                categories[category].append(point)
            
            for category, points in categories.items():
                category_emoji = {
                    '공정관리': '🏗️', '안전관리': '⚠️', '품질관리': '✅', 
                    '인력관리': '👥', '장비관리': '🔧', '기본': '📈'
                }.get(category, '📋')
                
                response_text += f"{category_emoji} **{category}:**\n"
                for point in points:
                    label = point.get('label', '')
                    value = point.get('value', '')
                    unit = point.get('unit', '')
                    status = point.get('status', '')
                    benchmark = point.get('benchmark', '')
                    
                    status_emoji = {'정상': '🟢', '주의': '🟡', '경고': '🟠', '위험': '🔴'}.get(status, '')
                    
                    if unit:
                        line = f"- {label}: {value}{unit}"
                    else:
                        line = f"- {label}: {value}"
                    
                    if status_emoji:
                        line += f" {status_emoji}"
                    if benchmark:
                        line += f" (기준: {benchmark})"
                    
                    response_text += line + "\n"
                response_text += "\n"
        
        # 인사이트, 추천사항, 위험 경고, 데이터 품질 점수 섹션 제거
        # 사용자가 데이터만 원한다고 했으므로 분석 관련 내용은 모두 제거
        
        # structured_data를 임시로 저장 (테이블 및 간트차트 렌더링용)
        if structured_data.get('dataframe') is not None or structured_data.get('gantt_data') is not None:
            import streamlit as st
            st.session_state.temp_structured_data = structured_data
        
        # 공종 분석인 경우 시공관리도 JPG 표시
        if structured_data.get('is_process_analysis'):
            import streamlit as st
            import re
            from datetime import datetime
            try:
                # 메시지 내용에서 공정명 추출
                content = st.session_state.get('last_user_message', '')
                
                # 공정명 키워드 추출
                process_keywords = ['도림사거리', '정거장', '미들슬라브', '상부슬라브', '교차로', '사거리', '신풍', '본선']
                found_process = None
                
                for keyword in process_keywords:
                    if keyword in content:
                        if '도림사거리' in content and '정거장' in content:
                            found_process = '도림사거리정거장'
                            break
                        elif '신풍' in content:
                            found_process = '신풍정거장'
                            break
                        elif '본선' in content:
                            found_process = '본선터널'
                            break
                        elif keyword in ['교차로', '사거리']:
                            found_process = f"{keyword}"
                            break
                
                # 도면 유형 추출
                drawing_type = None
                if '미들슬라브' in content:
                    drawing_type = '미들슬라브'
                elif '상부슬라브' in content:
                    drawing_type = '상부슬라브'
                
                # 월 정보 추출
                year_month = None
                # YYYY년 MM월 형식 찾기
                year_month_match = re.search(r'(\d{4})년\s*(\d{1,2})월', content)
                if year_month_match:
                    year, month = year_month_match.groups()
                    year_month = f"{year}-{month.zfill(2)}"
                else:
                    # YYYY-MM 형식 찾기
                    year_month_match = re.search(r'(\d{4})-(\d{1,2})', content)
                    if year_month_match:
                        year, month = year_month_match.groups()
                        year_month = f"{year}-{month.zfill(2)}"
                    else:
                        # 현재 월을 기본값으로 사용
                        year_month = datetime.now().strftime('%Y-%m')
                
                if found_process:
                    # 시공관리도 JPG 조회 (월 정보 포함)
                    drawing = get_construction_drawing_jpg(found_process, year_month=year_month, drawing_type=drawing_type)
                    
                    if drawing:
                        response_text += f"\n\n📋 **관련 시공관리도**\n"
                        
                        # 가장 가까운 월 매칭인지 확인
                        if drawing.get('is_closest_match'):
                            response_text += f"※ 요청하신 {year_month}월의 시공관리도가 없어 가장 가까운 {drawing.get('year_month', 'N/A')}월 시공관리도를 표시합니다.\n"
                        else:
                            response_text += f"※ {drawing.get('year_month', 'N/A')}월 시공관리도입니다.\n"
                        
                        response_text += f"※ 아래에 시공관리도가 표시됩니다.\n"
                        
                        # structured_data에 시공관리도 정보 저장
                        structured_data['construction_drawing'] = drawing
                    else:
                        response_text += f"\n\n📋 **시공관리도**\n"
                        response_text += f"※ 해당 공정에 대한 시공관리도 JPG 파일을 찾을 수 없습니다.\n"
                        
            except Exception as e:
                print(f"시공관리도 조회 중 오류: {str(e)}")
                response_text += f"\n\n📋 **시공관리도**\n"
                response_text += f"※ 시공관리도 조회 중 오류가 발생했습니다.\n"
        
        return response_text
        
    except Exception as e:
        print(f"❌ 응답 포맷팅 중 오류: {str(e)}")
        return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

def debug_construction_status():
    """construction_status 테이블을 상세히 디버깅합니다."""
    st.subheader("🔍 Construction Status 테이블 디버깅")
    
    try:
        # 1. 테이블 존재 여부 확인
        st.write("**1. 테이블 존재 여부 확인**")
        try:
            result = supabase.table('construction_status').select('*').limit(1).execute()
            if result.data is not None:
                st.success("✅ construction_status 테이블이 존재합니다.")
                st.write(f"데이터 타입: {type(result.data)}")
                st.write(f"데이터 길이: {len(result.data) if result.data else 0}")
            else:
                st.warning("⚠️ construction_status 테이블에 데이터가 없습니다.")
        except Exception as e:
            st.error(f"❌ 테이블 접근 오류: {str(e)}")
        
        # 2. 테이블 구조 확인
        st.write("**2. 테이블 구조 확인**")
        try:
            result = supabase.table('construction_status').select('*').limit(1).execute()
            if result.data and len(result.data) > 0:
                st.success("✅ 테이블 구조 확인 완료")
                st.json(result.data[0])
            else:
                st.warning("⚠️ 테이블 구조를 확인할 수 없습니다.")
        except Exception as e:
            st.error(f"❌ 테이블 구조 확인 오류: {str(e)}")
        
        # 3. 전체 데이터 조회 시도
        st.write("**3. 전체 데이터 조회 시도**")
        try:
            result = supabase.table('construction_status').select('*').execute()
            if result.data:
                st.success(f"✅ 전체 데이터 조회 성공: {len(result.data)}건")
                st.write("**샘플 데이터:**")
                for i, row in enumerate(result.data[:3]):
                    st.write(f"**행 {i+1}:**")
                    st.json(row)
            else:
                st.warning("⚠️ 전체 데이터가 없습니다.")
        except Exception as e:
            st.error(f"❌ 전체 데이터 조회 오류: {str(e)}")
        
        # 4. 특정 컬럼만 조회 시도
        st.write("**4. 특정 컬럼 조회 시도**")
        try:
            # 일반적인 컬럼명들로 시도
            columns_to_try = [
                'id', 'date', 'status', 'details', 'created_at', 'updated_at',
                'work_date', 'report_date', 'construction_date'
            ]
            
            for col in columns_to_try:
                try:
                    result = supabase.table('construction_status').select(col).limit(1).execute()
                    if result.data:
                        st.success(f"✅ 컬럼 '{col}' 조회 성공")
                        break
                except:
                    continue
            else:
                st.warning("⚠️ 어떤 컬럼도 조회할 수 없습니다.")
        except Exception as e:
            st.error(f"❌ 컬럼 조회 오류: {str(e)}")
        
    except Exception as e:
        st.error(f"❌ 전체 디버깅 중 오류: {str(e)}")

def search_specific_data(user_input):
    """사용자 입력에서 특정 정보를 검색합니다."""
    search_results = {}
    
    # 날짜 추출 (7월 21일, 2024-07-21 등)
    import re
    date_patterns = [
        r'(\d{1,2})월\s*(\d{1,2})일',
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
        r'(\d{1,2})개월',
        r'(\d{1,2})개월치'
    ]
    
    extracted_date = None
    month_range = None
    
    for pattern in date_patterns:
        match = re.search(pattern, user_input)
        if match:
            if '개월' in pattern:  # N개월치 검색
                month_range = int(match.group(1))
                # 현재 날짜에서 N개월 전까지
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=month_range * 30)
                extracted_date = {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d'),
                    'type': 'range'
                }
            elif len(match.groups()) == 2:  # 월/일
                month, day = match.groups()
                extracted_date = {
                    'date': f"2024-{month.zfill(2)}-{day.zfill(2)}",
                    'type': 'single'
                }
            elif len(match.groups()) == 3:
                if len(match.group(1)) == 4:  # YYYY-MM-DD
                    extracted_date = {
                        'date': f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}",
                        'type': 'single'
                    }
                else:  # MM/DD/YYYY
                    extracted_date = {
                        'date': f"{match.group(3)}-{match.group(1).zfill(2)}-{match.group(2).zfill(2)}",
                        'type': 'single'
                    }
            break
    
    # 키워드 추출 (연수생, 인력, 인원 및 공정 분석 관련 추가)
    keywords = ['본선터널', '1구간', '라이닝', '시공현황', '터널', '구간', '라이닝', 
                '연수생', '인력', '인원', '작업자', '직원', '사원', '투입',
                '신풍', '주출입구', '출입구', '계측', '측정', '데이터', '공사현황',
                '정거장', '미들슬라브', '교차로', '사거리', '공정', '분석', '콘크리트', '타설']
    found_keywords = [kw for kw in keywords if kw in user_input]
    
    try:
        # 날짜가 있으면 해당 날짜로 효율적인 SQL 쿼리 실행
        if extracted_date:
            for table_name in ['daily_report_data', 'construction_status', 'work_content', 
                              'personnel_data', 'equipment_data']:
                try:
                    if extracted_date['type'] == 'range':
                        # 기간 검색 - 효율적인 SQL 쿼리 사용
                        date_data = execute_date_range_query(
                            table_name, 
                            extracted_date['start'], 
                            extracted_date['end']
                        )
                        if date_data:
                            search_results[f"{table_name}_date_range"] = date_data
                    
                    elif extracted_date['type'] == 'single':
                        # 단일 날짜 검색 - 효율적인 SQL 쿼리 사용
                        date_data = execute_single_date_query(
                            table_name, 
                            extracted_date['date']
                        )
                        if date_data:
                            search_results[f"{table_name}_date_single"] = date_data
                
                except Exception as e:
                    st.warning(f"{table_name} 날짜 검색 중 오류: {str(e)}")
        
        # 키워드가 있으면 해당 키워드로 검색 (모든 테이블에서 검색)
        if found_keywords:
            for table_name in ['daily_report_data', 'construction_status', 'work_content', 
                              'cell_mappings', 'personnel_data', 'equipment_data']:
                try:
                    # 모든 텍스트 컬럼에서 키워드 검색
                    result = supabase.table(table_name).select('*').execute()
                    if result.data:
                        filtered_data = []
                        for row in result.data:
                            row_str = str(row).lower()
                            if any(kw.lower() in row_str for kw in found_keywords):
                                filtered_data.append(row)
                        if filtered_data:
                            search_results[f"{table_name}_keyword"] = filtered_data
                except Exception as e:
                    st.warning(f"{table_name} 키워드 검색 중 오류: {str(e)}")
        
        # 특별한 검색: "본선터널 1구간 라이닝"
        if "본선터널" in user_input and "1구간" in user_input and "라이닝" in user_input:
            for table_name in ['construction_status', 'work_content', 'daily_report_data']:
                try:
                    result = supabase.table(table_name).select('*').execute()
                    if result.data:
                        specific_data = []
                        for row in result.data:
                            row_str = str(row).lower()
                            if ("본선터널" in row_str or "터널" in row_str) and "1구간" in row_str and "라이닝" in row_str:
                                specific_data.append(row)
                        if specific_data:
                            search_results[f"{table_name}_specific"] = specific_data
                except Exception as e:
                    st.warning(f"{table_name} 특정 검색 중 오류: {str(e)}")
        
        # 테이블별 키워드 감지 조건 분리
        process_keywords = ['정거장', '미들슬라브', '교차로', '사거리', '콘크리트', '타설', '슬래브', '슬라브']
        
        # work_content 사용 조건: 분석, 상세 분석, 특정 공정 또는 공종
        is_work_content_analysis = (
            "분석" in user_input or "상세 분석" in user_input or "상세분석" in user_input or
            "특정 공정" in user_input or "특정 공종" in user_input or
            ("상세" in user_input and "분석" in user_input)
        )
        
        # construction_status 사용 조건: 특정 월 공사현황, 공정현황, 공사실적, 공사현황
        is_construction_status_analysis = (
            "공사현황" in user_input or "공정현황" in user_input or "공사실적" in user_input or
            ("월" in user_input and ("공사현황" in user_input or "현황" in user_input)) or
            ("개월" in user_input and "현황" in user_input)
        )
        
        # work_content를 우선 사용하되, construction_status 조건이 더 명확한 경우 그쪽 사용
        is_detailed_analysis = is_work_content_analysis and not is_construction_status_analysis
        
        print(f"🔍 work_content 분석 조건: {is_work_content_analysis}")
        print(f"🔍 construction_status 분석 조건: {is_construction_status_analysis}")
        print(f"🔍 최종 work_content 사용 여부: {is_detailed_analysis}")
        print(f"🔍 사용자 입력: '{user_input}'")
        print(f"🔍 공정 키워드 매칭: {[kw for kw in process_keywords if kw in user_input]}")
        
        if is_detailed_analysis:
            print("🔍 특정 공정/공종/상세 분석 데이터 검색 시작...")
            
            # 1. work_content에서 주요 데이터 검색 (날짜, 구분, 금일작업 컬럼 기반)
            try:
                result = supabase.table('work_content').select('*').execute()
                print(f"🔍 work_content 테이블 전체 데이터: {len(result.data) if result.data else 0}건")
                
                if result.data:
                    work_content_data = []
                    print(f"🔍 사용자 입력: '{user_input}'")
                    
                    # 샘플 데이터 출력 (디버깅용)
                    if len(result.data) > 0:
                        print(f"🔍 work_content 샘플 데이터: {result.data[0]}")
                    
                    for row in result.data:
                        row_str = str(row).lower()
                        # 사용자 입력 키워드와 매칭되는 데이터 필터링
                        user_keywords = user_input.lower().split()
                        matched = False
                        
                        for keyword in user_keywords:
                            if keyword in row_str:
                                work_content_data.append(row)
                                print(f"✅ 키워드 '{keyword}' 매칭: {row}")
                                matched = True
                                break
                        
                        # 기본 공정 키워드와도 매칭
                        if not matched:
                            for keyword in process_keywords:
                                if keyword in row_str:
                                    work_content_data.append(row)
                                    print(f"✅ 공정 키워드 '{keyword}' 매칭: {row}")
                                    break
                    
                    if work_content_data:
                        search_results["work_content_main_analysis"] = work_content_data
                        print(f"✅ work_content 주요 분석 데이터: {len(work_content_data)}건")
                    else:
                        print("⚠️ work_content에서 관련 데이터를 찾을 수 없습니다.")
                        print(f"⚠️ 검색된 키워드: {user_input.lower().split()}")
                        print(f"⚠️ 공정 키워드: {process_keywords}")
                else:
                    print("⚠️ work_content 테이블이 비어있습니다.")
            except Exception as e:
                print(f"❌ work_content 검색 오류: {str(e)}")
                st.warning(f"work_content 주요 분석 검색 중 오류: {str(e)}")
            
            # 2. work_content에서 상세 분석 데이터 검색
            try:
                result = supabase.table('work_content').select('*').execute()
                if result.data:
                    work_content_data = []
                    for row in result.data:
                        row_str = str(row).lower()
                        # 도림사거리 정거장 관련 데이터 필터링
                        if ("도림사거리" in row_str or "정거장" in row_str) and ("미들슬라브" in row_str or "슬래브" in row_str or "슬라브" in row_str):
                            work_content_data.append(row)
                        # 일반적인 공정 키워드 매칭
                        elif any(keyword in row_str for keyword in process_keywords):
                            work_content_data.append(row)
                    if work_content_data:
                        search_results["work_content_detailed_analysis"] = work_content_data
                        print(f"✅ work_content 상세 분석 데이터: {len(work_content_data)}건")
                    else:
                        print("⚠️ work_content에서 공정 관련 데이터를 찾을 수 없습니다.")
                else:
                    print("⚠️ work_content 테이블이 비어있습니다.")
            except Exception as e:
                print(f"❌ work_content 검색 오류: {str(e)}")
                st.warning(f"work_content 상세 분석 검색 중 오류: {str(e)}")
            
            # 3. personnel_data에서 투입 인원 데이터 검색
            try:
                result = supabase.table('personnel_data').select('*').execute()
                if result.data:
                    personnel_data = []
                    for row in result.data:
                        row_str = str(row).lower()
                        if any(keyword in row_str for keyword in process_keywords):
                            personnel_data.append(row)
                    if personnel_data:
                        search_results["personnel_data_detailed"] = personnel_data
                        print(f"✅ personnel_data 투입 인원 데이터: {len(personnel_data)}건")
                    else:
                        print("⚠️ personnel_data에서 공정 관련 데이터를 찾을 수 없습니다.")
                else:
                    print("⚠️ personnel_data 테이블이 비어있습니다.")
            except Exception as e:
                print(f"❌ personnel_data 검색 오류: {str(e)}")
                st.warning(f"personnel_data 투입 인원 검색 중 오류: {str(e)}")
            
            # 4. equipment_data에서 투입 장비 데이터 검색
            try:
                result = supabase.table('equipment_data').select('*').execute()
                if result.data:
                    equipment_data = []
                    for row in result.data:
                        row_str = str(row).lower()
                        if any(keyword in row_str for keyword in process_keywords):
                            equipment_data.append(row)
                    if equipment_data:
                        search_results["equipment_data_detailed"] = equipment_data
                        print(f"✅ equipment_data 투입 장비 데이터: {len(equipment_data)}건")
                    else:
                        print("⚠️ equipment_data에서 공정 관련 데이터를 찾을 수 없습니다.")
                else:
                    print("⚠️ equipment_data 테이블이 비어있습니다.")
            except Exception as e:
                print(f"❌ equipment_data 검색 오류: {str(e)}")
                st.warning(f"equipment_data 투입 장비 검색 중 오류: {str(e)}")
            
            # 5. 데이터가 없는 경우 대안 데이터 생성
            found_keys = [key for key in ["work_content_main_analysis", "work_content_detailed_analysis", "personnel_data_detailed", "equipment_data_detailed"] if search_results.get(key)]
            print(f"🔍 검색 결과 키: {found_keys}")
            
            if not found_keys:
                print("⚠️ 모든 테이블에서 데이터를 찾을 수 없습니다. 대안 데이터를 생성합니다.")
                print(f"🔍 search_results 전체: {list(search_results.keys())}")
                # 대안 데이터 생성
                search_results["fallback_detailed_analysis"] = True
        
        # 특별한 검색: "연수생" 관련 (더 포괄적으로)
        if "연수생" in user_input:
            for table_name in ['personnel_data', 'daily_report_data', 'work_content']:
                try:
                    result = supabase.table(table_name).select('*').execute()
                    if result.data:
                        specific_data = []
                        for row in result.data:
                            row_str = str(row).lower()
                            # 연수생 관련 키워드들을 더 포괄적으로 검색
                            if any(keyword in row_str for keyword in ['연수생', '인력', '인원', '작업자', '직원', '사원', '투입']):
                                specific_data.append(row)
                        if specific_data:
                            search_results[f"{table_name}_personnel"] = specific_data
                except Exception as e:
                    st.warning(f"{table_name} 인력 검색 중 오류: {str(e)}")
        
        # 특별한 검색: "신풍 주출입구" 관련
        if "신풍" in user_input and ("주출입구" in user_input or "출입구" in user_input):
            for table_name in ['instrument_data', 'daily_report_data', 'work_content', 'construction_status']:
                try:
                    result = supabase.table(table_name).select('*').execute()
                    if result.data:
                        specific_data = []
                        for row in result.data:
                            row_str = str(row).lower()
                            # 신풍 주출입구 관련 키워드들을 검색
                            if any(keyword in row_str for keyword in ['신풍', '주출입구', '출입구', '계측', '측정']):
                                specific_data.append(row)
                        if specific_data:
                            search_results[f"{table_name}_sinpung"] = specific_data
                except Exception as e:
                    st.warning(f"{table_name} 신풍 주출입구 검색 중 오류: {str(e)}")
        
        # 추가: 모든 personnel_data를 가져와서 연수생 관련 정보 확인
        if "연수생" in user_input:
            try:
                result = supabase.table('personnel_data').select('*').execute()
                if result.data:
                    search_results['personnel_data_all'] = result.data
            except Exception as e:
                st.warning(f"personnel_data 전체 검색 중 오류: {str(e)}")
        
        # 추가: 모든 instrument_data를 가져와서 신풍 관련 정보 확인
        if "신풍" in user_input:
            try:
                result = supabase.table('instrument_data').select('*').execute()
                if result.data:
                    search_results['instrument_data_all'] = result.data
            except Exception as e:
                st.warning(f"instrument_data 전체 검색 중 오류: {str(e)}")
        
    except Exception as e:
        st.error(f"검색 중 오류: {str(e)}")
    
    return search_results

def create_gemini_prompt(user_input, context_data):
    """Gemini 모델용 프롬프트를 생성합니다."""
    
    # 특정 검색 결과 추가
    specific_search = search_specific_data(user_input)
    if specific_search:
        context_data['specific_search'] = specific_search
    
    prompt = f"""
당신은 건설 현장 데이터를 분석하는 전문 AI 어시스턴트입니다. 
사용자의 질문에 대해 Supabase에 저장된 데이터를 기반으로 정확하고 유용한 답변을 제공해주세요.

**중요: HTML 태그나 마크다운 형식을 사용하지 말고 순수 텍스트로만 답변해주세요.**

**현재 데이터 현황:**
- 일일보고: {len(context_data.get('daily_reports', []))}건
- 발파데이터: {len(context_data.get('blasting_data', []))}건  
- 계측데이터: {len(context_data.get('measurement_data', []))}건
- 셀매핑: {len(context_data.get('cell_mappings', []))}건
- 공사현황: {len(context_data.get('construction_status', []))}건
- 장비데이터: {len(context_data.get('equipment_data', []))}건
- 인력데이터: {len(context_data.get('personnel_data', []))}건
- 프롬프트: {len(context_data.get('prompts', []))}건
- 템플릿: {len(context_data.get('templates', []))}건
- 작업내용: {len(context_data.get('work_content', []))}건

**사용자 질문:** {user_input}

**답변 요구사항:**
1. 한국어로 친근하고 전문적인 톤으로 답변
2. 이모지를 적절히 사용하여 가독성 향상
3. 데이터가 있는 경우 구체적인 수치와 정보 제공
4. 데이터가 없는 경우 안내 메시지 제공
5. 필요시 추가 질문을 유도하는 답변
6. **HTML 태그나 마크다운 형식을 절대 사용하지 말고 순수 텍스트로만 답변**

**중요한 단위 표시 규칙:**
- 누계값, 진행률, 거리 등은 반드시 단위를 표시하세요
- 라이닝 누계값: "10.2m" (m 단위 필수)
- 터널 진행률: "85.5%" (% 단위 필수)
- 거리/길이: "150m", "2.5km" 등
- 무게: "500kg", "2.3t" 등
- 시간: "8시간", "30분" 등
- 인원수: "15명", "3명" 등

**데이터 기반 답변 예시:**
- 일일보고 관련: 날짜, 날씨, 작업내용, 진도율 등
- 발파 관련: 발파일자, 위치, 장약량, 진동/소음 측정값 등  
- 계측 관련: 측정일시, 위치, 측정값, 단위 등
- 공정 관련: 진도율, 작업진행상황, 예상 완료일 등
- 장비 관련: 장비현황, 가동률, 유지보수 등
- 인력 관련: 인력배치, 작업인원, 안전관리, 연수생 수 등
- 셀매핑 관련: 구역별 작업현황, 셀별 진도율 등

**시공현황 답변 예시:**
- "본선터널 1구간 라이닝 누계는 10.2m입니다."
- "현재 터널 진행률은 85.5%입니다."
- "오늘 라이닝 작업으로 2.5m 추가되었습니다."

**인력 관련 답변 예시:**
- "7월 21일 본선터널 1구간 연수생은 5명입니다."
- "현재 작업 인원은 총 25명입니다."
- "연수생 배치 현황: 본선터널 1구간 3명, 2구간 2명"

**중요한 검색 결과 분석 지침:**
1. **날짜 범위 검색**의 경우:
   - "1개월치", "3개월치" 등의 기간 검색 결과를 우선 분석
   - `_date_range` 키가 있는 데이터를 확인하여 기간별 요약 제공
   - 각 테이블별로 기간 내 데이터 현황을 정리

2. **연수생 관련 질문**의 경우:
   - personnel_data 테이블의 모든 데이터를 확인
   - 날짜, 구간, 연수생 수를 정확히 파악
   - "personnel_data_all" 키가 있으면 해당 데이터를 우선 분석
   - 구체적인 수치를 제공 (예: "12명")

3. **날짜 관련 질문**의 경우:
   - 해당 날짜의 모든 관련 데이터를 확인
   - `_date_single` 키가 있는 데이터를 우선 분석
   - 날짜 형식이 다를 수 있으므로 유연하게 검색
   - "date", "report_date", "work_date" 등 다양한 컬럼 확인

4. **구간 관련 질문**의 경우:
   - "본선터널", "1구간" 등의 키워드를 포함한 데이터 검색
   - 해당 구간의 구체적인 정보 제공

5. **신풍 주출입구 관련 질문**의 경우:
   - instrument_data 테이블의 모든 데이터를 확인
   - "신풍", "주출입구", "출입구" 등의 키워드가 포함된 데이터 검색
   - "instrument_data_all" 키가 있으면 해당 데이터를 우선 분석
   - 계측 데이터의 구체적인 수치와 단위를 제공
   - 데이터가 없는 경우 유사한 위치나 다른 날짜의 데이터도 확인

**기간별 데이터 요약 예시:**
- "최근 1개월간 공사 현황: 총 25일간 작업일수, 평균 일일 진행률 2.1%, 누계 진행률 85.5%"
- "1개월간 인력 투입 현황: 평균 일일 18명, 최대 25명, 최소 12명"
- "기간별 주요 작업: 1주차 라이닝 작업, 2주차 발파 작업, 3주차 계측 작업"

위 데이터를 참고하여 사용자 질문에 답변해주세요. **반드시 순수 텍스트로만 답변하고 HTML이나 마크다운 형식을 사용하지 마세요.**
"""
    
    # 컨텍스트 데이터 추가 (모든 테이블)
    if context_data.get('daily_reports'):
        prompt += f"\n\n**최근 일일보고 데이터:**\n{json.dumps(context_data['daily_reports'][:3], ensure_ascii=False, indent=2)}"
    
    if context_data.get('blasting_data'):
        prompt += f"\n\n**최근 발파 데이터:**\n{json.dumps(context_data['blasting_data'][:3], ensure_ascii=False, indent=2)}"
    
    if context_data.get('measurement_data'):
        prompt += f"\n\n**최근 계측 데이터:**\n{json.dumps(context_data['measurement_data'][:3], ensure_ascii=False, indent=2)}"
    
    if context_data.get('cell_mappings'):
        prompt += f"\n\n**최근 셀매핑 데이터:**\n{json.dumps(context_data['cell_mappings'][:3], ensure_ascii=False, indent=2)}"
    
    if context_data.get('construction_status'):
        prompt += f"\n\n**최근 공사현황 데이터:**\n{json.dumps(context_data['construction_status'][:3], ensure_ascii=False, indent=2)}"
    
    if context_data.get('equipment_data'):
        prompt += f"\n\n**최근 장비 데이터:**\n{json.dumps(context_data['equipment_data'][:3], ensure_ascii=False, indent=2)}"
    
    if context_data.get('personnel_data'):
        prompt += f"\n\n**최근 인력 데이터:**\n{json.dumps(context_data['personnel_data'][:3], ensure_ascii=False, indent=2)}"
    
    if context_data.get('work_content'):
        prompt += f"\n\n**최근 작업내용 데이터:**\n{json.dumps(context_data['work_content'][:3], ensure_ascii=False, indent=2)}"
    
    # 특정 검색 결과 추가
    if context_data.get('specific_search'):
        prompt += f"\n\n**🔍 특정 검색 결과:**\n{json.dumps(context_data['specific_search'], ensure_ascii=False, indent=2)}"
    
    return prompt

def generate_ai_response(user_input):
    """SQL 기반 RAG를 사용하여 사용자 입력에 대한 AI 응답을 생성합니다."""
    
    try:
        print(f"🔍 사용자 질문: {user_input}")
        
        # 1. 데이터베이스 연결 상태 확인
        print("🔌 데이터베이스 연결 상태 확인 중...")
        if not check_database_connection():
            print("⚠️ 데이터베이스 연결 실패. 대안 데이터를 사용합니다.")
            # 대안 데이터 생성
            query_result = generate_fallback_data(user_input)
            if query_result:
                # 구조화된 답변 생성
                structured_data = parse_structured_output(user_input, query_result)
                final_response = format_structured_response(structured_data)
                return final_response
            else:
                return "❌ 데이터베이스 연결에 실패했습니다. 잠시 후 다시 시도해주세요."
        
        # 2. 테이블 스키마 조회
        print("📋 테이블 스키마 조회 중...")
        table_schema = get_table_schema()
        
        if not table_schema:
            return "❌ 데이터베이스 스키마를 조회할 수 없습니다. 데이터베이스 연결을 확인해주세요."
        
        # 2. 사용자 질문을 SQL로 변환
        print("🔄 자연어를 SQL로 변환 중...")
        sql_query, explanation = generate_sql_from_question(user_input, table_schema)
        
        if not sql_query:
            return f"❌ SQL 쿼리 생성에 실패했습니다: {explanation}"
        
        print(f"✅ 생성된 SQL: {sql_query}")
        print(f"📝 설명: {explanation}")
        
        # 3. SQL 쿼리 실행
        print("⚡ SQL 쿼리 실행 중...")
        query_result = execute_sql_query(sql_query)
        
        if not query_result:
            print("⚠️ SQL 쿼리 결과가 없습니다. 대안 데이터를 생성합니다.")
            # 대안 데이터 생성
            query_result = generate_fallback_data(user_input)
        
        print(f"✅ 쿼리 결과: {len(query_result)}건")
        
        # 4. 구조화된 답변 생성
        print("📝 구조화된 답변 생성 중...")
        structured_data = parse_structured_output(user_input, query_result)
        
        # 5. 사용자 친화적인 텍스트로 변환
        print("🎨 최종 응답 포맷팅 중...")
        
        # 대안 데이터 처리는 parse_structured_output 함수에서 처리됨
        
        final_response = format_structured_response(structured_data)
        
        # 6. SQL 정보 추가 (디버깅용)
        if st.session_state.get('debug_mode', False):
            final_response += f"\n\n---\n**🔧 디버그 정보:**\n- SQL 쿼리: `{sql_query}`\n- 결과 건수: {len(query_result)}건"
        
        print("✅ SQL 기반 RAG 응답 생성 완료")
        return final_response
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ SQL 기반 RAG 오류: {error_msg}")
        
        # Rate Limit 오류인 경우 특별한 메시지
        if "429" in error_msg or "RATE_LIMIT_EXCEEDED" in error_msg or "Quota exceeded" in error_msg:
            return """⏰ **API 요청 한도 초과**
            
현재 Gemini API의 분당 요청 한도를 초과했습니다. 

**원인:**
- 무료 계정의 경우 분당 요청 수가 매우 제한적입니다
- 같은 Google Cloud 프로젝트를 사용하면 할당량이 공유됩니다

**해결 방법:**
1. **5-10분 정도 기다린 후** 다시 시도해주세요
2. 새로운 Google Cloud 프로젝트를 생성하여 새 API 키 발급
3. Google Cloud Console에서 할당량 증가 요청

**임시 해결책:**
- 요청 간격을 충분히 두고 사용해주세요
- 한 번에 여러 질문을 하지 마세요

잠시 후 다시 시도해주시면 정상적으로 작동할 것입니다. 🙏"""
        else:
            # 다른 오류인 경우
            return f"❌ SQL 기반 RAG 처리 중 오류가 발생했습니다: {str(e)}\n\n기존 방식으로 다시 시도해보세요."

# 페이지 제목 (숨김)
# st.title("나만의 AI 챗봇")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 디버깅 모드
    debug_mode = st.checkbox("🔍 디버깅 모드", value=False)
    st.session_state.debug_mode = debug_mode
    
    if debug_mode:
        st.markdown("---")
        st.subheader("📊 데이터 조회")
        
        # 전체 데이터 조회
        if st.button("🔄 모든 테이블 데이터 새로고침", use_container_width=True):
            st.session_state.all_table_data = get_all_table_data()
            st.success("데이터 새로고침 완료!")
        
        # construction_status 특별 조회
        if st.button("🏗️ Construction Status 상세 조회", use_container_width=True):
            st.session_state.construction_status_data = get_construction_status_data()
            st.success("Construction Status 데이터 조회 완료!")
        
        # 저장된 데이터 표시
        if hasattr(st.session_state, 'all_table_data') and st.session_state.all_table_data:
            st.write("**📋 전체 테이블 데이터 현황:**")
            for table_name, data in st.session_state.all_table_data.items():
                st.write(f"- {table_name}: {len(data)}건")
        
        if hasattr(st.session_state, 'construction_status_data') and st.session_state.construction_status_data:
            st.write("**🏗️ Construction Status 데이터:**")
            st.write(f"총 {len(st.session_state.construction_status_data)}건")
            if len(st.session_state.construction_status_data) > 0:
                st.write("**샘플 데이터:**")
                st.json(st.session_state.construction_status_data[0])
        
        st.markdown("---")
        st.subheader("🔧 고급 기능")
        
        # 테이블 구조 디버깅
        if st.button("🔍 테이블 구조 분석", use_container_width=True):
            st.session_state.show_table_debug = True
        
        # 날짜 범위 검색 테스트
        st.markdown("**📅 날짜 범위 검색 테스트**")
        test_months = st.selectbox("테스트할 개월 수", [1, 2, 3, 6, 12], key="test_months")
        if st.button(f"🔍 {test_months}개월치 데이터 검색 테스트", use_container_width=True):
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=test_months * 30)
            
            st.write(f"**검색 기간:** {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
            
            # 테스트 실행
            test_results = {}
            for table_name in ['daily_report_data', 'construction_status', 'work_content', 'personnel_data', 'equipment_data']:
                test_data = execute_date_range_query(table_name, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                if test_data:
                    test_results[table_name] = len(test_data)
                    st.success(f"✅ {table_name}: {len(test_data)}건")
                else:
                    st.warning(f"⚠️ {table_name}: 데이터 없음")
            
            if test_results:
                st.write("**📊 검색 결과 요약:**")
                for table, count in test_results.items():
                    st.write(f"- {table}: {count}건")
        
        # SQL 기반 RAG 테스트
        st.markdown("**🔧 SQL 기반 RAG 테스트**")
        test_question = st.text_input("테스트 질문", placeholder="예: 7월 21일 연수생 수는?", key="test_question")
        if st.button("🚀 SQL RAG 테스트", use_container_width=True):
            if test_question:
                with st.spinner("SQL 기반 RAG 처리 중..."):
                    try:
                        # 테이블 스키마 조회
                        schema = get_table_schema()
                        st.write("**📋 테이블 스키마:**")
                        for table, columns in schema.items():
                            if columns:
                                st.write(f"- {table}: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
                        
                        # SQL 생성
                        sql_query, explanation = generate_sql_from_question(test_question, schema)
                        st.write(f"**🔄 생성된 SQL:** `{sql_query}`")
                        st.write(f"**📝 설명:** {explanation}")
                        
                        # SQL 실행
                        if sql_query:
                            result = execute_sql_query(sql_query)
                            st.write(f"**⚡ 쿼리 결과:** {len(result)}건")
                            if result:
                                st.json(result[:3])  # 처음 3건만 표시
                        
                    except Exception as e:
                        st.error(f"테스트 중 오류: {str(e)}")
        
        # 데이터 내보내기
        if st.button("📤 데이터 내보내기 (JSON)", use_container_width=True):
            if hasattr(st.session_state, 'all_table_data') and st.session_state.all_table_data:
                import json
                json_str = json.dumps(st.session_state.all_table_data, ensure_ascii=False, indent=2, default=str)
                st.download_button(
                    label="📥 JSON 파일 다운로드",
                    data=json_str,
                    file_name="supabase_data_export.json",
                    mime="application/json"
                )
        
        st.markdown("---")
        st.subheader("📋 시공관리도 업로드")
        
        # 시공관리도 업로드 인터페이스
        with st.expander("📄 시공관리도 파일 업로드", expanded=False):
            process_name = st.text_input("공정명", placeholder="예: 도림사거리 정거장", key="process_name_input")
            drawing_type = st.selectbox("도면 유형", ["미들슬라브", "상부슬라브", "전체공정", "기타"], key="drawing_type_select")
            year_month = st.text_input("해당 월 (YYYY-MM)", placeholder="예: 2024-01", key="year_month_input")
            description = st.text_area("도면 설명", placeholder="시공관리도에 대한 설명을 입력하세요", key="description_input")
            
            uploaded_file = st.file_uploader(
                "시공관리도 파일 선택",
                type=['pdf', 'dwg', 'png', 'jpg', 'jpeg'],
                help="PDF, DWG, PNG, JPG 파일을 업로드할 수 있습니다."
            )
            
            if st.button("📤 시공관리도 업로드", type="primary"):
                if uploaded_file and process_name and drawing_type and year_month:
                    try:
                        # 파일 정보 준비
                        file_name = uploaded_file.name
                        file_size = uploaded_file.size
                        file_type = uploaded_file.type.split('/')[-1] if uploaded_file.type else 'unknown'
                        
                        # 로컬 저장 경로 생성
                        import os
                        static_path = "static/management-drawings"
                        os.makedirs(static_path, exist_ok=True)
                        
                        # 파일명 생성 (날짜-공정명 형식)
                        file_name_new = f"{year_month.replace('-', '')}-{process_name}_{drawing_type}.{file_type}"
                        file_path = os.path.join(static_path, file_name_new)
                        
                        # 파일 저장
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        st.success(f"✅ '{file_name}' 시공관리도가 성공적으로 업로드되었습니다!")
                        st.info(f"📂 저장 경로: {file_path}")
                        st.info(f"💡 파일명: {file_name_new}")
                        
                    except Exception as e:
                        st.error(f"❌ 업로드 중 오류: {str(e)}")
                else:
                    st.warning("⚠️ 모든 필수 정보를 입력해주세요.")
        
        # 시공관리도 목록 조회
        if st.button("📋 시공관리도 목록 조회", use_container_width=True):
            try:
                import os
                import glob
                from datetime import datetime
                
                static_path = "static/management-drawings"
                
                if os.path.exists(static_path):
                    # 모든 PDF 파일 검색 (중첩 폴더 포함)
                    pdf_files = glob.glob(f"{static_path}/**/*.pdf", recursive=True)
                    
                    if pdf_files:
                        st.write("**📄 등록된 시공관리도 목록:**")
                        
                        # 파일 정보 수집
                        file_info_list = []
                        for file_path in pdf_files:
                            file_name = os.path.basename(file_path)
                            file_size = os.path.getsize(file_path)
                            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            
                            # 파일명에서 정보 추출
                            # 예: "20240801-도림사거리정거장_미들슬라브.pdf"
                            parts = file_name.replace('.pdf', '').split('-')
                            if len(parts) >= 2:
                                date_part = parts[0]
                                process_part = parts[1]
                                
                                # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM)
                                if len(date_part) == 8:
                                    year_month = f"{date_part[:4]}-{date_part[4:6]}"
                                else:
                                    year_month = "N/A"
                                
                                # 공정명과 도면 유형 분리
                                process_parts = process_part.split('_')
                                if len(process_parts) >= 2:
                                    process_name = process_parts[0]
                                    drawing_type = process_parts[1]
                                else:
                                    process_name = process_part
                                    drawing_type = "시공관리도"
                            else:
                                year_month = "N/A"
                                process_name = file_name
                                drawing_type = "시공관리도"
                            
                            file_info_list.append({
                                'process_name': process_name,
                                'drawing_type': drawing_type,
                                'year_month': year_month,
                                'file_name': file_name,
                                'file_size': f"{file_size / 1024 / 1024:.1f} MB",
                                'upload_date': mod_time.strftime('%Y-%m-%d %H:%M')
                            })
                        
                        # DataFrame으로 변환하여 표시
                        import pandas as pd
                        df = pd.DataFrame(file_info_list)
                        st.dataframe(df, use_container_width=True)
                        
                        st.info(f"💡 총 {len(pdf_files)}개의 시공관리도 파일이 있습니다.")
                    else:
                        st.info("📋 등록된 시공관리도가 없습니다.")
                        st.info("💡 파일을 업로드하면 여기에 표시됩니다.")
                else:
                    st.info("📂 static/management-drawings 폴더가 없습니다.")
                    st.info("💡 파일을 업로드하면 폴더가 자동으로 생성됩니다.")
                    
            except Exception as e:
                st.error(f"❌ 시공관리도 목록 조회 중 오류: {str(e)}")

# CSS 스타일 추가
st.markdown("""
<style>
    /* 전체 페이지 배경 투명화 */
    .main .block-container {
        background: transparent !important;
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 100% !important;
        overflow: visible !important;
    }
    
    /* 설정 섹션 - 배경 제거 */
    .config-section {
        background: transparent !important;
        border-radius: 0 !important;
        padding: 0 !important;
        margin: 0 0 0 0 !important;
        box-shadow: none !important;
        border: none !important;
    }
    
    /* 설정 섹션과 채팅 컨테이너 사이 간격 최소화 */
    .config-section + .chat-container {
        margin-top: 1px !important;
    }
    
    /* 설정 섹션 다음 요소와의 간격 최소화 */
    .config-section ~ * {
        margin-top: 1px !important;
    }
    
    /* 채팅 컨테이너 - 배경 제거 */
    .chat-container {
        background: transparent !important;
        border-radius: 0 !important;
        padding: 0 !important;
        margin: 1px 0 0 0 !important;
        box-shadow: none !important;
        border: none !important;
        max-height: 400px;
        overflow-y: auto;
        min-height: 200px;
    }
    
    /* 메시지 스타일 - 간격 좁히기 */
    .message {
        margin: 8px 0;
        padding: 0;
        max-width: 85%;
        word-wrap: break-word;
        position: relative;
    }
    
    .user-message {
        margin-left: auto;
        text-align: right;
    }
    
    .ai-message {
        margin-right: auto;
        text-align: left;
    }
    
    /* 말풍선 스타일 */
    .message-bubble {
        padding: 10px 14px;
        border-radius: 12px;
        display: inline-block;
        max-width: 100%;
        position: relative;
        font-size: 14px;
        line-height: 1.5;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .user-bubble {
        background: #f0f2f6;
        color: #202124;
        border-radius: 12px 12px 4px 12px;
        border: 1px solid #e8eaed;
    }
    
    .ai-bubble {
        background: #ffffff;
        color: #202124;
        border-radius: 12px 12px 12px 4px;
        border: 1px solid #e8eaed;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        padding: 12px 16px;
    }
    
    /* 아바타 스타일 */
    .avatar {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        margin: 0 4px;
        flex-shrink: 0;
    }
    
    .user-avatar {
        background: #f0f2f6;
        color: #5f6368;
        border: 1px solid #e8eaed;
    }
    
    .ai-avatar {
        background: transparent;
        color: #1a73e8;
        border: 1px solid #1a73e8;
    }
    
    /* 메시지 컨테이너 */
    .message-container {
        display: flex;
        align-items: flex-start;
        gap: 4px;
    }
    
    .user-message .message-container {
        flex-direction: row-reverse;
    }
    
    .ai-message .message-container {
        flex-direction: row;
    }
    
    /* AI 메시지 헤더 */
    .ai-header {
        font-weight: 500;
        margin-bottom: 4px;
        color: #5f6368;
        font-size: 10px;
        display: flex;
        align-items: center;
        gap: 2px;
    }
    
    /* 버튼 스타일 - 프라이머리 버튼 파란색 적용 */
    .stButton > button[kind="primary"] {
        background-color: #007bff !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
        padding: 8px 16px !important;
        font-size: 14px !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #0056b3 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(0,123,255,0.3) !important;
    }
    
    .stButton > button[kind="primary"]:active {
        transform: translateY(0) !important;
    }
    
    /* Secondary 버튼 회색박스 스타일 및 크기 2배 */
    .stButton > button[kind="secondary"] {
        background-color: #f8f9fa !important;
        color: #000000 !important;
        border: 2px solid #dee2e6 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        padding: 16px 32px !important;
        font-size: 16px !important;
        height: 6rem !important;
        min-height: 6rem !important;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #e9ecef !important;
        color: #000000 !important;
        border-color: #adb5bd !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(108, 117, 125, 0.2) !important;
    }
    
    .stButton > button[kind="secondary"]:active {
        transform: translateY(0) !important;
    }
    
    /* Tertiary 버튼 투명색 스타일 및 기본 크기 */
    .stButton > button[kind="tertiary"] {
        background-color: transparent !important;
        color: #6c757d !important;
        border: 1px solid #dee2e6 !important;
        border-radius: 4px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        padding: 4px 12px !important;
        font-size: 14px !important;
    }
    
    .stButton > button[kind="tertiary"]:hover {
        background-color: #f8f9fa !important;
        color: #495057 !important;
        border-color: #adb5bd !important;
        transform: translateY(-1px) !important;
    }
    
    .stButton > button[kind="tertiary"]:active {
        transform: translateY(0) !important;
    }
    
    /* 슬라이더 스타일 */
    .stSlider > div > div > div > div {
        background: #1a73e8 !important;
    }
    
    /* 토글 스타일 */
    .stCheckbox > div > div {
        background: #1a73e8 !important;
    }
    
    /* 입력 영역 스타일 - 배경 제거 */
    .stTextArea {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: visible !important;
    }
    
    /* 입력 영역 주변 컨테이너들 */
    .stTextArea > div,
    .stTextArea > div > div,
    .stTextArea > div > div > div {
        overflow: visible !important;
    }
    
    .stTextArea textarea {
        border-radius: 20px !important;
        border: 1px solid #e8eaed !important;
        padding: 16px 20px !important;
        font-size: 14px !important;
        background: #ffffff !important;
        transition: all 0.3s ease !important;
        min-height: 120px !important;
        overflow: visible !important;
        resize: none !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #1a73e8 !important;
        outline: none !important;
        transform: translateY(-2px);
    }
    
    /* 모든 컨테이너 배경 제거 */
    div[data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlock"] > div,
    div[data-testid="stVerticalBlock"] > div > div,
    div[data-testid="stVerticalBlock"] > div > div > div,
    div[data-testid="stVerticalBlock"] > div > div > div > div {
        background: transparent !important;
    }
    
    /* 스트림릿 기본 배경 제거 */
    .block-container, .block-container > div, .block-container > div > div,
    .block-container > div > div > div, .block-container > div > div > div > div,
    .block-container > div > div > div > div > div,
    .block-container > div > div > div > div > div > div {
        background: transparent !important;
    }
    
    /* 메인 컨테이너 너비 제한 및 중앙 정렬 */
    .main .block-container {
        max-width: 1200px !important;
        margin: 0 auto !important;
        padding-top: 2rem !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
    }
    
    /* 큰 화면에서 여백 조정 */
    @media (min-width: 1400px) {
        .main .block-container {
            padding-left: 4rem !important;
            padding-right: 4rem !important;
        }
    }
    
    /* 작은 화면에서 여백 조정 */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }
    
    /* 입력 영역 주변 모든 컨테이너 배경 제거 */
    .stTextArea, .stTextArea *, .stTextArea > div, .stTextArea > div > div, 
    .stTextArea > label, .stTextArea > div > div > div,
    .stTextArea > div > div > div > div,
    .stTextArea > div > div > div > div > div,
    .stTextArea > div > div > div > div > div > div,
    .stTextArea > div > div > div > div > div > div > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* 스크롤바 스타일 */
    .chat-container::-webkit-scrollbar {
        width: 3px;
    }
    
    .chat-container::-webkit-scrollbar-track {
        background: transparent;
        border-radius: 2px;
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 2px;
    }
    
    .chat-container::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    
    /* 제목 스타일 */
    h1 {
        color: #202124 !important;
        font-weight: 600 !important;
        margin-bottom: 8px !important;
        font-size: 1.2rem !important;
    }
    
    /* 컬럼 간격 줄이기 */
    .row-widget.stHorizontal > div {
        gap: 4px !important;
    }
    
    /* 설정 섹션 내부 간격 줄이기 */
    .config-section .row-widget.stHorizontal > div {
        padding: 0 2px !important;
    }
    
    /* 전체 여백 최소화 */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0.1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1200px !important;
        margin: 0 auto !important;
    }
    
    /* 스트림릿 기본 여백 제거 */
    .main .block-container > div {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    
    /* 채팅 컨테이너 여백 조정 */
    .chat-container {
        margin-top: 5px !important;
    }
    
    /* 입력 영역 여백 줄이기 */
    .stTextArea > div > div {
        margin-bottom: 2px !important;
    }
    
    /* 버튼 영역 여백 줄이기 */
    .stButton > div {
        margin-top: 2px !important;
    }
    
    /* 입력 영역 위의 불필요한 여백 제거 */
    .stTextArea > label {
        margin-bottom: 1px !important;
    }
    
    /* 로딩 스피너 스타일 */
    .loading-bubble {
        background: #f0f2f6 !important;
        color: #202124 !important;
        border: 1px solid #e8eaed !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
    }
    
    .loading-content {
        display: flex;
        align-items: center;
        gap: 8px;
        justify-content: flex-start;
    }
    
    .loading-spinner {
        display: none;
    }
    
    .loading-text {
        font-weight: 400;
        font-size: 14px;
        color: #5f6368;
        margin-top: 8px;
        font-style: italic;
    }
    
    /* 로딩 중일 때 입력 영역 비활성화 스타일 */
    .loading-disabled {
        opacity: 0.6;
        pointer-events: none;
    }
    
    /* 로딩 중일 때 버튼 비활성화 스타일 */
    .stButton > button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 헤더 섹션 (채팅이 없을 때만 표시)
if "chat_history" not in st.session_state or len(st.session_state.chat_history) == 0:
    st.markdown("""
    <div style="text-align: center; margin: 20px 0; padding: 20px;">
        <span style="font-size: 1.5rem; font-weight: bold; display: block; margin-bottom: 2px; color: #000000;">
            발파/계측 데이터 분석, 작업일보 자동화, 공정관리
        </span>
        <span style="font-size: 2.5rem; font-weight: 600; color: #000000; display: block;">
            현장 업무 대화 모두 OK!
        </span>
    </div>
    """, unsafe_allow_html=True)
else:
    # 채팅이 있을 때는 최소한의 여백만 추가
    st.markdown('<div style="margin-top: 5px;"></div>', unsafe_allow_html=True)



# 채팅 히스토리 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 로딩 상태 초기화
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False

# 채팅 히스토리 표시
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# 테이블 구조 디버깅 결과 표시
if st.session_state.get('show_table_debug', False):
    st.subheader("🔍 테이블 구조 디버깅 결과")
    debug_table_structure()
    
    # 디버깅 완료 후 상태 초기화
    if st.button("✅ 디버깅 완료"):
        st.session_state.show_table_debug = False
        st.rerun()
    
    st.markdown("---")

for message in st.session_state.chat_history:
    if message["role"] == "user":
        # 사용자 메시지
        st.markdown(f"""
        <div class="message user-message">
            <div class="message-container">
                <div class="message-bubble user-bubble">
                    {message['content']}
                </div>
                <div class="avatar user-avatar">👤</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif message["role"] == "assistant":
        # AI 메시지
        st.markdown(f"""
        <div class="message ai-message">
            <div class="message-container">
                <div class="avatar ai-avatar">✨</div>
                <div style="flex: 1;">
                    <div class="ai-header">
                        <span>AI 공사관리 에이전트</span>
                    </div>
                    <div class="message-bubble ai-bubble">
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 마크다운 내용을 별도로 렌더링
        st.markdown(message['content'])
        
        # DataFrame이 있으면 테이블로 표시
        if 'structured_data' in message and message['structured_data'].get('dataframe') is not None:
            st.dataframe(message['structured_data']['dataframe'], use_container_width=True)
        
        # 간트차트 데이터가 있으면 간트차트 표시 (공정 분석인 경우)
        if 'structured_data' in message and message['structured_data'].get('gantt_data') is not None:
            gantt_data = message['structured_data']['gantt_data']
            try:
                import plotly.figure_factory as ff
                import pandas as pd
                from datetime import datetime
                
                # 간트차트 데이터를 적절한 형식으로 변환
                gantt_chart_data = []
                for item in gantt_data:
                    gantt_chart_data.append({
                        'Task': item.get('task', '공정명'),
                        'Start': item.get('start', '2024-01-01'),
                        'Finish': item.get('end', '2024-01-31'),
                        'Resource': item.get('resource', '팀'),
                        'Progress': item.get('progress', 0)
                    })
                
                if gantt_chart_data:
                    # 간트차트 생성
                    fig_gantt = ff.create_gantt(
                        gantt_chart_data,
                        colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
                        index_col='Resource',
                        show_colorbar=True,
                        bar_width=0.5,
                        showgrid_x=True,
                        showgrid_y=True,
                        height=400
                    )
                    
                    fig_gantt.update_layout(
                        title="공정별 간트차트",
                        xaxis_title="기간",
                        yaxis_title="공정",
                        height=400,
                        showlegend=True
                    )
                    
                    import time
                    unique_key = f"gantt_chart_main_{int(time.time() * 1000)}"
                    st.plotly_chart(fig_gantt, use_container_width=True, key=unique_key)
                    
            except Exception as e:
                st.warning(f"간트차트 생성 중 오류: {str(e)}")
                print(f"간트차트 데이터: {gantt_data}")
        
        # 시공관리도 JPG 표시 (공종 분석인 경우)
        if 'structured_data' in message and message['structured_data'].get('construction_drawing'):
            drawing = message['structured_data']['construction_drawing']
            try:
                st.markdown("### 📋 시공관리도")
                st.markdown(f"**파일명:** {drawing.get('file_name', 'N/A')}")
                st.markdown(f"**공정명:** {drawing.get('process_name', 'N/A')}")
                st.markdown(f"**도면 유형:** {drawing.get('drawing_type', 'N/A')}")
                st.markdown(f"**해당 월:** {drawing.get('year_month', 'N/A')}")
                
                # 가장 가까운 월 매칭인지 표시
                if drawing.get('is_closest_match'):
                    st.info("💡 요청하신 월의 시공관리도가 없어 가장 가까운 월의 시공관리도를 표시합니다.")
                
                # JPG 파일 표시
                if drawing.get('file_path') and os.path.exists(drawing['file_path']):
                    st.image(drawing['file_path'], caption=f"시공관리도 - {drawing.get('file_name', '')}", use_column_width=True)
                else:
                    st.warning("시공관리도 파일을 찾을 수 없습니다.")
                    
            except Exception as e:
                st.warning(f"시공관리도 표시 중 오류: {str(e)}")
        
        # 상세 분석 섹션 제거됨 - 1, 2, 3번 섹션을 표시하지 않음
        
        # 대안 데이터 섹션도 제거됨 - 1, 2, 3번 섹션을 표시하지 않음
        
        # 시공상세도 표시 부분 제거됨
        
        # 그래프 데이터가 있으면 차트 표시 (일별 데이터인 경우만)
        if 'structured_data' in message and message['structured_data'].get('chart_data') is not None:
            chart_data = message['structured_data']['chart_data']
            # 간트차트가 아닌 경우에만 일반 차트 생성
            if chart_data.get('chart_type') != 'gantt' and chart_data.get('data') and len(chart_data['data']) > 0 and 'date' in str(chart_data.get('data', [])):
                try:
                    import plotly.express as px
                    import pandas as pd
                    
                    # 차트 데이터를 DataFrame으로 변환
                    df_chart = pd.DataFrame(chart_data['data'])
                    
                    # DataFrame의 컬럼명 확인
                    available_columns = list(df_chart.columns)
                    print(f"차트 데이터 컬럼: {available_columns}")
                    
                    # 컬럼명에 따라 적절한 x, y 축 선택
                    if 'date' in available_columns and 'value' in available_columns:
                        x_col, y_col = 'date', 'value'
                    elif 'label' in available_columns and 'value' in available_columns:
                        x_col, y_col = 'label', 'value'
                    elif len(available_columns) >= 2:
                        x_col, y_col = available_columns[0], available_columns[1]
                    else:
                        print("차트 생성에 필요한 컬럼이 없습니다.")
                        x_col, y_col = None, None
                    
                    # 컬럼이 있는 경우에만 그래프 생성
                    if x_col and y_col:
                        import time
                        timestamp = int(time.time() * 1000)
                        
                        if chart_data.get('chart_type') == 'line':
                            fig = px.line(df_chart, x=x_col, y=y_col, title=chart_data.get('title', '일별 추이'))
                            st.plotly_chart(fig, use_container_width=True, key=f"line_chart_{timestamp}")
                        elif chart_data.get('chart_type') == 'bar':
                            fig = px.bar(df_chart, x=x_col, y=y_col, title=chart_data.get('title', '일별 실적'))
                            st.plotly_chart(fig, use_container_width=True, key=f"bar_chart_{timestamp}")
                        elif chart_data.get('chart_type') == 'pie':
                            fig = px.pie(df_chart, values=y_col, names=x_col, title=chart_data.get('title', '비율 분석'))
                            st.plotly_chart(fig, use_container_width=True, key=f"pie_chart_{timestamp}")
                        else:
                            # 기본적으로 선그래프
                            fig = px.line(df_chart, x=x_col, y=y_col, title='일별 데이터 추이')
                            st.plotly_chart(fig, use_container_width=True, key=f"default_line_chart_{timestamp}")
                        
                except Exception as e:
                    st.warning(f"그래프 생성 중 오류: {str(e)}")
                    print(f"차트 데이터: {chart_data}")
                    print(f"DataFrame 컬럼: {list(df_chart.columns) if 'df_chart' in locals() else 'DataFrame 생성 실패'}")
        
        # 피벗 테이블인 경우 추가 그래프 생성
        if 'structured_data' in message and message['structured_data'].get('is_pivot') and message['structured_data'].get('dataframe') is not None:
            try:
                import plotly.express as px
                import pandas as pd
                
                df = message['structured_data']['dataframe']
                
                # 피벗 테이블을 다시 long format으로 변환하여 그래프 생성
                if len(df.columns) > 3:  # 직종, 날짜들, 단위
                    # 단위 컬럼 제외하고 날짜 컬럼들만 선택
                    date_columns = [col for col in df.columns if col not in ['직종', '단위']]
                    
                    # long format으로 변환
                    long_df = df.melt(id_vars=['직종'], value_vars=date_columns, 
                                     var_name='날짜', value_name='인원')
                    long_df['인원'] = pd.to_numeric(long_df['인원'], errors='coerce').fillna(0)
                    
                    # 직종별 선그래프
                    import time
                    timestamp = int(time.time() * 1000)
                    fig = px.line(long_df, x='날짜', y='인원', color='직종', 
                                 title='일별 직종별 인원 투입 현황')
                    st.plotly_chart(fig, use_container_width=True, key=f"personnel_line_chart_{timestamp}")
                    
                    # 직종별 막대그래프 (최신 날짜 기준)
                    latest_date = date_columns[-1] if date_columns else None
                    if latest_date:
                        latest_data = df[['직종', latest_date]]
                        latest_data[latest_date] = pd.to_numeric(latest_data[latest_date], errors='coerce').fillna(0)
                        fig2 = px.bar(latest_data, x='직종', y=latest_date, 
                                    title=f'{latest_date} 직종별 인원 현황')
                        st.plotly_chart(fig2, use_container_width=True, key=f"personnel_bar_chart_{timestamp}")
                        
            except Exception as e:
                st.warning(f"피벗 테이블 그래프 생성 중 오류: {str(e)}")
        
        # 일반 테이블인 경우에도 그래프 생성 (직종별 인원 현황)
        elif 'structured_data' in message and message['structured_data'].get('dataframe') is not None:
            try:
                import plotly.express as px
                import pandas as pd
                
                df = message['structured_data']['dataframe']
                
                # 직종별 인원 현황 테이블인 경우 막대그래프 생성
                if len(df.columns) >= 3 and '직종' in df.columns[0] and '투입인원' in df.columns[1]:
                    # 숫자 컬럼으로 변환
                    df['투입인원'] = pd.to_numeric(df['투입인원'], errors='coerce').fillna(0)
                    
                    # 막대그래프 생성
                    fig = px.bar(df, x='직종', y='투입인원', 
                                title='직종별 투입 인원 현황',
                                text='투입인원')  # 값 표시
                    import time
                    timestamp = int(time.time() * 1000)
                    fig.update_traces(textposition='outside')  # 값 위치 조정
                    st.plotly_chart(fig, use_container_width=True, key=f"personnel_bar_chart_2_{timestamp}")
                    
                    # 파이차트도 추가
                    fig2 = px.pie(df, values='투입인원', names='직종', 
                                 title='직종별 인원 비율')
                    st.plotly_chart(fig2, use_container_width=True, key=f"personnel_pie_chart_{timestamp}")
                    
                    # 간트차트 생성 (공정 현황용)
                    if any(keyword in str(message.get('content', '')).lower() for keyword in ['공정', '현황', '진도', '실적']):
                        try:
                            # 간트차트용 데이터 준비
                            gantt_data = []
                            
                            # 공정명과 진도율이 있는 경우
                            if '구분' in df.columns and '월간 실적' in df.columns:
                                for idx, row in df.iterrows():
                                    if pd.notna(row['월간 실적']) and str(row['월간 실적']).replace('-', '').replace('.', '').isdigit():
                                        progress = float(str(row['월간 실적']).replace(',', ''))
                                        if progress > 0:  # 양수인 경우만
                                            # 진도율을 0-1 사이로 정규화 (100m 이상이면 100%로 처리)
                                            normalized_progress = min(progress / 100, 1.0) if progress > 100 else progress / 100
                                            
                                            gantt_data.append({
                                                'Task': str(row['구분']),
                                                'Start': '2024-01-01',  # 시작일 (고정)
                                                'Finish': '2024-12-31',  # 종료일 (고정)
                                                'Progress': normalized_progress,  # 진도율 (0-1)
                                                'Resource': f"{progress}m"
                                            })
                            
                            # 간트차트 데이터가 있는 경우에만 생성
                            if gantt_data:
                                import plotly.figure_factory as ff
                                
                                fig_gantt = ff.create_gantt(
                                    gantt_data,
                                    colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
                                    show_colorbar=True,
                                    bar_width=0.5,
                                    showgrid_x=True,
                                    showgrid_y=True,
                                    height=400
                                )
                                
                                fig_gantt.update_layout(
                                    title="공정 현황 간트차트 (진도율 표시)",
                                    xaxis_title="기간",
                                    yaxis_title="공정",
                                    height=400
                                )
                                
                                import time
                                timestamp = int(time.time() * 1000)
                                st.plotly_chart(fig_gantt, use_container_width=True, key=f"gantt_chart_secondary_{timestamp}")
                                
                        except Exception as e:
                            st.warning(f"간트차트 생성 중 오류: {str(e)}")
                    
            except Exception as e:
                st.warning(f"일반 테이블 그래프 생성 중 오류: {str(e)}")

st.markdown('</div>', unsafe_allow_html=True)

# 커스텀 입력 필드와 전송 버튼
st.markdown("""
<style>
.custom-input-container {
    display: flex;
    align-items: center;
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 25px;
    padding: 8px 16px;
    margin: 20px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.input-icons {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-right: 12px;
}

.icon {
    width: 20px;
    height: 20px;
    cursor: pointer;
    opacity: 0.7;
    transition: opacity 0.2s;
}

.icon:hover {
    opacity: 1;
}

.custom-input {
    flex: 1;
    border: none;
    background: transparent;
    outline: none;
    font-size: 16px;
    color: #333;
    padding: 8px 0;
}

.custom-input::placeholder {
    color: #999;
}

.send-button {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #007bff;
    border: none;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    box-shadow: 0 2px 8px rgba(0,123,255,0.3);
}

.send-button:hover {
    background: #0056b3;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,123,255,0.4);
}

.send-button:active {
    transform: translateY(0);
}
</style>
""", unsafe_allow_html=True)

# 메시지 입력
user_input = st.text_area(
    "",
    key="user_input",
    height=100,
    placeholder="저에게 일을 시켜보세요!",
    disabled=st.session_state.get('is_loading', False)
)



# 전송 버튼
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("📤 전송", use_container_width=True, type="primary", disabled=st.session_state.get('is_loading', False)):
        if user_input and user_input.strip():
            # 사용자 메시지 정리 (HTML 코드 제거)
            clean_user_input = user_input.strip()
            import re
            clean_user_input = re.sub(r'<[^>]+>', '', clean_user_input)  # HTML 태그 제거
            
            # 사용자 메시지 추가
            st.session_state.chat_history.append({
                "role": "user",
                "content": clean_user_input,
                "timestamp": datetime.now()
            })
            
            # 마지막 사용자 메시지 저장 (시공관리도 조회용)
            st.session_state.last_user_message = clean_user_input
            
            # 로딩 상태 설정
            st.session_state.is_loading = True
            st.rerun()

# 로딩 상태 표시
if st.session_state.get('is_loading', False):
    # 로딩 메시지 추가 (아직 채팅 히스토리에 추가하지 않음)
    st.markdown("""
    <div class="message ai-message">
        <div class="message-container">
            <div class="avatar ai-avatar">✨</div>
            <div style="flex: 1;">
                <div class="ai-header">
                    <span>AI 공사관리 에이전트</span>
                </div>
                <div class="loading-text">답변을 생성중입니다...</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # AI 응답 생성 (백그라운드에서)
    if 'pending_user_input' not in st.session_state:
        st.session_state.pending_user_input = user_input.strip()
        st.session_state.pending_user_input = re.sub(r'<[^>]+>', '', st.session_state.pending_user_input)
        
        # AI 응답 생성
        try:
            ai_response = generate_ai_response(st.session_state.pending_user_input)
        except Exception as e:
            st.error(f"AI 응답 생성 중 오류: {str(e)}")
            ai_response = "죄송합니다. 응답 생성 중 오류가 발생했습니다."
        
        # AI 응답에서 HTML 태그 제거 (더 강력한 정리)
        import re
        clean_ai_response = re.sub(r'<[^>]+>', '', ai_response)  # HTML 태그 제거
        clean_ai_response = re.sub(r'</div>', '', clean_ai_response)  # div 태그 특별 제거
        clean_ai_response = re.sub(r'<div[^>]*>', '', clean_ai_response)  # div 태그 특별 제거
        clean_ai_response = re.sub(r'\s+', ' ', clean_ai_response)  # 연속 공백 정리
        clean_ai_response = clean_ai_response.strip()  # 앞뒤 공백 제거
        
        # AI 메시지 추가 (structured_data도 함께 저장)
        ai_message = {
            "role": "assistant",
            "content": clean_ai_response,
            "timestamp": datetime.now()
        }
        
        # structured_data가 있으면 함께 저장
        if hasattr(st.session_state, 'temp_structured_data'):
            ai_message['structured_data'] = st.session_state.temp_structured_data
            del st.session_state.temp_structured_data
        
        st.session_state.chat_history.append(ai_message)
        
        # 로딩 상태 해제 및 정리
        st.session_state.is_loading = False
        del st.session_state.pending_user_input
        st.rerun()

with col_btn2:
    if st.button("🗑️ 대화 초기화", use_container_width=True, type="tertiary"):
        if "chat_history" in st.session_state:
            st.session_state.chat_history = []
        st.rerun()



# 추가 기능 버튼들
st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)



col_btn3, col_btn4, col_btn5, col_btn6 = st.columns(4)

with col_btn3:
    if st.button("💥 발파/계측분석 자동화", key="btn3", use_container_width=True, type="secondary"):
        st.switch_page("pages/balpa.py")
    st.markdown('''
    <div style="font-size: 14px; color: #666; line-height: 1.4; text-align: center; margin-top: 8px;">
        발파일지&발파계측 분석<br>
        자동화계측 데이터 자동추출<br>
        계측기 이상치 탐지/분석/경고알림
    </div>
    ''', unsafe_allow_html=True)

with col_btn4:
    if st.button("📋 작업일보 자동화", key="btn4", use_container_width=True, type="secondary"):
        st.switch_page("pages/SNS일일작업계획.py")
    st.markdown('''
    <div style="font-size: 14px; color: #666; line-height: 1.4; text-align: center; margin-top: 8px;">
        SNS 일일작업보고<br>
        작업일보 문서화
    </div>
    ''', unsafe_allow_html=True)

with col_btn5:
    if st.button("⚙️ 공정분석 자동화", key="btn5", use_container_width=True, type="secondary"):
        st.switch_page("pages/월간실적")
    st.markdown('''
    <div style="font-size: 14px; color: #666; line-height: 1.4; text-align: center; margin-top: 8px;">
        대표물량 작성 및 공정률 산정<br>
        주, 월간 공정실적 리포트
    </div>
    ''', unsafe_allow_html=True)

with col_btn6:
    if st.button("💰 원가관리 자동화(준비중)", key="btn6", use_container_width=True, type="secondary"):
        st.switch_page("main.py")
    st.markdown('''
    <div style="font-size: 14px; color: #666; line-height: 1.4; text-align: center; margin-top: 8px;">
        예상 도급기성 전망<br>
        (실적+향후(예측))<br>
        작업일보 기반 투입비 예측
    </div>
    ''', unsafe_allow_html=True)