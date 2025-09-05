import streamlit as st

main_page = st.Page("pages/main.py", title="메인 페이지")
sns_page = st.Page("pages/SNS일일작업계획.py", title="SNS일일작업계획")
work_report_page = st.Page("pages/작업일보 작성.py", title="작업일보 작성")
monthly_page = st.Page("pages/월간실적.py", title="월간실적")
balpa_page = st.Page("pages/balpa.py", title="발파데이터 자동화")

pg = st.navigation(
    {
        "메인 페이지": [main_page],
        "발파/계측분석 자동화": [balpa_page],
        "공정분석 자동화": [monthly_page],
        "작업일보": [sns_page, work_report_page],
    }
)
pg.run()