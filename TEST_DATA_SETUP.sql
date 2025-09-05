-- 테스트용 간단한 데이터 설정
-- 파일 업로드 전에 먼저 실행하여 시스템 테스트

-- 테이블 생성 (없는 경우)
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

-- 기존 테스트 데이터 삭제
DELETE FROM management_drawings WHERE process_name LIKE '%테스트%';

-- 테스트용 데이터 삽입 (실제 파일 없이도 테스트 가능)
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
-- 도림사거리 정거장 테스트 데이터
('도림사거리 정거장', '미들슬라브', '2024-08', 'management-drawings/2025-08/test-도림사거리-미들슬라브.pdf', 'test-도림사거리-미들슬라브.pdf', 100000, '도림사거리 정거장 미들슬라브 테스트 데이터', 'admin', 'approved'),
('도림사거리 정거장', '시공관리도', '2024-08', 'management-drawings/2025-08/test-도림사거리-시공관리도.pdf', 'test-도림사거리-시공관리도.pdf', 150000, '도림사거리 정거장 시공관리도 테스트 데이터', 'admin', 'approved'),

-- 신풍 정거장 테스트 데이터
('신풍 정거장', '시공관리도', '2024-08', 'management-drawings/2025-08/test-신풍-시공관리도.pdf', 'test-신풍-시공관리도.pdf', 120000, '신풍 정거장 시공관리도 테스트 데이터', 'admin', 'approved'),

-- 본선 구간 테스트 데이터
('본선 1구간', '시공관리도', '2024-08', 'management-drawings/2025-08/test-본선1구간-시공관리도.pdf', 'test-본선1구간-시공관리도.pdf', 180000, '본선 1구간 시공관리도 테스트 데이터', 'admin', 'approved'),
('본선 2구간', '시공관리도', '2024-08', 'management-drawings/2025-08/test-본선2구간-시공관리도.pdf', 'test-본선2구간-시공관리도.pdf', 160000, '본선 2구간 시공관리도 테스트 데이터', 'admin', 'approved');

-- 데이터 확인
SELECT 
    id,
    process_name,
    drawing_type,
    year_month,
    file_name,
    file_path,
    is_active,
    approval_status
FROM management_drawings 
WHERE is_active = true 
ORDER BY process_name, year_month, drawing_type;

