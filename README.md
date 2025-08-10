# 🏗️ Construction Status Management System

건설 현황을 관리하고 월간 실적을 추적하는 Streamlit 기반 웹 애플리케이션입니다.

## 🚀 주요 기능

### 📊 월간실적 관리
- **시공현황 기본 구조**: 위치별 설계 및 전체 현황 관리
- **월간 누계 계산**: 25년 1월부터 26년 12월까지의 월별 진행률 추적
- **동적 열 관리**: 사용자 정의 열 추가/제거 기능
- **Supabase 연동**: 실시간 데이터베이스 연동

### 📋 작업일보 자동화
- **SNS 일일작업계획**: 일일 작업 계획 수립 및 관리
- **작업일보 작성**: 작업 진행 상황 기록 및 보고

### 🎯 핵심 특징
- **Excel 호환 드래그 복사**: Ctrl+C로 선택된 범위를 Excel에 붙여넣기 가능
- **셀 편집 기능**: 설계, 월간 누계, 사용자 정의 열 편집 가능
- **고정 열 시스템**: 위치, 전체, 누계, 진도율, 잔여 등 핵심 정보 고정 표시
- **반응형 UI**: streamlit-aggrid를 활용한 전문적인 데이터 그리드

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **Database**: Supabase (PostgreSQL)
- **Data Grid**: streamlit-aggrid
- **Data Processing**: Pandas
- **Language**: Python 3.13

## 📁 프로젝트 구조

```
project4/
├── Project3/
│   ├── .streamlit/
│   │   └── secrets.toml          # Supabase 연결 정보
│   ├── pages/
│   │   ├── SNS일일작업계획.py     # SNS 일일작업계획 페이지
│   │   ├── 작업일보 작성.py       # 작업일보 작성 페이지
│   │   └── 월간실적              # 월간실적 관리 페이지
│   ├── app.py                    # 메인 앱 설정
│   └── main.py                   # 메인 페이지
├── .gitignore                    # Git 제외 파일 목록
└── README.md                     # 프로젝트 설명서
```

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install streamlit pandas streamlit-aggrid supabase
```

### 2. 환경 설정
`.streamlit/secrets.toml` 파일에 Supabase 연결 정보를 설정하세요:
```toml
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_anon_key"
```

### 3. 애플리케이션 실행
```bash
cd Project3
streamlit run app.py
```

## 📊 사용법

### 월간실적 관리
1. **기본 구조 설정**: 위치별 설계 및 전체 현황 입력
2. **사용자 정의 열 추가**: 필요한 추가 정보 열 생성
3. **데이터 편집**: 설계, 월간 누계 등 셀 내용 수정
4. **Excel 연동**: 드래그 선택 후 Ctrl+C로 복사하여 Excel에 붙여넣기

### 드래그 복사 기능
- **마우스 드래그**: 셀을 드래그하여 범위 선택
- **Ctrl+C**: 선택된 범위를 클립보드에 복사
- **Excel 호환**: 탭으로 구분된 데이터 형식으로 Excel에 붙여넣기 가능

## 🔧 주요 설정

### AgGrid 옵션
- `enableRangeSelection`: 범위 선택 활성화
- `allowRangeSelection`: 범위 선택 허용
- `enableRangeHandle`: 범위 핸들 활성화
- `enableFillHandle`: 채우기 핸들 활성화
- `fit_columns_on_grid_load`: False (전체 열명 표시)
- `height`: 1200px (충분한 테이블 높이)

### 고정 열 설정
- **기본 정보**: 위치, 전체, 누계, 진도율, 잔여
- **월별 컬럼**: 25-01부터 26-12까지 (150px 고정 너비)
- **편집 가능**: 설계, 월간 누계, 사용자 정의 열

## 📈 데이터 구조

### construction_status 테이블
- **날짜**: 작업 진행 날짜
- **위치**: 작업 위치 정보
- **진행률**: 해당 날짜의 진행률

### 월간 누계 계산
- **월별 진행률**: 각 월의 진행 상황
- **누계 계산**: 월별 진행률의 누적 합계
- **대비 분석**: 전월 대비 진행률 변화

## 🐛 문제 해결

### Supabase 연결 문제
1. `secrets.toml` 파일의 연결 정보 확인
2. "Supabase 연결 테스트" 버튼으로 연결 상태 확인
3. "construction_status 테이블 구조 확인"으로 테이블 접근성 확인

### 드래그 복사 문제
1. "🔍 드래그 복사 상태 확인" 버튼으로 설정 상태 확인
2. 브라우저 개발자 도구(F12)의 Console 탭에서 오류 메시지 확인
3. 셀을 클릭한 후 드래그하여 범위 선택

## 📝 업데이트 내역

### 최신 업데이트
- ✅ Supabase 데이터 연동 완료
- ✅ 드래그 복사 기능 구현
- ✅ 동적 열 관리 시스템 구축
- ✅ 셀 편집 기능 구현
- ✅ 고정 열 시스템 구현
- ✅ Excel 호환 데이터 형식 지원

## 🤝 기여하기

프로젝트 개선을 위한 제안이나 버그 리포트는 언제든 환영합니다!

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 