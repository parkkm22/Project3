-- 시공관리도 관리 테이블 생성
CREATE TABLE IF NOT EXISTS management_drawings (
    id SERIAL PRIMARY KEY,
    process_name VARCHAR(255) NOT NULL,        -- 공정명 (예: 도림사거리 정거장)
    drawing_type VARCHAR(100) NOT NULL,       -- 도면 유형 (미들슬라브, 상부슬라브, 전체 등)
    year_month VARCHAR(7) NOT NULL,           -- 해당 월 (2024-01 형식)
    file_path VARCHAR(500) NOT NULL,          -- Supabase Storage 파일 경로
    file_name VARCHAR(255) NOT NULL,          -- 원본 파일명
    file_size INTEGER,                        -- 파일 크기 (bytes)
    file_type VARCHAR(20) DEFAULT 'pdf',      -- 파일 형식 (pdf, dwg, png 등)
    upload_date TIMESTAMP DEFAULT NOW(),     -- 업로드 일시
    created_by VARCHAR(100),                  -- 업로드한 사용자
    is_active BOOLEAN DEFAULT true,          -- 활성 상태
    description TEXT,                         -- 도면 설명
    version VARCHAR(20) DEFAULT '1.0',       -- 도면 버전
    approval_status VARCHAR(50) DEFAULT 'pending', -- 승인 상태 (pending, approved, rejected)
    
    -- 검색 최적화를 위한 복합 인덱스
    UNIQUE(process_name, drawing_type, year_month, version)
);

-- 인덱스 생성 (빠른 검색을 위해)
CREATE INDEX IF NOT EXISTS idx_management_drawings_process ON management_drawings(process_name);
CREATE INDEX IF NOT EXISTS idx_management_drawings_month ON management_drawings(year_month);
CREATE INDEX IF NOT EXISTS idx_management_drawings_type ON management_drawings(drawing_type);
CREATE INDEX IF NOT EXISTS idx_management_drawings_active ON management_drawings(is_active);

-- 샘플 데이터 삽입
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
('도림사거리 정거장', '미들슬라브', '2024-01', 'management-drawings/2024-01/도림사거리_정거장_미들슬라브_202401.pdf', '도림사거리_정거장_미들슬라브_202401.pdf', 2048576, '도림사거리 정거장 미들슬라브 시공관리도 (2024년 1월)', 'admin', 'approved'),
('도림사거리 정거장', '상부슬라브', '2024-01', 'management-drawings/2024-01/도림사거리_정거장_상부슬라브_202401.pdf', '도림사거리_정거장_상부슬라브_202401.pdf', 1856432, '도림사거리 정거장 상부슬라브 시공관리도 (2024년 1월)', 'admin', 'approved'),
('도림사거리 정거장', '전체공정', '2024-01', 'management-drawings/2024-01/도림사거리_정거장_전체_202401.pdf', '도림사거리_정거장_전체_202401.pdf', 3145728, '도림사거리 정거장 전체 시공관리도 (2024년 1월)', 'admin', 'approved'),
('도림사거리 정거장', '미들슬라브', '2024-02', 'management-drawings/2024-02/도림사거리_정거장_미들슬라브_202402.pdf', '도림사거리_정거장_미들슬라브_202402.pdf', 2156032, '도림사거리 정거장 미들슬라브 시공관리도 (2024년 2월)', 'admin', 'approved');

-- 뷰 생성 (활성화된 최신 도면만 조회)
CREATE OR REPLACE VIEW active_management_drawings AS
SELECT 
    id,
    process_name,
    drawing_type,
    year_month,
    file_path,
    file_name,
    file_size,
    file_type,
    upload_date,
    description,
    version,
    approval_status
FROM management_drawings 
WHERE is_active = true 
  AND approval_status = 'approved'
ORDER BY process_name, drawing_type, year_month DESC;

COMMENT ON TABLE management_drawings IS '시공관리도 파일 관리 테이블';
COMMENT ON COLUMN management_drawings.process_name IS '공정명 (예: 도림사거리 정거장)';
COMMENT ON COLUMN management_drawings.drawing_type IS '도면 유형 (미들슬라브, 상부슬라브, 전체공정 등)';
COMMENT ON COLUMN management_drawings.year_month IS '해당 월 (YYYY-MM 형식)';
COMMENT ON COLUMN management_drawings.file_path IS 'Supabase Storage 내 파일 경로';

