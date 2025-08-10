-- daily_report_data 테이블 생성 (특정 셀 데이터 저장용)
CREATE TABLE IF NOT EXISTS daily_report_data (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,  -- UNIQUE 제약 조건 추가
    construction_data JSONB DEFAULT '{}',
    personnel_data JSONB DEFAULT '{}',
    equipment_data JSONB DEFAULT '{}',
    work_content_data JSONB DEFAULT '{}',  -- 작업내용 데이터 컬럼 추가
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_daily_report_data_date ON daily_report_data(date);

-- 업데이트 트리거 함수 생성
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 트리거 생성
DROP TRIGGER IF EXISTS update_daily_report_data_updated_at ON daily_report_data;
CREATE TRIGGER update_daily_report_data_updated_at
    BEFORE UPDATE ON daily_report_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 댓글 추가
COMMENT ON TABLE daily_report_data IS '일일 작업보고 특정 셀 데이터 저장 테이블';
COMMENT ON COLUMN daily_report_data.date IS '작업일자 (UNIQUE)';
COMMENT ON COLUMN daily_report_data.construction_data IS '시공현황 데이터 (A11~43, T11~43)';
COMMENT ON COLUMN daily_report_data.personnel_data IS '인원 데이터 (A66~87, L66~87, N66~87, Y66~87)';
COMMENT ON COLUMN daily_report_data.equipment_data IS '장비 데이터 (A91~119, L91~119, N91~119, Y91~119)';
COMMENT ON COLUMN daily_report_data.work_content_data IS '작업내용 데이터 (1단계 AI 추출 결과)'; 