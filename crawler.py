"""
뉴스 크롤러
- 국내: 네이버 뉴스 API
- 글로벌: Google News RSS
- 본문: Newspaper3k
"""

import requests
import time
import pandas as pd
import urllib.parse
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta
from newspaper import Article
from config import CRAWL_CONFIG

def is_korean(text):
    """한글 포함 여부 확인"""
    return bool(re.search('[가-힣]', text))


def crawl_naver(keyword, client_id, client_secret, display=20):
    """
    네이버 뉴스 API 검색
    """
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": keyword,
        "display": display,
        "sort": "date",
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for item in data.get("items", []):
            # HTML 태그 제거
            title = re.sub(r'<[^>]+>', '', item.get("title", ""))
            snippet = re.sub(r'<[^>]+>', '', item.get("description", ""))
            
            articles.append({
                "title": title,
                "link": item.get("originallink") or item.get("link", ""),
                "snippet": snippet,
                "date": item.get("pubDate", ""),
                "source": "네이버뉴스",
                "keyword": keyword,
            })
        
        return articles
        
    except Exception as e:
        print(f"❌ 네이버 검색 실패 [{keyword}]: {e}")
        return []


def crawl_google_rss(keyword, num=20, lang="en"):
    """
    Google News RSS 검색 (무료 무제한)
    """
    encoded_keyword = urllib.parse.quote(keyword)
    
    if lang == "ko":
        url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    else:
        url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=en&gl=US&ceid=US:en"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        articles = []
        
        for item in root.findall(".//item")[:num]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            
            # 소스 추출 (제목에서 " - 소스명" 패턴)
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source = parts[1] if len(parts) > 1 else "Google News"
            
            articles.append({
                "title": title,
                "link": link,
                "snippet": "",  # RSS는 snippet 없음
                "date": pub_date,
                "source": source,
                "keyword": keyword,
            })
        
        return articles
        
    except Exception as e:
        print(f"❌ 구글 RSS 검색 실패 [{keyword}]: {e}")
        return []


def fetch_full_article(url):
    """
    Newspaper3k로 기사 본문 크롤링
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text[:3000]  # 최대 3000자
    except Exception as e:
        return ""


def parse_date(date_str):
    """
    다양한 날짜 형식 파싱
    """
    from datetime import datetime
    import re
    
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    try:
        # "2 hours ago", "3일 전" 등 상대 시간
        date_lower = date_str.lower()
        
        if "hour" in date_lower or "시간" in date_lower or "분" in date_lower or "minute" in date_lower:
            return datetime.now()
        
        if "day" in date_lower or "일 전" in date_str:
            nums = re.findall(r'\d+', date_str)
            days = int(nums[0]) if nums else 1
            return datetime.now() - timedelta(days=days)
        
        if "week" in date_lower or "주" in date_str:
            nums = re.findall(r'\d+', date_str)
            weeks = int(nums[0]) if nums else 1
            return datetime.now() - timedelta(days=weeks * 7)
        
        if "month" in date_lower or "달" in date_str or "개월" in date_str:
            nums = re.findall(r'\d+', date_str)
            months = int(nums[0]) if nums else 1
            return datetime.now() - timedelta(days=months * 30)
        
        # RFC 2822 형식: "Tue, 14 Oct 2025 11:40:00 +0900"
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            pass
        
        # ISO 형식: "2025-10-14"
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except:
            pass
        
        # 한글 형식: "2025.10.14"
        try:
            return datetime.strptime(date_str[:10], "%Y.%m.%d")
        except:
            pass
        
    except:
        pass
    
    return None


def filter_by_date(df, days_ago):
    """
    날짜 기준 필터링
    """
    if df.empty:
        return df
    
    df = df.copy()
    cutoff_date = datetime.now() - timedelta(days=days_ago)
    
    def is_within_range(date_str):
        parsed = parse_date(date_str)
        if parsed is None:
            return False
        
        # timezone 제거 (naive로 통일)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        
        return parsed >= cutoff_date
    
    before_count = len(df)
    df = df[df["date"].apply(is_within_range)]
    df = df.reset_index(drop=True)
    after_count = len(df)
    
    print(f"📅 날짜 필터: {before_count}건 → {after_count}건 ({days_ago}일 이내)")
    
    return df

def crawl_all(keywords_dict, naver_id, naver_secret, days_ago=7):
    """
    전체 키워드 크롤링
    - 한글 키워드 → 네이버 API
    - 영문 키워드 → Google RSS
    """
    all_articles = []
    delay = CRAWL_CONFIG.get("delay", 0.5)
    naver_display = CRAWL_CONFIG.get("naver_display", 20)
    google_num = CRAWL_CONFIG.get("google_num", 20)
    
    total = sum(len(kws) for kws in keywords_dict.values())
    current = 0
    
    for category, keywords in keywords_dict.items():
        for keyword in keywords:
            current += 1
            
            if is_korean(keyword):
                # 한글 → 네이버
                print(f"🔍 [{current}/{total}] 네이버: {keyword}")
                articles = crawl_naver(keyword, naver_id, naver_secret, naver_display)
            else:
                # 영문 → 구글 RSS
                print(f"🔍 [{current}/{total}] 구글: {keyword}")
                articles = crawl_google_rss(keyword, google_num, lang="en")
            
            # 카테고리 추가
            for article in articles:
                article["category"] = category
            
            all_articles.extend(articles)
            time.sleep(delay)
    
# DataFrame 변환
    df = pd.DataFrame(all_articles)
    
    # 링크 기준 중복 제거 (1차)
    if not df.empty:
        df = df.drop_duplicates(subset=["link"], keep="first")
        df = df.reset_index(drop=True)
        
        # 날짜 필터링
        df = filter_by_date(df, days_ago)
        
        print(f"✅ 총 {len(df)}건 수집 완료 (날짜 필터 적용)")
    
    return df


def crawl_with_fulltext(df):
    """
    DataFrame의 모든 기사 본문 수집
    """
    if df.empty:
        return df
    
    df = df.copy()
    full_texts = []
    
    total = len(df)
    for idx, row in df.iterrows():
        print(f"📄 본문 수집 [{idx+1}/{total}] {row['title'][:40]}...")
        full_text = fetch_full_article(row["link"])
        full_texts.append(full_text)
        time.sleep(0.3)
    
    df["full_text"] = full_texts
    
    # snippet이 비어있으면 full_text로 대체
    df["snippet"] = df.apply(
        lambda x: x["full_text"][:500] if not x["snippet"] and x["full_text"] else x["snippet"],
        axis=1
    )
    
    print(f"✅ 본문 수집 완료: {total}건")
    return df