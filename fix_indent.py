# 들여쓰기 수정 스크립트
import re

filename = '엑셀 작업일보 자동화_추가_rev0.py'

with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

corrected_lines = []
in_create_excel_function = False
indent_level = 0

for i, line in enumerate(lines):
    # create_excel_report 함수 시작 감지
    if line.strip().startswith('def create_excel_report'):
        in_create_excel_function = True
        corrected_lines.append(line)
        continue
    
    # 함수 끝 감지 (다음 함수나 클래스, 또는 들여쓰기가 없는 라인)
    if in_create_excel_function and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
        in_create_excel_function = False
    
    if in_create_excel_function:
        stripped = line.lstrip()
        if not stripped:  # 빈 줄
            corrected_lines.append('\n')
            continue
            
        # 들여쓰기 레벨 계산
        if stripped.startswith('for ') or stripped.startswith('if ') or stripped.startswith('with ') or stripped.startswith('try:') or stripped.startswith('except') or stripped.startswith('else:') or stripped.startswith('elif '):
            # 제어문은 기본 4칸
            corrected_lines.append('    ' + stripped)
        elif i > 0 and lines[i-1].strip().endswith(':'):
            # 이전 줄이 콜론으로 끝나면 추가 들여쓰기
            corrected_lines.append('        ' + stripped)
        elif stripped.startswith('#'):
            # 주석은 기본 4칸
            corrected_lines.append('    ' + stripped)
        else:
            # 기본적으로 4칸 들여쓰기
            corrected_lines.append('    ' + stripped)
    else:
        corrected_lines.append(line)

# 파일 저장
with open(filename, 'w', encoding='utf-8') as f:
    f.writelines(corrected_lines)

print("들여쓰기 수정 완료") 