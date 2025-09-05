import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date
import calendar

# 페이지 설정
st.set_page_config(
    page_title="AI 공사관리 에이전트",
    page_icon="✨",
    layout="wide"
)   

# 프라이머리 버튼 CSS 스타일 추가 (강화된 버전)
st.markdown("""
<style>
    /* PRIMARY 버튼 모던한 색상 스타일 - 강화된 선택자 */
    div[data-testid="stButton"] > button[kind="primary"],
    .stButton > button[kind="primary"],
    button[kind="primary"] {
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
    
    div[data-testid="stButton"] > button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:hover,
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
    }
    
    div[data-testid="stButton"] > button[kind="primary"]:active,
    .stButton > button[kind="primary"]:active,
    button[kind="primary"]:active {
        transform: translateY(0) !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }
    
    /* 추가 강제 스타일 적용 */
    [data-testid="stButton"] button[kind="primary"] {
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
</style>

<script>
// 프라이머리 버튼에 강제로 스타일 적용
function applyPrimaryButtonStyles() {
    const primaryButtons = document.querySelectorAll('button[kind="primary"]');
    primaryButtons.forEach(button => {
        button.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        button.style.color = 'white';
        button.style.border = 'none';
        button.style.borderRadius = '8px';
        button.style.fontWeight = '600';
        button.style.transition = 'all 0.3s ease';
        button.style.padding = '8px 16px';
        button.style.fontSize = '14px';
        button.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.3)';
        
        // 호버 이벤트 추가
        button.addEventListener('mouseenter', function() {
            this.style.background = 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)';
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 8px 25px rgba(102, 126, 234, 0.4)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.3)';
        });
    });
}

// 페이지 로드 후 실행
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyPrimaryButtonStyles);
} else {
    applyPrimaryButtonStyles();
}

// Streamlit이 요소를 다시 렌더링할 때마다 실행
const observer = new MutationObserver(applyPrimaryButtonStyles);
observer.observe(document.body, { childList: true, subtree: true });

// 주기적으로도 실행 (Streamlit의 특성상 필요할 수 있음)
setInterval(applyPrimaryButtonStyles, 1000);
</script>
""", unsafe_allow_html=True)   

# Supabase 연결 설정
@st.cache_resource
def init_supabase():
    try:
        # secrets.toml에서 Supabase 정보 가져오기
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase 연결 정보를 가져올 수 없습니다: {str(e)}")
        st.info("secrets.toml 파일에 SUPABASE_URL과 SUPABASE_KEY가 올바르게 설정되어 있는지 확인해주세요.")
        return None

# 사용 가능한 테이블 목록 가져오기
@st.cache_data(ttl=3600)
def get_available_tables():
    try:
        supabase = init_supabase()
        
        if supabase is None:
            return []
        
        # PostgreSQL 시스템 테이블에서 사용자 테이블 목록 가져오기
        response = supabase.rpc('get_tables').execute()
        return response.data if response.data else []
    except:
        # RPC가 실패하면 직접 쿼리 시도
        try:
            response = supabase.table('information_schema.tables').select('table_name').eq('table_schema', 'public').execute()
            return [item['table_name'] for item in response.data] if response.data else []
        except:
            return []

# construction_status 데이터 가져오기
@st.cache_data(ttl=3600)  # 1시간마다 캐시 갱신
def get_construction_status():
    try:
        supabase = init_supabase()
        
        if supabase is None:
            return pd.DataFrame()
        
        # construction_status 테이블에서 데이터 가져오기
        response = supabase.table('construction_status').select('*').execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # 날짜 컬럼을 datetime으로 변환
            if '날짜' in df.columns:
                df['날짜'] = pd.to_datetime(df['날짜'])
            elif 'date' in df.columns:
                df['날짜'] = pd.to_datetime(df['date'])
            elif 'created_at' in df.columns:
                df['날짜'] = pd.to_datetime(df['created_at'])
            
            # 위치 컬럼 확인 및 매핑
            if '위치' not in df.columns:
                # 구분 컬럼을 위치로 매핑
                if '구분' in df.columns:
                    df['위치'] = df['구분']
                else:
                    # 위치 관련 컬럼 찾기
                    location_cols = [col for col in df.columns if '위치' in col or 'location' in col.lower() or 'name' in col.lower()]
                    if location_cols:
                        df['위치'] = df[location_cols[0]]
                    else:
                        df['위치'] = df.iloc[:, 0]
            
            # 진행률 컬럼 확인 및 매핑
            if '진행률' not in df.columns:
                # 누계 컬럼을 진행률로 매핑
                if '누계' in df.columns:
                    # 누계 값을 숫자로 변환
                    df['진행률'] = pd.to_numeric(df['누계'], errors='coerce').fillna(0)
                else:
                    # 진행률 관련 컬럼 찾기
                    progress_cols = [col for col in df.columns if '진행률' in col or 'progress' in col.lower() or 'rate' in col.lower() or 'percent' in col.lower()]
                    if progress_cols:
                        df['진행률'] = df[progress_cols[0]]
                    else:
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        if len(numeric_cols) > 0:
                            df['진행률'] = df[numeric_cols[0]]
                        else:
                            df['진행률'] = 0
            
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# 고정된 건설 항목으로 월간 테이블 생성
def create_monthly_table_from_supabase(supabase_df):
    # 고정된 건설 항목 목록 (35개)
    construction_items = [
        "1. 본선터널 (1구간, 대림-신풍) 굴착",
        "1. 본선터널 (1구간, 대림-신풍) 라이닝",
        "2. 신풍정거장 - 1)정거장 라이닝",
        "2. 신풍정거장 - 1)정거장 미들 슬라브",
        "2. 신풍정거장 - 2)주출입구 수직구 라이닝",
        "2. 신풍정거장 - 2)주출입구 - (1)PCB 정거장 방면 라이닝",
        "2. 신풍정거장 - 2)주출입구 - (1)PCB 환승통로 방면 라이닝",
        "2. 신풍정거장 - 2)주출입구 - (2)PCC 라이닝",
        "2. 신풍정거장 - 2)주출입구 - (3)PCD 라이닝",
        "2. 신풍정거장 - 2)주출입구 - (4)PHA 라이닝",
        "2. 신풍정거장 - 3)특별피난계단 - 수직구 라이닝",
        "2. 신풍정거장 - 3)특별피난계단 - PHB 라이닝",
        "2. 신풍정거장 - 4)외부출입구 출입구(#3) 굴착",
        "2. 신풍정거장 - 4)외부출입구 출입구(#2) 굴착",
        "2. 신풍정거장 - 4)외부출입구 출입구(#1) 굴착",
        "3. 신풍 환승통로 - 1)환승터널 연결터널(PCF) 굴착",
        "3. 신풍 환승통로 - 1)환승터널 연결터널(PCF) 라이닝",
        "3. 신풍 환승통로 - 1)환승터널 연결터널(PCE) 굴착",
        "3. 신풍 환승통로 - 1)환승터널 연결터널(PCE) 라이닝",
        "3. 신풍 환승통로 - 2)개착 BOX 보라매 방면 구조물",
        "3. 신풍 환승통로 - 2)개착 BOX 대림 방면 굴착",
        "4. 본선터널(2구간, 신풍-도림) 굴착",
        "4. 본선터널(2구간, 신풍-도림) 라이닝",
        "5. 도림사거리정거장 - 1)정거장 터널 라이닝",
        "5. 도림사거리정거장 - 1)정거장 미들 슬라브",
        "5. 도림사거리정거장 - 2)출입구#1 수직구 라이닝",
        "5. 도림사거리정거장 - 2)출입구#1 PCA 라이닝",
        "5. 도림사거리정거장 - 2)출입구#1 PCC 라이닝",
        "5. 도림사거리정거장 - 2)출입구#1 PHA 라이닝",
        "5. 도림사거리정거장 - 3)출입구#2 수직구 라이닝",
        "5. 도림사거리정거장 - 3)출입구#2 PCA 라이닝",
        "5. 도림사거리정거장 - 3)출입구#2 PCC 라이닝",
        "5. 도림사거리정거장 - 3)출입구#2 PHB 라이닝"
    ]
    
    # 기본 테이블 구조 생성 (고정된 35개 항목)
    base_data = []
    for item in construction_items:
        # Supabase에서 저장된 설계량 불러오기
        saved_design = 1000  # 기본값
        
        # 먼저 Supabase에서 불러오기 시도
        if 'supabase_design_values' not in st.session_state:
            st.session_state.supabase_design_values = load_design_values_from_supabase()
        
        if item in st.session_state.supabase_design_values:
            saved_design = st.session_state.supabase_design_values[item]
        # session_state에도 있으면 우선 적용 (최신 편집 내용)
        elif 'saved_design_values' in st.session_state and item in st.session_state.saved_design_values:
            saved_design = st.session_state.saved_design_values[item]
        
        row_data = {
            '위치': item,
            '설계': float(saved_design),     # 저장된 설계값 또는 기본값 (float로 명시)
            '누계': 0.0,        # 고정열 (실제 데이터에서 계산)
            '진도율': 0.0,      # 고정열 (누계/설계 * 100)
            '잔여': float(saved_design)      # 고정열 (설계 - 누계)
        }
        
        # 25-01부터 26-12까지의 월별 컬럼들 추가
        for year in [25, 26]:
            for month in range(1, 13):
                month_col = f"{year:02d}-{month:02d}"
                row_data[month_col] = 0
        
        # 사용자가 추가한 열들도 포함
        if 'custom_columns' in st.session_state:
            for col_name, default_value in st.session_state.custom_columns.items():
                row_data[col_name] = default_value
        
        base_data.append(row_data)
    
    return pd.DataFrame(base_data)

# 설계량 저장 함수 (Supabase 연동)
def save_design_values_to_supabase(df):
    """설계량을 Supabase에 저장하여 영구적으로 유지되도록 함"""
    try:
        st.info("🔗 Supabase 연결을 확인 중...")
        supabase = init_supabase()
        if supabase is None:
            st.error("❌ Supabase 연결이 필요합니다.")
            return False
        
        st.success("✅ Supabase 연결 성공!")
        
        # design_values 테이블이 존재하는지 확인
        st.info("🔍 design_values 테이블 존재 여부를 확인 중...")
        try:
            test_response = supabase.table('design_values').select('id').limit(1).execute()
            st.success("✅ design_values 테이블 접근 성공!")
        except Exception as e:
            st.error(f"❌ design_values 테이블에 접근할 수 없습니다: {str(e)}")
            st.info("💡 Supabase에 design_values 테이블을 생성해야 합니다.")
            return False
        
        # 설계값이 변경된 위치들만 찾기
        st.info("📊 저장할 설계값을 확인 중...")
        updated_locations = []
        for idx, row in df.iterrows():
            location = row['위치']
            design_value = row['설계']
            
            # 데이터 타입 확인 및 변환
            if pd.isna(design_value):
                st.warning(f"⚠️ {location}: 설계값이 비어있습니다.")
                continue
                
            try:
                design_value = float(design_value)
                if design_value <= 0:
                    st.warning(f"⚠️ {location}: 설계값은 0보다 커야 합니다. (현재: {design_value})")
                    continue
            except (ValueError, TypeError):
                st.error(f"❌ {location}: '{design_value}'은(는) 유효한 숫자가 아닙니다.")
                continue
            
            updated_locations.append({
                'location': location,
                'design_value': design_value,
                'updated_at': datetime.now().isoformat()
            })
        
        if not updated_locations:
            st.info("📝 저장할 설계값이 없습니다.")
            return True
        
        st.info(f"🔍 {len(updated_locations)}개 위치의 설계값을 Supabase에 저장 중...")
        
        # 처음 3개 데이터 미리보기
        st.write("**📋 저장할 데이터 샘플:**")
        sample_data = pd.DataFrame(updated_locations[:3])
        st.dataframe(sample_data, use_container_width=True)
        
        # design_values 테이블에 upsert (있으면 업데이트, 없으면 삽입)
        success_count = 0
        error_count = 0
        
        for i, item in enumerate(updated_locations):
            try:
                st.info(f"💾 {i+1}/{len(updated_locations)}: {item['location']} 저장 중...")
                
                # 기존 데이터 확인
                response = supabase.table('design_values').select('*').eq('location', item['location']).execute()
                
                if response.data:
                    # 기존 데이터 업데이트
                    st.info(f"🔄 {item['location']} 기존 데이터 업데이트 중...")
                    update_response = supabase.table('design_values').update({
                        'design_value': item['design_value'],
                        'updated_at': item['updated_at']
                    }).eq('location', item['location']).execute()
                    
                    if update_response.data:
                        success_count += 1
                        st.success(f"✅ {item['location']} 업데이트 성공!")
                    else:
                        st.warning(f"⚠️ {item['location']} 업데이트 실패")
                        error_count += 1
                else:
                    # 새 데이터 삽입
                    st.info(f"➕ {item['location']} 새 데이터 삽입 중...")
                    insert_response = supabase.table('design_values').insert({
                        'location': item['location'],
                        'design_value': item['design_value'],
                        'created_at': item['updated_at'],
                        'updated_at': item['updated_at']
                    }).execute()
                    
                    if insert_response.data:
                        success_count += 1
                        st.success(f"✅ {item['location']} 삽입 성공!")
                    else:
                        st.warning(f"⚠️ {item['location']} 삽입 실패")
                        error_count += 1
                
            except Exception as e:
                st.error(f"❌ {item['location']} 설계값 저장 실패: {str(e)}")
                error_count += 1
        
        # 최종 결과 요약
        st.info(f"📊 저장 결과 요약:")
        st.info(f"✅ 성공: {success_count}개")
        st.info(f"❌ 실패: {error_count}개")
        
        if success_count > 0:
            st.success(f"✅ {success_count}개 위치의 설계값이 Supabase에 저장되었습니다!")
            return True
        else:
            st.error("❌ 모든 설계값 저장에 실패했습니다.")
            return False
        
    except Exception as e:
        st.error(f"❌ Supabase 저장 중 오류 발생: {str(e)}")
        st.info("💡 Supabase 연결 상태와 design_values 테이블을 확인해주세요.")
        return False

# 설계량 불러오기 함수 (Supabase에서)
def load_design_values_from_supabase():
    """Supabase에서 저장된 설계값을 불러오기"""
    try:
        supabase = init_supabase()
        if supabase is None:
            return {}
        
        # design_values 테이블에서 모든 설계값 가져오기
        response = supabase.table('design_values').select('*').execute()
        
        if response.data:
            design_values = {}
            for item in response.data:
                design_values[item['location']] = item['design_value']
            return design_values
        else:
            return {}
            
    except Exception as e:
        st.warning(f"⚠️ Supabase에서 설계값을 불러올 수 없습니다: {str(e)}")
        return {}

# 진도율에 따른 스타일 HTML 생성 함수 (이미지와 동일)
def get_styled_progress_html(progress_rate):
    """진도율에 따라 이미지와 동일한 스타일의 HTML을 생성"""
    if pd.isna(progress_rate):
        progress_rate = 0
    
    # 소숫점 2자리까지 표시
    formatted_value = f"{progress_rate:.2f}%"
    
    # 배경색 결정
    if progress_rate == 0:
        bg_color = "#FFFFFF"  # 흰색 (0%)
    else:
        bg_color = "#E0F7FA"  # 연한 파란색 (0% 초과)
    
    # 텍스트 색상 결정
    if progress_rate == 100:
        text_color = "#FF0000"  # 빨간색 (100%)
    else:
        text_color = "#000000"  # 검은색 (기타)
    
    # HTML 생성
    html = f'<div style="background-color: {bg_color}; color: {text_color}; padding: 4px 8px; text-align: right; border-radius: 2px; font-family: monospace;">{formatted_value}</div>'
    return html

# 파생 컬럼 재계산 함수
def recalculate_derived_columns(df):
    """설계값이 변경된 경우 누계, 진도율, 잔여를 재계산"""
    for idx, row in df.iterrows():
        design_value = row['설계']
        if pd.notna(design_value) and design_value > 0:
            # 25년 7월까지의 누계 계산
            total_cumulative = 0
            for year in [25]:
                for month in range(1, 8):
                    month_col = f"{year:02d}-{month:02d}"
                    if month_col in df.columns:
                        month_value = df.at[idx, month_col]
                        if pd.notna(month_value) and month_value > 0:
                            total_cumulative = month_value
            
            # 누계, 진도율, 잔여 업데이트
            df.at[idx, '누계'] = round(total_cumulative, 1)
            df.at[idx, '진도율'] = round((total_cumulative / design_value) * 100, 2)
            df.at[idx, '잔여'] = round(design_value - total_cumulative, 1)
    
    return df

# 설계량 저장 함수 (session_state용 - 임시)
def save_design_values(df):
    """설계량을 session_state에 저장하여 다음 실행 시에도 유지되도록 함"""
    if 'saved_design_values' not in st.session_state:
        st.session_state.saved_design_values = {}
    
    for idx, row in df.iterrows():
        location = row['위치']
        design_value = row['설계']
        if pd.notna(design_value) and design_value > 0:
            st.session_state.saved_design_values[location] = design_value



# 월간 누계 계산 (Supabase 데이터 직접 처리)
def calculate_monthly_cumulative(supabase_df):
    if supabase_df.empty:
        return pd.DataFrame()
    
    # Supabase 데이터로부터 기본 테이블 생성
    result_df = create_monthly_table_from_supabase(supabase_df)
    
    # 25년과 26년의 월별 데이터 처리 - 각 월의 최종 날짜 데이터만 사용
    for year in [25, 26]:
        for month in range(1, 13):
            month_col = f"{year:02d}-{month:02d}"
            
            # 해당 월의 데이터만 필터링
            month_data = supabase_df[
                (supabase_df['날짜'].dt.year == (2000 + year)) & 
                (supabase_df['날짜'].dt.month == month)
            ]
            
            if not month_data.empty:
                # 각 위치별로 해당 월의 최신 데이터(최종 누계값) 가져오기
                for idx, row in result_df.iterrows():
                    location = row['위치']
                    
                    # 해당 위치의 데이터 찾기
                    location_data = month_data[month_data['위치'] == location]
                        
                    if not location_data.empty:
                        # 해당 월의 최신 데이터(최종 누계값) 사용
                        latest_data = location_data.sort_values('날짜', ascending=False).iloc[0]
                        cumulative = latest_data['진행률'] if '진행률' in latest_data else 0
                        result_df.at[idx, month_col] = cumulative
                    else:
                        result_df.at[idx, month_col] = 0
            else:
                # 해당 월에 데이터가 없으면 0으로 설정
                for idx in result_df.index:
                    result_df.at[idx, month_col] = 0
    
    # 누계, 진도율, 잔여 자동 계산
    for idx, row in result_df.iterrows():
        # 설계값 설정
        design_value = row['설계']
        
        # 25년 7월까지의 누계 계산 (실제 데이터 기반)
        total_cumulative = 0
        for year in [25]:
            for month in range(1, 8):  # 1월부터 7월까지
                month_col = f"{year:02d}-{month:02d}"
                if month_col in result_df.columns:
                    month_value = result_df.at[idx, month_col]
                    if pd.notna(month_value) and month_value > 0:
                        total_cumulative = month_value  # 해당 월의 누계값 사용
        
        result_df.at[idx, '누계'] = total_cumulative
        
        # 진도율 계산 (누계/설계 * 100)
        if design_value > 0:
            progress_rate = (total_cumulative / design_value) * 100
            result_df.at[idx, '진도율'] = round(progress_rate, 2)
        else:
            result_df.at[idx, '진도율'] = 0
        
        # 잔여 계산 (설계 - 누계)
        result_df.at[idx, '잔여'] = round(design_value - total_cumulative, 1)
    
    return result_df

# AgGrid 설정 함수
def configure_aggrid(df, title, height=400, is_base_table=False):
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # 기본 설정
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sortable=True,
        editable=True  # 기본적으로 편집 가능하게 설정
    )
    
    # 고정열 설정 (편집 불가)
    fixed_columns = ["위치", "전체", "누계", "진도율", "잔여"]
    
    # 위치 컬럼 설정 (넓게, 편집 불가)
    gb.configure_column("위치", width=350, pinned="left", editable=False)
    
    # 설계 컬럼 설정 (편집 가능)
    gb.configure_column("설계", width=150, pinned="left", editable=True, 
                       type=['numericColumn', 'numberColumnFilter'])
    
    # 사용자 정의 열들 설정 (편집 가능)
    if 'custom_columns' in st.session_state:
        for col_name in st.session_state.custom_columns.keys():
            gb.configure_column(col_name, 
                               width=150,
                               type=['textColumn', 'textColumnFilter'],
                               editable=True)
    
    # 고정열들 설정 (편집 가능)
    for col in fixed_columns:
        if col in df.columns:
            if col == "위치":
                continue  # 이미 설정됨
            elif col == "전체":
                gb.configure_column(col, width=150, editable=True, type=['numericColumn', 'numberColumnFilter'])
            elif col == "누계":
                gb.configure_column(col, width=150, editable=True, type=['numericColumn', 'numberColumnFilter'])
            elif col == "진도율":
                gb.configure_column(col, width=150, editable=True, type=['numericColumn', 'numberColumnFilter'])
            elif col == "잔여":
                gb.configure_column(col, width=150, editable=True, type=['numericColumn', 'numberColumnFilter'])
    
    # 월별 컬럼들 설정 (25-01부터 26-12까지, 편집 가능)
    for year in [25, 26]:
        for month in range(1, 13):
            month_col = f"{year:02d}-{month:02d}"
            if month_col in df.columns:
                gb.configure_column(month_col, 
                                   header_name=f"{year:02d}-{month:02d}",
                                   width=150,
                                   type=['numericColumn', 'numberColumnFilter'],
                                   valueFormatter="value.toFixed(2)",
                                   editable=True)
    
    # 기본 테이블이 아닌 경우 (월간 누계 테이블) 편집 가능한 컬럼들 설정
    if not is_base_table:
        # 설계 컬럼 편집 가능
        gb.configure_column("설계", 
                                   width=150,
                           pinned="left", 
                           editable=True, 
                                   type=['numericColumn', 'numberColumnFilter'],
                           cellEditor='agNumberCellEditor')  # 숫자 편집기 사용
        
        # 전체, 누계, 진도율, 잔여 컬럼 편집 가능
        for col in ["전체", "누계", "진도율", "잔여"]:
            if col in df.columns:
                gb.configure_column(col, 
                                   width=150,
                                   type=['numericColumn', 'numberColumnFilter'],
                                   valueFormatter="value.toFixed(2)",
                                   editable=True,
                                   cellEditor='agNumberCellEditor')  # 숫자 편집기 사용
        
        # 월별 컬럼들도 편집 가능하게 설정
        for year in [25, 26]:
            for month in range(1, 13):
                month_col = f"{year:02d}-{month:02d}"
                if month_col in df.columns:
                    gb.configure_column(month_col, 
                                       header_name=f"{year:02d}-{month:02d}",
                                   width=150,
                                   type=['numericColumn', 'numberColumnFilter'],
                                   valueFormatter="value.toFixed(2)",
                                       editable=True,
                                       cellEditor='agNumberCellEditor')  # 숫자 편집기 사용
    else:
        # 기본 테이블인 경우 모든 컬럼 편집 불가
        for col in df.columns:
            if col not in ["위치"]:
                gb.configure_column(col, editable=False)
    
    # 그리드 옵션 설정
    gb.configure_grid_options(
        domLayout='normal',
        rowHeight=35,
        headerHeight=50,
        suppressRowClickSelection=False,  # 행 클릭 선택 허용
        enableRangeSelection=True,
        rowSelection='multiple',
        suppressHorizontalScroll=False,  # 가로 스크롤 활성화
        suppressColumnVirtualisation=False,  # 열 가상화 비활성화하여 모든 열이 렌더링되도록 함
        # 편집 기능 활성화
        enableCellEditing=True,  # 셀 편집 활성화
        # 드래그 복사 기능을 위한 추가 설정
        allowRangeSelection=True,
        enableRangeHandle=True,
        enableFillHandle=True,
        suppressCopyRowsToClipboard=False,
        suppressCopySingleCellRanges=False,
        suppressPasteSingleCellRanges=False,
        suppressPasteMultipleCellRanges=False,
        # 클립보드 복사 설정
        clipboardDelimiter='\t',  # 탭으로 구분하여 Excel 호환성 향상
        # 드래그 선택 시 시각적 피드백
        enableCellTextSelection=True,
        suppressRowDeselection=False
    )
    
    # 페이지네이션 설정
    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=20
    )
    
    # 도구 모음 설정
    gb.configure_side_bar()
    
    grid_options = gb.build()
    
    # AgGrid 렌더링
    grid_response = AgGrid(
        df,
        grid_options=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,  # 값 변경 감지
        fit_columns_on_grid_load=False,  # 모든 열이 완전히 보이도록 설정
        height=height,
        allow_unsafe_jscode=True,
        theme="streamlit",
        # 드래그 복사 기능을 위한 JavaScript 코드
        js_code=JsCode("""
            // 그리드 준비 완료 시 실행되는 함수
            function onGridReady(params) {
                console.log('Grid is ready');
                
                // 편집 기능 강제 활성화
                params.api.setGridOption('enableCellEditing', true);
                
                // 모든 컬럼을 편집 가능하게 설정
                var columns = params.api.getColumns();
                columns.forEach(function(col) {
                    if (col.colId !== '위치') {  // 위치 컬럼 제외
                        col.editable = true;
                        col.cellEditor = 'agNumberCellEditor';
                    }
                });
                params.api.setColumns(columns);
                
                // 셀 편집 이벤트 리스너
                params.api.addEventListener('cellEditingStarted', function(event) {
                    console.log('Cell editing started:', event);
                });
                
                params.api.addEventListener('cellEditingStopped', function(event) {
                    console.log('Cell editing stopped:', event);
                });
                
                // 더블클릭 편집 활성화
                params.api.addEventListener('cellDoubleClicked', function(event) {
                    console.log('Cell double clicked:', event);
                    if (event.colDef.colId !== '위치') {
                        event.api.startEditingCell({
                            rowIndex: event.rowIndex,
                            colKey: event.colDef.colId
                        });
                    }
                });
                
                // 범위 선택 이벤트 리스너
                params.api.addEventListener('rangeSelectionChanged', function(event) {
                    console.log('Range selection changed:', event);
                });
                
                // 키보드 이벤트 리스너 (Ctrl+C)
                params.api.addEventListener('keydown', function(event) {
                    if (event.ctrlKey && event.key === 'c') {
                        console.log('Ctrl+C pressed');
                        copySelectedRanges(params.api);
                    }
                });
                
                // 마우스 이벤트 리스너 (드래그 복사)
                params.api.addEventListener('mouseup', function(event) {
                    console.log('Mouse up event:', event);
                });
            }
            
            // 선택된 범위를 클립보드에 복사하는 함수
            function copySelectedRanges(api) {
                try {
                    var selectedRanges = api.getCellRanges();
                    console.log('Selected ranges:', selectedRanges);
                    
                    if (selectedRanges && selectedRanges.length > 0) {
                        var data = [];
                        
                        selectedRanges.forEach(function(range) {
                            var rowData = [];
                            
                            for (var rowIndex = range.startRow.rowIndex; rowIndex <= range.endRow.rowIndex; rowIndex++) {
                                for (var colIndex = range.startColumn.colIndex; colIndex <= range.endColumn.colIndex; colIndex++) {
                                    var value = api.getValue(range.startColumn.colId, rowIndex);
                                    rowData.push(value || '');
                                }
                                data.push(rowData.join('\\t'));
                            }
                        });
                        
                        var text = data.join('\\n');
                        console.log('Data to copy:', text);
                        
                        // 클립보드에 복사
                        navigator.clipboard.writeText(text).then(function() {
                            console.log('Data copied to clipboard successfully');
                        }).catch(function(err) {
                            console.error('Failed to copy to clipboard:', err);
                            // 대체 방법: 임시 textarea 사용
                            fallbackCopyTextToClipboard(text);
                        });
                    }
                } catch (error) {
                    console.error('Error copying data:', error);
                }
            }
            
            // 클립보드 복사 대체 방법
            function fallbackCopyTextToClipboard(text) {
                var textArea = document.createElement("textarea");
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                try {
                    var successful = document.execCommand('copy');
                    if (successful) {
                        console.log('Data copied using fallback method');
                    }
                } catch (err) {
                    console.error('Fallback copy failed:', err);
                }
                
                document.body.removeChild(textArea);
            }
            
            // 그리드 준비 완료 시 이벤트 리스너 등록
            if (typeof onGridReady === 'function') {
                onGridReady(params);
            }
        """)
    )
    
    return grid_response

# 메인 페이지
st.title("📊 월간 공정실적")
st.markdown("---")







# Supabase에서 데이터 가져오기
with st.spinner("construction_status 테이블에서 데이터를 가져오는 중..."):
    supabase_df = get_construction_status()

if supabase_df.empty:
    st.warning("⚠️ construction_status 테이블에서 데이터를 가져올 수 없습니다.")
    st.info("""
    **가능한 원인:**
    1. Supabase 연결 문제
    2. construction_status 테이블이 존재하지 않음
    3. 테이블에 데이터가 없음
    4. 접근 권한 문제
    
    **해결 방법:**
    1. 위의 'Supabase 연결 테스트' 버튼을 클릭하여 연결 상태 확인
    2. 'construction_status 테이블 구조 확인' 버튼으로 테이블 존재 여부 확인
    3. '테이블 데이터 미리보기'에서 다른 테이블 확인
    """)
else:

    
    # 월간 누계 계산 (Supabase 데이터 직접 처리)
    try:
        # st.session_state에 'monthly_df'가 없으면 최초 실행으로 간주하고 데이터를 계산하여 저장
        if 'monthly_df' not in st.session_state:
            st.session_state.monthly_df = calculate_monthly_cumulative(supabase_df)
        
        # 설계량 편집 및 일괄 적용 로직은 st.session_state.monthly_df를 사용
        monthly_df = st.session_state.monthly_df
        
        if not monthly_df.empty:

            

            

            

            

            
            # 컬럼명 정리 (고정열 포함) - 진도율_표시는 나중에 생성
            display_columns = ['위치', '설계', '누계', '진도율', '잔여']
            
            # 사용자 정의 열들 추가
            if 'custom_columns' in st.session_state:
                display_columns.extend(list(st.session_state.custom_columns.keys()))
            
            # 25-01부터 26-12까지의 월별 컬럼들 추가 (고정열)
            for year in [25, 26]:
                for month in range(1, 13):
                    month_col = f"{year:02d}-{month:02d}"
                    display_columns.append(month_col)
            
            # 존재하는 컬럼만 필터링
            available_columns = [col for col in display_columns if col in st.session_state.monthly_df.columns]
            missing_columns = [col for col in display_columns if col not in st.session_state.monthly_df.columns]
            
            if missing_columns:
                st.warning(f"⚠️ 일부 컬럼이 누락되었습니다: {missing_columns}")
            
            # 월간 누계 데이터를 기본 Streamlit 테이블로 표시
            monthly_display_df = st.session_state.monthly_df[available_columns].copy()
            
            # 숫자 컬럼들을 float로 변환
            for col in monthly_display_df.columns:
                if col not in ['위치', '설계']:
                    monthly_display_df[col] = pd.to_numeric(monthly_display_df[col], errors='coerce').fillna(0)
            

            
            # 진도율 셀에 색상을 적용하기 위한 CSS 추가
            st.markdown("""
            <style>
            /* 진도율 셀 색상 스타일 */
            [data-testid="stDataFrame"] .stDataFrame td[data-col="진도율"] {
                background-color: var(--progress-bg-color) !important;
                color: var(--progress-text-color) !important;
                font-weight: bold !important;
                text-align: right !important;
                font-family: monospace !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # 기본 Streamlit 테이블로 표시 (편집 가능)
            # 모든 컬럼에 대한 설정 생성
            column_config = {
                "위치": st.column_config.TextColumn("위치", width="large", disabled=True)
            }
            
            # 고정 컬럼들 설정 (위치 제외한 모든 컬럼을 동일한 너비로)
            for col in monthly_display_df.columns:
                if col != "위치":
                    if col in ["설계", "전체", "누계", "잔여"]:
                        column_config[col] = st.column_config.NumberColumn(col, width="small", format="%.1f", min_value=0, step=0.1)
                    elif col == "진도율":
                        column_config[col] = st.column_config.NumberColumn(
                            col, 
                            width="small", 
                            format="%.2f", 
                            min_value=0, 
                            max_value=100, 
                            step=0.01,
                            help="진도율 (0%: 흰색, 0%초과: 연한파란색, 100%: 빨간색텍스트)"
                        )
                    else:
                        # 월별 컬럼들 (25-01부터 26-12까지)
                        column_config[col] = st.column_config.NumberColumn(col, width="small", format="%.1f", min_value=0, step=0.1)
            
            edited_df = st.data_editor(
                monthly_display_df,
                use_container_width=True,
                height=800,
                column_config=column_config,
                num_rows="dynamic",
                key="monthly_table_editor",
                hide_index=True  # 행 인덱스 숨김
            )
            
            # 진도율 셀에 색상을 동적으로 적용하는 JavaScript (강화된 버전)
            st.markdown("""
            <script>
            // 진도율 셀에 색상을 적용하는 함수
            function applyProgressColors() {
                // 모든 가능한 테이블 선택자 시도
                const selectors = [
                    '[data-testid="stDataFrame"]',
                    '.stDataFrame',
                    'table',
                    '[data-testid="stDataEditor"]'
                ];
                
                let table = null;
                for (const selector of selectors) {
                    table = document.querySelector(selector);
                    if (table) break;
                }
                
                if (table) {
                    console.log('테이블을 찾았습니다:', table);
                    
                    // 모든 행 찾기 (헤더 제외)
                    const rows = table.querySelectorAll('tbody tr, tr:not(:first-child)');
                    console.log('찾은 행 수:', rows.length);
                    
                    rows.forEach((row, rowIndex) => {
                        const cells = row.querySelectorAll('td');
                        console.log(`행 ${rowIndex + 1}의 셀 수:`, cells.length);
                        
                        cells.forEach((cell, cellIndex) => {
                            // 진도율 컬럼 찾기 (위치, 설계, 누계 다음)
                            if (cellIndex === 3) { // 진도율 컬럼 인덱스
                                const cellText = cell.textContent || cell.innerText;
                                console.log(`진도율 셀 ${rowIndex + 1}:`, cellText);
                                
                                const value = parseFloat(cellText.replace(/[^\d.-]/g, ''));
                                if (!isNaN(value)) {
                                    console.log(`파싱된 값:`, value);
                                    
                                    let bgColor, textColor;
                                    
                                    if (value === 0) {
                                        bgColor = '#FFFFFF'; // 흰색
                                        textColor = '#000000'; // 검은색
                                    } else if (value >= 100) {
                                        bgColor = '#E0F7FA'; // 연한 파란색
                                        textColor = '#FF0000'; // 빨간색
                                    } else {
                                        bgColor = '#E0F7FA'; // 연한 파란색
                                        textColor = '#000000'; // 검은색
                                    }
                                    
                                    // 스타일 직접 적용
                                    cell.style.setProperty('background-color', bgColor, 'important');
                                    cell.style.setProperty('color', textColor, 'important');
                                    cell.style.setProperty('font-weight', 'bold', 'important');
                                    cell.style.setProperty('text-align', 'right', 'important');
                                    cell.style.setProperty('font-family', 'monospace', 'important');
                                    
                                    console.log(`색상 적용 완료: 배경=${bgColor}, 텍스트=${textColor}`);
                                }
                            }
                        });
                    });
                } else {
                    console.log('테이블을 찾을 수 없습니다');
                }
            }
            
            // 여러 방법으로 실행 시도
            function tryApplyColors() {
                // 즉시 실행
                applyProgressColors();
                
                // 약간의 지연 후 다시 실행
                setTimeout(applyProgressColors, 100);
                setTimeout(applyProgressColors, 500);
                setTimeout(applyProgressColors, 1000);
            }
            
            // 페이지 로드 후 실행
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', tryApplyColors);
            } else {
                tryApplyColors();
            }
            
            // Streamlit이 테이블을 다시 렌더링할 때마다 실행
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        setTimeout(applyProgressColors, 100);
                    }
                });
            });
            
            observer.observe(document.body, { 
                childList: true, 
                subtree: true 
            });
            
            // 주기적으로 색상 적용 (Streamlit의 특성상 필요할 수 있음)
            setInterval(applyProgressColors, 2000);
            </script>
            """, unsafe_allow_html=True)
            
            # 테이블 하단에 엑셀 다운로드와 설계량 편집 배치
            st.markdown("---")
            
            # 엑셀 다운로드와 설계량 편집을 화면의 반씩 너비로 배치
            col1, col2 = st.columns(2)
            
            with col1:
                # 엑셀 다운로드 버튼
                try:
                    # pandas DataFrame을 엑셀 형식으로 변환
                    import io
                    buffer = io.BytesIO()
                    
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        st.session_state.monthly_df.to_excel(writer, sheet_name='월간누계', index=False)
                    
                    buffer.seek(0)
                    excel_data = buffer.getvalue()
                    
                    st.download_button(
                        label="📥 엑셀 다운로드",
                        data=excel_data,
                        file_name=f"시공현황_월간누계_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                except ImportError:
                    st.error("❌ openpyxl 패키지가 설치되지 않았습니다.")
                    st.info("💡 터미널에서 다음 명령어를 실행하세요: `pip install openpyxl`")
                    
                    # fallback: CSV 다운로드
                    csv = st.session_state.monthly_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 CSV 다운로드 (fallback)",
                        data=csv,
                        file_name=f"시공현황_월간누계_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        type="secondary"
                    )
            
            with col2:
                # 설계량 편집 expander (간소화)
                with st.expander("⚙️ 설계량 편집", expanded=False):
                    # 직접 편집 테이블
                    edit_df = st.session_state.monthly_df[['위치', '설계']].copy()
                    edited_design_df = st.data_editor(
                        edit_df,
                        use_container_width=True,
                        height=400,
                        column_config={
                            "위치": st.column_config.TextColumn("위치", width="large", disabled=True),
                            "설계": st.column_config.NumberColumn("설계", width="medium", format="%.1f", min_value=0, step=0.1)
                        },
                        key="design_editor_table_bottom"
                    )
                    
                    # 설계량이 변경되었는지 확인
                    design_changed = not edited_design_df.equals(edit_df)
                    
                    if design_changed:
                        if st.button("💾 설계량 저장하기", key="save_design_button_bottom", type="primary", use_container_width=True):
                            updated_count = 0
                            for idx, row in edited_design_df.iterrows():
                                location = row['위치']
                                new_design = row['설계']
                                
                                if pd.isna(new_design):
                                    continue
                                
                                try:
                                    new_design = float(new_design)
                                    if new_design < 0:
                                        continue
                                except (ValueError, TypeError):
                                    continue
                                
                                st.session_state.monthly_df.loc[st.session_state.monthly_df['위치'] == location, '설계'] = new_design
                                updated_count += 1
                            
                            if updated_count > 0:
                                st.session_state.monthly_df = recalculate_derived_columns(st.session_state.monthly_df)
                                
                                if save_design_values_to_supabase(st.session_state.monthly_df):
                                    st.success("💾 설계량이 Supabase에 저장되었습니다!")
                                    st.session_state.supabase_design_values = load_design_values_from_supabase()
                                    st.rerun()
                                else:
                                    st.warning("⚠️ Supabase 저장에 실패했습니다.")
                                    save_design_values(st.session_state.monthly_df)
                    else:
                        st.info("📝 설계량을 수정한 후 '저장하기' 버튼을 눌러주세요.")
            
            # 편집된 데이터가 있는지 확인하고 자동 저장
            if not edited_df.equals(monthly_display_df):
                st.success("✅ 테이블 데이터가 편집되었습니다!")
                
                # 편집된 데이터를 session_state에 반영
                st.session_state.monthly_df = edited_df.copy()
                
                # 설계량이 변경된 경우 Supabase에 자동 저장
                design_changed = False
                for idx, (orig_row, edit_row) in enumerate(zip(monthly_display_df.iterrows(), edited_df.iterrows())):
                    if orig_row[1]['설계'] != edit_row[1]['설계']:
                        design_changed = True
                        break
                
                if design_changed:
                    st.info("🔍 설계량 변경이 감지되었습니다. Supabase에 자동 저장 중...")
                    
                    # 설계량을 Supabase에 영구 저장
                    if save_design_values_to_supabase(st.session_state.monthly_df):
                        st.success("💾 설계량이 Supabase에 자동 저장되었습니다!")
                        # Supabase에서 최신 설계값 다시 불러오기
                        st.session_state.supabase_design_values = load_design_values_from_supabase()
                    else:
                        st.warning("⚠️ Supabase 자동 저장에 실패했습니다. session_state에만 임시 저장됩니다.")
                        save_design_values(st.session_state.monthly_df)
                else:
                    st.info("📝 설계량 외의 데이터가 편집되었습니다.")
                
                # 파생 컬럼 재계산
                st.session_state.monthly_df = recalculate_derived_columns(st.session_state.monthly_df)
                
                st.info("🔄 파생 컬럼(누계, 진도율, 잔여)이 자동으로 재계산되었습니다.")
                
                # 변경사항 확인을 위한 expander
                with st.expander("📝 변경된 데이터 확인", expanded=False):
                    st.write("**편집된 행들:**")
                    for idx, (orig_row, edit_row) in enumerate(zip(monthly_display_df.iterrows(), edited_df.iterrows())):
                        if not orig_row[1].equals(edit_row[1]):
                            st.write(f"**행 {idx+1} ({orig_row[1]['위치']}):**")
                            for col in monthly_display_df.columns:
                                if col != '위치' and orig_row[1][col] != edit_row[1][col]:
                                    st.write(f"  - {col}: {orig_row[1][col]} → {edit_row[1][col]}")
            

            

        else:
            st.error("❌ 월간 누계 데이터를 계산할 수 없습니다.")
    except Exception as e:
        st.error(f"❌ 월간 누계 계산 중 오류가 발생했습니다: {str(e)}")
        st.info("데이터 구조를 확인하고 다시 시도해주세요.")

