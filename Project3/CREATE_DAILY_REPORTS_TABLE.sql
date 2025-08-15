-- daily_reports 테이블 생성
CREATE TABLE IF NOT EXISTS daily_reports (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    project_name TEXT,
    construction_status JSONB,
    work_content JSONB,
    personnel JSONB,
    equipment JSONB,
    basic_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_reports(date);
CREATE INDEX IF NOT EXISTS idx_daily_reports_project ON daily_reports(project_name);

-- 댓글 추가
COMMENT ON TABLE daily_reports IS '일일 작업보고 데이터 저장 테이블';
COMMENT ON COLUMN daily_reports.date IS '작업일자';
COMMENT ON COLUMN daily_reports.project_name IS '공사명';
COMMENT ON COLUMN daily_reports.construction_status IS '시공현황 데이터 (JSON)';
COMMENT ON COLUMN daily_reports.work_content IS '작업내용 데이터 (JSON)';
COMMENT ON COLUMN daily_reports.personnel IS '인원 데이터 (JSON)';
COMMENT ON COLUMN daily_reports.equipment IS '장비 데이터 (JSON)';
COMMENT ON COLUMN daily_reports.basic_info IS '기본정보 데이터 (JSON)'; 