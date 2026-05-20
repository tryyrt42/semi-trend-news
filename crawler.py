import feedparser
import requests
import os
import re
import time
from datetime import datetime

# 🔑 깃허브 보안 설정에서 불러올 Gemini API 키
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY")

# 🎯 1순위 타겟 전문 매체 리스트 (White List)
TARGET_SITES = [
    "eetimes.com", "digitimes.com", "reuters.com", 
    "bloomberg.com", "tomshardware.com", "wsj.com"
]

# 🏢 모니터링 기업 리스트 (HTML과 매칭되도록 ID 설정)
COMPANIES = [
    {"id": "alphachips", "name": "AlphaChips"},
    {"id": "nvidia", "name": "NVIDIA"},
    {"id": "amd", "name": "AMD"},
    {"id": "tesla", "name": "Tesla"},
    {"id": "apple", "name": "Apple"},
    {"id": "tsmc", "name": "TSMC"},
    {"id": "samsungfoundry", "name": "Samsung Foundry"},
    {"id": "furiosaai", "name": "FuriosaAI"},
    {"id": "rebellions", "name": "Rebellions"},
    {"id": "lxsemicon", "name": "LX Semicon"},
    {"id": "adtechnology", "name": "ADTechnology"},
    {"id": "gaonchips", "name": "Gaonchips"},
    {"id": "semifive", "name": "Semifive"},
    {"id": "asicland", "name": "ASICLAND"},
    {"id": "guc", "name": "Global Unichip"}
    # 필요에 따라 CSV의 영문명을 여기에 계속 추가하시면 됩니다.
]

def fetch_news(company_name):
    """1순위 전문 매체를 먼저 검색하고, 없으면 2순위 구글 뉴스 전체를 검색합니다."""
    
    # [Step 1] 1순위: 지정된 전문 매체에서 검색
    site_query = " OR ".join([f"site:{s}" for s in TARGET_SITES])
    url_primary = f"https://news.google.com/rss/search?q={company_name}+semiconductor+({site_query})&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(url_primary)
    if feed.entries:
        print(f"✅ [{company_name}] 1순위 전문 매체 기사 발견!")
        return {"title": feed.entries[0].title, "link": feed.entries[0].link}

    # [Step 2] 2순위: 구글 뉴스 전체로 확장하여 검색
    print(f"⚠️ [{company_name}] 1순위 매체 기사 없음. 2순위 검색 진행.")
    url_secondary = f"https://news.google.com/rss/search?q={company_name}+semiconductor&hl=en-US&gl=US&ceid=US:en"
    
    feed_sec = feedparser.parse(url_secondary)
    if feed_sec.entries:
        return {"title": feed_sec.entries[0].title, "link": feed_sec.entries[0].link}

    print(f"❌ [{company_name}] 최근 기사를 찾을 수 없습니다.")
    return None

def summarize_news(title):
    """구글 Gemini API를 호출하여 영문 기사 제목을 한국어로 3줄 요약합니다."""
    if GEMINI_API_KEY == "YOUR_API_KEY" or not GEMINI_API_KEY:
        return "Gemini API 키가 설정되지 않아 AI 요약을 수행할 수 없습니다."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = (
        f"너는 글로벌 반도체 시장 분석가야. 다음 영문 반도체 뉴스의 제목을 보고, "
        f"어떤 내용인지 핵심을 파악해서 한국어로 명확하게 3줄 이내로 요약해 줘.\n\n"
        f"뉴스 제목: {title}"
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        res_json = response.json()
        summary = res_json['candidates'][0]['content']['parts'][0]['text']
        return summary.strip()
    except Exception as e:
        return f"요약 중 오류 발생: {e}"

def update_html(news_html_content):
    """완성된 뉴스 카드(HTML)를 index.html 파일에 덮어씁니다."""
    html_file = "index.html"
    if not os.path.exists(html_file):
        print(f"Error: {html_file} 파일을 찾을 수 없습니다.")
        return

    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 업데이트 시간 갱신 (2시간 간격으로 텍스트 변경)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = re.sub(
        r'<div class="updated-time">.*?</div>',
        f'<div class="updated-time">최근 업데이트: {current_time} (2시간 간격 자동 갱신)</div>',
        content
    )

    # index.html 내의 뉴스 섹션을 새 뉴스로 교체
    pattern = re.compile(r'<div class="news-section">.*?</div>\s*</div>\s*<script>', re.DOTALL)
    new_section_html = f'<div class="news-section">\n            <h2>기업별 실시간 모니터링 기사</h2>\n            <p style="color: #64748b; margin-top:-5px; margin-bottom:20px; font-size:0.85rem;">※ 위 회사 버튼을 클릭하면 관련 기사 위치로 이동합니다.</p>\n{news_html_content}        </div>\n    </div>\n\n    <script>'
    
    content = pattern.sub(new_section_html, content)

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("✨ index.html 업데이트 완료!")

if __name__ == "__main__":
    print("🚀 반도체 뉴스 수집 및 AI 요약 파이프라인 가동...")
    generated_cards = ""
    
    for comp in COMPANIES:
        news_info = fetch_news(comp['name'])
        
        if news_info:
            ai_summary = summarize_news(news_info['title'])
            
            # HTML 형식으로 뉴스 카드 생성
            card_html = f"""            <div id="co-{comp['id']}" class="news-card">
                <h3 style="color: #1e293b; margin-top:0; font-size: 1.1rem;">{comp['name']}</h3>
                <p><strong>📰 기사 제목:</strong> {news_info['title']}</p>
                <p><strong>✨ AI 요약:</strong> {ai_summary}</p>
                <a href="{news_info['link']}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: bold;">[ 원문 기사 보기 ]</a>
            </div>\n"""
            generated_cards += card_html
            
        # API 과부하 방지를 위해 1초 대기
        time.sleep(1)
            
    if generated_cards:
        update_html(generated_cards)
