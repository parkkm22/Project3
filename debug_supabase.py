import streamlit as st
from main import supabase_client, init_supabase
from datetime import datetime

def debug_supabase():
    """Supabase 연결과 테이블 상태를 확인합니다."""
    
    print("=== Supabase 디버깅 시작 ===")
    
    # 1. Supabase 클라이언트 상태 확인
    print(f"1. Supabase 클라이언트 상태: {supabase_client is not None}")
    
    if supabase_client:
        try:
            # 2. daily_reports 테이블 존재 확인
            print("2. daily_reports 테이블 확인 중...")
            result = supabase_client.table("daily_reports").select("id").limit(1).execute()
            print(f"   테이블 존재: {result is not None}")
            print(f"   결과: {result}")
            
            # 3. 테이블 구조 확인
            print("3. 테이블 구조 확인 중...")
            try:
                # 간단한 쿼리로 테이블 구조 확인
                test_result = supabase_client.table("daily_reports").select("*").limit(1).execute()
                print(f"   테이블 구조 확인 성공: {test_result}")
            except Exception as e:
                print(f"   테이블 구조 확인 실패: {e}")
            
            # 4. 테스트 데이터 삽입
            print("4. 테스트 데이터 삽입 시도...")
            try:
                test_data = {
                    "date": "2025-01-01",
                    "project_name": "테스트 프로젝트",
                    "construction_status": {"test": "data"},
                    "work_content": {"test": "data"},
                    "personnel": {"test": "data"},
                    "equipment": {"test": "data"},
                    "basic_info": {"test": "data"},
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                insert_result = supabase_client.table("daily_reports").insert(test_data).execute()
                print(f"   테스트 데이터 삽입 성공: {insert_result}")
                
                # 5. 삽입된 데이터 확인
                print("5. 삽입된 데이터 확인...")
                check_result = supabase_client.table("daily_reports").select("*").eq("date", "2025-01-01").execute()
                print(f"   확인 결과: {check_result}")
                
            except Exception as e:
                print(f"   테스트 데이터 삽입 실패: {e}")
                
        except Exception as e:
            print(f"   테이블 확인 중 오류: {e}")
    else:
        print("   Supabase 클라이언트가 None입니다.")
    
    print("=== Supabase 디버깅 완료 ===")

if __name__ == "__main__":
    debug_supabase() 