import streamlit as st
import folium
from streamlit_folium import st_folium
import ezdxf
from pyproj import Geod, Transformer
import io
import os
import json
import base64

# 페이지 설정
st.set_page_config(
    page_title="GIS/CAD 뷰어",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목
st.markdown("---")

# 사이드바에 DXF 파일 업로드 추가
st.sidebar.header("📁 DXF 파일 업로드")
uploaded_file = st.sidebar.file_uploader("DXF 파일을 선택하세요", type=['dxf'], key="dxf_uploader")

if uploaded_file is not None:
    # DXF 파일 처리
    try:
        # 파일 내용을 바이트로 읽기
        file_content = uploaded_file.read()
        
        # ezdxf로 DXF 파일 파싱
        doc = ezdxf.read(io.BytesIO(file_content))
        
        # 엔티티 정보 추출
        entities_data = []
        for entity in doc.entitydb.values():
            if hasattr(entity, 'dxftype'):
                entity_info = {
                    'type': entity.dxftype(),
                    'layer': getattr(entity, 'layer', '0'),
                    'color': getattr(entity, 'color', 7),  # 7은 흰색
                    'coordinates': []
                }
                
                # 엔티티 타입별로 좌표 추출
                if entity.dxftype() == 'LINE':
                    if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        entity_info['coordinates'] = [
                            {'x': entity.dxf.start.x, 'y': entity.dxf.start.y},
                            {'x': entity.dxf.end.x, 'y': entity.dxf.end.y}
                        ]
                elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                    if hasattr(entity, 'get_points'):
                        points = entity.get_points()
                        entity_info['coordinates'] = [{'x': p[0], 'y': p[1]} for p in points]
                elif entity.dxftype() == 'CIRCLE':
                    if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
                        entity_info['coordinates'] = [
                            {'x': entity.dxf.center.x, 'y': entity.dxf.center.y},
                            {'radius': entity.dxf.radius}
                        ]
                elif entity.dxftype() in ['TEXT', 'MTEXT']:
                    if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'insert'):
                        entity_info['coordinates'] = [{'x': entity.dxf.insert.x, 'y': entity.dxf.insert.y}]
                        entity_info['text'] = getattr(entity, 'text', getattr(entity, 'text_string', ''))
                
                if entity_info['coordinates']:
                    entities_data.append(entity_info)
        
        # 결과를 세션 상태에 저장
        st.session_state.dxf_data = {
            'entities': entities_data,
            'filename': uploaded_file.name
        }
        
        st.sidebar.success(f"✅ {uploaded_file.name} 파일 처리 완료!")
        st.sidebar.info(f"📊 총 {len(entities_data)}개 엔티티 발견")
        
        # 처리된 데이터 미리보기
        if st.sidebar.button("📋 데이터 미리보기"):
            st.sidebar.json(entities_data[:5])  # 처음 5개만 표시
        
    except Exception as e:
        st.sidebar.error(f"❌ DXF 파일 처리 실패: {str(e)}")
        st.session_state.dxf_data = None

# HTML 파일 읽기
def load_html_file():
    try:
        # 현재 파일이 pages 폴더 안에 있으므로 상위 폴더의 pages 폴더로 이동
        with open('pages/map.html', 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        try:
            # 상대 경로로 시도
            with open('../pages/map.html', 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            try:
                # 절대 경로로 시도
                current_dir = os.getcwd()
                map_path = os.path.join(current_dir, 'pages', 'map.html')
                with open(map_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except FileNotFoundError:
                st.error(f"map.html 파일을 찾을 수 없습니다. 현재 작업 디렉토리: {os.getcwd()}")
                st.error(f"시도한 경로: {map_path}")
                return None

# HTML 파일 로드
html_content = load_html_file()

if html_content:
    # DXF 데이터가 있으면 JavaScript 변수로 주입
    if hasattr(st.session_state, 'dxf_data') and st.session_state.dxf_data:
        # JavaScript 코드 생성
        js_code = f"""
        <script>
        // DXF 데이터를 전역 변수로 설정
        window.dxfData = {json.dumps(st.session_state.dxf_data)};
        console.log('DXF 데이터 로드됨:', window.dxfData);
        </script>
        """
        
        # HTML에 JavaScript 코드 삽입
        html_content = html_content.replace('</head>', js_code + '</head>')
    
    # HTML을 Streamlit에 표시
    st.components.v1.html(
        html_content,
        height=800,
        scrolling=True
    )
else:
    st.error("HTML 파일을 로드할 수 없습니다.")