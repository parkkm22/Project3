# 시공관리도 관리 시스템 구축 가이드

## 🎯 시스템 개요

특정 공정 분석 요청 시 해당 월의 시공관리도를 자동으로 표시하는 기능이 구현되었습니다.

## 📋 구현된 기능

### 1. 데이터베이스 구조
- **테이블명**: `management_drawings`
- **주요 필드**:
  - `process_name`: 공정명 (예: 도림사거리 정거장)
  - `drawing_type`: 도면 유형 (미들슬라브, 상부슬라브, 전체공정)
  - `year_month`: 해당 월 (YYYY-MM 형식)
  - `file_path`: 파일 저장 경로
  - `file_name`: 원본 파일명
  - `approval_status`: 승인 상태

### 2. 자동 연동 기능
```python
# 공정 분석 요청 시 자동으로 시공관리도 표시
"도림사거리 정거장 미들슬라브 공정 분석해줘"
↓
1. 공정명: "도림사거리 정거장" 추출
2. 도면유형: "미들슬라브" 추출  
3. 현재월: "2024-01" 자동 설정
4. 관련 시공관리도 검색 및 표시
```

## 📁 파일 저장 방식

### A. Supabase Storage 구조 (추천)
```
supabase-storage/
├── management-drawings/
│   ├── 2024-01/
│   │   ├── 도림사거리_정거장_미들슬라브_202401.pdf
│   │   ├── 도림사거리_정거장_상부슬라브_202401.pdf
│   │   └── 도림사거리_정거장_전체공정_202401.pdf
│   ├── 2024-02/
│   └── 2024-03/
```

### B. 로컬 파일 시스템 (대안)
```
project5/
├── static/
│   └── management-drawings/
│       ├── 2024-01/
│       ├── 2024-02/
│       └── 2024-03/
```

## 🔧 설정 방법

### 1. 데이터베이스 테이블 생성
```sql
-- CREATE_MANAGEMENT_DRAWINGS_TABLE.sql 실행
psql -d your_database -f CREATE_MANAGEMENT_DRAWINGS_TABLE.sql
```

### 2. Supabase Storage 버킷 생성
```javascript
// Supabase 대시보드에서
// Storage > Create Bucket
// Name: management-drawings
// Public: true (또는 필요에 따라)
```

### 3. 파일 업로드 방법

#### A. 관리자 인터페이스 사용
1. 사이드바 → 디버깅 모드 활성화
2. "시공관리도 업로드" 섹션 이용
3. 공정명, 도면유형, 해당월, 파일 선택
4. 업로드 버튼 클릭

#### B. 직접 데이터베이스 입력
```sql
INSERT INTO management_drawings (
    process_name, drawing_type, year_month, 
    file_path, file_name, description
) VALUES (
    '도림사거리 정거장', '미들슬라브', '2024-01',
    'management-drawings/2024-01/도림사거리_정거장_미들슬라브_202401.pdf',
    '도림사거리_정거장_미들슬라브_202401.pdf',
    '도림사거리 정거장 미들슬라브 시공관리도'
);
```

## 📄 지원 파일 형식

- **PDF**: ✅ 추천 (가장 안정적)
- **DWG**: ✅ CAD 도면 
- **PNG/JPG**: ✅ 이미지 형태 도면
- **기타**: 필요에 따라 확장 가능

## 🚀 사용 예시

### 사용자 질문:
```
"도림사거리 정거장 미들슬라브 공정 분석해줘"
```

### 시스템 응답:
1. **구조화된 테이블** (공정 현황)
2. **간트차트** (진행률 시각화)
3. **시공관리도** (관련 PDF 파일)
   - 📄 도림사거리_정거장_미들슬라브_202401.pdf
   - 📥 [시공관리도 다운로드] 버튼
   - 💡 PDF 뷰어 안내

## ⚙️ 고급 설정

### 1. 파일 접근 권한
```python
# Supabase Storage Policy 설정
CREATE POLICY "Public read access" ON storage.objects
FOR SELECT USING (bucket_id = 'management-drawings');
```

### 2. 자동 월별 폴더 생성
```python
def create_monthly_folder(year_month):
    """월별 폴더 자동 생성"""
    folder_path = f"management-drawings/{year_month}/"
    # Supabase Storage API 호출
```

### 3. 파일 버전 관리
```sql
-- 버전별 파일 관리
UPDATE management_drawings 
SET is_active = false 
WHERE process_name = '도림사거리 정거장' 
  AND drawing_type = '미들슬라브'
  AND year_month = '2024-01';
```

## 🔒 보안 고려사항

1. **파일 접근 제어**: 승인된 사용자만 접근
2. **파일 크기 제한**: 대용량 파일 관리
3. **바이러스 검사**: 업로드 파일 검증
4. **백업**: 정기적인 파일 백업

## 📊 모니터링

### 저장소 사용량 체크
```sql
SELECT 
    year_month,
    COUNT(*) as file_count,
    SUM(file_size)/1024/1024 as total_mb
FROM management_drawings 
WHERE is_active = true
GROUP BY year_month
ORDER BY year_month DESC;
```

### 인기 공정 분석
```sql
SELECT 
    process_name,
    COUNT(*) as request_count
FROM management_drawings 
GROUP BY process_name
ORDER BY request_count DESC;
```

이제 공정 분석 요청 시 자동으로 해당 월의 시공관리도가 함께 표시됩니다! 🎉

