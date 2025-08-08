import streamlit as st
from main import supabase_client, init_supabase, get_previous_day_data, extract_cell_data_from_excel
from datetime import datetime, timedelta

def test_supabase_connection():
    """Supabase 연결과 테이블 상태를 테스트합니다."""
    print("=== Supabase 연결 테스트 ===")
    
    # 1. Supabase 클라이언트 확인
    print(f"1. Supabase 클라이언트: {supabase_client}")
    
    if supabase_client:
        try:
            # 2. daily_report_data 테이블 존재 확인
            print("2. daily_report_data 테이블 확인 중...")
            result = supabase_client.table("daily_report_data").select("id").limit(1).execute()
            print(f"   테이블 존재: {result is not None}")
            print(f"   결과: {result}")
            
            # 3. 테이블 구조 확인
            print("3. 테이블 구조 확인 중...")
            try:
                # 간단한 쿼리로 테이블 구조 확인
                test_result = supabase_client.table("daily_report_data").select("*").limit(1).execute()
                print(f"   테이블 구조 확인 성공: {test_result}")
            except Exception as e:
                print(f"   테이블 구조 확인 실패: {e}")
            
            # 4. 테스트 데이터 삽입
            print("4. 테스트 데이터 삽입 중...")
            test_data = {
                "date": "2025-07-21",
                "construction_data": {"테스트": {"누계": 100}},
                "personnel_data": {"테스트": {"전일까지": 50, "금일": 10, "누계": 60}},
                "equipment_data": {"테스트": {"전일까지": 5, "금일": 2, "누계": 7}}
            }
            
            try:
                insert_result = supabase_client.table("daily_report_data").insert(test_data).execute()
                print(f"   테스트 데이터 삽입 성공: {insert_result}")
            except Exception as e:
                print(f"   테스트 데이터 삽입 실패: {e}")
            
            # 5. 전일 데이터 조회 테스트
            print("5. 전일 데이터 조회 테스트...")
            previous_data = get_previous_day_data("2025-07-22")
            print(f"   전일 데이터 조회 결과: {previous_data}")
            
            return True
            
        except Exception as e:
            print(f"연결 실패: {e}")
            return False
    else:
        print("Supabase 클라이언트가 None입니다.")
        return False

if __name__ == "__main__":
    test_supabase_connection() 