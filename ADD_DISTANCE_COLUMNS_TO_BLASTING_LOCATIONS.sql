-- 기존 blasting_locations 테이블에 distance_3d 열만 추가
-- 이 SQL을 Supabase SQL Editor에서 실행하세요

-- 1. distance_3d 열만 추가
ALTER TABLE blasting_locations 
ADD COLUMN IF NOT EXISTS distance_3d DECIMAL(15, 3);

-- 2. 테이블 구조 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'blasting_locations' 
ORDER BY ordinal_position;

-- 3. 샘플 데이터 확인
SELECT 
    id,
    location_id,
    sta,
    coordinates_x,
    coordinates_y,
    depth,
    distance_3d
FROM blasting_locations 
LIMIT 5;
