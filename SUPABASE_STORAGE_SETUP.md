# Supabase Storage 설정 가이드

## 1단계: Storage 버킷 생성

### A. Supabase 대시보드 접속
1. [Supabase Dashboard](https://supabase.com/dashboard) 접속
2. 프로젝트 선택

### B. Storage 버킷 생성
1. **Storage** 메뉴 클릭
2. **New Bucket** 클릭
3. 설정:
   - **Bucket name**: `management-drawings`
   - **Public bucket**: ✅ 체크 (파일 접근용)
   - **File size limit**: 50MB (또는 필요에 따라)
4. **Create bucket** 클릭

## 2단계: 폴더 구조 생성

### A. 월별 폴더 생성
1. 생성된 `management-drawings` 버킷 클릭
2. **New Folder** 클릭
3. 폴더명: `2024-08`
4. 반복하여 `2024-01`, `2024-02` 등 생성

### B. 폴더 구조
```
management-drawings/
├── 2024-01/
├── 2024-02/
├── 2024-03/
└── 2024-08/
```

## 3단계: 파일 업로드

### A. PDF 파일 업로드
1. `2024-08` 폴더 클릭
2. **Upload files** 클릭
3. 파일 선택: `20250818-도림사거리정거장 시공 관리도.pdf`
4. 업로드 완료

### B. 파일 경로 확인
업로드 후 파일 경로: `management-drawings/2024-08/20250818-도림사거리정거장 시공 관리도.pdf`

## 4단계: Storage Policy 설정

### A. 공개 접근 정책
```sql
-- Storage > Policies에서 설정
CREATE POLICY "Public read access" ON storage.objects
FOR SELECT USING (bucket_id = 'management-drawings');
```

### B. 업로드 정책 (관리자용)
```sql
CREATE POLICY "Authenticated users can upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'management-drawings' AND auth.role() = 'authenticated');
```

## 5단계: 데이터베이스 설정

### A. 테이블 생성
```sql
CREATE TABLE IF NOT EXISTS management_drawings (
    id SERIAL PRIMARY KEY,
    process_name VARCHAR(255) NOT NULL,
    drawing_type VARCHAR(100) NOT NULL,
    year_month VARCHAR(7) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size INTEGER,
    file_type VARCHAR(20) DEFAULT 'pdf',
    upload_date TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    version VARCHAR(20) DEFAULT '1.0',
    approval_status VARCHAR(50) DEFAULT 'pending',
    UNIQUE(process_name, drawing_type, year_month, version)
);
```

### B. 데이터 삽입
```sql
INSERT INTO management_drawings (
    process_name, 
    drawing_type, 
    year_month, 
    file_path, 
    file_name, 
    file_size, 
    description,
    created_by,
    approval_status
) VALUES 
('도림사거리 정거장', '시공관리도', '2024-08', 'management-drawings/2024-08/20250818-도림사거리정거장 시공 관리도.pdf', '20250818-도림사거리정거장 시공 관리도.pdf', 243710, '도림사거리 정거장 시공관리도 (2024년 8월)', 'admin', 'approved');
```

## 6단계: 파일 URL 확인

### A. 파일 URL 형식
```
https://[PROJECT_ID].supabase.co/storage/v1/object/public/management-drawings/2024-08/20250818-도림사거리정거장%20시공%20관리도.pdf
```

### B. URL 인코딩
- 공백: `%20`
- 특수문자: URL 인코딩 필요

## 7단계: 테스트

### A. 파일 접근 테스트
브라우저에서 파일 URL 접속하여 PDF 확인

### B. 애플리케이션 테스트
```
"도림사거리 정거장 공정 분석해줘"
```

## 문제 해결

### A. 파일 접근 안됨
- Storage Policy 확인
- 파일 경로 확인
- URL 인코딩 확인

### B. 업로드 실패
- 파일 크기 제한 확인
- 권한 설정 확인
- 네트워크 연결 확인

