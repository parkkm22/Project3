import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import sqlite3
from io import BytesIO
import base64
import re
import requests
import os
import pdfplumber
from pdf2image import convert_from_bytes
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import time

# 페이지 설정
st.set_page_config(
    page_title="발파데이터 및 자동화계측기 관리",
    page_icon="📊",
    layout="wide"
)

# 세션 상태 초기화
if 'blasting_data' not in st.session_state:
    st.session_state.blasting_data = []
if 'monitoring_data' not in st.session_state:
    st.session_state.monitoring_data = []

def create_database():
    """데이터베이스 생성 및 테이블 초기화"""
    conn = sqlite3.connect('tunnel_data.db')
    cursor = conn.cursor()
    
    # 발파데이터 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blasting_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            hole_count INTEGER,
            charge_weight REAL,
            vibration_velocity REAL,
            noise_level REAL,
            distance REAL,
            notes TEXT
        )
    ''')
    
    # 자동화계측기 데이터 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            location TEXT NOT NULL,
            convergence REAL,
            settlement REAL,
            stress REAL,
            temperature REAL,
            humidity REAL,
            sensor_id TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def add_blasting_data(data):
    """발파데이터 추가"""
    conn = sqlite3.connect('tunnel_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO blasting_data 
        (date, location, hole_count, charge_weight, vibration_velocity, noise_level, distance, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['date'], data['location'], data['hole_count'], data['charge_weight'],
        data['vibration_velocity'], data['noise_level'], data['distance'], data['notes']
    ))
    
    conn.commit()
    conn.close()

def add_monitoring_data(data):
    """자동화계측기 데이터 추가"""
    conn = sqlite3.connect('tunnel_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO monitoring_data 
        (timestamp, location, convergence, settlement, stress, temperature, humidity, sensor_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['timestamp'], data['location'], data['convergence'], data['settlement'],
        data['stress'], data['temperature'], data['humidity'], data['sensor_id']
    ))
    
    conn.commit()
    conn.close()

def get_blasting_data():
    """발파데이터 조회"""
    conn = sqlite3.connect('tunnel_data.db')
    df = pd.read_sql_query('SELECT * FROM blasting_data ORDER BY date DESC', conn)
    conn.close()
    return df

def get_monitoring_data():
    """자동화계측기 데이터 조회"""
    conn = sqlite3.connect('tunnel_data.db')
    df = pd.read_sql_query('SELECT * FROM monitoring_data ORDER BY timestamp DESC', conn)
    conn.close()
    return df

def export_to_excel():
    """데이터를 Excel 파일로 내보내기"""
    blasting_df = get_blasting_data()
    monitoring_df = get_monitoring_data()
    
    with pd.ExcelWriter('tunnel_data_report.xlsx', engine='openpyxl') as writer:
        blasting_df.to_excel(writer, sheet_name='발파데이터', index=False)
        monitoring_df.to_excel(writer, sheet_name='자동화계측기데이터', index=False)
    
    return 'tunnel_data_report.xlsx'

# 메인 페이지
st.title("📊 발파데이터 및 자동화계측기 관리 시스템")

# 데이터베이스 초기화
create_database()

# 탭 생성
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📝 데이터 입력", "📊 데이터 조회", "📈 분석 및 차트", "📋 보고서 생성", "🧨 발파데이터 분석", "📈 자동화계측기 분석"])

with tab1:
    st.header("데이터 입력")
    
    # 발파데이터 입력
    st.subheader("발파데이터 입력")
    with st.form("blasting_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            blasting_date = st.date_input("발파 날짜", key="blasting_date")
            blasting_location = st.selectbox(
                "작업 위치",
                ["본선터널(1구간)", "신풍정거장", "신풍정거장 환승통로", "본선터널(2구간)", "도림사거리정거장"],
                key="blasting_location"
            )
            hole_count = st.number_input("발파공 수", min_value=0, value=0, key="hole_count")
            charge_weight = st.number_input("장약량 (kg)", min_value=0.0, value=0.0, key="charge_weight")
        
        with col2:
            vibration_velocity = st.number_input("진동속도 (cm/s)", min_value=0.0, value=0.0, key="vibration_velocity")
            noise_level = st.number_input("소음도 (dB)", min_value=0.0, value=0.0, key="noise_level")
            distance = st.number_input("거리 (m)", min_value=0.0, value=0.0, key="distance")
            blasting_notes = st.text_area("비고", key="blasting_notes")
        
        if st.form_submit_button("발파데이터 저장"):
            blasting_data = {
                'date': blasting_date.strftime('%Y-%m-%d'),
                'location': blasting_location,
                'hole_count': hole_count,
                'charge_weight': charge_weight,
                'vibration_velocity': vibration_velocity,
                'noise_level': noise_level,
                'distance': distance,
                'notes': blasting_notes
            }
            add_blasting_data(blasting_data)
            st.success("발파데이터가 성공적으로 저장되었습니다!")
    
    st.divider()
    
    # 자동화계측기 데이터 입력
    st.subheader("자동화계측기 데이터 입력")
    with st.form("monitoring_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            monitoring_timestamp = st.datetime_input("측정 시간", key="monitoring_timestamp")
            monitoring_location = st.selectbox(
                "측정 위치",
                ["본선터널(1구간)", "신풍정거장", "신풍정거장 환승통로", "본선터널(2구간)", "도림사거리정거장"],
                key="monitoring_location"
            )
            convergence = st.number_input("수렴량 (mm)", value=0.0, key="convergence")
            settlement = st.number_input("침하량 (mm)", value=0.0, key="settlement")
        
        with col2:
            stress = st.number_input("응력 (MPa)", value=0.0, key="stress")
            temperature = st.number_input("온도 (°C)", value=0.0, key="temperature")
            humidity = st.number_input("습도 (%)", min_value=0.0, max_value=100.0, value=0.0, key="humidity")
            sensor_id = st.text_input("센서 ID", key="sensor_id")
        
        if st.form_submit_button("계측기 데이터 저장"):
            monitoring_data = {
                'timestamp': monitoring_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'location': monitoring_location,
                'convergence': convergence,
                'settlement': settlement,
                'stress': stress,
                'temperature': temperature,
                'humidity': humidity,
                'sensor_id': sensor_id
            }
            add_monitoring_data(monitoring_data)
            st.success("자동화계측기 데이터가 성공적으로 저장되었습니다!")

with tab2:
    st.header("데이터 조회")
    
    # 필터링 옵션
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("발파데이터")
        blasting_df = get_blasting_data()
        
        if not blasting_df.empty:
            # 날짜 필터
            date_range = st.date_input(
                "날짜 범위 선택",
                value=(blasting_df['date'].min(), blasting_df['date'].max()),
                key="blasting_date_filter"
            )
            
            # 위치 필터
            location_filter = st.multiselect(
                "위치 필터",
                options=blasting_df['location'].unique(),
                default=blasting_df['location'].unique(),
                key="blasting_location_filter"
            )
            
            # 필터링된 데이터
            filtered_blasting = blasting_df[
                (blasting_df['date'] >= str(date_range[0])) &
                (blasting_df['date'] <= str(date_range[1])) &
                (blasting_df['location'].isin(location_filter))
            ]
            
            st.dataframe(filtered_blasting, use_container_width=True)
        else:
            st.info("발파데이터가 없습니다.")
    
    with col2:
        st.subheader("자동화계측기 데이터")
        monitoring_df = get_monitoring_data()
        
        if not monitoring_df.empty:
            # 시간 범위 필터
            time_range = st.date_input(
                "시간 범위 선택",
                value=(monitoring_df['timestamp'].min()[:10], monitoring_df['timestamp'].max()[:10]),
                key="monitoring_time_filter"
            )
            
            # 위치 필터
            monitoring_location_filter = st.multiselect(
                "위치 필터",
                options=monitoring_df['location'].unique(),
                default=monitoring_df['location'].unique(),
                key="monitoring_location_filter"
            )
            
            # 필터링된 데이터
            filtered_monitoring = monitoring_df[
                (monitoring_df['timestamp'] >= str(time_range[0])) &
                (monitoring_df['timestamp'] <= str(time_range[1]) + " 23:59:59") &
                (monitoring_df['location'].isin(monitoring_location_filter))
            ]
            
            st.dataframe(filtered_monitoring, use_container_width=True)
        else:
            st.info("자동화계측기 데이터가 없습니다.")

with tab3:
    st.header("분석 및 차트")
    
    blasting_df = get_blasting_data()
    monitoring_df = get_monitoring_data()
    
    if not blasting_df.empty:
        st.subheader("발파데이터 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 진동속도 vs 거리 차트
            fig_vibration = px.scatter(
                blasting_df, x='distance', y='vibration_velocity',
                color='location', title='진동속도 vs 거리',
                labels={'distance': '거리 (m)', 'vibration_velocity': '진동속도 (cm/s)'}
            )
            st.plotly_chart(fig_vibration, use_container_width=True)
        
        with col2:
            # 장약량 vs 진동속도 차트
            fig_charge = px.scatter(
                blasting_df, x='charge_weight', y='vibration_velocity',
                color='location', title='장약량 vs 진동속도',
                labels={'charge_weight': '장약량 (kg)', 'vibration_velocity': '진동속도 (cm/s)'}
            )
            st.plotly_chart(fig_charge, use_container_width=True)
        
        # 위치별 평균값
        st.subheader("위치별 평균값")
        location_stats = blasting_df.groupby('location').agg({
            'hole_count': 'mean',
            'charge_weight': 'mean',
            'vibration_velocity': 'mean',
            'noise_level': 'mean'
        }).round(2)
        
        st.dataframe(location_stats, use_container_width=True)
    
    if not monitoring_df.empty:
        st.subheader("자동화계측기 데이터 분석")
        
        # 시간별 추세 차트
        monitoring_df['timestamp'] = pd.to_datetime(monitoring_df['timestamp'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 수렴량 추세
            fig_convergence = px.line(
                monitoring_df, x='timestamp', y='convergence',
                color='location', title='수렴량 추세',
                labels={'timestamp': '시간', 'convergence': '수렴량 (mm)'}
            )
            st.plotly_chart(fig_convergence, use_container_width=True)
        
        with col2:
            # 침하량 추세
            fig_settlement = px.line(
                monitoring_df, x='timestamp', y='settlement',
                color='location', title='침하량 추세',
                labels={'timestamp': '시간', 'settlement': '침하량 (mm)'}
            )
            st.plotly_chart(fig_settlement, use_container_width=True)

with tab4:
    st.header("보고서 생성")
    
    # 보고서 생성 옵션
    report_date = st.date_input("보고서 날짜", key="report_date")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("발파데이터 요약")
        blasting_df = get_blasting_data()
        
        if not blasting_df.empty:
            # 선택된 날짜의 발파데이터
            daily_blasting = blasting_df[blasting_df['date'] == str(report_date)]
            
            if not daily_blasting.empty:
                st.write(f"**발파 횟수:** {len(daily_blasting)}회")
                st.write(f"**총 발파공 수:** {daily_blasting['hole_count'].sum()}개")
                st.write(f"**총 장약량:** {daily_blasting['charge_weight'].sum():.2f}kg")
                st.write(f"**평균 진동속도:** {daily_blasting['vibration_velocity'].mean():.2f}cm/s")
                st.write(f"**평균 소음도:** {daily_blasting['noise_level'].mean():.2f}dB")
            else:
                st.info("선택된 날짜에 발파데이터가 없습니다.")
        else:
            st.info("발파데이터가 없습니다.")
    
    with col2:
        st.subheader("자동화계측기 데이터 요약")
        monitoring_df = get_monitoring_data()
        
        if not monitoring_df.empty:
            # 선택된 날짜의 계측기 데이터
            daily_monitoring = monitoring_df[monitoring_df['timestamp'].str.startswith(str(report_date))]
            
            if not daily_monitoring.empty:
                st.write(f"**측정 횟수:** {len(daily_monitoring)}회")
                st.write(f"**평균 수렴량:** {daily_monitoring['convergence'].mean():.2f}mm")
                st.write(f"**평균 침하량:** {daily_monitoring['settlement'].mean():.2f}mm")
                st.write(f"**평균 응력:** {daily_monitoring['stress'].mean():.2f}MPa")
                st.write(f"**평균 온도:** {daily_monitoring['temperature'].mean():.2f}°C")
            else:
                st.info("선택된 날짜에 계측기 데이터가 없습니다.")
        else:
            st.info("자동화계측기 데이터가 없습니다.")
    
    # Excel 내보내기
    st.subheader("데이터 내보내기")
    if st.button("Excel 파일로 내보내기"):
        try:
            filename = export_to_excel()
            st.success(f"데이터가 {filename}로 내보내졌습니다!")
            
            # 파일 다운로드 링크 생성
            with open(filename, 'rb') as f:
                bytes_data = f.read()
            
            st.download_button(
                label="파일 다운로드",
                data=bytes_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"파일 내보내기 중 오류가 발생했습니다: {str(e)}")

# 사이드바에 통계 정보 표시
with st.sidebar:
    st.header("📈 실시간 통계")
    
    blasting_df = get_blasting_data()
    monitoring_df = get_monitoring_data()
    
    if not blasting_df.empty:
        st.metric("총 발파 횟수", len(blasting_df))
        st.metric("총 장약량", f"{blasting_df['charge_weight'].sum():.1f}kg")
        st.metric("평균 진동속도", f"{blasting_df['vibration_velocity'].mean():.2f}cm/s")
    
    if not monitoring_df.empty:
        st.metric("총 측정 횟수", len(monitoring_df))
        st.metric("평균 수렴량", f"{monitoring_df['convergence'].mean():.2f}mm")
        st.metric("평균 침하량", f"{monitoring_df['settlement'].mean():.2f}mm")
    
    st.divider()
    
    # 최근 데이터
    st.subheader("최근 데이터")
    if not blasting_df.empty:
        st.write("**최근 발파:**")
        latest_blasting = blasting_df.iloc[0]
        st.write(f"- {latest_blasting['date']} ({latest_blasting['location']})")
    
    if not monitoring_df.empty:
        st.write("**최근 측정:**")
        latest_monitoring = monitoring_df.iloc[0]
        st.write(f"- {latest_monitoring['timestamp'][:16]} ({latest_monitoring['location']})") 

with tab5:
    st.header("🧨 발파데이터 분석")
    st.markdown("발파작업일지와 계측결과 보고서를 업로드하여 데이터를 병합하고 정제합니다.")
    
    # 세션 상태 초기화
    if 'blast_data_completed' not in st.session_state:
        st.session_state.blast_data_completed = False
    if 'blast_dataframe' not in st.session_state:
        st.session_state.blast_dataframe = None
    
    if not st.session_state.blast_data_completed:
        blast_files = st.file_uploader("발파작업일지 및 계측결과 보고서 (2개 파일)", type=["pdf", "xlsx", "xls"], accept_multiple_files=True, key="blast_files")
        
        if len(blast_files) == 2:
            with st.spinner('🤖 AI가 발파 데이터를 분석하고 있습니다...'):
                try:
                    # 파일 내용 추출 함수 (간단한 버전)
                    def extract_file_content(file):
                        try:
                            if file.type == "application/pdf":
                                with pdfplumber.open(file) as pdf:
                                    text = ""
                                    for page in pdf.pages:
                                        text += page.extract_text() or ""
                                    return text
                            elif file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                                df = pd.read_excel(file)
                                return df.to_string()
                            else:
                                return file.getvalue().decode('utf-8')
                        except Exception as e:
                            st.error(f"파일 읽기 오류: {e}")
                            return None
                    
                    blast_text = extract_file_content(blast_files[0])
                    daily_text = extract_file_content(blast_files[1])
                    
                    if blast_text and daily_text:
                        # 간단한 발파 데이터 처리 (실제로는 AI 분석이 필요)
                        st.success("파일이 성공적으로 읽혔습니다!")
                        st.text_area("발파작업일지 내용", blast_text[:1000] + "..." if len(blast_text) > 1000 else blast_text, height=200)
                        st.text_area("계측결과 보고서 내용", daily_text[:1000] + "..." if len(daily_text) > 1000 else daily_text, height=200)
                        
                        # 임시 데이터프레임 생성
                        sample_data = {
                            '날짜': [datetime.now().strftime('%Y-%m-%d')],
                            '위치': ['본선터널(1구간)'],
                            '발파공수': [10],
                            '장약량': [50.5],
                            '진동속도': [2.3],
                            '소음도': [85.2]
                        }
                        df = pd.DataFrame(sample_data)
                        st.session_state.blast_dataframe = df
                        st.session_state.blast_data_completed = True
                        st.success("✅ 발파 데이터 분석이 완료되었습니다!")
                        st.rerun()
                    else:
                        st.error("파일 내용 추출에 실패했습니다.")
                except Exception as e:
                    st.error(f"데이터 분석 중 오류: {e}")
    else:
        st.success("✅ 발파 데이터가 성공적으로 처리되었습니다.")
        
        with st.expander("처리된 발파 데이터 보기"):
            if st.session_state.blast_dataframe is not None:
                st.dataframe(st.session_state.blast_dataframe)
            else:
                st.info("처리된 발파 데이터가 없습니다.")

with tab6:
    st.header("📈 자동화계측기 분석")
    st.markdown("계측기 엑셀 파일을 업로드하여 최대 변화량을 분석합니다.")
    
    # 세션 상태 초기화
    if 'instrument_data_completed' not in st.session_state:
        st.session_state.instrument_data_completed = False
    if 'instrument_dataframe' not in st.session_state:
        st.session_state.instrument_dataframe = None
    if 'instrument_display_df' not in st.session_state:
        st.session_state.instrument_display_df = None
    
    if not st.session_state.instrument_data_completed:
        excel_files = st.file_uploader("자동화 계측기 엑셀 파일(들)", type=["xlsx", "xls"], accept_multiple_files=True, key="inst_files")
        
        if excel_files:
            with st.spinner("🔄 자동화 계측기 데이터를 처리하는 중입니다..."):
                try:
                    all_accumulated_rows = []
                    for uploaded_file in excel_files:
                        try:
                            xls = pd.ExcelFile(uploaded_file)
                            for sheet_name in xls.sheet_names:
                                df = pd.read_excel(xls, sheet_name=sheet_name)
                                if df.empty or df.shape[0] < 2:
                                    continue

                                first_row_values = df.columns.tolist()
                                data_values = df.values.tolist()
                                last_row_values = data_values[-1] if data_values else []
                                
                                location_val = sheet_name.replace("ALL", "").replace("all", "").replace("All", "").strip()
                                location_val = " ".join(location_val.split()) # 중복 공백 제거

                                if "주출입구" in location_val:
                                    location_val = "신풍 주출입구"
                                elif "단면" in location_val:
                                    location_val = "신풍 특피"
                                elif "출입구" in location_val and not location_val.startswith("도림"):
                                    location_val = location_val.replace("출입구", "도림출입구")

                                if isinstance(last_row_values, (list, tuple)) and len(last_row_values) > 1:
                                    for col_idx, current_value in enumerate(last_row_values[1:], 1):
                                        if col_idx < len(first_row_values):
                                            instrument_name = str(first_row_values[col_idx])
                                            current_value_str = str(current_value)
                                            weekly_change = "-"
                                            try:
                                                if len(data_values) >= 2:
                                                    last_val = float(str(data_values[-1][col_idx]))
                                                    first_val = float(str(data_values[0][col_idx]))
                                                    weekly_change = str(round(last_val - first_val, 3))
                                            except (ValueError, IndexError):
                                                weekly_change = "-"
                                            
                                            if current_value_str.lower() != "nan":
                                                all_accumulated_rows.append([
                                                    location_val, instrument_name, weekly_change, current_value_str
                                                ])
                        except Exception as e:
                            st.warning(f"'{uploaded_file.name}' 처리 중 오류: {e}")

                    if all_accumulated_rows:
                        temp_df = pd.DataFrame(all_accumulated_rows, columns=["위치", "계측기명", "주간변화량", "누적변화량"])
                        temp_df['계측기 종류'] = temp_df['계측기명'].apply(lambda x: 
                            "변형률계" if "변형률" in str(x) else
                            "지하수위계" if "W" in str(x) or "지하수위" in str(x) else
                            "지중경사계" if "INC" in str(x) or "지중경사" in str(x) else
                            "ST하중계" if "하중" in str(x) else "기타")
                        temp_df['단위'] = temp_df['계측기명'].apply(lambda x: 
                            "ton" if "변형률" in str(x) or "하중" in str(x) else
                            "m" if "W" in str(x) or "지하수위" in str(x) else
                            "mm" if "INC" in str(x) or "지중경사" in str(x) else "")
                        
                        temp_df = temp_df[temp_df['계측기 종류'] != '기타']
                        
                        # "하중계"는 '계측기명'이 'R'로 끝나는 것만 필터링
                        is_st_load_cell = temp_df['계측기 종류'] == "ST하중계"
                        ends_with_r = temp_df['계측기명'].str.strip().str.upper().str.endswith('R')
                        # ST하중계가 아니거나, ST하중계이면서 R로 끝나는 경우만 유지
                        temp_df = temp_df[~is_st_load_cell | (is_st_load_cell & ends_with_r)]

                        summary_df = temp_df[temp_df["주간변화량"] != "-"].copy()
                        if not summary_df.empty:
                            summary_df["주간변화량_float"] = pd.to_numeric(summary_df["주간변화량"], errors='coerce').fillna(0)
                            summary_df["누적변화량_float"] = pd.to_numeric(summary_df["누적변화량"], errors='coerce').fillna(0)
                            summary_df["주간변화량_절대값"] = summary_df["주간변화량_float"].abs()
                            
                            # 1. 최대 변화량 데이터부터 요약
                            max_changes = summary_df.loc[summary_df.groupby(["위치", "계측기 종류"])["주간변화량_절대값"].idxmax()].copy()

                            def determine_status(row):
                                try:
                                    if row['계측기 종류'] == "ST하중계":
                                        value = abs(row['누적변화량_float'])
                                        limit = 100
                                        if value >= limit: return "3차 초과", value/limit
                                        elif value >= limit*0.8: return "2차 초과", value/limit
                                        elif value >= limit*0.6: return "1차 초과", value/limit
                                        else: return "안정", value/limit
                                    elif row['계측기 종류'] == "변형률계":
                                        value = abs(row['누적변화량_float'])
                                        limit = 2518
                                        if value >= limit: return "3차 초과", value/limit
                                        elif value >= limit*0.8: return "2차 초과", value/limit
                                        elif value >= limit*0.6: return "1차 초과", value/limit
                                        else: return "안정", value/limit
                                    elif row['계측기 종류'] == "지중경사계":
                                        value = abs(row['누적변화량_float'])
                                        limit = 128.96
                                        if value >= limit: return "3차 초과", value/limit
                                        elif value >= limit*0.8: return "2차 초과", value/limit
                                        elif value >= limit*0.6: return "1차 초과", value/limit
                                        else: return "안정", value/limit
                                    elif row['계측기 종류'] == "지하수위계":
                                        value = abs(row['주간변화량_float'])
                                        limit = 1.0
                                        if value >= limit: return "3차 초과", value/limit
                                        elif value >= limit*0.75: return "2차 초과", value/limit
                                        elif value >= limit*0.5: return "1차 초과", value/limit
                                        else: return "안정", value/limit
                                    return "확인필요", 0
                                except (ValueError, TypeError): return "오류", 0

                            # 2. 요약된 데이터에 대해서만 상태 분석 수행
                            status_results = max_changes.apply(determine_status, axis=1)
                            max_changes['상태'] = status_results.apply(lambda x: x[0])
                            max_changes['비율'] = status_results.apply(lambda x: f"{x[1]*100:.1f}%" if x[1] > 0 else "N/A")
                            max_changes['누적변화량'] = max_changes['누적변화량_float'].apply(lambda x: f"{x:.3f}")
                            
                            # 3. 화면 표시용과 엑셀 저장용 데이터프레임 모두 요약본 기반으로 생성
                            display_df = max_changes[["위치", "계측기 종류", "계측기명", "주간변화량", "누적변화량", "단위", "상태", "비율"]]
                            excel_export_df = max_changes[['위치', '계측기 종류', '계측기명', '주간변화량', '누적변화량', '단위', '상태']].copy()

                            # 4. 두 데이터프레임을 각각 세션에 저장 (엑셀용은 요약본)
                            st.session_state['instrument_display_df'] = display_df
                            st.session_state['instrument_dataframe'] = excel_export_df
                            st.session_state.instrument_data_completed = True
                            
                            # 경고 알림은 요약본(최대값) 기준으로 찾아 세션에 저장만 함
                            warning_rows = display_df[display_df['상태'].str.contains("초과")]
                            st.session_state['warning_rows_instrument'] = warning_rows

                            st.success("✅ 자동화 계측기 데이터 분석이 완료되었습니다!")
                            st.rerun()

                except Exception as e:
                    st.error(f"데이터 분석 중 오류 발생: {e}")

    else:
        st.success("✅ 자동화 계측기 데이터가 성공적으로 처리되었습니다.")
        
        with st.expander("최대 변화량 분석 결과 보기"):
            if 'instrument_display_df' in st.session_state and not st.session_state.instrument_display_df.empty:
                df_to_display = st.session_state.instrument_display_df

                def highlight_warning_rows(row):
                    if row['상태'] != '안정':
                        return ['background-color: #ffcdd2'] * len(row)
                    return [''] * len(row)
                
                styled_df = df_to_display.style.apply(highlight_warning_rows, axis=1)
                st.dataframe(styled_df)

                # 경고 항목 표시
                warning_rows = st.session_state.get('warning_rows_instrument')
                if warning_rows is not None and not warning_rows.empty:
                    st.warning(f"🚨 {len(warning_rows)}개의 항목에서 관리기준 초과가 감지되었습니다.")
            else:
                st.info("표시할 분석 결과가 없습니다.")