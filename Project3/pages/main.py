import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import requests
from supabase import create_client, Client
import os
import google.generativeai as genai

# 페이지 설정
st.set_page_config(
    page_title="나만의 AI 챗봇",
    page_icon="🤖",
    layout="wide"
)

# Supabase 설정
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
else:
    st.error("Supabase 설정이 필요합니다. 환경변수 SUPABASE_URL과 SUPABASE_KEY를 확인해주세요.")
    st.stop()

# Gemini AI 설정
GENAI_API_KEY = "AIzaSyD69-wKYfZSID327fczrkx-JveJdGYIUIk"
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel("models/gemini-2.5-flash-preview-05-20")
else:
    st.error("Gemini API 키가 필요합니다.")
    st.stop()

# 함수 정의 (사용하기 전에 먼저 정의)
def debug_table_structure():
    """테이블 구조를 디버깅합니다."""
    st.subheader("🔍 테이블 구조 디버깅")
    
    tables = [
        'daily_report_data', 'blast_data', 'instrument_data', 
        'cell_mappings', 'construction_status', 'equipment_data',
        'personnel_data', 'prompts', 'templates', 'work_content'
    ]
    
    for table_name in tables:
        try:
            # 테이블에서 첫 번째 레코드 가져오기
            result = supabase.table(table_name).select('*').limit(1).execute()
            
            if result.data:
                st.write(f"✅ **{table_name}** - 데이터 있음")
                st.json(result.data[0])
            else:
                st.write(f"❌ **{table_name}** - 데이터 없음")
                
        except Exception as e:
            st.write(f"❌ **{table_name}** - 오류: {str(e)}")
        
        st.markdown("---")

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

def search_specific_data(user_input):
    """사용자 입력에서 특정 정보를 검색합니다."""
    search_results = {}
    
    # 날짜 추출 (7월 21일, 2024-07-21 등)
    import re
    date_patterns = [
        r'(\d{1,2})월\s*(\d{1,2})일',
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})'
    ]
    
    extracted_date = None
    for pattern in date_patterns:
        match = re.search(pattern, user_input)
        if match:
            if len(match.groups()) == 2:  # 월/일
                month, day = match.groups()
                extracted_date = f"2024-{month.zfill(2)}-{day.zfill(2)}"
            elif len(match.groups()) == 3:
                if len(match.group(1)) == 4:  # YYYY-MM-DD
                    extracted_date = f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                else:  # MM/DD/YYYY
                    extracted_date = f"{match.group(3)}-{match.group(1).zfill(2)}-{match.group(2).zfill(2)}"
            break
    
    # 키워드 추출 (연수생, 인력, 인원 등 추가)
    keywords = ['본선터널', '1구간', '라이닝', '시공현황', '터널', '구간', '라이닝', 
                '연수생', '인력', '인원', '작업자', '직원', '사원', '투입',
                '신풍', '주출입구', '출입구', '계측', '측정', '데이터']
    found_keywords = [kw for kw in keywords if kw in user_input]
    
    try:
        # 날짜가 있으면 해당 날짜로 검색 (더 유연한 검색)
        if extracted_date:
            for table_name in ['daily_report_data', 'construction_status', 'work_content', 
                              'personnel_data', 'equipment_data']:
                try:
                    # 모든 데이터를 가져와서 날짜 필터링
                    result = supabase.table(table_name).select('*').execute()
                    if result.data:
                        date_filtered_data = []
                        for row in result.data:
                            # 다양한 날짜 컬럼 확인
                            date_columns = ['date', 'report_date', 'work_date', 'created_at', 'work_date']
                            for col in date_columns:
                                if col in row:
                                    row_date = str(row[col])
                                    # 다양한 날짜 형식 지원
                                    if (extracted_date in row_date or 
                                        row_date.startswith(extracted_date) or
                                        row_date.endswith(extracted_date)):
                                        date_filtered_data.append(row)
                                        break
                        if date_filtered_data:
                            search_results[f"{table_name}_date"] = date_filtered_data
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
1. **연수생 관련 질문**의 경우:
   - personnel_data 테이블의 모든 데이터를 확인
   - 날짜, 구간, 연수생 수를 정확히 파악
   - "personnel_data_all" 키가 있으면 해당 데이터를 우선 분석
   - 구체적인 수치를 제공 (예: "12명")

2. **날짜 관련 질문**의 경우:
   - 해당 날짜의 모든 관련 데이터를 확인
   - 날짜 형식이 다를 수 있으므로 유연하게 검색
   - "date", "report_date", "work_date" 등 다양한 컬럼 확인

3. **구간 관련 질문**의 경우:
   - "본선터널", "1구간" 등의 키워드를 포함한 데이터 검색
   - 해당 구간의 구체적인 정보 제공

4. **신풍 주출입구 관련 질문**의 경우:
   - instrument_data 테이블의 모든 데이터를 확인
   - "신풍", "주출입구", "출입구" 등의 키워드가 포함된 데이터 검색
   - "instrument_data_all" 키가 있으면 해당 데이터를 우선 분석
   - 계측 데이터의 구체적인 수치와 단위를 제공
   - 데이터가 없는 경우 유사한 위치나 다른 날짜의 데이터도 확인

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
    """사용자 입력에 대한 AI 응답을 생성합니다."""
    
    try:
        # Supabase에서 데이터 가져오기
        context_data = get_context_data()
        
        # Gemini 프롬프트 생성
        prompt = create_gemini_prompt(user_input, context_data)
        
        # Gemini 모델로 응답 생성
        response = GEMINI_MODEL.generate_content(prompt)
        
        # HTML 태그 제거 (더 강력한 방법)
        import re
        clean_response = response.text
        
        # HTML 태그 제거
        clean_response = re.sub(r'<[^>]+>', '', clean_response)
        
        # HTML 엔티티 복원
        clean_response = clean_response.replace('&lt;', '<').replace('&gt;', '>')
        clean_response = clean_response.replace('&amp;', '&').replace('&quot;', '"')
        clean_response = clean_response.replace('&#39;', "'").replace('&nbsp;', ' ')
        
        # 불필요한 공백 정리
        clean_response = re.sub(r'\s+', ' ', clean_response).strip()
        
        # 빈 줄 제거
        clean_response = re.sub(r'\n\s*\n', '\n', clean_response)
        
        return clean_response
        
    except Exception as e:
        # 오류 발생 시 기본 응답
        return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"

# 페이지 제목 (숨김)
# st.title("나만의 AI 챗봇")

# CSS 스타일 추가
st.markdown("""
<style>
    /* 전체 페이지 배경 투명화 */
    .main .block-container {
        background: transparent !important;
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 100% !important;
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
        background: #1a73e8;
        color: white;
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
    
    /* 버튼 스타일 */
    .stButton > button {
        border-radius: 4px !important;
        font-weight: 500 !important;
        padding: 4px 8px !important;
        transition: all 0.2s ease !important;
        border: none !important;
        font-size: 12px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15) !important;
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
    }
    
    .stTextArea textarea {
        border-radius: 6px !important;
        border: 1px solid #e8eaed !important;
        padding: 6px 8px !important;
        font-size: 13px !important;
        background: #ffffff !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #1a73e8 !important;
        box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2) !important;
        outline: none !important;
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
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
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
</style>
""", unsafe_allow_html=True)

# 헤더 섹션 (채팅이 없을 때만 표시)
if "chat_history" not in st.session_state or len(st.session_state.chat_history) == 0:
    st.markdown("""
    <div style="text-align: center; margin: 40px 0; padding: 20px;">
        <h1 style="font-size: 2.5rem; font-weight: bold; margin-bottom: 10px;">
            <span style="color: #007bff;">실시간 검색</span>, 사진 이해, 그림/차트 생성
        </h1>
        <h2 style="font-size: 1.8rem; font-weight: 600; color: #333; margin: 0;">
            업무 대화 모두 OK!
        </h2>
    </div>
    """, unsafe_allow_html=True)
else:
    # 채팅이 있을 때는 최소한의 여백만 추가
    st.markdown('<div style="margin-top: 5px;"></div>', unsafe_allow_html=True)



# 채팅 히스토리 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 채팅 히스토리 표시
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

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
                <div class="avatar ai-avatar">🤖</div>
                <div style="flex: 1;">
                    <div class="ai-header">
                        <span>Gemini</span>
                    </div>
                    <div class="message-bubble ai-bubble">
                        {message['content']}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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
    "메시지를 입력하세요:",
    key="user_input",
    height=100,
    placeholder="질문이나 요청사항을 입력하세요..."
)

# 전송 버튼 스타일링
st.markdown("""
<style>
.stButton > button[kind="primary"] {
    background-color: #007bff !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: bold !important;
    transition: all 0.3s ease !important;
}

.stButton > button[kind="primary"]:hover {
    background-color: #0056b3 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0,123,255,0.4) !important;
}

.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
}

/* 대화 초기화 버튼 스타일링 */
.stButton > button:not([kind="primary"]) {
    background-color: transparent !important;
    color: #dc3545 !important;
    border: 2px solid #dc3545 !important;
    border-radius: 8px !important;
    font-weight: bold !important;
    transition: all 0.3s ease !important;
}

.stButton > button:not([kind="primary"]):hover {
    background-color: #dc3545 !important;
    color: white !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(220,53,69,0.4) !important;
}

.stButton > button:not([kind="primary"]):active {
    transform: translateY(0) !important;
}
</style>
""", unsafe_allow_html=True)

# 전송 버튼
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("📤 전송", use_container_width=True, type="primary"):
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
            
            # AI 응답 생성
            try:
                ai_response = generate_ai_response(clean_user_input)
            except Exception as e:
                st.error(f"AI 응답 생성 중 오류: {str(e)}")
                ai_response = "죄송합니다. 응답 생성 중 오류가 발생했습니다."
            
            # AI 메시지 추가
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now()
            })
            
            st.rerun()

with col_btn2:
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        if "chat_history" in st.session_state:
            st.session_state.chat_history = []
        st.rerun()



# 추가 기능 버튼들
st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)

# 큰 버튼을 위한 CSS 스타일 추가
st.markdown("""
<style>
.big-button {
    height: 120px !important;
    font-size: 18px !important;
    font-weight: bold !important;
    padding: 20px !important;
    margin: 10px 0 !important;
    border-radius: 15px !important;
    border: 2px solid #e0e0e0 !important;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important;
    transition: all 0.3s ease !important;
}

.big-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
    border-color: #007bff !important;
}

.big-button:active {
    transform: translateY(0) !important;
}
</style>
""", unsafe_allow_html=True)

col_btn3, col_btn4, col_btn5, col_btn6 = st.columns(4)

with col_btn3:
    st.markdown('''
    <div class="big-button" style="display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; text-align: center;" onclick="window.location.href='pages/2_발파데이터_자동화계측기.py'">
        <div style="font-size: 20px; font-weight: bold; margin-bottom: 8px;">💥 발파/계측분석 자동화</div>
        <div style="font-size: 14px; color: #666; line-height: 1.4;">
            발파일지&발파계측 분석<br>
            자동화계측 데이터 자동추출<br>
            계측기 이상치 탐지/분석/경고알림
        </div>
    </div>
    ''', unsafe_allow_html=True)

with col_btn4:
    st.markdown('''
    <div class="big-button" style="display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; text-align: center;" onclick="window.location.href='pages/SNS일일작업계획.py'">
        <div style="font-size: 20px; font-weight: bold; margin-bottom: 8px;">📋 작업일보 자동화</div>
        <div style="font-size: 14px; color: #666; line-height: 1.4;">
            SNS 일일작업보고<br>
            작업일보 문서화
        </div>
    </div>
    ''', unsafe_allow_html=True)

with col_btn5:
    st.markdown('''
    <div class="big-button" style="display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; text-align: center;" onclick="window.location.href='pages/작업일보_작성.py'">
        <div style="font-size: 20px; font-weight: bold; margin-bottom: 8px;">⚙️ 공정분석 자동화</div>
        <div style="font-size: 14px; color: #666; line-height: 1.4;">
            대표물량 작성 및 공정률 산정<br>
            주, 월간 공정실적 리포트
        </div>
    </div>
    ''', unsafe_allow_html=True)

with col_btn6:
    st.markdown('''
    <div class="big-button" style="display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; text-align: center;" onclick="window.location.href='pages/작업일보_작성.py'">
        <div style="font-size: 20px; font-weight: bold; margin-bottom: 8px;">💰 원가관리 자동화</div>
        <div style="font-size: 14px; color: #666; line-height: 1.4;">
            예상 도급기성 전망<br>
            (실적+향후(예측))<br>
            작업일보 기반 투입비 예측
        </div>
    </div>
    ''', unsafe_allow_html=True)