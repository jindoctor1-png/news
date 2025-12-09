"""
전략 점수 계산
- Main/Bonus 조합별 순위 점수
- 신선도, 노출횟수 반영
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import (
    SCORE_CONFIG, SOURCE_PRIORITY,
    MAIN_PRODUCT, MAIN_COMPANY,
    BONUS_PRODUCT, BONUS_COMPANY,
    KEYWORD_MAPPING
)


def get_mapped_keywords(keyword):
    """키워드 + 매핑된 키워드 반환"""
    keywords = [keyword.lower()]
    kw_lower = keyword.lower()
    if kw_lower in KEYWORD_MAPPING:
        keywords.append(KEYWORD_MAPPING[kw_lower].lower())
    return keywords


def check_keyword_in_text(text, keyword):
    """텍스트에 키워드 포함 여부"""
    text_lower = text.lower()
    for kw in get_mapped_keywords(keyword):
        if kw in text_lower:
            return True
    return False


def remove_duplicates_by_similarity(df, threshold=0.8):
    if df.empty or len(df) < 2:
        return df
    
    df = df.copy()
    
    # 불용어 (자주 바뀌는 동사/관사 등)
    stopwords = [
        # 영문 동사
        'sets', 'set', 'up', 'launches', 'launch', 'secures', 'secure',
        'advances', 'advance', 'begins', 'begin', 'starts', 'start',
        'announces', 'announce', 'unveils', 'unveil', 'reveals', 'reveal',
        'plans', 'plan', 'opens', 'open', 'closes', 'close',
        # 영문 관사/전치사
        'the', 'a', 'an', 'to', 'for', 'with', 'in', 'on', 'at', 'by',
        'its', 'their', 'new', 'will', 'has', 'have', 'is', 'are',
        # 한글 동사/조사
        '개최', '열어', '진행', '발표', '공개', '시작', '추진', '계획',
        '을', '를', '이', '가', '은', '는', '의', '에', '에서', '로', '으로',
    ]
    
    def get_compare_text(row):
        title = str(row.get("title", "")).lower()
        snippet = str(row.get("snippet", ""))[:200].lower()
        text = f"{title} {snippet}"
        
        # 불용어 제거
        words = text.split()
        filtered = [w for w in words if w not in stopwords]
        return " ".join(filtered)
    
    texts = df.apply(get_compare_text, axis=1).tolist()
    
    if all(t.strip() == "" for t in texts):
        return df
    
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(texts)
        sim_matrix = cosine_similarity(tfidf_matrix)
        
        to_remove = set()
        for i in range(len(sim_matrix)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(sim_matrix)):
                if sim_matrix[i][j] >= threshold:
                    to_remove.add(j)
        
        df = df.drop(df.index[list(to_remove)])
        df = df.reset_index(drop=True)
        
        print(f"🧹 유사도 중복 제거: {len(to_remove)}건")
        
    except Exception as e:
        print(f"⚠️ 유사도 계산 실패: {e}")
    
    return df


def count_exposures(df):
    """노출 횟수 계산"""
    if df.empty:
        return df
    
    df = df.copy()
    exposure_counts = df.groupby("link").size().to_dict()
    df["exposure_count"] = df["link"].map(exposure_counts)
    
    print(f"📊 노출 횟수 계산 완료")
    return df


def calculate_strategy_score(df):
    """
    전략 점수 계산
    
    순위:
    1순위: Main제품 + Main회사 (10점)
    2순위: Main제품 + Bonus회사 (7점)
    3순위: Main회사 + Bonus제품 (5점)
    4순위: Main제품 or Main회사만 (3점)
    5순위: Bonus제품 + Bonus회사 (1점)
    제외: Bonus만 단독
    """
    if df.empty:
        return df
    
    df = df.copy()
    combo_scores = SCORE_CONFIG["combo_scores"]
    weights = SCORE_CONFIG["weights"]
    
    # 키워드 리스트 생성
    all_main_product_kw = [kw for kws in MAIN_PRODUCT.values() for kw in kws]
    all_main_company_kw = [kw for kws in MAIN_COMPANY.values() for kw in kws]
    all_bonus_product_kw = [kw for kws in BONUS_PRODUCT.values() for kw in kws]
    all_bonus_company_kw = [kw for kws in BONUS_COMPANY.values() for kw in kws]
    
    # ============================================================
    # 1. 각 카테고리 포함 여부 체크
    # ============================================================
    def check_categories(row):
        text = f"{row.get('title', '')} {row.get('snippet', '')}"
        
        # 매칭된 Main 제품 카테고리
        matched_main_product = [cat for cat, kws in MAIN_PRODUCT.items() 
                               if any(check_keyword_in_text(text, kw) for kw in kws)]
        
        # 매칭된 Main 회사 카테고리
        matched_main_company = [cat for cat, kws in MAIN_COMPANY.items() 
                               if any(check_keyword_in_text(text, kw) for kw in kws)]
        
        # 매칭된 Bonus 제품 카테고리
        matched_bonus_product = [cat for cat, kws in BONUS_PRODUCT.items() 
                                if any(check_keyword_in_text(text, kw) for kw in kws)]
        
        # 매칭된 Bonus 회사 카테고리
        matched_bonus_company = [cat for cat, kws in BONUS_COMPANY.items() 
                                if any(check_keyword_in_text(text, kw) for kw in kws)]
        
        return pd.Series({
            "has_main_product": len(matched_main_product) > 0,
            "has_main_company": len(matched_main_company) > 0,
            "has_bonus_product": len(matched_bonus_product) > 0,
            "has_bonus_company": len(matched_bonus_company) > 0,
            "main_keywords": ", ".join(matched_main_product + matched_main_company),
            "bonus_keywords": ", ".join(matched_bonus_product + matched_bonus_company),
        })
    
    category_flags = df.apply(check_categories, axis=1)
    df = pd.concat([df, category_flags], axis=1)
    
    # ============================================================
    # 2. 조합별 점수 계산
    # ============================================================
    def combo_score(row):
        mp = row["has_main_product"]
        mc = row["has_main_company"]
        bp = row["has_bonus_product"]
        bc = row["has_bonus_company"]
        
        # 1순위: Main제품 + Main회사
        if mp and mc:
            return combo_scores["main_product_main_company"], 1
        
        # 2순위: Main제품 + Bonus회사(경쟁사)
        if mp and bc:
            return combo_scores["main_product_bonus_company"], 2
        
        # 3순위: Main회사 + Bonus제품
        if mc and bp:
            return combo_scores["main_company_bonus_product"], 3
        
        # 4순위: Main제품 or Main회사만
        if mp or mc:
            return combo_scores["main_only"], 4
        
        # 5순위: Bonus제품 + Bonus회사
        if bp and bc:
            return combo_scores["bonus_product_bonus_company"], 5
        
        # 6순위: Bonus회사만 (경쟁사 동향)
        if bc:
            return combo_scores["bonus_company_only"], 6
        
        # 제외: Bonus제품만
        return 0, 99
    
    combo_results = df.apply(combo_score, axis=1)
    df["score_combo"] = combo_results.apply(lambda x: x[0])
    df["rank_combo"] = combo_results.apply(lambda x: x[1])
    
    # ============================================================
    # 3. Bonus 단독 기사 제외 (rank 99)
    # ============================================================
    before_filter = len(df)
    df = df[df["rank_combo"] < 99].copy()
    after_filter = len(df)
    print(f"🔒 Main Keyword 필터: {before_filter}건 → {after_filter}건")
    
    if df.empty:
        print("⚠️ 유효한 기사 없음")
        return df
    
    # ============================================================
    # 4. 제목 가산점
    # ============================================================
    def title_boost(row):
        title = row.get("title", "")
        
        all_main_kw = all_main_product_kw + all_main_company_kw
        if any(check_keyword_in_text(title, kw) for kw in all_main_kw):
            return weights["title_boost"]
        return 0
    
    df["score_title"] = df.apply(title_boost, axis=1)
    
    # ============================================================
    # 5. 경쟁사 복수 등장 가산점
    # ============================================================
    def multi_competitor_score(row):
        text = f"{row.get('title', '')} {row.get('snippet', '')}"
        
        count = sum(1 for kw in all_bonus_company_kw if check_keyword_in_text(text, kw))
        
        if count >= 2:
            return (count - 1) * weights["multi_competitor"]
        return 0
    
    df["score_multi_comp"] = df.apply(multi_competitor_score, axis=1)
    
    # ============================================================
    # 6. 노출 횟수 점수
    # ============================================================
    if "exposure_count" not in df.columns:
        df["exposure_count"] = 1
    
    df["score_exposure"] = np.log1p(df["exposure_count"]) * weights["exposure_count"]

    # ============================================================
    # 경쟁사 포함 기사 최신 가산점 (2순위, 5순위, 6순위)
    # ============================================================
    def competitor_recency_boost(row):
        # 경쟁사 포함된 순위만 (2, 5, 6순위)
        if row["rank_combo"] not in [2, 5, 6]:
            return 0
        
        date_str = str(row.get("date", "")).lower()
        
        # 오늘/어제 기사면 추가 가산
        if "hour" in date_str or "시간" in date_str or "분" in date_str:
            return 3.0  # 오늘 기사
        elif "1 day" in date_str or "1일" in date_str:
            return 2.0  # 어제 기사
        elif "2 day" in date_str or "2일" in date_str:
            return 1.0  # 2일 전
        
        return 0
    
    df["score_recency_boost"] = df.apply(competitor_recency_boost, axis=1)
    
    # ============================================================
    # 7. 신선도 (곱하기)
    # ============================================================
    def recency_multiplier(date_str):
        if not date_str:
            return 1.0
        
        date_str = str(date_str).lower()
        days = 7
        
        try:
            if "hour" in date_str or "시간" in date_str or "분" in date_str:
                days = 0
            elif "day" in date_str or "일" in date_str:
                nums = re.findall(r'\d+', date_str)
                days = int(nums[0]) if nums else 1
            elif "week" in date_str or "주" in date_str:
                nums = re.findall(r'\d+', date_str)
                days = (int(nums[0]) if nums else 1) * 7
            elif "month" in date_str or "달" in date_str or "개월" in date_str:
                days = 30
        except:
            days = 7
        
        base = SCORE_CONFIG["recency_base"]
        decay = SCORE_CONFIG["recency_decay"]
        return base / (1.0 + decay * days)
    
    df["recency_mult"] = df["date"].apply(recency_multiplier)
    
    # ============================================================
    # 8. 소스 신뢰도 (곱하기)
    # ============================================================
    df["source_mult"] = df["source"].map(SOURCE_PRIORITY).fillna(1.0)
    
    # ============================================================
    # 최종 점수 계산
    # ============================================================
    df["base_score"] = (
        df["score_combo"] +
        df["score_title"] +
        df["score_multi_comp"] +
        df["score_exposure"] +
        df["score_recency_boost"]
    )
    
    df["strategy_score"] = df["base_score"] * df["recency_mult"] * df["source_mult"]
    
    # 정렬: 1차 rank_combo(순위), 2차 strategy_score(점수)
    df = df.sort_values(["rank_combo", "strategy_score"], ascending=[True, False])
    df = df.reset_index(drop=True)
    
    print(f"📊 전략 점수 계산 완료")
    return df


def get_top_articles(df, top_n=None):
    """상위 N개 기사 추출"""
    if top_n is None:
        top_n = SCORE_CONFIG["top_n"]
    
    df = df.head(top_n)
    print(f"🏆 Top {len(df)} 기사 추출")
    return df