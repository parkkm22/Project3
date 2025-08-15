-- Supabase Templates 테이블 생성 스크립트
-- 이 스크립트를 Supabase SQL Editor에서 실행하세요

-- templates 테이블 생성
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL,
    template_data TEXT NOT NULL,  -- base64 인코딩된 엑셀 파일 데이터
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_templates_name ON templates(template_name);
CREATE INDEX IF NOT EXISTS idx_templates_created_at ON templates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_templates_is_default ON templates(is_default);

-- RLS (Row Level Security) 설정 (선택사항)
-- ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

-- 기본 템플릿은 하나만 허용하는 제약조건
CREATE UNIQUE INDEX IF NOT EXISTS idx_templates_default_unique 
ON templates(template_name) 
WHERE is_default = TRUE;

-- 템플릿 이름 중복 방지 (같은 이름의 최신 버전만 유지)
CREATE UNIQUE INDEX IF NOT EXISTS idx_templates_name_latest 
ON templates(template_name, created_at DESC);

-- 테이블 설명 추가
COMMENT ON TABLE templates IS '엑셀 템플릿 파일 저장 테이블';
COMMENT ON COLUMN templates.template_name IS '템플릿 이름';
COMMENT ON COLUMN templates.template_data IS 'base64 인코딩된 엑셀 파일 데이터';
COMMENT ON COLUMN templates.description IS '템플릿 설명';
COMMENT ON COLUMN templates.is_default IS '기본 템플릿 여부';

-- 샘플 데이터 삽입 (선택사항)
-- INSERT INTO templates (template_name, template_data, description, is_default) 
-- VALUES ('default', 'base64_encoded_excel_data_here', '기본 공사일보 템플릿', TRUE); 