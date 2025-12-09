"""
GPT 기반 뉴스 요약
"""

import time
from openai import OpenAI
from config import SUMMARY_CONFIG


def summarize_article(title, snippet, full_text, api_key):
    """
    단일 기사 요약
    """
    client = OpenAI(api_key=api_key)
    
    # 본문이 있으면 본문 사용, 없으면 snippet 사용
    content = full_text if full_text else snippet
    text = f"제목: {title}\n내용: {content[:2000]}"
    
    try:
        response = client.chat.completions.create(
            model=SUMMARY_CONFIG["model"],
            messages=[
                {"role": "system", "content": SUMMARY_CONFIG["system_prompt"]},
                {"role": "user", "content": text}
            ],
            max_tokens=SUMMARY_CONFIG["max_tokens"],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"요약 실패: {str(e)[:50]}"


def summarize_dataframe(df, api_key, delay=1.0):
    """
    DataFrame 전체 기사 요약
    """
    if df.empty:
        return df
    
    df = df.copy()
    summaries = []
    
    total = len(df)
    for idx, row in df.iterrows():
        print(f"🤖 요약 [{idx+1}/{total}] {row['title'][:40]}...")
        
        summary = summarize_article(
            title=row.get("title", ""),
            snippet=row.get("snippet", ""),
            full_text=row.get("full_text", ""),
            api_key=api_key
        )
        summaries.append(summary)
        time.sleep(delay)
    
    df["summary"] = summaries
    print(f"✅ 요약 완료: {total}건")
    return df