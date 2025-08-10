# 🚀 GitHub 저장소 설정 및 푸시 가이드

## 📋 1단계: GitHub에서 새 저장소 생성

1. **GitHub.com**에 로그인
2. 우측 상단의 **"+"** 버튼 클릭 → **"New repository"** 선택
3. 저장소 설정:
   - **Repository name**: `construction-status-management`
   - **Description**: `건설 현황 관리 및 월간 실적 추적 시스템`
   - **Visibility**: Public 또는 Private 선택
   - **README, .gitignore, license 체크 해제** (이미 로컬에 있음)
4. **"Create repository"** 클릭

## 🔗 2단계: 원격 저장소 연결

GitHub에서 저장소를 생성한 후, 제공되는 URL을 사용하여 원격 저장소를 연결하세요:

```bash
# HTTPS 방식 (권장)
git remote add origin https://github.com/YOUR_USERNAME/construction-status-management.git

# 또는 SSH 방식 (SSH 키가 설정된 경우)
git remote add origin git@github.com:YOUR_USERNAME/construction-status-management.git
```

## 📤 3단계: 코드 푸시

```bash
# 원격 저장소에 푸시
git push -u origin master

# 또는 main 브랜치를 사용하는 경우
git branch -M main
git push -u origin main
```

## 🔄 4단계: 향후 업데이트

코드를 수정한 후에는 다음 명령어로 업데이트를 푸시하세요:

```bash
# 변경사항 확인
git status

# 변경된 파일 추가
git add .

# 커밋
git commit -m "업데이트 내용 설명"

# 푸시
git push
```

## 📁 프로젝트 구조

```
construction-status-management/
├── .streamlit/
│   └── secrets.toml          # Supabase 연결 정보 (민감정보)
├── pages/
│   ├── SNS일일작업계획.py     # SNS 일일작업계획 페이지
│   ├── 작업일보 작성.py       # 작업일보 작성 페이지
│   └── 월간실적              # 월간실적 관리 페이지
├── app.py                    # 메인 앱 설정
├── main.py                   # 메인 페이지
├── requirements.txt           # Python 패키지 의존성
├── README.md                 # 프로젝트 설명서
└── .gitignore                # Git 제외 파일 목록
```

## ⚠️ 주의사항

### 민감정보 보호
- `.streamlit/secrets.toml` 파일에는 Supabase API 키가 포함되어 있습니다
- 이 파일은 `.gitignore`에 포함되어 있어 Git에 추가되지 않습니다
- GitHub에 푸시할 때 API 키가 노출되지 않도록 주의하세요

### 환경 설정
- 다른 환경에서 프로젝트를 실행할 때는 `secrets.toml` 파일을 별도로 생성해야 합니다
- `README.md`의 설치 가이드를 참고하여 환경을 설정하세요

## 🎯 완료 후 확인사항

1. ✅ GitHub 저장소 생성 완료
2. ✅ 원격 저장소 연결 완료
3. ✅ 코드 푸시 완료
4. ✅ README.md가 GitHub에서 올바르게 표시되는지 확인
5. ✅ 프로젝트 구조가 올바르게 표시되는지 확인

## 🆘 문제 해결

### 인증 오류
```bash
# GitHub 인증 정보 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 푸시 거부
```bash
# 원격 저장소 강제 푸시 (주의: 기존 내용 덮어씀)
git push -f origin master
```

### 브랜치 충돌
```bash
# 원격 저장소의 최신 변경사항 가져오기
git pull origin master
```

## 📞 지원

문제가 발생하면 GitHub Issues를 통해 문의하거나, 프로젝트 문서를 참고하세요. 