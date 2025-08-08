# Supabase 설정 가이드

## 1. 필요한 테이블 생성

다음 SQL 명령어를 Supabase SQL Editor에서 실행하세요:

```sql
-- 날씨 보고서 테이블
CREATE TABLE IF NOT EXISTS weather_reports (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    구분 TEXT NOT NULL,
    값 TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 시공 현황 테이블
CREATE TABLE IF NOT EXISTS construction_status (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    구분 TEXT NOT NULL,
    누계 TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 작업 내용 테이블
CREATE TABLE IF NOT EXISTS work_content (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    구분 TEXT NOT NULL,
    금일작업 TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인원 데이터 테이블
CREATE TABLE IF NOT EXISTS personnel_data (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    구분 TEXT NOT NULL,
    section_1 INTEGER DEFAULT 0,
    section_2_1 INTEGER DEFAULT 0,
    section_2_2_1 INTEGER DEFAULT 0,
    section_2_2_2 INTEGER DEFAULT 0,
    section_2_2_3 INTEGER DEFAULT 0,
    section_2_2_4 INTEGER DEFAULT 0,
    section_2_3 INTEGER DEFAULT 0,
    section_2_4 INTEGER DEFAULT 0,
    section_3_1 INTEGER DEFAULT 0,
    section_3_2 INTEGER DEFAULT 0,
    section_4 INTEGER DEFAULT 0,
    section_5_1 INTEGER DEFAULT 0,
    section_5_2 INTEGER DEFAULT 0,
    section_5_3 INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 장비 데이터 테이블
CREATE TABLE IF NOT EXISTS equipment_data (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    구분 TEXT NOT NULL,
    section_1 INTEGER DEFAULT 0,
    section_2_1 INTEGER DEFAULT 0,
    section_2_2_1 INTEGER DEFAULT 0,
    section_2_2_2 INTEGER DEFAULT 0,
    section_2_2_3 INTEGER DEFAULT 0,
    section_2_2_4 INTEGER DEFAULT 0,
    section_2_3 INTEGER DEFAULT 0,
    section_2_4 INTEGER DEFAULT 0,
    section_3_1 INTEGER DEFAULT 0,
    section_3_2 INTEGER DEFAULT 0,
    section_4 INTEGER DEFAULT 0,
    section_5_1 INTEGER DEFAULT 0,
    section_5_2 INTEGER DEFAULT 0,
    section_5_3 INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 발파 데이터 테이블
CREATE TABLE IF NOT EXISTS blast_data (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 계측기 데이터 테이블
CREATE TABLE IF NOT EXISTS instrument_data (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 프롬프트 관리 테이블
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS 비활성화 (개발용)
ALTER TABLE weather_reports DISABLE ROW LEVEL SECURITY;
ALTER TABLE construction_status DISABLE ROW LEVEL SECURITY;
ALTER TABLE work_content DISABLE ROW LEVEL SECURITY;
ALTER TABLE personnel_data DISABLE ROW LEVEL SECURITY;
ALTER TABLE equipment_data DISABLE ROW LEVEL SECURITY;
ALTER TABLE blast_data DISABLE ROW LEVEL SECURITY;
ALTER TABLE instrument_data DISABLE ROW LEVEL SECURITY;
ALTER TABLE prompts DISABLE ROW LEVEL SECURITY;

-- 업데이트된 기본 프롬프트 삽입/업데이트
INSERT INTO prompts (name, content, description) VALUES (
    '기본 프롬프트',
    '# INSTRUCTIONS
1. 일일작업보고 텍스트에서 **작업 날짜**를 추출하여 첫 번째로 출력 (YYYY-MM-DD 형식)
2. 기상청 서울 지역 관측 자료를 기반으로 "날씨정보" 테이블을 TSV(UTF-8) 형식의 별도 코드블록으로 생성
3. 일일작업보고 원문에서 데이터를 파싱하여 4개 테이블("시공현황", "작업내용", "인원", "장비") 각각을 TSV(UTF-8) 형식의 별도 코드블록으로 차례대로 출력하며 아래의 조건을 철저히 준수할 것

# OUTPUT 
## 0. 작업날짜 (최우선 출력)
- 형식: WORK_DATE: YYYY-MM-DD
- 예시: WORK_DATE: 2024-01-15
- 일일작업보고 텍스트에서 작업일/보고일을 찾아 추출
- 날짜가 명시되지 않은 경우 텍스트 맥락으로 추정

## 테이블(총 5개)  
## 1. 날씨정보 테이블
1. 고정 열 : "구분", "값"
2. 고정 행 : "최고온도", "최저온도", "강수량"
3. 추출데이터 : 서울(유) 오늘 날씨 예보 (최신 업데이트)
4. 주의사항 
- 서울 지역(영등포구 우선)의 최고 기온, 최저 기온, 강수량의 단일값 추출
- 데이터는 최신 업데이트된 기상청 정보를 기반으로 제공
- "값"만 숫자로 추출할 것 (예: 20.0 °C에서 "20.0" 추출)

## 2. 시공현황 테이블  
1. 고정 열 : "구분", "누계"  
2. 고정 행(총 33행) - 아래 순서와 명칭을 그대로  
- "1. 본선터널 (1구간, 대림-신풍)"  
- "1. 본선터널 (1구간, 대림-신풍) 라이닝" 
- "2. 신풍정거장 - 1)정거장 라이닝"
- "2. 신풍정거장 - 1)정거장 미들 슬라브"
- "2. 신풍정거장 – 2)주출입구 수직구 라이닝"
- "2. 신풍정거장 - 2)주출입구 - (1)PCB 정거장 방면 라이닝"
- "2. 신풍정거장 - 2)주출입구 - (1)PCB 환승통로 방면 라이닝"
- "2. 신풍정거장 - 2)주출입구 - (2)PCC 라이닝"
- "2. 신풍정거장 - 2)주출입구 - (3)PCD 라이닝"
- "2. 신풍정거장 - 2)주출입구 - (4)PHA 라이닝"
- "2. 신풍정거장 - 3)특별피난계단 - 수직구 라이닝"
- "2. 신풍정거장 - 3)특별피난계단 - PHB 라이닝"
- "2. 신풍정거장 - 4)외부출입구 출입구(#3) 굴착" 
- "2. 신풍정거장 - 4)외부출입구 출입구(#2) 굴착"
- "2. 신풍정거장 - 4)외부출입구 출입구(#1) 굴착" 
- "3. 신풍 환승통로 - 1)환승터널 연결터널(PCF) 굴착" 
- "3. 신풍 환승통로 - 1)환승터널 연결터널(PCF) 라이닝"  
- "3. 신풍 환승통로 - 1)환승터널 연결터널(PCE) 굴착" 
- "3. 신풍 환승통로 - 1)환승터널 연결터널(PCE) 라이닝"  
- "3. 신풍 환승통로 - 2)개착 BOX 보라매 방면 구조물"  
- "3. 신풍 환승통로 - 2)개착 BOX 대림 방면 굴착"  
- "4. 본선터널(2구간, 신풍-도림) 굴착"  
- "4. 본선터널(2구간, 신풍-도림) 라이닝"  
- "5. 도림사거리정거장 - 1)정거장 터널 라이닝"  
- "5. 도림사거리정거장 - 1)정거장 미들 슬라브" 
- "5. 도림사거리정거장 - 2)출입구#1 수직구 라이닝"  
- "5. 도림사거리정거장 - 2)출입구#1 PCA 라이닝"  
- "5. 도림사거리정거장 - 2)출입구#1 PCC 라이닝"  
- "5. 도림사거리정거장 - 2)출입구#1 PHA 라이닝"  
- "5. 도림사거리정거장 - 3)출입구#2 수직구 라이닝"  
- "5. 도림사거리정거장 - 3)출입구#2 PCA 라이닝"  
- "5. 도림사거리정거장 - 3)출입구#2 PCC 라이닝"  
- "5. 도림사거리정거장 - 3)출입구#2 PHB 라이닝"  
3. 추출데이터  
- "누계"값만 숫자로 추출할 것 (예: 945.3m / 1,116m 에서 "945.3" 추출)

## 3. 작업내용 테이블  
1. 고정 열 : "구분", "금일작업"  
2. 고정 행(총 14행) - 아래 순서와 명칭(매핑 후 결과)을 그대로  
- "1. 본선터널 (1구간, 대림-신풍)"  
- "2.신풍정거장 - 1)정거장 터널"  
- "2.신풍정거장 - 2)주출입구 - (1)PCB"  
- "2.신풍정거장 - 2)주출입구 - (2)PCC"  
- "2.신풍정거장 - 2)주출입구 - (3)PCD"  
- "2.신풍정거장 - 2)주출입구 - (4)PHA"  
- "2.신풍정거장 - 3)특별피난계단"  
- "2.신풍정거장 - 4)외부출입구"  
- "3.신풍 환승통로 - 1)환승터널"  
- "3.신풍 환승통로 - 2)개착 BOX"  
- "4.본선터널(2구간, 신풍-도림)"  
- "5.도림사거리정거장 - 1)정거장 터널"  
- "5.도림사거리정거장 - 2)출입구#1"  
- "5.도림사거리정거장 - 3)출입구#2"  
3. 주의사항  
- '작업내용' 셀은 여러 세부 내용을 포함할 수 있습니다. 내용을 구분할 때는, 최종 TSV 출력 시 해당 셀을 큰따옴표("...")로 감싸되, 셀 내부의 각 내용은 **실제 줄바꿈 문자(예: '\\n' 문자열 대신 엔터 키 입력에 해당)**를 사용하여 분리하며, '-'기호는 생략함

## 4. 인원 / 장비 테이블  
1. 고정 열 (총 15열) - 열 순서는 아래와 같음
- "구분" 
- "1. 본선터널 (1구간, 대림~신풍)"  
- "2.신풍정거장 - 1)정거장 터널"  
- "2.신풍정거장 - 2)주출입구 - (1)PCB"  
- "2.신풍정거장 - 2)주출입구 - (2)PCC"  
- "2.신풍정거장 - 2)주출입구 - (3)PCD"  
- "2.신풍정거장 - 2)주출입구 - (4)PHA"  
- "2.신풍정거장 - 3)특별피난계단"  
- "2.신풍정거장 - 4)외부출입구"  
- "3.신풍 환승통로 - 1)환승터널"  
- "3.신풍 환승통로 - 2)개착 BOX"  
- "4.본선터널(2구간, 신풍~도림)"  
- "5.도림사거리정거장 - 1)정거장 터널"  
- "5.도림사거리정거장 - 2)출입구#1"  
- "5.도림사거리정거장 - 3)출입구#2"    
2. 고정 행(인원 테이블 – 총 36행)  
(인원 목록은 아래 순서와 명칭(매핑 후 결과)을 반드시 그대로 사용):
"직영반장", "연수생", "장비운전원", "전기주임", "화약주임", "터널공", "목공", "철근공", "라이닝폼공", "오폐수처리공", "카리프트공", "BP공", "가시설공/해체공", "동바리공", "신호수", "부단수공", "슬러리월공", "CIP공", "미장공", "시설물공", "경계석공", "조경공", "배관공", "도색공", "방수공", "장비/작업지킴이", "보통인부", "포장공", "용접공", "타설공", "보링공/앙카공", "비계공", "도장공", "석면공", "주입공/그라우팅공"
3. 고정 행 (장비 테이블 – 총 46행)  
(장비 목록은 아래 순서와 명칭(매핑 후 결과)을 반드시 그대로 사용):
"B/H(1.0LC)", "B/H(08W)", "B/H(08LC)", "B/H(06W)", "B/H(06LC)", "B/H(03LC)", "B/H(02LC)", "B/H(015)", "덤프트럭(5T)", "덤프트럭(15T)", "덤프트럭(25T)", "앵글크레인(100T)", "앵글크레인(80T)", "앵글크레인(35T)", "앵글크레인(25T)", "카고크레인(25T)", "카고크레인(5T)", "콤프", "점보드릴", "페이로더", "숏트머신", "차징카", "살수차", "하이드로크레인", "믹서트럭", "화물차(5T)", "펌프카", "스카이", "콘크리트피니셔", "전주오거", "로더(바브켓)", "유제살포기(비우다)", "지게차", "싸인카", "BC커터기", "바이브로해머", "롤러(2.5T)", "롤러(1T)", "롤러(0.7T)", "몰리", "항타기", "크레인", "콤비로라", "공압드릴", "유압드릴", "기타"

## 5. Parsing Rules 
1. 시공현황: "누계/설계" → **앞 값(소수 허용)** 만 추출.    
2. 인원·장비: 투입현황에서 **정수만** 추출, 빈셀은 **0**    
3. 하위 섹션 매핑    
   - 정거장 터널 → 열 ②, PCB → ③, PCC → ④, PCD → ⑤, PHA → ⑥, 특별피난 → ⑦, 외부출입구 → ⑧    
4. 매핑 딕셔너리 적용    
- "B/H08W" → "B/H(08W)"   
- "25톤 카고크레인" → "카고크레인(25T)"   
- "특공" → "보통인부"    
- "기계타설공" → "타설공"    
- "목공연수생" 또는 "목수연수생" → "연수생"    
- "5톤트럭" → "화물차(5T)"    
- "카리프트" → "카리프트공"    
- "하이드로크레인(20T)" → "하이드로크레인"    
- "라이닝폼조립" → "라이닝폼공"  
- "S/C타설팀" → "터널공"  
- "목수" → "목공"    
5. 사전에 없는 항목 → 유사항목, 없으면 **인원: 보통인부 / 장비: 기타** 로 합산하고 '오류요약'에 기재.

## 6. 변환로그 (변경사항이 있을 때만 출력)
변경된 항목만 아래 형식으로 출력:
(원문) 목수 -> (변경) 목공   *위치: 1. 본선터널(1구간, 대림-신풍)
(원문) 특공 -> (변경) 보통인부   *위치: 2.신풍정거장 - 1)정거장 터널
(원문) B/H08W -> (변경) B/H(08W)   *위치: 4.본선터널(2구간, 신풍-도림)
주의사항:
- 변경사항이 없으면 "변환로그: 변경사항 없음" 출력
- 각 변경사항은 별도 행으로 출력
- 위치는 구체적인 작업 구간명 기재',
    '기본 카카오톡 작업보고 분석용 프롬프트 (날짜 추출 기능 포함)'
) ON CONFLICT (name) DO UPDATE SET 
    content = EXCLUDED.content,
    description = EXCLUDED.description,
    updated_at = NOW();
```

## 2. Streamlit 설정

`.streamlit/secrets.toml` 파일을 생성하고 다음 내용을 추가하세요:

```toml
# Supabase 연결 설정
SUPABASE_URL = "https://txlkfywysdnoigcwbags.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR4bGtmeXd5c2Rub2lnY3diYWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM2MTU4NDEsImV4cCI6MjA2OTE5MTg0MX0.svkW2EFuqUTfomf8_FDRhdghfCC5_NbmF1zEXhI3TD0"

# 기존 API 키들
GENAI_API_KEY = "AIzaSyD69-wKYfZSID327fczrkx-JveJdGYIUIk"
TEAMS_WEBHOOK_URL = "https://poscoenc365.webhook.office.com/webhookb2/f6efcf11-c6a7-4385-903f-f3fd8937de55@ec1d3aa9-13ec-4dc5-8672-06fc64ca7701/IncomingWebhook/1fb9d9ce7f4c4093ba4fe9a8db67dc2f/1a2e3f7d-551b-40ec-90a1-e815373c81a7/V2qbqRtbAap4il8cvVljyk_ApZuHTDE0AfOYLQ8V9SqQs1"
```

2. 필요한 패키지를 설치하세요:
```bash
pip install -r requirements.txt
```

## 4. 애플리케이션 실행

```bash
streamlit run "엑셀 작업일보 자동화_추가_rev0.py"
```

## 5. 기능 설명

### 데이터 저장
- 각 단계에서 "💾 Supabase에 저장" 버튼을 클릭하면 데이터가 Supabase에 저장됩니다.
- 저장된 데이터는 날짜별로 구분되어 관리됩니다.

### 데이터 조회
- "📅 날짜별 데이터 조회" 버튼을 클릭하면 특정 날짜의 데이터를 조회할 수 있습니다.
- 각 데이터 타입별로 별도 조회가 가능합니다.

### 보안
- API 키와 연결 정보는 `.streamlit/secrets.toml` 파일에 안전하게 저장됩니다.
- 이 파일은 Git에 커밋하지 않도록 주의하세요.

## 6. 문제 해결

### 연결 오류
- Supabase URL과 API 키가 올바른지 확인하세요.
- 네트워크 연결을 확인하세요.

### 테이블 오류
- Supabase에서 테이블이 올바르게 생성되었는지 확인하세요.
- RLS(Row Level Security) 설정을 확인하세요.

### 패키지 오류
- `pip install -r requirements.txt`로 모든 패키지를 설치했는지 확인하세요. 