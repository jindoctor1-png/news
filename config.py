"""
Polymer 영업부문 뉴스 크롤링 설정
"""

# ============================================================
# 🔑 API 키
# ============================================================
NAVER_CLIENT_ID = "TpraDVPGcPZtYNBvTnY2"
NAVER_CLIENT_SECRET = "qbNqlnMDJH"
OPENAI_KEY = "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"

# ============================================================
# 🔴 Main Keyword
# ============================================================
MAIN_PRODUCT = {
    "PE": [
        "Polyethylene",
        "HDPE",
        "LDPE",
        "LLDPE",
        "폴리에틸렌",
    ],
    "PP": [
        "Polypropylene",
        "폴리프로필렌",
    ],
    "PO": [
        "Propylene Oxide",
        "산화프로필렌",
    ],
}

MAIN_COMPANY = {
    "S-OIL": [
        "S-OIL",
        "에쓰오일",
        "에스오일",
    ],
    "ARAMCO": [
        "Saudi Aramco",
        "Aramco",
        "아람코",
    ],
    "SABIC": [
        "Sabic",
        "사빅",
    ],
}

# ============================================================
# 🔵 Bonus Keyword
# ============================================================
BONUS_PRODUCT = {
    "POE": [
        "POE",
        "Polyolefin Elastomer",
        "폴리올레핀 엘라스토머",
    ],
    "POP": [
        "POP",
        "Polyolefin Plastomer",
        "폴리올레핀 플라스토머",
    ],
    "EVA": [
        "EVA",
        "Ethylene Vinyl Acetate",
        "에틸렌 비닐 아세테이트",
    ],
    "Polyol": [
        "Polyol",
        "폴리올",
    ],
    "MTBE": [
        "MTBE",
        "Methyl tert-butyl ether",
    ],
}

BONUS_COMPANY = {
    "국내유화사": [
        "LG Chem",
        "LG화학",
        "Lotte Chemical",
        "롯데케미칼",
        "한화솔루션",
        "Hanwha Solutions",
        "한화토탈",
        "Hanwha Total",
        "금호석유화학",
        "Kumho Petrochemical",
        "SK지오센트릭",
        "SK Geocentric",
        "SK이노베이션",
        "SK Innovation",
        "대한유화",
        "Korea Petrochemical",
        "효성화학",
        "Hyosung Chemical",
        "여천NCC",
        "Yeochun NCC",
        "GS칼텍스",
        "GS Caltex",
        "현대케미칼",
        "Hyundai Chemical",
    ],
    "Global유화사": [
        "BASF",
        "LyondellBasell",
        "ExxonMobil",
        "Exxon Mobil",
        "Dow Chemical",
        "Dow Inc",
        "INEOS",
        "Sinopec",
        "시노펙",
        "PetroChina",
        "페트로차이나",
        "Shell Chemical",
        "쉘",
        "Chevron Phillips",
        "쉐브론필립스",
        "TotalEnergies",
        "토탈에너지",
        "Formosa Plastics",
        "포모사",
        "Reliance Industries",
        "릴라이언스",
        "Braskem",
        "브라스켐",
        "Borealis",
        "보레알리스",
        "Mitsui Chemicals",
        "미쓰이화학",
        "Sumitomo Chemical",
        "스미토모화학",
        "Mitsubishi Chemical",
        "미쓰비시화학",
    ],
}

# 크롤링용 전체 키워드
KEYWORDS = {**MAIN_PRODUCT, **MAIN_COMPANY, **BONUS_PRODUCT, **BONUS_COMPANY}

# ============================================================
# 🔄 한글-영문 키워드 매핑
# ============================================================
KEYWORD_MAPPING = {
    "폴리에틸렌": "polyethylene",
    "polyethylene": "폴리에틸렌",
    "폴리프로필렌": "polypropylene",
    "polypropylene": "폴리프로필렌",
    "산화프로필렌": "propylene oxide",
    "propylene oxide": "산화프로필렌",
    "아람코": "aramco",
    "aramco": "아람코",
    "사빅": "sabic",
    "sabic": "사빅",
    "에쓰오일": "s-oil",
    "에스오일": "s-oil",
    "s-oil": "에쓰오일",
}

# ============================================================
# ⚙️ 크롤링 설정
# ============================================================
CRAWL_CONFIG = {
    "naver_display": 20,
    "google_num": 20,
    "delay": 0.5,
}

# ============================================================
# 📊 전략 점수 설정
# ============================================================
SCORE_CONFIG = {
    "top_n": 30,
    
    # 조합별 기본 점수 (순위 결정)
    "combo_scores": {
        "main_product_main_company": 10.0,    # 1순위: Main제품 + Main회사
        "main_product_bonus_company": 9.0,    # 2순위: Main제품 + Bonus회사(경쟁사)
        "main_company_bonus_product": 7.0,    # 3순위: Main회사 + Bonus제품
        "main_only": 6.0,                     # 4순위: Main제품 or Main회사만
        "bonus_product_bonus_company": 5.0,   # 5순위: Bonus제품 + Bonus회사
        "bonus_company_only": 2.0,            # 6순위: Bonus회사만 (경쟁사 동향)
    },
    
    # 추가 가산점
    "weights": {
        "title_boost": 1.8,           # 제목에 키워드 있으면
        "multi_competitor": 1.5,      # 경쟁사 2개 이상 (개당)
        "exposure_count": 1.0,        # 노출 횟수
    },
    
    # 신선도
    "recency_base": 1.15,
    "recency_decay": 0.1,
    
    # 중복 제거
    "similarity_threshold": 0.4,
}

# 소스별 신뢰도 점수
SOURCE_PRIORITY = {
    "ICIS": 1.3,
    "Platts": 1.3,
    "Reuters": 1.2,
    "Bloomberg": 1.2,
    "Chemical Week": 1.15,
    "McKinsey": 1.15,
    "네이버뉴스": 1.0,
    "연합뉴스": 1.05,
    "한국경제": 1.0,
    "매일경제": 1.0,
    "BBC": 1.1,
    "Google News": 1.0,
}

# ============================================================
# 🤖 GPT 요약 설정
# ============================================================
SUMMARY_CONFIG = {
    "model": "gpt-4o-mini",
    "max_tokens": 100,
    "system_prompt": """석유화학/폴리머 산업 전문가로서 뉴스를 2-3문장으로 한글 요약하세요.
핵심 내용과 시장 영향을 간결하게 작성하세요.""",
}

# ============================================================
# 📧 이메일 설정
# ============================================================
EMAIL_CONFIG = {
    "subject_prefix": "[Polymer 뉴스]",
}