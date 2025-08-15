-- 기존 daily_report_data 테이블에 work_content_data 컬럼 추가
-- Supabase SQL Editor에서 실행하세요

-- 컬럼 추가
ALTER TABLE daily_report_data 
ADD COLUMN IF NOT EXISTS work_content_data JSONB DEFAULT '{}';

-- 컬럼 댓글 추가
COMMENT ON COLUMN daily_report_data.work_content_data IS '작업내용 데이터 (1단계 AI 추출 결과)';

-- 테이블 구조 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'daily_report_data' 
ORDER BY ordinal_position; 