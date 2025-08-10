-- Supabase SQL Editor에서 실행하세요
-- 간단한 templates 테이블 생성

CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL,
    template_data TEXT NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_templates_name ON templates(template_name);
CREATE INDEX IF NOT EXISTS idx_templates_created_at ON templates(created_at DESC);

-- 테이블 확인
SELECT * FROM templates LIMIT 1; 