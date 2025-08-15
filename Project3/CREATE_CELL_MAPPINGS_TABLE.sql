-- Supabase SQL Editor에서 실행하세요
-- cell_mappings 테이블 생성

CREATE TABLE IF NOT EXISTS cell_mappings (
    id SERIAL PRIMARY KEY,
    mapping_name VARCHAR(255) NOT NULL,
    mapping_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_cell_mappings_name ON cell_mappings(mapping_name);
CREATE INDEX IF NOT EXISTS idx_cell_mappings_created_at ON cell_mappings(created_at DESC);

-- 테이블 확인
SELECT * FROM cell_mappings LIMIT 1; 