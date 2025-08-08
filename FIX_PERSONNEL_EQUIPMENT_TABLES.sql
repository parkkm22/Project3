-- personnel_data와 equipment_data 테이블 수정
-- Supabase SQL Editor에서 실행하세요

-- 기존 테이블 삭제 (데이터가 있다면 백업 후 실행)
DROP TABLE IF EXISTS personnel_data CASCADE;
DROP TABLE IF EXISTS equipment_data CASCADE;

-- 인원 데이터 테이블 재생성
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

-- 장비 데이터 테이블 재생성
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

-- RLS 비활성화
ALTER TABLE personnel_data DISABLE ROW LEVEL SECURITY;
ALTER TABLE equipment_data DISABLE ROW LEVEL SECURITY;

-- 테이블 구조 확인
SELECT 
    table_name,
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name IN ('personnel_data', 'equipment_data')
ORDER BY table_name, ordinal_position; 