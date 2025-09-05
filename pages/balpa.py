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
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

# Gemini AI 설정
try:
    GENAI_API_KEY = "AIzaSyDAWXpI2F95oV_BlBMhHU4mHlIYn5vy1TA"
    genai.configure(api_key=GENAI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel("models/gemini-2.5-flash-preview-05-20")
    AI_AVAILABLE = True
    print("✅ Gemini AI API 키가 성공적으로 설정되었습니다.")
except Exception as e:
    st.error(f"❌ Gemini AI API 설정 중 오류: {e}")
    AI_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="AI 공사관리 에이전트",
    page_icon="✨",
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
2023-07-27	13:47	0.4	0.8	77	PD-2c
# 입력2 예시 (**2페이지 이후 표만**)
Date/Time	Peak Particle Vel (X_Axis) (mm/sec)	Peak Particle Vel (Y_Axis) (mm/sec)	Peak Particle Vel (Z_Axis) (mm/sec)	LMax (Sound) (dBA)	측정위치
2023/07/27 1:47:00 PM	0.71	0.36	0.71	61.23	양말집
2023/07/27 1:47:00 PM	0.87	0.56	0.87	53.29	티스테이션
# Mapping Rules
- 두 입력을 병합하여 위 예시와 동일한 TSV만 출력
- 설명, 마크다운, 코드블록, 주석, 기타 텍스트는 절대 포함하지 마세요.
- 계측일지 표는 반드시 PDF 2페이지 이후의 표만 사용 
- 최종 헤더(고정열): 발파일자, 발파시간, 지발당장약량(최소, kg), 지발당장약량(최대, kg), 폭약사용량(kg), 발파진동(mm/sec), 발파소음(dB(A)), 계측위치, 비고
- 정렬: 발파시간 오름차순, 계측위치 오름차순(필요시)
- 병합/매칭/포맷 규칙은 기존과 동일
'''

# Supabase 클라이언트 초기화
def init_supabase():
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        
        client = create_client(supabase_url, supabase_key)
        
        # 연결 테스트
        response = client.table('blasting_locations').select('count').execute()
        
        return client
    except Exception as e:
        st.error(f"❌ Supabase 연결 실패: {e}")
        st.error(f"❌ 오류 타입: {type(e).__name__}")
        return None

# 세션 상태 초기화
def initialize_session_state():
    if 'blast_dataframe' not in st.session_state:
        st.session_state.blast_dataframe = None
    if 'blast_data_completed' not in st.session_state:
        st.session_state.blast_data_completed = False
    if 'blasting_locations' not in st.session_state:
        st.session_state.blasting_locations = []
    if 'measurement_locations' not in st.session_state:
        st.session_state.measurement_locations = []
    if 'supabase_client' not in st.session_state:
        st.session_state.supabase_client = init_supabase()
    if 'auto_sync_completed' not in st.session_state:
        st.session_state.auto_sync_completed = False

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

# 발파위치와 계측위치 간의 거리 계산 함수
def calculate_distance_between_locations(blasting_sta, measurement_location, blasting_locations, measurement_locations):
    """
    발파위치와 계측위치 간의 실이격거리를 계산합니다.
    """
    try:
        # 발파위치 찾기
        blasting_loc = None
        for loc in blasting_locations:
            if loc.get('sta', '').replace('STA. ', '') == blasting_sta:
                blasting_loc = loc
                break
        
        if not blasting_loc:
            return "발파위치 없음"
        
        # 계측위치 찾기
        measurement_loc = None
        for loc in measurement_locations:
            if loc.get('sta', '').replace('STA. ', '') == measurement_location:
                measurement_loc = loc
                break
        
        if not measurement_loc:
            return "계측위치 없음"
        
        # 좌표 추출 (EPSG:5186)
        try:
            # 발파위치 좌표
            blasting_coords = blasting_loc.get('coordinates', '')
            if 'X:' in blasting_coords and 'Y:' in blasting_coords:
                blasting_x = float(blasting_coords.split('X: ')[1].split(',')[0])
                blasting_y = float(blasting_coords.split('Y: ')[1])
            else:
                return "발파위치 좌표 오류"
            
            # 계측위치 좌표
            measurement_coords = measurement_loc.get('coordinates', '')
            if 'X:' in measurement_coords and 'Y:' in blasting_coords:
                measurement_x = float(measurement_coords.split('X: ')[1].split(',')[0])
                measurement_y = float(measurement_coords.split('Y: ')[1])
            else:
                return "계측위치 좌표 오류"
            
            # 깊이 정보
            blasting_depth = blasting_loc.get('depth', 0)
            if isinstance(blasting_depth, str):
                blasting_depth = float(blasting_depth.replace('m', ''))
            
            # 수평 거리 계산 (미터)
            horizontal_distance = ((blasting_x - measurement_x) ** 2 + (blasting_y - measurement_y) ** 2) ** 0.5
            
            # 3D 거리 계산 (피타고라스 정리)
            vertical_distance = blasting_depth
            distance_3d = (horizontal_distance ** 2 + vertical_distance ** 2) ** 0.5
            
            # 거리 형식화 (소수점 2자리)
            return f"{horizontal_distance:.2f}m"
            
        except Exception as e:
            return f"좌표 계산 오류: {str(e)}"
            
    except Exception as e:
        return f"거리 계산 오류: {str(e)}"

# 발파위치 정보를 발파데이터에 매칭하는 함수
def match_blasting_locations_with_data(blast_df, blasting_locations):
    """
    발파데이터와 발파위치 정보를 STA 값으로 매칭하여 '발파위치' 열에 station만 표시합니다.
    지도에서 새로 추가한 데이터를 우선적으로 사용합니다.
    """
    if blast_df is None or len(blast_df) == 0:
        return blast_df
    
    # 기존 발파위치 열이 있으면 제거
    if '발파위치' in blast_df.columns:
        blast_df = blast_df.drop('발파위치', axis=1)
    
    # 발파위치 열을 발파일자 왼쪽에 추가
    blast_df.insert(0, '발파위치', '')
    
    # 지도에서 새로 추가한 데이터와 Supabase 데이터를 구분
    map_locations = [loc for loc in blasting_locations if loc.get('source') == 'map']
    supabase_locations = [loc for loc in blasting_locations if loc.get('source') != 'map']
    
    # 지도 데이터를 우선적으로 사용
    all_locations = map_locations + supabase_locations
    
    # 매칭 전략: STA 값 기반 매칭
    matched_locations = set()  # 이미 매칭된 위치 추적
    
    for i, location in enumerate(all_locations):
        location_sta = location.get('sta', '')
        
        if location_sta:
            # STA 값에서 km 추출 (예: STA. 25km688 -> 25.688)
            try:
                if 'km' in location_sta:
                    sta_km = float(location_sta.replace('STA. ', '').replace('km', ''))
                    
                    # 발파데이터에서 가장 적합한 행 찾기
                    best_match_row = None
                    best_match_score = 0
                    
                    for row_idx in range(len(blast_df)):
                        if row_idx in matched_locations:
                            continue
                        
                        # 매칭 점수 계산 (여러 기준 사용)
                        score = 0
                        
                        # 1. 지도에서 새로 추가한 데이터 우선 (가장 중요)
                        if location.get('source') == 'map':
                            score += 20
                        
                        # 2. STA 값 기반 매칭
                        if '계측위치' in blast_df.columns:
                            measurement_location = blast_df.iloc[row_idx].get('계측위치', '')
                            if measurement_location and measurement_location != '-':
                                # 계측위치가 있는 행에 우선 매칭
                                score += 10
                        
                        # 3. 발파시간 기반 매칭 (시간대별로 그룹화)
                        if '발파시간' in blast_df.columns:
                            blast_time = blast_df.iloc[row_idx].get('발파시간', '')
                            if blast_time:
                                # 오전/오후 구분으로 매칭
                                try:
                                    hour = int(blast_time.split(':')[0])
                                    if 6 <= hour <= 12:  # 오전
                                        score += 5
                                    elif 13 <= hour <= 18:  # 오후
                                        score += 5
                                except:
                                    pass
                        
                        # 4. 순서 기반 매칭 (보조적)
                        if row_idx == i:
                            score += 3
                        
                        # 5. 아직 매칭되지 않은 행 우선
                        if row_idx not in matched_locations:
                            score += 2
                        
                        if score > best_match_score:
                            best_match_score = score
                            best_match_row = row_idx
                    
                    # 최적의 매칭 행에 STA 값만 추가 (ID 제외)
                    if best_match_row is not None:
                        # STA 값만 표시 (예: 25km688)
                        station_only = location_sta.replace('STA. ', '')
                        blast_df.at[best_match_row, '발파위치'] = station_only
                        matched_locations.add(best_match_row)
                        
                        # 디버깅 정보
                        print(f"매칭 성공: {station_only} -> 행 {best_match_row} (점수: {best_match_score})")
                    else:
                        # 매칭 실패 시 빈 행에 추가
                        for row_idx in range(len(blast_df)):
                            if blast_df.iloc[row_idx].get('발파위치', '') == '':
                                station_only = location_sta.replace('STA. ', '')
                                blast_df.at[row_idx, '발파위치'] = station_only
                                matched_locations.add(row_idx)
                                print(f"빈 행에 매칭: {station_only} -> 행 {row_idx}")
                                break
                        
            except Exception as e:
                print(f"STA 파싱 오류: {location_sta}, 오류: {e}")
                # 오류 발생 시 빈 행에 추가
                for row_idx in range(len(blast_df)):
                    if blast_df.iloc[row_idx].get('발파위치', '') == '':
                        station_only = location_sta.replace('STA. ', '')
                        blast_df.at[row_idx, '발파위치'] = station_only
                        matched_locations.add(row_idx)
                        break
    
    # 매칭 결과 요약
    matched_count = len([x for x in blast_df['발파위치'] if x != ''])
    total_locations = len(blasting_locations)
    print(f"매칭 완료: {matched_count}/{total_locations} 위치가 발파데이터에 매칭됨")
    
    return blast_df



# 3D 거리 계산 및 Supabase 저장 함수
def calculate_3d_distance(blasting_location, measurement_location, row_index):
    """
    발파위치와 계측위치 간의 3D 거리를 계산하고 Supabase에 저장합니다.
    """
    try:
        # 발파위치 좌표 추출
        blasting_coords = blasting_location.get('coordinates', '')
        if 'X:' not in blasting_coords or 'Y:' not in blasting_coords:
            st.warning("⚠️ 발파위치 좌표 정보가 부족합니다.")
            return False
        
        blasting_x = float(blasting_coords.split('X: ')[1].split(',')[0])
        blasting_y = float(blasting_coords.split('Y: ')[1])
        
        # 깊이 정보
        blasting_depth = blasting_location.get('depth', 0)
        if isinstance(blasting_depth, str):
            blasting_depth = float(blasting_depth.replace('m', ''))
        
        # 계측위치 좌표 (발파 데이터에서 가져오기)
        # 여기서는 간단한 예시로 계산 (실제로는 정확한 계측위치 좌표 필요)
        # 발파위치에서 일정 거리 떨어진 지점으로 가정
        measurement_x = blasting_x + 50  # 예시: 50m 떨어진 지점
        measurement_y = blasting_y + 30  # 예시: 30m 떨어진 지점
        
        # 3D 거리 계산 (피타고라스 정리)
        horizontal_distance = ((blasting_x - measurement_x) ** 2 + (blasting_y - measurement_y) ** 2) ** 0.5
        distance_3d = (horizontal_distance ** 2 + blasting_depth ** 2) ** 0.5
        
        # Supabase에 3D 거리 저장
        if st.session_state.supabase_client:
            try:
                update_data = {
                    'distance_3d': round(distance_3d, 3)
                }
                
                # blasting_locations 테이블 업데이트
                response = st.session_state.supabase_client.table('blasting_locations').update(update_data).eq('location_id', blasting_location['id']).execute()
                
                if response.data:
                    st.success(f"✅ 3D 거리 {distance_3d:.3f}m을 Supabase에 저장했습니다!")
                else:
                    st.warning("⚠️ Supabase 저장은 실패했지만 거리 계산은 완료되었습니다.")
            except Exception as e:
                st.warning(f"⚠️ Supabase 저장 중 오류: {e}")
        
        # 발파 데이터 테이블에 거리 정보 표시
        if st.session_state.blast_dataframe is not None:
            st.session_state.blast_dataframe.at[row_index, '거리(발파↔계측)'] = f"{distance_3d:.3f}m"
        
        st.success(f"✅ 3D 거리 계산 완료: {distance_3d:.3f}m (수평: {horizontal_distance:.3f}m, 깊이: {blasting_depth}m)")
        return True
        
    except Exception as e:
        st.error(f"❌ 3D 거리 계산 중 오류: {e}")
        return False

# 발파위치 정보를 발파데이터에 매칭하는 함수
def match_blasting_locations_with_data(blast_df, blasting_locations):
    """
    발파데이터와 발파위치 정보를 STA 값으로 매칭하여 '발파위치' 열에 station만 표시합니다.
    지도에서 새로 추가한 데이터를 우선적으로 사용합니다.
    """
    if blast_df is None or len(blast_df) == 0:
        return blast_df
    
    # 기존 발파위치 열이 있으면 제거
    if '발파위치' in blast_df.columns:
        blast_df = blast_df.drop('발파위치', axis=1)
    
    # 발파위치 열을 발파일자 왼쪽에 추가
    blast_df.insert(0, '발파위치', '')
    
    # 지도에서 새로 추가한 데이터와 Supabase 데이터를 구분
    map_locations = [loc for loc in blasting_locations if loc.get('source') == 'map']
    supabase_locations = [loc for loc in blasting_locations if loc.get('source') != 'map']
    
    # 지도 데이터를 우선적으로 사용
    all_locations = map_locations + supabase_locations
    
    # 매칭 전략: STA 값 기반 매칭
    matched_locations = set()  # 이미 매칭된 위치 추적
    
    for i, location in enumerate(all_locations):
        location_sta = location.get('sta', '')
        
        if location_sta:
            # STA 값에서 km 추출 (예: STA. 25km688 -> 25.688)
            try:
                if 'km' in location_sta:
                    sta_km = float(location_sta.replace('STA. ', '').replace('km', ''))
                    
                    # 발파데이터에서 가장 적합한 행 찾기
                    best_match_row = None
                    best_match_score = 0
                    
                    for row_idx in range(len(blast_df)):
                        if row_idx in matched_locations:
                            continue
                        
                        # 매칭 점수 계산 (여러 기준 사용)
                        score = 0
                        
                        # 1. 지도에서 새로 추가한 데이터 우선 (가장 중요)
                        if location.get('source') == 'map':
                            score += 20
                        
                        # 2. STA 값 기반 매칭
                        if '계측위치' in blast_df.columns:
                            measurement_location = blast_df.iloc[row_idx].get('계측위치', '')
                            if measurement_location and measurement_location != '-':
                                # 계측위치가 있는 행에 우선 매칭
                                score += 10
                        
                        # 3. 발파시간 기반 매칭 (시간대별로 그룹화)
                        if '발파시간' in blast_df.columns:
                            blast_time = blast_df.iloc[row_idx].get('발파시간', '')
                            if blast_time:
                                # 오전/오후 구분으로 매칭
                                try:
                                    hour = int(blast_time.split(':')[0])
                                    if 6 <= hour <= 12:  # 오전
                                        score += 5
                                    elif 13 <= hour <= 18:  # 오후
                                        score += 5
                                except:
                                    pass
                        
                        # 4. 순서 기반 매칭 (보조적)
                        if row_idx == i:
                            score += 3
                        
                        # 5. 아직 매칭되지 않은 행 우선
                        if row_idx not in matched_locations:
                            score += 2
                        
                        if score > best_match_score:
                            best_match_score = score
                            best_match_row = row_idx
                    
                    # 최적의 매칭 행에 STA 값만 추가 (ID 제외)
                    if best_match_row is not None:
                        # STA 값만 표시 (예: 25km688)
                        station_only = location_sta.replace('STA. ', '')
                        blast_df.at[best_match_row, '발파위치'] = station_only
                        matched_locations.add(best_match_row)
                        
                        # 디버깅 정보
                        print(f"매칭 성공: {station_only} -> 행 {best_match_row} (점수: {best_match_score})")
                    else:
                        # 매칭 실패 시 빈 행에 추가
                        for row_idx in range(len(blast_df)):
                            if blast_df.iloc[row_idx].get('발파위치', '') == '':
                                station_only = location_sta.replace('STA. ', '')
                                blast_df.at[row_idx, '발파위치'] = station_only
                                matched_locations.add(row_idx)
                                print(f"빈 행에 매칭: {station_only} -> 행 {row_idx}")
                                break
                        
            except Exception as e:
                print(f"STA 파싱 오류: {location_sta}, 오류: {e}")
                # 오류 발생 시 빈 행에 추가
                for row_idx in range(len(blast_df)):
                    if blast_df.iloc[row_idx].get('발파위치', '') == '':
                        station_only = location_sta.replace('STA. ', '')
                        blast_df.at[row_idx, '발파위치'] = station_only
                        matched_locations.add(row_idx)
                        break
    
    # 매칭 결과 요약
    matched_count = len([x for x in blast_df['발파위치'] if x != ''])
    total_locations = len(blasting_locations)
    print(f"매칭 완료: {matched_count}/{total_locations} 위치가 발파데이터에 매칭됨")
    
    return blast_df



# Supabase에서 발파위치 데이터 조회 (distance_3d 포함)
def fetch_blasting_locations_from_supabase():
    try:
        if st.session_state.supabase_client:
            response = st.session_state.supabase_client.table('blasting_locations').select('*').execute()
            
            if response.data:
                # Supabase 데이터를 기존 형식으로 변환
                locations = []
                for item in response.data:
                    # UTC 시간을 한국 시간으로 변환
                    utc_time = item['created_at']
                    if utc_time:
                        try:
                            # UTC 시간을 한국 시간으로 변환
                            korea_tz = timezone(timedelta(hours=9))
                            if isinstance(utc_time, str):
                                # ISO 형식 문자열을 datetime 객체로 변환
                                if utc_time.endswith('Z'):
                                    utc_time = utc_time.replace('Z', '+00:00')
                                utc_dt = datetime.fromisoformat(utc_time)
                            else:
                                utc_dt = utc_time
                            
                            # UTC를 한국 시간으로 변환
                            korea_time = utc_dt.astimezone(korea_tz)
                            formatted_time = korea_time.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception as time_error:
                            # 시간 변환 실패 시 원본 시간 사용
                            formatted_time = str(utc_time)
                    else:
                        formatted_time = 'N/A'
                    
                    locations.append({
                        'id': item['location_id'],
                        'sta': item['sta'],
                        'coordinates': f"X: {item['coordinates_x']}, Y: {item['coordinates_y']}",
                        'depth': item['depth'],
                        'description': item['description'],
                        'distance_3d': item.get('distance_3d', None),  # 3D 거리 정보 추가
                        'timestamp': formatted_time,  # 한국 시간으로 변환된 시간
                        'source': 'supabase'  # Supabase에서 온 데이터임을 표시
                    })
                
                st.session_state.blasting_locations = locations
                # 발파위치 데이터 로드 완료
                return locations
            else:
                st.info("ℹ️ Supabase에 등록된 발파위치가 없습니다.")
                return []
        else:
            st.warning("⚠️ Supabase 클라이언트가 초기화되지 않았습니다.")
            return []
            
    except Exception as e:
        st.error(f"❌ Supabase 데이터 조회 중 오류: {e}")
        return []

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

# 메인 코드
def main():
    # 페이지 로드 시 자동으로 Supabase 동기화 실행
    if st.session_state.supabase_client and not st.session_state.get('auto_sync_completed', False):
        try:
            # 발파위치 데이터만 가져오기
            st.session_state.blasting_locations = fetch_blasting_locations_from_supabase()
            st.session_state.auto_sync_completed = True
        except Exception as e:
            st.warning(f"⚠️ 자동 동기화 중 오류 발생: {e}")
    
    # URL 파라미터에서 발파위치 데이터 확인
    try:
        blasting_data_param = st.query_params.get('blasting_data', None)
        if blasting_data_param:
            try:
                blasting_data = json.loads(blasting_data_param)
                if isinstance(blasting_data, list) and len(blasting_data) > 0:
                    # 기존 발파위치 데이터와 병합 (중복 제거)
                    existing_ids = {loc.get('id') for loc in st.session_state.blasting_locations}
                    
                    for new_location in blasting_data:
                        if new_location.get('id') not in existing_ids:
                            # 지도에서 새로 추가한 데이터임을 표시
                            new_location['source'] = 'map'
                            st.session_state.blasting_locations.append(new_location)
                    
                    if len(blasting_data) > 0:
                        # 발파데이터가 있으면 자동으로 발파위치 열 업데이트
                        if st.session_state.blast_dataframe is not None:
                            st.session_state.blast_dataframe = match_blasting_locations_with_data(
                                st.session_state.blast_dataframe, 
                                st.session_state.blasting_locations
                            )
                            
                            # URL 파라미터 정리
                            st.query_params.clear()
                        
            except json.JSONDecodeError:
                st.warning("⚠️ HTML에서 전송된 데이터 형식이 올바르지 않습니다.")
            except Exception as e:
                st.error(f"❌ 발파위치 데이터 동기화 중 오류: {e}")
    except Exception as e:
        pass  # URL 파라미터가 없거나 오류가 발생해도 계속 진행

    # HTML 파일 로드
    html_content = load_html_file()

    if html_content:
        # JavaScript 코드 초기화
        js_code = ""
        
        # 기본 파일들을 HTML에 포함시키기 위한 JavaScript 코드
        try:
            # 기본 노선 데이터 로드 (pages 폴더의 route.geojson)
            route_data = None
            route_paths = ['route.geojson', './route.geojson', '../route.geojson', '../../route.geojson']
            
            # pages 폴더의 route4.geojson 파일 확인
            pages_route_path = 'route4.geojson'
            if os.path.exists(pages_route_path):
                try:
                    with open(pages_route_path, 'r', encoding='utf-8') as f:
                        route_data = json.load(f)
                except Exception as e:
                    route_data = None
            
            # 노선 데이터 로드
            for route_path in route_paths:
                try:
                    with open(route_path, 'r', encoding='utf-8') as f:
                        route_data = json.load(f)
                        break
                except Exception as e:
                    continue
            
            # 기본 DXF 파일 로드 (여러 경로 시도)
            dxf_content = None
            dxf_paths = ['테스트1.dxf', '../테스트1.dxf', '../../테스트1.dxf']
            
            for dxf_path in dxf_paths:
                try:
                    with open(dxf_path, 'r', encoding='utf-8') as f:
                        dxf_content = f.read()
                        break
                except Exception as e:
                    continue
            
            # JavaScript 코드 생성
            js_code = """
            <script>
            // 기본 데이터를 전역 변수로 설정
            """
            
            if route_data:
                js_code += f"""
                window.defaultRouteData = {json.dumps(route_data)};
                console.log('기본 노선 데이터 로드됨:', window.defaultRouteData);
                """
            
            if dxf_content:
                js_code += f"""
                window.defaultDxfContent = `{dxf_content}`;
                console.log('기본 DXF 파일 로드됨:', window.defaultDxfContent);
                """
            
            js_code += """
            </script>
            """
            
        except Exception as e:
            st.error(f"기본 파일 로드 중 오류: {e}")
        
        # DXF 데이터가 있으면 JavaScript 변수로 주입
        if hasattr(st.session_state, 'dxf_data') and st.session_state.dxf_data:
            # 기존 JavaScript 코드에 추가
            js_code += f"""
            <script>
            // DXF 데이터를 전역 변수로 설정
            window.dxfData = {json.dumps(st.session_state.dxf_data)};
            console.log('DXF 데이터 로드됨:', window.dxfData);
            </script>
            """
        

        
        
        # 발파 데이터 확인 (일반 텍스트)
        st.title("💥발파데이터 분석 자동화")
        st.write("발파데이터를 업로드하면, AI가 자동으로 정리하고 분석합니다.")
        st.markdown("---")
        
        st.markdown("### 📄1. 발파 데이터 업로드")
        

        # 발파 데이터 처리 상태 확인
        if not st.session_state.blast_data_completed:
            # 파일 업로드 영역
            blast_files = st.file_uploader(
                "",
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
                                    # 발파위치 정보와 매칭
                                    df = match_blasting_locations_with_data(df, st.session_state.blasting_locations)
                                    
                                    st.session_state.blast_dataframe = df
                                    st.session_state.blast_data_completed = True
                                    st.success("✅ 2단계 완료: 발파 데이터 분석 완료!")
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
            st.success("✅ 1단계 완료: 발파 데이터가 성공적으로 처리되었습니다.")

        # 발파/계측위치 입력 섹션 추가
        st.markdown("---")
        st.markdown("### 🗺️2. 발파/계측위치 입력")

        
        # 즉시 동기화 버튼 추가
        col_sync1, col_sync2 = st.columns([3, 1])
        with col_sync1:
            st.info("💡 **지도에서 발파위치를 추가한 후 아래 버튼을 클릭하여 즉시 동기화하세요.**")
        with col_sync2:
            if st.button("🔄 즉시 동기화", type="primary", help="Supabase에서 최신 발파위치 데이터를 가져옵니다"):
                with st.spinner('🔄 최신 발파위치 데이터를 동기화하고 있습니다...'):
                    try:
                        # Supabase에서 최신 데이터 가져오기
                        st.session_state.blasting_locations = fetch_blasting_locations_from_supabase()
                        
                        # 발파데이터가 있으면 자동으로 발파위치 열 업데이트
                        if st.session_state.blast_dataframe is not None:
                            # 발파위치 매칭
                            st.session_state.blast_dataframe = match_blasting_locations_with_data(
                                st.session_state.blast_dataframe, 
                                st.session_state.blasting_locations
                            )
                        
                        st.success("✅ 최신 발파위치 데이터 동기화 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 동기화 중 오류 발생: {e}")



        # HTML에 JavaScript 코드 삽입
        html_content = html_content.replace('</head>', js_code + '</head>')
        
        # HTML을 Streamlit에 표시 (화면 하단에 배치)
        html_component = st.components.v1.html(
            html_content,
            height=800,
            scrolling=True
        )
        

        
        # 처리된 데이터 표시
        if st.session_state.blast_data_completed and st.session_state.blast_dataframe is not None:
            with st.expander("📊 처리된 발파 데이터 보기", expanded=True):
                # 발파 데이터 표시
                st.markdown("**📋 발파 데이터 테이블**")
                
                # 발파위치 연결 기능
                st.markdown("**🔗 발파위치 연결**")
                st.info("💡 **사용법**: 아래에서 발파위치(STA)를 선택하면 해당 행의 발파위치와 실거리를 자동으로 매핑합합니다.")
                
                # 발파위치(STA) 선택
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    selected_row = st.selectbox(
                        "발파 데이터 행 선택",
                        range(len(st.session_state.blast_dataframe)),
                        format_func=lambda x: f"행 {x+1}: {st.session_state.blast_dataframe.iloc[x]['발파일자']} {st.session_state.blast_dataframe.iloc[x]['발파시간']}"
                    )
                with col_b:
                    # 발파위치 목록을 최신 데이터로 업데이트
                    station_options = ["발파위치 없음"]
                    if st.session_state.blasting_locations:
                        # 지도에서 추가한 데이터를 우선적으로 표시
                        map_locations = [loc for loc in st.session_state.blasting_locations if loc.get('source') == 'map']
                        supabase_locations = [loc for loc in st.session_state.blasting_locations if loc.get('source') != 'map']
                        
                        # 지도 데이터 + Supabase 데이터 순서로 정렬
                        all_locations = map_locations + supabase_locations
                        
                        for loc in all_locations:
                            sta_value = loc['sta'].replace('STA. ', '')
                            source_marker = "🆕" if loc.get('source') == 'map' else "💾"
                            station_options.append(f"{source_marker} {sta_value}")
                    
                    selected_station = st.selectbox(
                        "발파위치(STA) 선택",
                        station_options,
                        key="station_selector"
                    )
                
                if st.button("🔗 발파위치 연결", type="primary"):
                    if selected_station != "발파위치 없음":
                        # 디버깅 정보 추가
                        st.info(f"🔍 **디버깅 정보**: 선택된 행 {selected_row+1}, 선택된 발파위치: {selected_station}")
                        
                        # 선택된 위치 정보 찾기 (이모지 제거 후 비교)
                        selected_sta = selected_station.replace('🆕 ', '').replace('💾 ', '')
                        st.info(f"🔍 **STA 값**: {selected_sta}")
                        
                        # blasting_locations 상태 확인
                        st.info(f"🔍 **발파위치 데이터 수**: {len(st.session_state.blasting_locations)}")
                        
                        selected_location = next((loc for loc in st.session_state.blasting_locations if loc['sta'].replace('STA. ', '') == selected_sta), None)
                        
                        if selected_location:
                            st.info(f"✅ **위치 찾음**: {selected_location}")
                            
                            # 발파위치 열 업데이트 (STA 값만 표시)
                            station_only = selected_location['sta'].replace('STA. ', '')
                            st.session_state.blast_dataframe.at[selected_row, '발파위치'] = station_only
                            
                            # 계측위치 확인 및 거리 계산
                            measurement_location = st.session_state.blast_dataframe.iloc[selected_row].get('계측위치', '')
                            st.info(f"🔍 **계측위치**: {measurement_location}")
                            
                            # Supabase에 저장된 distance_3d 값이 있는지 확인
                            if selected_location.get('distance_3d') and selected_location['distance_3d'] > 0:
                                # 저장된 3D 거리 값 사용
                                stored_distance = selected_location['distance_3d']
                                if st.session_state.blast_dataframe is not None:
                                    st.session_state.blast_dataframe.at[selected_row, '거리(발파↔계측)'] = f"{stored_distance:.3f}m"
                                st.success(f"✅ Supabase에 저장된 3D 거리: {stored_distance:.3f}m")
                            elif measurement_location and measurement_location != '-':
                                # 기존 계측위치와 3D 거리 계산
                                try:
                                    calculate_3d_distance(
                                        selected_location, 
                                        measurement_location,
                                        selected_row
                                    )
                                except Exception as e:
                                    st.warning(f"⚠️ 3D 거리 계산 중 오류: {e}")
                            else:
                                st.info("💡 계측위치 정보가 필요합니다. 발파 데이터에 계측위치를 입력한 후 다시 시도해주세요.")
                            
                            # 연결 성공 메시지에 소스 정보 포함
                            source_info = "🆕 새로 추가됨" if selected_location.get('source') == 'map' else "💾 기존 데이터"
                            st.success(f"✅ 행 {selected_row+1}에 발파위치 '{station_only}' 연결 완료! ({source_info})")
                            st.rerun()
                        else:
                            st.error(f"❌ 선택된 발파위치를 찾을 수 없습니다. STA: {selected_sta}")
                            st.error(f"❌ 사용 가능한 발파위치: {[loc['sta'].replace('STA. ', '') for loc in st.session_state.blasting_locations]}")
                    else:
                        st.warning("발파위치(STA)를 선택해주세요.")
                
                st.markdown("---")
                st.markdown("**📊 발파 데이터 테이블**")
                
                # 모든 열을 표시
                st.dataframe(st.session_state.blast_dataframe, use_container_width=True)
                
                # AI 데이터 분석 정보
                st.markdown("**📈 AI 데이터 분석**")
                
                try:
                    if st.session_state.blast_dataframe is not None and len(st.session_state.blast_dataframe) > 0:
                        df = st.session_state.blast_dataframe
                        

                        
                        # 1. 발파위치 분석
                        blasting_locations = df['발파위치'].dropna().unique()
                        blasting_locations = [loc for loc in blasting_locations if loc != '' and loc != '-']
                        location_count = len(blasting_locations)
                        location_text = f"{location_count}곳({', '.join(blasting_locations)})" if location_count > 0 else "0곳"
                        
                        # 2. 발파횟수
                        blast_count = len(df)
                        
                        # 3. 안정성 평가 (관리기준치 0.2Kine(0.2cm/sec)로 표시하지만 실제 비교는 테이블 값 기준)
                        safety_threshold = 0.2  # 테이블 값 기준 (0.2)
                        
                        # 실제 컬럼명 확인 및 처리
                        vibration_column_name = None
                        for col in df.columns:
                            if '발파진동' in col:
                                vibration_column_name = col
                                break
                        
                        if vibration_column_name:
                            vibration_col = pd.to_numeric(df[vibration_column_name], errors='coerce')
                            # 테이블 값 그대로 사용 (단위만 cm/sec로 표시)
                            max_vibration_value = vibration_col.dropna().max()
                        else:
                            vibration_col = pd.Series([], dtype=float)
                            max_vibration_value = None
                        
                        if pd.isna(max_vibration_value):
                            safety_status = "데이터 없음"
                        elif max_vibration_value <= safety_threshold:
                            safety_status = f"관리기준치 0.2Kine(0.2cm/sec) 이내로 안정적으로 관리중"
                        else:
                            safety_status = f"관리기준치 0.2Kine(0.2cm/sec)를 초과하였습니다. 이상 유무 확인바랍니다."
                        
                        # 4. 최대 진동 상세 정보
                        if not pd.isna(max_vibration_value) and max_vibration_value > 0:
                            # 최대 진동이 발생한 행 찾기
                            max_vibration_row = df.loc[vibration_col.idxmax()]
                            max_time = max_vibration_row.get('발파시간', 'N/A')
                            max_location = max_vibration_row.get('발파위치', 'N/A')
                            # 테이블 값 그대로 사용하고 단위만 cm/sec로 표시
                            max_vibration_detail = f"최대 진동은 {max_time} {max_location} 발파시, {max_vibration_value:.3f}cm/sec로 기록되었습니다."
                        else:
                            max_vibration_detail = "진동 데이터가 없습니다."
                        
                        # 결과 표시 - 4개 컬럼으로 깔끔하게 구성
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.markdown(f"""
                            <div style="text-align: center;">
                                <div style="font-size: 16px; font-weight: 600; color: #1f77b4; margin-bottom: 8px;">
                                    🌏 발파위치
                                </div>
                                <div style="font-size: 36px; font-weight: 700; color: #2c3e50; margin-bottom: 4px;">
                                    {location_count}곳
                                </div>
                                <div style="font-size: 12px; color: #7f8c8d; line-height: 1.3;">
                                    {', '.join(blasting_locations) if location_count > 0 else '위치 없음'}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(f"""
                            <div style="text-align: center;">
                                <div style="font-size: 16px; font-weight: 600; color: #e74c3c; margin-bottom: 8px;">
                                    💥 발파횟수
                                </div>
                                <div style="font-size: 36px; font-weight: 700; color: #2c3e50;">
                                    {blast_count}회
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            # 최대 진동치 + 기준치 이내 여부 코멘트
                            if vibration_column_name and not pd.isna(max_vibration_value) and max_vibration_value > 0:
                                try:
                                    max_vibration_row = df.loc[vibration_col.idxmax()]
                                    max_time = max_vibration_row.get('발파시간', 'N/A')
                                    max_location = max_vibration_row.get('발파위치', 'N/A')
                                    
                                    if max_vibration_value <= safety_threshold:
                                        status_icon = "✅"
                                        status_text = "기준치(0.2Kine(0.2cm/sec)) 이내"
                                        status_color = "#27ae60"
                                    else:
                                        status_icon = "⚠️"
                                        status_text = "기준치(0.2Kine(0.2cm/sec)) 초과"
                                        status_color = "#e67e22"
                                    
                                    st.markdown(f"""
                                    <div style="text-align: center;">
                                        <div style="font-size: 16px; font-weight: 600; color: #f39c12; margin-bottom: 8px;">
                                            📊 최대 진동치
                                        </div>
                                        <div style="font-size: 36px; font-weight: 700; color: #2c3e50; margin-bottom: 4px;">
                                            {max_vibration_value:.3f}cm/sec
                                        </div>
                                        <div style="font-size: 12px; color: #7f8c8d; margin-bottom: 4px;">
                                            {max_time} {max_location}
                                        </div>
                                        <div style="font-size: 14px; color: {status_color}; font-weight: 600;">
                                            {status_icon} {status_text}
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                except Exception as e:
                                    st.markdown(f"""
                                    <div style="text-align: center;">
                                        <div style="font-size: 16px; font-weight: 600; color: #f39c12; margin-bottom: 8px;">
                                            📊 최대 진동치
                                        </div>
                                        <div style="font-size: 14px; color: #7f8c8d;">
                                            계산 오류
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div style="text-align: center;">
                                    <div style="font-size: 16px; font-weight: 600; color: #f39c12; margin-bottom: 8px;">
                                        📊 최대 진동치
                                    </div>
                                    <div style="font-size: 14px; color: #7f8c8d;">
                                        데이터 없음
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        with col4:
                            # 최대 소음치
                            try:
                                if '발파소음(dB(A))' in df.columns:
                                    noise_col = pd.to_numeric(df['발파소음(dB(A))'], errors='coerce')
                                    max_noise = noise_col.dropna().max()
                                    if not pd.isna(max_noise):
                                        st.markdown(f"""
                                        <div style="text-align: center;">
                                            <div style="font-size: 16px; font-weight: 600; color: #9b59b6; margin-bottom: 8px;">
                                                🔊 최대 소음치
                                            </div>
                                            <div style="font-size: 36px; font-weight: 700; color: #2c3e50;">
                                                {max_noise:.1f} dB(A)
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"""
                                        <div style="text-align: center;">
                                            <div style="font-size: 16px; font-weight: 600; color: #9b59b6; margin-bottom: 8px;">
                                                🔊 최대 소음치
                                            </div>
                                            <div style="font-size: 14px; color: #7f8c8d;">
                                                데이터 없음
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.markdown(f"""
                                    <div style="text-align: center;">
                                        <div style="font-size: 16px; font-weight: 600; color: #9b59b6; margin-bottom: 8px;">
                                            🔊 최대 소음치
                                        </div>
                                        <div style="font-size: 14px; color: #7f8c8d;">
                                            컬럼 없음
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            except Exception as e:
                                st.markdown(f"""
                                <div style="text-align: center;">
                                    <div style="font-size: 16px; font-weight: 600; color: #9b59b6; margin-bottom: 8px;">
                                        🔊 최대 소음치
                                    </div>
                                    <div style="font-size: 14px; color: #7f8c8d;">
                                        계산 오류
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ 분석할 발파 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ 데이터 분석 중 오류가 발생했습니다: {str(e)}")
            
            # 저장하기 버튼
            if st.button("💾 Database에 저장하기", type="primary"):
                if st.session_state.blast_dataframe is not None and len(st.session_state.blast_dataframe) > 0:
                    try:
                        with st.spinner("💾 발파 데이터를 Daatabase에 저장 중..."):
                            # 발파데이터를 Supabase blast_data 테이블에 저장
                            success_count = save_blast_data_to_supabase(st.session_state.blast_dataframe)
                            
                            if success_count > 0:
                                st.success(f"✅ {success_count}개의 발파 데이터가 성공적으로 Supabase에 저장되었습니다!")
                            else:
                                st.warning("⚠️ 저장된 데이터가 없습니다.")
                    except Exception as e:
                        st.error(f"❌ 저장 중 오류가 발생했습니다: {str(e)}")
                else:
                    st.warning("⚠️ 저장할 발파 데이터가 없습니다.")
    else:
        st.error("HTML 파일을 로드할 수 없습니다.")

# 발파데이터를 Supabase blast_data 테이블에 저장하는 함수
def save_blast_data_to_supabase(blast_dataframe):
    """
    발파데이터프레임을 Supabase의 blast_data 테이블에 저장합니다.
    """
    try:
        if not st.session_state.supabase_client:
            st.error("❌ Supabase 클라이언트가 초기화되지 않았습니다.")
            return 0
        
        if blast_dataframe is None or len(blast_dataframe) == 0:
            st.warning("⚠️ 저장할 발파 데이터가 없습니다.")
            return 0
        
        # 데이터프레임을 딕셔너리 리스트로 변환
        blast_data_list = []
        
        for index, row in blast_dataframe.iterrows():
            # 거리 정보에서 숫자만 추출
            distance_str = str(row.get('거리(발파↔계측)', '0m'))
            distance_value = float(re.findall(r'[\d.]+', distance_str)[0]) if re.findall(r'[\d.]+', distance_str) else 0.0
            
            # 발파진동에서 숫자만 추출
            vibration_str = str(row.get('발파진동(mm/sec)', '0'))
            vibration_value = float(re.findall(r'[\d.]+', vibration_str)[0]) if re.findall(r'[\d.]+', vibration_str) else 0.0
            
            # 발파소음에서 숫자만 추출
            noise_str = str(row.get('발파소음(dB(A))', '0'))
            noise_value = float(re.findall(r'[\d.]+', noise_str)[0]) if re.findall(r'[\d.]+', noise_str) else 0.0
            
            # 폭약사용량에서 숫자만 추출
            explosive_str = str(row.get('폭약사용량(kg)', '0'))
            explosive_value = float(re.findall(r'[\d.]+', explosive_str)[0]) if re.findall(r'[\d.]+', explosive_str) else 0.0
            
            # 지발당장약량(최소)에서 숫자만 추출
            charge_min_str = str(row.get('지발당장약량(최소, kg)', '0'))
            charge_min_value = float(re.findall(r'[\d.]+', charge_min_str)[0]) if re.findall(r'[\d.]+', charge_min_str) else 0.0
            
            # 지발당장약량(최대)에서 숫자만 추출
            charge_max_str = str(row.get('지발당장약량(최대, kg)', '0'))
            charge_max_value = float(re.findall(r'[\d.]+', charge_max_str)[0]) if re.findall(r'[\d.]+', charge_max_str) else 0.0
            
            blast_data = {
                'blasting_location': str(row.get('발파위치', '')),
                'blasting_date': str(row.get('발파일자', '')),
                'blasting_time': str(row.get('발파시간', '')),
                'charge_per_delay_min': charge_min_value,
                'charge_per_delay_max': charge_max_value,
                'explosive_usage': explosive_value,
                'blasting_vibration': vibration_value,
                'blasting_noise': noise_value,
                'measurement_location': str(row.get('계측위치', '')),
                'remarks': str(row.get('비고', '')),
                'distance_blasting_to_measurement': distance_value
            }
            
            blast_data_list.append(blast_data)
        
        # Supabase에 저장
        success_count = 0
        
        for blast_data in blast_data_list:
            try:
                # blast_data 테이블에 upsert (중복 시 업데이트)
                response = st.session_state.supabase_client.table('blast_data').upsert(
                    blast_data,
                    on_conflict='blasting_location,blasting_date,blasting_time'
                ).execute()
                
                if response.data:
                    success_count += 1
                else:
                    st.warning(f"⚠️ {blast_data['blasting_location']} - {blast_data['blasting_date']} {blast_data['blasting_time']} 저장 실패")
                    
            except Exception as e:
                st.error(f"❌ {blast_data['blasting_location']} - {blast_data['blasting_date']} {blast_data['blasting_time']} 저장 중 오류: {str(e)}")
        
        return success_count
        
    except Exception as e:
        st.error(f"❌ 발파데이터 저장 중 오류: {str(e)}")
        return 0

# 메인 함수 실행
if __name__ == "__main__":
    initialize_session_state()
    main()