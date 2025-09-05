#!/usr/bin/env python3
# 테스트용 PDF 파일 생성 스크립트

import os
from datetime import datetime

def create_dummy_pdf(file_path, content_text):
    """더미 PDF 파일 생성 (텍스트 기반)"""
    try:
        # 간단한 PDF 콘텐츠 생성 (PDF 헤더 + 텍스트)
        pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 100
>>
stream
BT
/F1 12 Tf
72 720 Td
({content_text}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000189 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
340
%%EOF"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(pdf_content)
        
        print(f"✅ 더미 PDF 생성: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ PDF 생성 오류: {str(e)}")
        return False

def main():
    """메인 함수"""
    # static/management-drawings 폴더 확인/생성
    static_path = "static/management-drawings"
    os.makedirs(static_path, exist_ok=True)
    
    # 테스트용 PDF 파일 목록
    test_files = [
        {
            "filename": "20240801-도림사거리정거장_미들슬라브.pdf",
            "content": "도림사거리 정거장 미들슬라브 시공관리도"
        },
        {
            "filename": "20240801-신풍정거장_시공관리도.pdf", 
            "content": "신풍 정거장 시공관리도"
        },
        {
            "filename": "20240801-신풍 환승통로_터널.pdf",
            "content": "신풍 환승통로 터널 시공관리도"
        },
        {
            "filename": "20240801-본선 1구간_시공관리도.pdf",
            "content": "본선 1구간 시공관리도"
        },
        {
            "filename": "20240801-본선 2구간_시공관리도.pdf",
            "content": "본선 2구간 시공관리도"
        }
    ]
    
    # PDF 파일 생성
    created_count = 0
    for file_info in test_files:
        file_path = os.path.join(static_path, file_info["filename"])
        
        # 파일이 이미 존재하면 건너뛰기
        if os.path.exists(file_path):
            print(f"⚠️ 파일이 이미 존재: {file_path}")
            continue
            
        if create_dummy_pdf(file_path, file_info["content"]):
            created_count += 1
    
    print(f"\n🎯 총 {created_count}개의 테스트 PDF 파일이 생성되었습니다.")
    print(f"📂 저장 위치: {os.path.abspath(static_path)}")
    
    # 생성된 파일 목록 표시
    print("\n📋 생성된 파일 목록:")
    for file_name in os.listdir(static_path):
        if file_name.endswith('.pdf'):
            file_path = os.path.join(static_path, file_name)
            file_size = os.path.getsize(file_path)
            print(f"  - {file_name} ({file_size} bytes)")

if __name__ == "__main__":
    main()

