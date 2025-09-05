-- Supabase blasting_locations 테이블에 거리계산 열 추가
-- 이 SQL을 Supabase SQL Editor에서 실행하세요

-- 1. 거리계산 관련 열들 추가
ALTER TABLE blasting_locations 
ADD COLUMN IF NOT EXISTS measurement_sta VARCHAR(50),
ADD COLUMN IF NOT EXISTS horizontal_distance DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS vertical_distance DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS distance_3d DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS distance_unit VARCHAR(10) DEFAULT 'm',
ADD COLUMN IF NOT EXISTS distance_calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS distance_calculation_status VARCHAR(20) DEFAULT 'pending';

-- 2. 계측위치와의 연결 상태 열 추가
ALTER TABLE blasting_locations 
ADD COLUMN IF NOT EXISTS measurement_connected BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS measurement_connection_date TIMESTAMP WITH TIME ZONE;

-- 3. 거리계산 상태를 위한 인덱스 추가 (성능 향상)
CREATE INDEX IF NOT EXISTS idx_blasting_locations_distance_status 
ON blasting_locations(distance_calculation_status);

CREATE INDEX IF NOT EXISTS idx_blasting_locations_measurement_connected 
ON blasting_locations(measurement_connected);

-- 4. 기존 데이터에 대한 거리계산 상태 업데이트
UPDATE blasting_locations 
SET distance_calculation_status = 'pending' 
WHERE distance_calculation_status IS NULL;

-- 5. 테이블 구조 확인을 위한 뷰 생성
CREATE OR REPLACE VIEW blasting_locations_with_distance AS
SELECT 
    *,
    CASE 
        WHEN horizontal_distance IS NOT NULL THEN 
            CONCAT(horizontal_distance::TEXT, ' ', distance_unit)
        ELSE '계산 대기중'
    END as distance_display,
    CASE 
        WHEN measurement_connected THEN '연결됨'
        ELSE '미연결'
    END as connection_status
FROM blasting_locations
ORDER BY created_at DESC;

-- 6. 거리계산 함수 생성 (PostgreSQL)
CREATE OR REPLACE FUNCTION calculate_distance_between_points(
    x1 DECIMAL, y1 DECIMAL, z1 DECIMAL,
    x2 DECIMAL, y2 DECIMAL, z2 DECIMAL
) RETURNS DECIMAL AS $$
BEGIN
    -- 3D 거리 계산 (피타고라스 정리)
    RETURN SQRT(POWER(x2 - x1, 2) + POWER(y2 - y1, 2) + POWER(z2 - z1, 2));
END;
$$ LANGUAGE plpgsql;

-- 7. 거리 자동 업데이트를 위한 트리거 함수
CREATE OR REPLACE FUNCTION update_distance_calculation()
RETURNS TRIGGER AS $$
BEGIN
    -- 새로운 발파위치가 추가되거나 업데이트될 때 거리계산 상태를 pending으로 설정
    NEW.distance_calculation_status = 'pending';
    NEW.distance_calculated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 8. 트리거 생성
DROP TRIGGER IF EXISTS trigger_update_distance_calculation ON blasting_locations;
CREATE TRIGGER trigger_update_distance_calculation
    BEFORE INSERT OR UPDATE ON blasting_locations
    FOR EACH ROW
    EXECUTE FUNCTION update_distance_calculation();

-- 9. 테이블 구조 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'blasting_locations' 
ORDER BY ordinal_position;

-- 10. 샘플 데이터 확인
SELECT 
    location_id,
    sta,
    coordinates_x,
    coordinates_y,
    depth,
    measurement_sta,
    horizontal_distance,
    distance_3d,
    measurement_connected,
    distance_calculation_status
FROM blasting_locations 
LIMIT 5;

