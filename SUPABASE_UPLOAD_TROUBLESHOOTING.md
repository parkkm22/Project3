# Supabase 파일 업로드 문제 해결

## 🚨 **현재 문제**
- "도림사거리 정거장 미들슬라브 공정 분석해줘" → "조회된 데이터가 없습니다"
- Supabase Storage에 파일 업로드가 안됨

## 🔧 **단계별 해결 방법**

### **1단계: Storage Policy 설정**
**Supabase 대시보드** → **Storage** → **Policies**에서 `STORAGE_POLICY_FIX.sql` 실행

### **2단계: 테스트 데이터 생성**
**SQL Editor**에서 `TEST_DATA_SETUP.sql` 실행

### **3단계: 파일 업로드 시도**

#### **방법 A: 드래그 앤 드롭**
1. 파일을 선택
2. `2025-08` 폴더 영역으로 드래그
3. 파일 놓기

#### **방법 B: Upload files 버튼**
1. `2025-08` 폴더 클릭
2. **Upload files** 버튼 클릭
3. 파일 선택

#### **방법 C: 폴더 내부에서 업로드**
1. 폴더 내부로 이동
2. **Upload files** 클릭
3. 파일 선택

### **4단계: 업로드 실패 시 대안**

#### **A. 파일 크기 확인**
- 파일이 50MB 이하인지 확인
- 큰 파일은 압축하거나 분할

#### **B. 파일 형식 확인**
- PDF 파일인지 확인
- 파일명에 특수문자가 없는지 확인

#### **C. 브라우저 문제**
- 다른 브라우저로 시도 (Chrome, Firefox, Edge)
- 브라우저 캐시 삭제
- 시크릿 모드로 시도

#### **D. 네트워크 문제**
- 인터넷 연결 확인
- VPN 사용 중이면 해제

### **5단계: 수동 파일 경로 설정**

파일 업로드가 안되면 수동으로 경로 설정:
```sql
-- 실제 파일 경로로 업데이트
UPDATE management_drawings 
SET file_path = 'management-drawings/2025-08/실제파일명.pdf',
    file_name = '실제파일명.pdf'
WHERE process_name = '도림사거리 정거장' 
  AND drawing_type = '미들슬라브';
```

## 🧪 **테스트 방법**

### **1. 데이터베이스 연결 테스트**
```sql
SELECT COUNT(*) FROM management_drawings WHERE is_active = true;
```

### **2. 파일 경로 테스트**
```sql
SELECT file_path, file_name FROM management_drawings 
WHERE process_name LIKE '%도림사거리%';
```

### **3. 애플리케이션 테스트**
- "도림사거리 정거장 미들슬라브 공정 분석해줘"
- "신풍 정거장 시공관리도 보여줘"

## 🔍 **문제 진단**

### **A. Storage 버킷 확인**
1. **Storage** → **management-drawings** 버킷 존재 확인
2. **2025-08** 폴더 존재 확인
3. 파일이 실제로 업로드되었는지 확인

### **B. Policy 확인**
```sql
SELECT * FROM pg_policies 
WHERE tablename = 'objects' 
  AND schemaname = 'storage';
```

### **C. 파일 URL 테스트**
브라우저에서 직접 URL 접속:
```
https://[PROJECT_ID].supabase.co/storage/v1/object/public/management-drawings/2025-08/파일명.pdf
```

## 💡 **임시 해결책**

파일 업로드가 안되면:
1. `TEST_DATA_SETUP.sql`로 테스트 데이터 생성
2. 애플리케이션에서 "도림사거리 정거장 미들슬라브 공정 분석해줘" 테스트
3. 데이터는 나오지만 파일 다운로드는 안됨 (정상)

## 🎯 **최종 확인**

성공하면:
- ✅ 데이터베이스에 데이터 존재
- ✅ Storage Policy 설정 완료
- ✅ 파일 업로드 성공
- ✅ 애플리케이션에서 시공관리도 표시

