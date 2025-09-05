# Supabase Storage 파일 업로드 문제 해결

## 문제 1: 폴더명 불일치

### 현재 상황
- 화면에 보이는 폴더: `2025-08`
- 설정된 경로: `2024-08`

### 해결 방법
1. **올바른 폴더명으로 변경**
   - `2025-08` 폴더를 `2024-08`로 이름 변경
   - 또는 데이터베이스 경로를 `2025-08`로 수정

2. **새 폴더 생성 (권장)**
   - `2024-08` 폴더 새로 생성
   - 기존 `2025-08` 폴더 삭제

## 문제 2: 파일 업로드 실패 원인

### A. 파일 크기 제한
- **확인사항**: 파일이 50MB 이하인지 확인
- **해결**: 버킷 설정에서 파일 크기 제한 증가

### B. 파일 형식 제한
- **지원 형식**: PDF, PNG, JPG, DWG
- **확인사항**: 파일 확장자가 올바른지 확인

### C. 권한 문제
- **확인사항**: Storage Policy 설정 확인
- **해결**: 공개 읽기 정책 추가

## 문제 3: 업로드 방법

### 방법 1: 드래그 앤 드롭
1. 파일을 선택
2. `2024-08` 폴더 영역으로 드래그
3. 파일 놓기

### 방법 2: Upload files 버튼
1. `2024-08` 폴더 클릭
2. **Upload files** 버튼 클릭
3. 파일 선택 후 업로드

### 방법 3: 폴더 내에서 업로드
1. 폴더 내부에서 **Upload files** 클릭
2. 파일 선택

## 문제 4: Storage Policy 설정

### 필수 정책 추가
```sql
-- Storage > Policies에서 실행
CREATE POLICY "Public read access" ON storage.objects
FOR SELECT USING (bucket_id = 'management-drawings');

CREATE POLICY "Authenticated users can upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'management-drawings');
```

## 문제 5: 파일 경로 확인

### 업로드 후 확인사항
1. 파일이 올바른 경로에 업로드되었는지 확인
2. 파일명에 공백이나 특수문자가 있는지 확인
3. 파일 크기가 정확히 표시되는지 확인

## 문제 6: 대안 방법

### A. 다른 폴더명 사용
```sql
-- 데이터베이스 경로를 현재 폴더명에 맞춤
UPDATE management_drawings 
SET file_path = 'management-drawings/2025-08/20250818-도림사거리정거장 시공 관리도.pdf'
WHERE process_name = '도림사거리 정거장' AND year_month = '2024-08';
```

### B. 파일명 단순화
- 파일명에서 공백 제거
- 특수문자 제거
- 예: `20250818-도림사거리정거장_시공관리도.pdf`

## 문제 7: 테스트 방법

### A. 간단한 파일로 테스트
1. 작은 크기의 PDF 파일로 테스트
2. 파일명에 공백 없는 파일로 테스트

### B. 업로드 확인
1. 업로드 후 파일 목록에서 파일 확인
2. 파일 클릭하여 다운로드 테스트
3. 파일 URL 복사하여 브라우저에서 접근 테스트

