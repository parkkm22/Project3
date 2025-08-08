import streamlit as st
from main import supabase_client, init_supabase, extract_cell_data_from_excel, get_previous_day_data
from datetime import datetime
import io

def test_supabase_save():
    """Supabase 저장 기능을 테스트합니다."""
    print("=== Supabase 저장 테스트 ===")
    
    # 1. Supabase 클라이언트 확인
    print(f"1. Supabase 클라이언트: {supabase_client}")
    
    if not supabase_client:
        print("❌ Supabase 클라이언트가 None입니다.")
        return False
    
    try:
        # 2. daily_report_data 테이블 존재 확인
        print("2. daily_report_data 테이블 확인 중...")
        result = supabase_client.table("daily_report_data").select("id").limit(1).execute()
        print(f"   테이블 존재: {result is not None}")
        print(f"   결과: {result}")
        
        # 3. 테스트 데이터 생성
        print("3. 테스트 데이터 생성 중...")
        test_data = {
            "date": "2025-07-21",
            "construction_data": {
                "본선터널(1구간)": {"누계": 100},
                "본선터널(2구간)": {"누계": 200}
            },
            "personnel_data": {
                "터널공": {"전일까지": 50, "금일": 10, "누계": 60},
                "목공": {"전일까지": 20, "금일": 5, "누계": 25}
            },
            "equipment_data": {
                "B/H(1.0LC)": {"전일까지": 5, "금일": 2, "누계": 7},
                "덤프트럭(5T)": {"전일까지": 3, "금일": 1, "누계": 4}
            }
        }
        
        # 4. 테스트 데이터 삽입
        print("4. 테스트 데이터 삽입 중...")
        try:
            insert_result = supabase_client.table("daily_report_data").insert(test_data).execute()
            print(f"   삽입 성공: {insert_result}")
            
            # 5. 삽입된 데이터 확인
            print("5. 삽입된 데이터 확인 중...")
            check_result = supabase_client.table("daily_report_data").select("*").eq("date", "2025-07-21").execute()
            print(f"   확인 결과: {check_result}")
            
            # 6. 전일 데이터 조회 테스트
            print("6. 전일 데이터 조회 테스트...")
            previous_data = get_previous_day_data("2025-07-22")
            print(f"   전일 데이터 조회 결과: {previous_data}")
            
            return True
            
        except Exception as e:
            print(f"   삽입 실패: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_supabase_save() 