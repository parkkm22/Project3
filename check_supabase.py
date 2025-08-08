import streamlit as st
from main import supabase_client

def check_supabase():
    print("=== Supabase 연결 확인 ===")
    print(f"Supabase 클라이언트: {supabase_client}")
    
    if supabase_client:
        try:
            # 간단한 테스트 쿼리
            result = supabase_client.table("daily_reports").select("id").limit(1).execute()
            print(f"연결 성공! 테이블 접근 가능: {result}")
            return True
        except Exception as e:
            print(f"연결 실패: {e}")
            return False
    else:
        print("Supabase 클라이언트가 None입니다.")
        return False

if __name__ == "__main__":
    check_supabase() 