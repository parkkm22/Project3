# AI 공사관리 에이전트

## 🔑 **API 키 설정 (필수)**

### Gemini AI API 키 설정
1. [Google AI Studio](https://aistudio.google.com/)에서 API 키 발급
2. 환경변수 설정:
   ```bash
   # Windows
   set GEMINI_API_KEY=your_new_api_key_here
   
   # 또는 .env 파일 생성 (프로젝트 루트에)
   GEMINI_API_KEY=your_new_api_key_here
   ```

### Supabase 설정
```bash
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
```

## 🚀 **실행 방법**

1. 환경변수 설정
2. `pip install -r requirements.txt`
3. `streamlit run app.py`

## ⚠️ **주의사항**

- API 키는 절대 코드에 하드코딩하지 마세요
- `.env` 파일은 `.gitignore`에 추가하여 버전 관리에서 제외
- 만료된 API 키는 즉시 교체 