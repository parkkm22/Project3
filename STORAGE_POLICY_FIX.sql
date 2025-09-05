-- Supabase Storage Policy 설정
-- Storage > Policies에서 실행

-- 1. 기존 정책 삭제 (있는 경우)
DROP POLICY IF EXISTS "Public read access" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can upload" ON storage.objects;
DROP POLICY IF EXISTS "Public access to management-drawings" ON storage.objects;

-- 2. 공개 읽기 정책 생성
CREATE POLICY "Public read access" ON storage.objects
FOR SELECT USING (bucket_id = 'management-drawings');

-- 3. 인증된 사용자 업로드 정책 생성
CREATE POLICY "Authenticated users can upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'management-drawings');

-- 4. 인증된 사용자 업데이트 정책 생성
CREATE POLICY "Authenticated users can update" ON storage.objects
FOR UPDATE USING (bucket_id = 'management-drawings');

-- 5. 인증된 사용자 삭제 정책 생성
CREATE POLICY "Authenticated users can delete" ON storage.objects
FOR DELETE USING (bucket_id = 'management-drawings');

-- 6. 정책 확인
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'objects' 
  AND schemaname = 'storage';

