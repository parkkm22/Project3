import streamlit as st
import folium
from streamlit_folium import st_folium
import ezdxf
from pyproj import Geod, Transformer
import io
import os
import json
import base64
import pandas as pd
import re
import google.generativeai as genai
from datetime import datetime

# Gemini AI 설정
try:
    GENAI_API_KEY = st.secrets["GENAI_API_KEY"]
    genai.configure(api_key=GENAI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel("models/gemini-2.5-flash-preview-05-20")
    AI_AVAILABLE = True
except:
    st.warning("⚠️ Gemini AI API 키가 설정되지 않았습니다. Streamlit secrets에 GENAI_API_KEY를 추가해주세요.")
    AI_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="GIS/CAD 뷰어",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 발파데이터 추출 프롬프트
BLAST_EXTRACTION_PROMPT = '''
# INSTRUCTION
- 반드시 아래 예시처럼 오직 TSV(탭 구분) 데이터만 출력하세요.
- 설명, 마크다운, 코드블록, 주석, 기타 텍스트는 절대 포함하지 마세요.
- 아래 예시와 동일한 형식으로만 출력하세요.
발파일자	발파시간	지발당장약량(최소, kg)	지발당장약량(최대, kg)	폭약사용량(kg)	발파진동(cm/sec)	발파소음(dB(A))	계측위치	비고
2023-07-27	08:05	0.5	0.9	73	-	-	-	PLA-2
2023-07-27	13:47	0.4	0.8	77	0.87	53.29	티스테이션	PD-2
2023-07-27	13:47	-	-	-	0.71	61.23	양말집	PD-2
(위 예시는 형식만 참고, 실제 데이터는 입력값에 따라 동적으로 생성)
# 입력
- 입력1: 발파작업일지_TSV (아래와 같은 형식)
- 입력2: 계측일지_TSV (아래와 같은 형식, **계측일지 표는 PDF 2페이지 이후부터 추출**)
# 입력1 예시
발파일자	발파시간	지발당장약량(최소, kg)	지발당장약량(최대, kg)	폭약사용량(kg)	비고
2023-07-27	08:05	0.5	0.9	73	PLA-2
2023-07-27	13:47	0.4	0.8	77	PD-2
# 입력2 예시 (**2페이지 이후 표만**)
Date/Time	Peak Particle Vel (X_Axis) (mm/sec)	Peak Particle Vel (Y_Axis) (mm/sec)	Peak Particle Vel (Z_Axis) (mm/sec)	LMax (Sound) (dBA)	측정위치
2023/07/27 1:47:00 PM	0.71	0.36	0.71	61.23	양말집
2023/07/27 1:47:00 PM	0.87	0.56	0.87	53.29	티스테이션
# Mapping Rules
- 두 입력을 병합하여 위 예시와 동일한 TSV만 출력
- 설명, 마크다운, 코드블록, 주석, 기타 텍스트는 절대 포함하지 마세요.
- 계측일지 표는 반드시 PDF 2페이지 이후의 표만 사용 
- 최종 헤더(고정열): 발파일자, 발파시간, 지발당장약량(최소, kg), 지발당장약량(최대, kg), 폭약사용량(kg), 발파진동(cm/sec), 발파소음(dB(A)), 계측위치, 비고
- 정렬: 발파시간 오름차순, 계측위치 오름차순(필요시)
- 병합/매칭/포맷 규칙은 기존과 동일
'''

# 세션 상태 초기화
def initialize_session_state():
    if 'blast_dataframe' not in st.session_state:
        st.session_state.blast_dataframe = None
    if 'blast_data_completed' not in st.session_state:
        st.session_state.blast_data_completed = False

# 안전한 AI 모델 호출 함수
def safe_generate_content(prompt, files=None):
    if not AI_AVAILABLE:
        st.warning("⚠️ Gemini AI API 키가 설정되지 않았습니다. 실제 구현을 위해서는 API 키가 필요합니다.")
        return None
    try:
        # Gemini AI 모델을 사용하여 프롬프트 생성 및 응답 받기
        response = GEMINI_MODEL.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"❌ Gemini AI 모델 호출 중 오류 발생: {e}")
        return None

# 파일 내용 추출 함수
def extract_file_content(file):
    if file.name.endswith('.pdf'):
        if not AI_AVAILABLE:
            st.warning("⚠️ PDF 파일 처리를 위해서는 Gemini AI API 키가 필요합니다.")
            return None
        try:
            # PDF 파일을 Gemini AI에 업로드하여 내용 추출
            file.seek(0)
            uploaded_file = genai.upload_file(file, mime_type="application/pdf")
            
            filename_lower = file.name.lower()
            is_measurement_file = any(keyword in filename_lower for keyword in ["계측", "진동", "소음"])
            is_blast_log_file = any(keyword in filename_lower for keyword in ["발파", "작업", "일지"])

            if is_measurement_file:
                pdf_prompt = """이 PDF 파일은 '발파진동소음 계측일지'입니다. 
                다음 지침에 따라 데이터를 TSV 형식으로 추출해주세요:
                1. PDF 2페이지 이후의 표만 추출
                2. Date/Time, Peak Particle Vel (X_Axis) (mm/sec), Peak Particle Vel (Y_Axis) (mm/sec), 
                   Peak Particle Vel (Z_Axis) (mm/sec), LMax (Sound) (dBA), 측정위치 컬럼 포함
                3. TSV 형식으로만 출력 (탭으로 구분)
                4. 설명이나 주석은 포함하지 마세요."""
            elif is_blast_log_file:
                pdf_prompt = """이 PDF 파일은 '발파작업일지'입니다. 
                다음 지침에 따라 주요 데이터를 TSV 형식으로 추출해주세요:
                1. 발파일자, 발파시간, 지발당장약량(최소, kg), 지발당장약량(최대, kg), 폭약사용량(kg), 비고 컬럼 포함
                2. TSV 형식으로만 출력 (탭으로 구분)
                3. 설명이나 주석은 포함하지 마세요."""
            else:
                pdf_prompt = """이 PDF에서 가장 중요해 보이는 표를 찾아 TSV 형식으로 추출해주세요.
                탭으로 구분된 데이터만 출력하고, 설명이나 주석은 포함하지 마세요."""

            # AI 모델을 사용하여 PDF 내용 추출
            response = GEMINI_MODEL.generate_content([pdf_prompt, uploaded_file])
            
            # 사용이 끝난 파일은 즉시 삭제
            genai.delete_file(uploaded_file.name)

            if response.text:
                return re.sub(r'```tsv|```', '', response.text).strip()
            
            return None

        except Exception as e:
            st.error(f"❌ {file.name} 처리 중 AI 오류 발생: {e}")
            return None
    elif file.name.endswith(('.xlsx', '.xls')):
        try:
            return pd.read_excel(file, engine='openpyxl').to_csv(sep='\t', index=False, encoding='utf-8')
        except Exception as e:
            st.error(f"❌ 엑셀 데이터 추출 실패: {e}")
            return None
    return None

# TSV 응답에서 데이터 추출
def extract_tsv_from_response(response_text):
    # TSV 데이터 추출 로직
    lines = response_text.strip().split('\n')
    tsv_lines = []
    for line in lines:
        if '\t' in line:  # 탭이 포함된 줄만 TSV로 간주
            tsv_lines.append(line)
    return '\n'.join(tsv_lines)

# TSV를 데이터프레임으로 파싱
def parse_tsv_to_dataframe(tsv_text):
    try:
        # TSV 데이터를 StringIO로 변환하여 pandas로 읽기
        from io import StringIO
        df = pd.read_csv(StringIO(tsv_text), sep='\t', encoding='utf-8')
        return df
    except Exception as e:
        st.error(f"❌ TSV 파싱 실패: {e}")
        return None

# TSV 필드 수 수정
def fix_tsv_field_count(tsv_text):
    lines = tsv_text.strip().split('\n')
    fixed_lines = []
    
    for line in lines:
        fields = line.split('\t')
        # 헤더는 9개 필드, 데이터는 9개 필드로 맞춤
        if len(fields) < 9:
            fields.extend([''] * (9 - len(fields)))
        elif len(fields) > 9:
            fields = fields[:9]
        fixed_lines.append('\t'.join(fields))
    
    return '\n'.join(fixed_lines)

# 세션 상태 초기화
initialize_session_state()

# 제목
st.markdown("---")

# 사이드바에 DXF 파일 업로드 추가
st.sidebar.header("📁 DXF 파일 업로드")
uploaded_file = st.sidebar.file_uploader("DXF 파일을 선택하세요", type=['dxf'], key="dxf_uploader")

if uploaded_file is not None:
    # DXF 파일 처리
    try:
        # 파일 내용을 바이트로 읽기
        file_content = uploaded_file.read()
        
        # ezdxf로 DXF 파일 파싱
        doc = ezdxf.read(io.BytesIO(file_content))
        
        # 엔티티 정보 추출
        entities_data = []
        for entity in doc.entitydb.values():
            if hasattr(entity, 'dxftype'):
                entity_info = {
                    'type': entity.dxftype(),
                    'layer': getattr(entity, 'layer', '0'),
                    'color': getattr(entity, 'color', 7),  # 7은 흰색
                    'coordinates': []
                }
                
                # 엔티티 타입별로 좌표 추출
                if entity.dxftype() == 'LINE':
                    if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        entity_info['coordinates'] = [
                            {'x': entity.dxf.start.x, 'y': entity.dxf.start.y},
                            {'x': entity.dxf.end.x, 'y': entity.dxf.end.y}
                        ]
                elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                    if hasattr(entity, 'get_points'):
                        points = entity.get_points()
                        entity_info['coordinates'] = [{'x': p[0], 'y': p[1]} for p in points]
                elif entity.dxftype() == 'CIRCLE':
                    if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
                        entity_info['coordinates'] = [
                            {'x': entity.dxf.center.x, 'y': entity.dxf.center.y},
                            {'radius': entity.dxf.radius}
                        ]
                elif entity.dxftype() in ['TEXT', 'MTEXT']:
                    if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'insert'):
                        entity_info['coordinates'] = [{'x': entity.dxf.insert.x, 'y': entity.dxf.insert.y}]
                        entity_info['text'] = getattr(entity, 'text', getattr(entity, 'text_string', ''))
                
                if entity_info['coordinates']:
                    entities_data.append(entity_info)
        
        # 결과를 세션 상태에 저장
        st.session_state.dxf_data = {
            'entities': entities_data,
            'filename': uploaded_file.name
        }
        
        st.sidebar.success(f"✅ {uploaded_file.name} 파일 처리 완료!")
        st.sidebar.info(f"📊 총 {len(entities_data)}개 엔티티 발견")
        
        # 처리된 데이터 미리보기
        if st.sidebar.button("📋 데이터 미리보기"):
            st.sidebar.json(entities_data[:5])  # 처음 5개만 표시
        
    except Exception as e:
        st.sidebar.error(f"❌ DXF 파일 처리 실패: {str(e)}")
        st.session_state.dxf_data = None

# HTML 파일 읽기
def load_html_file():
    try:
        # 현재 파일이 pages 폴더 안에 있으므로 상위 폴더의 pages 폴더로 이동
        with open('pages/map.html', 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        try:
            # 상대 경로로 시도
            with open('../pages/map.html', 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            try:
                # 절대 경로로 시도
                current_dir = os.getcwd()
                map_path = os.path.join(current_dir, 'pages', 'map.html')
                with open(map_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except FileNotFoundError:
                st.error(f"map.html 파일을 찾을 수 없습니다. 현재 작업 디렉토리: {os.getcwd()}")
                st.error(f"시도한 경로: {map_path}")
                return None

# HTML 파일 로드
html_content = load_html_file()

if html_content:
    # DXF 데이터가 있으면 JavaScript 변수로 주입
    if hasattr(st.session_state, 'dxf_data') and st.session_state.dxf_data:
        # JavaScript 코드 생성
        js_code = f"""
        <script>
        // DXF 데이터를 전역 변수로 설정
        window.dxfData = {json.dumps(st.session_state.dxf_data)};
        console.log('DXF 데이터 로드됨:', window.dxfData);
        </script>
        """
        
        # HTML에 JavaScript 코드 삽입
        html_content = html_content.replace('</head>', js_code + '</head>')
    
    # HTML을 Streamlit에 표시
    st.components.v1.html(
        html_content,
        height=800,
        scrolling=True
    )

    # 발파 데이터 확인 섹션 추가
    st.markdown("---")

    # 발파 데이터 확인 컨테이너
    st.markdown("""
    <div style="
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid #e9ecef;
    ">
        <div style="
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        ">
            <span style="
                font-size: 24px;
                margin-right: 10px;
            ">🧨</span>
            <span style="
                font-size: 18px;
                font-weight: bold;
                color: #1f77b4;
            ">2. 발파 데이터 확인</span>
        </div>
        <p style="
            color: #6c757d;
            margin: 0;
            font-size: 14px;
        ">발파작업일지와 계측결과 보고서를 업로드하여 데이터를 병합하고 정제합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # 파일 업로드 라벨
    st.markdown("**발파작업일지 및 계측결과 보고서 (2개 파일)**")

    # 발파 데이터 처리 상태 확인
    if not st.session_state.blast_data_completed:
        # 파일 업로드 영역
        blast_files = st.file_uploader(
            "발파작업일지 및 계측결과 보고서를 업로드하세요",
            type=['pdf', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="blast_files"
        )

        if len(blast_files) == 2:
            with st.spinner('🤖 AI가 발파 데이터를 분석하고 있습니다...'):
                try:
                    # 두 파일의 내용 추출
                    blast_text = extract_file_content(blast_files[0])
                    daily_text = extract_file_content(blast_files[1])
                    
                    if blast_text and daily_text:
                        # AI 프롬프트 생성 및 실행
                        prompt = BLAST_EXTRACTION_PROMPT + f"\n\n## 입력 1: 발파작업일지_TSV\n{blast_text}\n\n## 입력 2: 계측일지_TSV\n{daily_text}"
                        response_text = safe_generate_content(prompt)

                        if response_text:
                            # TSV 데이터 추출 및 파싱
                            tsv_result = extract_tsv_from_response(response_text)
                            df = parse_tsv_to_dataframe(fix_tsv_field_count(tsv_result))
                            
                            if df is not None:
                                st.session_state.blast_dataframe = df
                                st.session_state.blast_data_completed = True
                                st.success("✅ 2단계 완료: 발파 데이터 분석 성공!")
                                st.rerun()
                            else: 
                                st.error("AI 응답에서 유효한 TSV를 추출하지 못했습니다.")
                        else:
                            st.error("AI 모델 응답을 받지 못했습니다.")
                    else: 
                        st.error("파일 내용 추출에 실패했습니다.")
                except Exception as e: 
                    st.error(f"데이터 분석 중 오류: {e}")
        elif len(blast_files) == 1:
            st.info("📁 두 번째 파일을 업로드해주세요.")
        elif len(blast_files) == 0:
            st.info("📁 발파작업일지와 계측결과 보고서를 업로드해주세요.")
    else:
        # 발파 데이터 처리 완료 상태
        st.success("✅ 2단계 완료: 발파 데이터가 성공적으로 처리되었습니다.")
        
        # 처리된 데이터 표시
        with st.expander("📊 처리된 발파 데이터 보기", expanded=True):
            if st.session_state.blast_dataframe is not None:
                st.dataframe(st.session_state.blast_dataframe, use_container_width=True)
                
                # 데이터 통계 정보
                st.markdown("**📈 데이터 통계**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 발파 횟수", len(st.session_state.blast_dataframe))
                with col2:
                    if '폭약사용량(kg)' in st.session_state.blast_dataframe.columns:
                        total_explosive = st.session_state.blast_dataframe['폭약사용량(kg)'].sum()
                        st.metric("총 폭약 사용량", f"{total_explosive:.1f} kg")
                with col3:
                    if '발파진동(cm/sec)' in st.session_state.blast_dataframe.columns:
                        max_vibration = st.session_state.blast_dataframe['발파진동(cm/sec)'].max()
                        st.metric("최대 진동", f"{max_vibration:.2f} cm/sec")
        
        # 데이터 재처리 버튼
        if st.button("🔄 데이터 재처리"):
            st.session_state.blast_data_completed = False
            st.session_state.blast_dataframe = None
            st.rerun()

else:
    st.error("HTML 파일을 로드할 수 없습니다.")