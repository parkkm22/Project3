-- 로컬 파일을 활용한 시공관리도 데이터 삽입
-- 실제 파일이 static 폴더에 저장되어 있음

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

-- 기존 데이터 삭제 (테스트용)
DELETE FROM management_drawings WHERE process_name = '도림사거리 정거장';

-- 로컬 파일을 활용한 데이터 삽입
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
-- 실제 로컬에 저장된 파일들
('도림사거리 정거장', '시공관리도', '2024-08', 'static/management-drawings/2024-08/20250818-도림사거리정거장_시공관리도.pdf', '20250818-도림사거리정거장 시공 관리도.pdf', 243710, '도림사거리 정거장 시공관리도 (2024년 8월)', 'admin', 'approved'),

-- 추가 샘플 데이터 (테스트용)
('도림사거리 정거장', '미들슬라브', '2024-01', 'static/management-drawings/2024-01/도림사거리_정거장_미들슬라브_202401.pdf', '도림사거리_정거장_미들슬라브_202401.pdf', 2048576, '도림사거리 정거장 미들슬라브 시공관리도 (2024년 1월)', 'admin', 'approved'),
('도림사거리 정거장', '상부슬라브', '2024-01', 'static/management-drawings/2024-01/도림사거리_정거장_상부슬라브_202401.pdf', '도림사거리_정거장_상부슬라브_202401.pdf', 1856432, '도림사거리 정거장 상부슬라브 시공관리도 (2024년 1월)', 'admin', 'approved'),
('도림사거리 정거장', '전체공정', '2024-01', 'static/management-drawings/2024-01/도림사거리_정거장_전체공정_202401.pdf', '도림사거리_정거장_전체공정_202401.pdf', 3145728, '도림사거리 정거장 전체 시공관리도 (2024년 1월)', 'admin', 'approved'),

-- 다른 공정들
('본선터널 1구간', '라이닝', '2024-01', 'static/management-drawings/2024-01/본선터널_1구간_라이닝_202401.pdf', '본선터널_1구간_라이닝_202401.pdf', 1500000, '본선터널 1구간 라이닝 시공관리도', 'admin', 'approved'),
('신풍 주출입구', '계측', '2024-01', 'static/management-drawings/2024-01/신풍_주출입구_계측_202401.pdf', '25년 4월 10일 계측결과.pdf', 1900000, '신풍 주출입구 계측 결과', 'admin', 'approved');

-- 데이터 확인
SELECT 
    process_name,
    drawing_type,
    year_month,
    file_name,
    file_size,
    file_path,
    description
FROM management_drawings 
WHERE is_active = true 
ORDER BY process_name, year_month, drawing_type;

