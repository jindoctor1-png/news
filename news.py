"""
Polymer 뉴스 대시보드 - Streamlit 메인
"""

import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, timedelta

from config import KEYWORDS, MAIN_PRODUCT, MAIN_COMPANY, BONUS_PRODUCT, BONUS_COMPANY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, OPENAI_KEY, SCORE_CONFIG
from crawler import crawl_all, crawl_with_fulltext
from processor import remove_duplicates_by_similarity, count_exposures, calculate_strategy_score, get_top_articles
from summarizer import summarize_dataframe
from mailer import create_html, send_outlook, save_draft, save_excel_report


# 페이지 설정
st.set_page_config(page_title="Polymer News", page_icon="🧪", layout="wide")
st.title("🧪 Polymer 뉴스 대시보드")

# S-OIL 스타일 적용
st.markdown("""
<style>
    /* 메인 버튼 (초록색) */
    .stButton > button[kind="primary"] {
        background-color: #00A651 !important;
        border-color: #00A651 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #008C45 !important;
        border-color: #008C45 !important;
    }
    
    /* 일반 버튼도 초록색 */
    .stButton > button {
        background-color: #00A651 !important;
        color: white !important;
        border-color: #00A651 !important;
    }
    .stButton > button:hover {
        background-color: #008C45 !important;
        border-color: #008C45 !important;
        color: white !important;
    }
    
    /* 다운로드 버튼 */
    .stDownloadButton > button {
        background-color: #00A651 !important;
        color: white !important;
        border-color: #00A651 !important;
    }
    .stDownloadButton > button:hover {
        background-color: #008C45 !important;
        border-color: #008C45 !important;
    }
    
    /* Multiselect 선택된 태그 */
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #00A651 !important;
    }
    
    /* Multiselect 포커스 테두리 */
    .stMultiSelect [data-baseweb="select"] > div {
        border-color: #00A651 !important;
    }
    .stMultiSelect [data-baseweb="select"]:focus-within > div {
        border-color: #00A651 !important;
        box-shadow: 0 0 0 1px #00A651 !important;
    }
    
    /* Checkbox 체크 색상 */
    .stCheckbox [data-baseweb="checkbox"] input:checked + div {
        background-color: #00A651 !important;
        border-color: #00A651 !important;
    }
    
    /* Slider 색상 */
    .stSlider [data-baseweb="slider"] div[role="slider"] {
        background-color: #00A651 !important;
    }
    .stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] > div {
        background-color: #00A651 !important;
    }
    
    /* 사이드바 헤더 */
    .stSidebar .stMarkdown h3 {
        color: #00A651 !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 사이드바
# ============================================================
st.sidebar.header("⚙️ 설정")
naver_id = NAVER_CLIENT_ID
naver_secret = NAVER_CLIENT_SECRET
openai_key = OPENAI_KEY

# 기간 선택
st.sidebar.subheader("📅 기간")
today = datetime.now()

period = st.sidebar.selectbox("검색 기간", ["전일", "이번주", "최근 일주일", "최근 30일", "전주", "이번달", "지난달", "올해"])

# 직접 지정 옵션
use_custom_date = st.sidebar.checkbox("📆 날짜 직접 지정")
if use_custom_date:
    start_date = st.sidebar.date_input("시작일", today - timedelta(days=7))
    end_date = st.sidebar.date_input("종료일", today)

today = datetime.now()
if use_custom_date:
    start = datetime.combine(start_date, datetime.min.time())
    end = datetime.combine(end_date, datetime.min.time())
    days_ago = (today - start).days
    period_label = f"{start.strftime('%m/%d')}~{end.strftime('%m/%d')}"
elif period == "전일":
    yesterday = today - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0)
    end = today.replace(hour=12, minute=0, second=0)
    days_ago = 2
    period_label = f"전일+오전 ({yesterday.strftime('%m/%d')}~{today.strftime('%m/%d')})"
elif period == "이번주":
    start = today - timedelta(days=today.weekday())
    end = today
    days_ago = 7
    period_label = f"이번주 ({start.strftime('%m/%d')}~{end.strftime('%m/%d')})"
elif period == "최근 일주일":
    start = today - timedelta(days=7)
    end = today
    days_ago = 7
    period_label = f"최근 일주일 ({start.strftime('%m/%d')}~{end.strftime('%m/%d')})"
elif period == "최근 30일":
    start = today - timedelta(days=30)
    end = today
    days_ago = 30
    period_label = f"최근 30일 ({start.strftime('%m/%d')}~{end.strftime('%m/%d')})"
elif period == "전주":
    start = today - timedelta(days=today.weekday() + 7)
    end = start + timedelta(days=6)
    days_ago = 14
    period_label = f"전주 ({start.strftime('%m/%d')}~{end.strftime('%m/%d')})"
elif period == "이번달":
    start = today.replace(day=1)
    end = today
    days_ago = 30
    period_label = f"이번달 ({start.strftime('%Y.%m')})"
elif period == "지난달":
    first_this = today.replace(day=1)
    end = first_this - timedelta(days=1)
    start = end.replace(day=1)
    days_ago = 60
    period_label = f"지난달 ({start.strftime('%Y.%m')})"
else:
    start = today.replace(month=1, day=1)
    end = today
    days_ago = 365
    period_label = f"올해 ({start.strftime('%Y')})"

st.sidebar.info(f"📆 {period_label}")
st.sidebar.divider()

# ============================================================
# Main Keyword (대분류)
# ============================================================
st.sidebar.subheader("🔴 Main Keyword")
st.sidebar.caption("⚠️ 최소 1개 필수 선택")

st.sidebar.caption("제품")
selected_main_product = st.sidebar.multiselect(
    "Main 제품",
    options=list(MAIN_PRODUCT.keys()),
    default=list(MAIN_PRODUCT.keys()),
    label_visibility="collapsed"
)

st.sidebar.caption("회사")
selected_main_company = st.sidebar.multiselect(
    "Main 회사",
    options=list(MAIN_COMPANY.keys()),
    default=list(MAIN_COMPANY.keys()),
    label_visibility="collapsed"
)

selected_main = selected_main_product + selected_main_company

if not selected_main:
    st.sidebar.error("❌ Main Keyword 최소 1개 필요!")

st.sidebar.divider()

# ============================================================
# Bonus Keyword (중분류)
# ============================================================
st.sidebar.subheader("🔵 Bonus Keyword")

st.sidebar.caption("제품")
selected_bonus_product = st.sidebar.multiselect(
    "Bonus 제품",
    options=list(BONUS_PRODUCT.keys()),
    default=list(BONUS_PRODUCT.keys()),
    label_visibility="collapsed"
)

st.sidebar.caption("유화사 (국내/Global)")
selected_bonus_company = st.sidebar.multiselect(
    "Bonus 유화사",
    options=list(BONUS_COMPANY.keys()),
    default=list(BONUS_COMPANY.keys()),
    label_visibility="collapsed"
)

# 전체 선택 카테고리
selected_categories = selected_main_product + selected_main_company + selected_bonus_product + selected_bonus_company

# Top N 설정
top_n = st.sidebar.slider("Top N 기사", 10, 50, SCORE_CONFIG["top_n"])

# AI 요약 제외 옵션
skip_summary = st.sidebar.checkbox(
    "⏩ AI 요약 제외 (수집 시간 단축)",
    value=False
)

# ============================================================
# 세션 상태
# ============================================================
if "news_df" not in st.session_state:
    st.session_state.news_df = None

# ============================================================
# 주차별 통계 저장 함수
# ============================================================
def save_weekly_summary(df, period_label):
    summary_dir = "./weekly_summary"
    os.makedirs(summary_dir, exist_ok=True)
    
    summary_data = []
    for category in df["category"].unique():
        cat_df = df[df["category"] == category]
        summary_data.append({
            "period": period_label,
            "category": category,
            "count": len(cat_df),
            "avg_score": round(cat_df["strategy_score"].mean(), 2) if "strategy_score" in cat_df.columns else 0,
            "top_keyword": cat_df["keyword"].value_counts().index[0] if len(cat_df) > 0 else "",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # 주차별 파일
    week_file = os.path.join(summary_dir, f"{period_label.replace('/', '-').replace(' ', '_')}.csv")
    summary_df.to_csv(week_file, index=False, encoding="utf-8-sig")
    
    # 누적 파일
    all_file = os.path.join(summary_dir, "category_summary_all.csv")
    if os.path.exists(all_file):
        existing = pd.read_csv(all_file)
        combined = pd.concat([existing, summary_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["period", "category"], keep="last")
    else:
        combined = summary_df
    combined.to_csv(all_file, index=False, encoding="utf-8-sig")
    
    print(f"📈 주차 통계 저장: {week_file}")

# ============================================================
# 메인 영역
# ============================================================

if st.button("🚀 뉴스 수집 시작", type="primary", use_container_width=True):
    
    if not naver_id or not naver_secret:
        st.error("네이버 API 키를 입력해주세요!")
    elif not selected_main:
        st.error("Main Keyword를 최소 1개 선택해주세요!")
    elif not selected_categories:
        st.error("카테고리를 선택해주세요!")
    else:
        keywords_to_search = {cat: KEYWORDS[cat] for cat in selected_categories}
        
        # Step 1: 크롤링
        with st.spinner("🔍 뉴스 수집 중..."):
            df = crawl_all(keywords_to_search, naver_id, naver_secret, days_ago)
        
        if df.empty:
            st.warning("검색 결과가 없습니다.")
        else:
            # Step 2: 노출 횟수 계산
            with st.spinner("📊 노출 횟수 계산 중..."):
                df = count_exposures(df)
            
            # Step 3: 유사도 중복 제거
            with st.spinner("🧹 중복 제거 중..."):
                df = remove_duplicates_by_similarity(df, SCORE_CONFIG["similarity_threshold"])
            
            # Step 4: 전략 점수
            with st.spinner("📊 전략 점수 계산 중..."):
                df = calculate_strategy_score(df)
                df = get_top_articles(df, top_n)
            
            # Step 5: 본문 크롤링
            with st.spinner("📄 본문 수집 중..."):
                df = crawl_with_fulltext(df)
            
            # Step 6: GPT 요약
            if skip_summary:
                df["summary"] = "-"
                st.info("⏩ AI 요약 생략됨")
            elif openai_key:
                with st.spinner("🤖 AI 요약 생성 중..."):
                    df = summarize_dataframe(df, openai_key, delay=0.5)
            else:
                df["summary"] = "API 키 없음"
                st.warning("OpenAI Key 없음 - 요약 생략")
            
            # Step 7: 주차 통계 저장
            save_weekly_summary(df, period_label)
            
            st.session_state.news_df = df
            st.success(f"✅ {len(df)}건 수집 완료!")

# ============================================================
# 결과 표시
# ============================================================
if st.session_state.news_df is not None:
    df = st.session_state.news_df
    
    st.divider()
    st.subheader(f"📰 {period_label} 뉴스 (Top {len(df)})")
    
    # 탭
    categories = df["category"].unique().tolist()
    tabs = st.tabs(["📋 전체"] + categories)
    
    with tabs[0]:
        for _, row in df.iterrows():
            date_str = row.get('date', '') or ''
            date_short = re.split(r'\d{2}:\d{2}', date_str)[0].strip().rstrip(',')
            source = row.get('source', '')
            with st.expander(f"**[{row['category']}]** {row['title'][:70]}... ({date_short} | {source})"):
                st.markdown(f"**키워드:** {row['keyword']} | **소스:** {row['source']} | **날짜:** {row.get('date', '')}")
                st.markdown(f"**요약:** {row.get('summary', '')}")
                st.markdown(f"[기사 원문 →]({row['link']})")
    
    for i, category in enumerate(categories):
        with tabs[i + 1]:
            cat_df = df[df["category"] == category]
            st.caption(f"{len(cat_df)}건")
            for _, row in cat_df.iterrows():
                date_short = row.get('date', '')[:20] if row.get('date') else ''
                with st.expander(f"**[{row['keyword']}]** {row['title'][:60]}... ({date_short})"):
                    st.markdown(f"**소스:** {row['source']} | **날짜:** {row.get('date', '')}")
                    st.markdown(f"**요약:** {row.get('summary', '')}")
                    st.markdown(f"[기사 원문 →]({row['link']})")
    
    # ============================================================
    # 내보내기
    # ============================================================
    st.divider()
    st.subheader("📤 내보내기")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Excel 저장"):
            filepath = save_excel_report(df, period_label)
            st.success(f"저장: {filepath}")
    
    with col2:
        to_email = st.text_input("수신자", placeholder="email@company.com")
    
    with col3:
        col3a, col3b = st.columns(2)
        with col3a:
            if st.button("📧 발송"):
                if to_email:
                    send_outlook(df, period_label, to_email)
                    st.success("발송 완료!")
        with col3b:
            if st.button("💾 임시저장"):
                save_draft(df, period_label, to_email)
                st.success("저장 완료!")
    
    # 이메일 미리보기 (아래쪽 전체 너비)
    st.divider()
    if st.button("👁️ 이메일 미리보기", use_container_width=True):
        html = create_html(df, period_label)
        st.components.v1.html(html, height=800, scrolling=True)
