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
    page_title="AI 챗봇",
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

def show_data_statistics():
    """데이터 통계를 보여줍니다."""
    try:
        # Supabase에서 데이터 가져오기
        daily_reports = supabase.table('daily_report_data').select('*').execute()
        blasting_data = supabase.table('blast_data').select('*').execute()
        measurement_data = supabase.table('instrument_data').select('*').execute()
        
        st.subheader("📊 데이터 통계")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("일일보고 총 건수", len(daily_reports.data) if daily_reports.data else 0)
            if daily_reports.data:
                latest_date = max([r.get('report_date', '') for r in daily_reports.data])
                st.metric("최신 보고 날짜", latest_date)
        
        with col2:
            st.metric("발파데이터 총 건수", len(blasting_data.data) if blasting_data.data else 0)
            if blasting_data.data:
                total_charge = sum([r.get('charge_weight', 0) for r in blasting_data.data])
                st.metric("총 장약량", f"{total_charge}kg")
        
        with col3:
            st.metric("계측데이터 총 건수", len(measurement_data.data) if measurement_data.data else 0)
            if measurement_data.data:
                avg_value = np.mean([r.get('measurement_value', 0) for r in measurement_data.data])
                st.metric("평균 측정값", f"{avg_value:.2f}")
        
    except Exception as e:
        st.error(f"통계 생성 중 오류: {str(e)}")

def show_trend_analysis():
    """트렌드 분석을 보여줍니다."""
    st.info("📈 트렌드 분석 기능은 개발 중입니다.")

def detect_anomalies():
    """이상치를 탐지합니다."""
    st.info("⚠️ 이상치 탐지 기능은 개발 중입니다.")

def generate_report():
    """자동 보고서를 생성합니다."""
    st.info("📋 자동 보고서 기능은 개발 중입니다.")

# 페이지 제목
st.title("🤖 AI 챗봇")
st.markdown("---")

# Gemini 스타일 전체 페이지 스타일
st.markdown("""
<style>
.main-header {
    background: #ffffff;
    color: #202124;
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 24px;
    text-align: center;
    border: 1px solid #e8eaed;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.sidebar-section {
    background: #ffffff;
    border-radius: 12px;
    padding: 16px;
    margin: 12px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border: 1px solid #e8eaed;
}
.data-metrics {
    background: #ffffff;
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border: 1px solid #e8eaed;
}
.metric-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #f1f3f4;
    font-size: 14px;
}
.metric-item:last-child {
    border-bottom: none;
}
.metric-label {
    font-weight: 500;
    color: #5f6368;
}
.metric-value {
    font-weight: 600;
    color: #1a73e8;
}
.feature-section {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border: 1px solid #e8eaed;
}
.feature-button {
    background: #1a73e8;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    transition: all 0.2s ease;
    width: 100%;
    margin: 4px 0;
    font-size: 14px;
}
.feature-button:hover {
    background: #1557b0;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
}
.help-section {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    border: 1px solid #e8eaed;
}
.stSelectbox > div > div {
    border-radius: 8px !important;
    border: 1px solid #e8eaed !important;
}
.stSelectbox > div > div:hover {
    border-color: #1a73e8 !important;
}
.stCheckbox > div {
    border-radius: 4px !important;
}
.stCheckbox > div > div {
    border-radius: 4px !important;
}
</style>
""", unsafe_allow_html=True)

# 사이드바 설정
st.sidebar.markdown("""
<div class="sidebar-section">
    <h3>⚙️ 챗봇 설정</h3>
</div>
""", unsafe_allow_html=True)

chat_model = st.sidebar.selectbox(
    "챗봇 모델 선택",
    ["Gemini 2.5 Flash", "GPT-3.5", "GPT-4", "Claude"],
    index=0
)

# 디버그 모드 추가
debug_mode = st.sidebar.checkbox("🔍 디버그 모드", value=False, key="debug_mode_checkbox")
st.session_state['debug_mode'] = debug_mode
if debug_mode:
    st.sidebar.markdown("""
    <div class="sidebar-section">
        <h4>🔍 디버그 정보</h4>
        <p>테이블 구조를 확인하려면 메인 화면에서 디버그 모드를 활성화하세요.</p>
    </div>
    """, unsafe_allow_html=True)

# 채팅 히스토리 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 메인 채팅 인터페이스
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 채팅창")
    
    # 디버그 모드가 활성화되면 테이블 구조 표시
    if st.session_state.get('debug_mode', False):
        st.info("🔍 디버그 모드가 활성화되었습니다. 테이블 구조를 확인합니다.")
        debug_table_structure()
    
    # Gemini 스타일 채팅 UI
    st.markdown("""
    <style>
    .chat-container {
        height: 600px;
        overflow-y: auto;
        border: none;
        border-radius: 16px;
        padding: 24px;
        background: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin: 16px 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .user-message {
        display: flex;
        justify-content: flex-end;
        margin: 8px 0;
        padding: 0 8px;
        order: 1;
    }
    .ai-message {
        display: flex;
        justify-content: flex-start;
        margin: 8px 0;
        padding: 0 8px;
        order: 2;
    }
    .message-bubble {
        padding: 12px 16px;
        border-radius: 18px;
        max-width: 70%;
        word-wrap: break-word;
        position: relative;
        font-size: 14px;
        line-height: 1.4;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .user-bubble {
        background: #f5f5f5;
        color: #333333;
        border-radius: 18px 18px 4px 18px;
        margin-left: auto;
        text-align: left;
        border: 1px solid #e0e0e0;
    }
    .ai-bubble {
        background: #ffffff;
        color: #202124;
        border-radius: 18px 18px 18px 4px;
        border: 1px solid #e0e0e0;
    }
    .message-header {
        font-weight: 500;
        margin-bottom: 4px;
        font-size: 12px;
        opacity: 0.8;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .ai-bubble .message-header {
        color: #5f6368;
    }
    .user-bubble .message-header {
        color: rgba(255,255,255,0.9);
    }
    .ai-icon {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #1a73e8;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 10px;
    }
    .chat-container::-webkit-scrollbar {
        width: 6px;
    }
    .chat-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 3px;
    }
    .chat-container::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 3px;
    }
    .chat-container::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 채팅 메시지들
    chat_html = '<div class="chat-container">'
    
    # 중복 제거를 위한 처리
    seen_messages = set()
    
    for message in st.session_state.chat_history:
        # 메시지 내용을 기반으로 한 고유 키 생성
        message_key = f"{message['role']}_{message['content']}_{message.get('timestamp', '')}"
        
        if message_key in seen_messages:
            continue  # 중복 메시지 건너뛰기
        seen_messages.add(message_key)
        
        if message["role"] == "user":
            # 사용자 메시지 - 말풍선 형태로 표시
            user_content = str(message['content']).strip()
            # HTML 태그 제거 및 특수문자 처리
            import re
            user_content = re.sub(r'<[^>]+>', '', user_content)  # HTML 태그 제거
            user_content = user_content.replace('&lt;', '<').replace('&gt;', '>')  # 이스케이프된 문자 복원
            user_content = user_content.replace('&amp;', '&')  # & 복원
            
            chat_html += f"""
            <div class="user-message">
                <div class="message-bubble user-bubble">
                    {user_content}
                </div>
            </div>
            """
        elif message["role"] == "assistant":
            # AI 응답 메시지 - 말풍선 형태로 표시하되 일반 텍스트로 처리
            ai_content = str(message['content']).strip()
            # HTML 태그 제거 및 특수문자 처리
            import re
            ai_content = re.sub(r'<[^>]+>', '', ai_content)  # HTML 태그 제거
            ai_content = ai_content.replace('&lt;', '<').replace('&gt;', '>')  # 이스케이프된 문자 복원
            ai_content = ai_content.replace('&amp;', '&')  # & 복원
            
            # AI 응답을 말풍선 형태로 표시하되 일반 텍스트로 처리
            chat_html += f"""
            <div class="ai-message">
                <div class="message-bubble ai-bubble">
                    <div class="message-header">
                        <span class="ai-icon">AI</span>
                        Gemini
                    </div>
                    {ai_content}
                </div>
            </div>
            """
    
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)
    
    # Gemini 스타일 입력 영역
    st.markdown("""
    <style>
    .input-container {
        margin-top: 24px;
        padding: 16px;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e8eaed;
    }
    .stTextArea textarea {
        border-radius: 12px !important;
        border: 1px solid #e8eaed !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        background: #ffffff !important;
        transition: all 0.2s ease !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    .stTextArea textarea:focus {
        border-color: #1a73e8 !important;
        box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2) !important;
        outline: none !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
        border: none !important;
        font-size: 14px !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    }
    .primary-button {
        background: #1a73e8 !important;
        color: white !important;
    }
    .primary-button:hover {
        background: #1557b0 !important;
    }
    .secondary-button {
        background: #f1f3f4 !important;
        color: #5f6368 !important;
        border: 1px solid #dadce0 !important;
    }
    .secondary-button:hover {
        background: #e8eaed !important;
        color: #202124 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    user_input = st.text_area(
        "💬 메시지를 입력하세요...",
        height=80,
        key="user_input",
        placeholder="오늘의 작업사항을 입력하거나, 현장 데이터 관련 사항 물어보세요."
    )
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("📤 전송", type="primary", use_container_width=True):
            if user_input.strip():
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
                    st.write("🔍 AI 응답 생성 완료:", ai_response[:100] + "..." if len(ai_response) > 100 else ai_response)
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
            st.session_state.chat_history = []
            st.rerun()

with col2:
    st.markdown("""
    <div class="data-metrics">
        <h3>📊 데이터 현황</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Supabase에서 데이터 가져오기
    try:
        # 일일보고 데이터
        daily_reports = supabase.table('daily_report_data').select('*').execute()
        reports_count = len(daily_reports.data) if daily_reports.data else 0
        
        # 발파 데이터
        blasting_data = supabase.table('blast_data').select('*').execute()
        blasting_count = len(blasting_data.data) if blasting_data.data else 0
        
        # 계측 데이터
        measurement_data = supabase.table('instrument_data').select('*').execute()
        measurement_count = len(measurement_data.data) if measurement_data.data else 0
        
        # 셀매핑 데이터
        cell_mappings = supabase.table('cell_mappings').select('*').execute()
        cell_count = len(cell_mappings.data) if cell_mappings.data else 0
        
        # 공사현황 데이터
        construction_status = supabase.table('construction_status').select('*').execute()
        construction_count = len(construction_status.data) if construction_status.data else 0
        
        # 장비 데이터
        equipment_data = supabase.table('equipment_data').select('*').execute()
        equipment_count = len(equipment_data.data) if equipment_data.data else 0
        
        # 인력 데이터
        personnel_data = supabase.table('personnel_data').select('*').execute()
        personnel_count = len(personnel_data.data) if personnel_data.data else 0
        
        # 작업내용 데이터
        work_content = supabase.table('work_content').select('*').execute()
        work_count = len(work_content.data) if work_content.data else 0
        
        # 모던한 메트릭 표시
        metrics_html = f"""
        <div class="data-metrics">
            <div class="metric-item">
                <span class="metric-label">📋 일일보고</span>
                <span class="metric-value">{reports_count}건</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">💥 발파데이터</span>
                <span class="metric-value">{blasting_count}건</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">📏 계측데이터</span>
                <span class="metric-value">{measurement_count}건</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">🗺️ 셀매핑</span>
                <span class="metric-value">{cell_count}건</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">🏗️ 공사현황</span>
                <span class="metric-value">{construction_count}건</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">🚜 장비데이터</span>
                <span class="metric-value">{equipment_count}건</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">👥 인력데이터</span>
                <span class="metric-value">{personnel_count}건</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">📝 작업내용</span>
                <span class="metric-value">{work_count}건</span>
            </div>
        </div>
        """
        st.markdown(metrics_html, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"데이터 로드 오류: {str(e)}")

# 하단에 추가 기능들
st.markdown("""
<div class="feature-section">
    <h3>🔧 추가 기능</h3>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**📊 데이터 분석**")
    if st.button("데이터 통계 보기", key="stats_btn"):
        show_data_statistics()

with col2:
    st.markdown("**📈 트렌드 분석**")
    if st.button("트렌드 차트", key="trend_btn"):
        show_trend_analysis()

with col3:
    st.markdown("**⚠️ 이상치 탐지**")
    if st.button("이상치 확인", key="anomaly_btn"):
        detect_anomalies()

with col4:
    st.markdown("**📋 보고서 생성**")
    if st.button("자동 보고서", key="report_btn"):
        generate_report()

# 페이지 하단에 도움말
st.markdown("""
<div class="help-section">
    <h3>💡 사용법</h3>
</div>
""", unsafe_allow_html=True)

with st.expander("💡 사용법"):
    st.markdown("""
    ### 챗봇 사용법
    
    1. **일일보고 관련 질문**
       - "오늘 일일보고 현황 알려줘"
       - "최근 작업보고 보여줘"
       - "어제 작업내용은 뭐였어?"
    
    2. **발파 관련 질문**
       - "발파 현황 알려줘"
       - "최근 폭파 데이터 보여줘"
       - "이번 주 발파 횟수는?"
    
    3. **계측 관련 질문**
       - "계측 데이터 현황"
       - "측정값 트렌드 보여줘"
       - "진동 측정값 어때?"
    
    4. **공사현황 관련 질문**
       - "공사 진도율 현황"
       - "현재 공사 진행상황"
       - "완료 예정일은 언제야?"
    
    5. **장비 관련 질문**
       - "장비 현황 알려줘"
       - "장비 가동률은?"
       - "유지보수 일정은?"
    
    6. **인력 관련 질문**
       - "현재 작업 인원 현황"
       - "인력 배치 상황"
       - "안전관리 현황"
    
    7. **셀매핑 관련 질문**
       - "구역별 작업현황"
       - "셀별 진도율"
       - "작업구역 현황"
    
    8. **작업내용 관련 질문**
       - "현재 작업내용"
       - "작업 일정"
       - "작업 우선순위"
    
    ### 특징
    - **Gemini 2.5 Flash** 모델 사용으로 더 정확한 답변
    - 실시간 Supabase 데이터 기반 응답 (10개 테이블)
    - 자연스러운 한국어 대화
    - 이모지와 함께 친근한 톤
    
    ### 팁
    - 구체적인 질문을 하시면 더 정확한 답변을 받을 수 있습니다.
    - 데이터가 없는 경우 안내 메시지를 제공합니다.
    - 추가 질문을 통해 더 자세한 정보를 얻을 수 있습니다.
    """) 