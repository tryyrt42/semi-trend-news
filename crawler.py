import feedparser
import requests
import os
import re
import time
import urllib.parse
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY")

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
]

TARGET_SITES = [
    "eetimes.com", "digitimes.com", "reuters.com", 
    "bloomberg.com", "tomshardware.com", "wsj.com"
]

def fetch_news(company_name):
    # [1순위] 국내 구글 뉴스 검색
    url_kr = "https://news.google.com/rss/search?q=" + str(company_name) + "+반도체&hl=ko&gl=KR&ceid=KR:ko"
    url_kr = url_kr.replace(" ", "%20") 
    
    feed_kr = feedparser.parse(url_kr)
    if getattr(feed_kr, 'entries', None) and len(feed_kr.entries) > 0:
        entry = feed_kr.entries[0]
        return {
            "title": str(getattr(entry, 'title', '제목 없음')), 
            "link": str(getattr(entry, 'link', '#')),
            "published": str(getattr(entry, 'published', '날짜 정보 없음')) # 💡 기사 발행일 추가
        }

    # [2순위] 해외 구글 뉴스 검색
    url_en = "https://news.google.com/rss/search?q=" + str(company_name) + "+semiconductor&hl=en-US&gl=US&ceid=US:en"
    url_en = url_en.replace(" ", "%20")
    
    feed_en = feedparser.parse(url_en)
    if getattr(feed_en, 'entries', None) and len(feed_en.entries) > 0:
        entry = feed_en.entries[0]
        return {
            "title": str(getattr(entry, 'title', '제목 없음')), 
            "link": str(getattr(entry, 'link', '#')),
            "published": str(getattr(entry, 'published', '날짜 정보 없음')) # 💡 기사 발행일 추가
        }

    return None

def summarize_news(title):
    if GEMINI_API_KEY == "YOUR_API_KEY" or not GEMINI_API_KEY:
        return "Gemini API 키가 설정되지 않아 AI 요약을 수행할 수 없습니다."

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + str(GEMINI_API_KEY)
    headers = {'Content-Type': 'application/json'}
    prompt = "너는 글로벌 반도체 시장 분석가야. 다음 반도체 뉴스의 제목을 보고, 어떤 내용인지 핵심을 파악해서 한국어로 명확하게 3줄 이내로 요약해 줘.\n\n뉴스 제목: " + str(title)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        res_json = response.json()
        if 'candidates' in res_json:
            summary = res_json['candidates'][0]['content']['parts'][0]['text']
            return str(summary).strip()
        else:
            error_msg = res_json.get('error', {}).get('message', '알 수 없는 오류')
            return "⚠️ AI 응답 오류 (사유: " + str(error_msg) + ")"
    except Exception as e:
        return "⚠️ 요약 중 시스템 오류 발생: " + str(e)

def update_html(news_html_content):
    html_file = "index.html"
    if not os.path.exists(html_file):
        return

    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = re.sub(
        r'<div class="updated-time">.*?</div>',
        '<div class="updated-time">최근 업데이트: ' + str(current_time) + ' (2시간 간격 자동 갱신)</div>',
        content
    )

    pattern = re.compile(r'<div class="news-section">.*?</div>\s*</div>\s*<script>', re.DOTALL)
    new_section_html = (
        '<div class="news-section">\n'
        '    <h2>기업별 실시간 모니터링 기사</h2>\n'
        '    <p style="color: #64748b; margin-top:-5px; margin-bottom:20px; font-size:0.85rem;">※ 위 회사 버튼을 클릭하면 관련 기사 위치로 이동합니다.</p>\n'
        + str(news_html_content) +
        '</div>\n</div>\n\n<script>'
    )
    content = pattern.sub(new_section_html, content)

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("✨ 업데이트 완료!")

if __name__ == "__main__":
    generated_cards = ""
    for comp in COMPANIES:
        news_info = fetch_news(comp['name'])
        if news_info:
            ai_summary = summarize_news(news_info['title'])
            
            translate_link = "https://translate.google.com/translate?sl=auto&tl=ko&u=" + urllib.parse.quote(str(news_info['link']))
            archive_link = "https://archive.is/?run=1&url=" + urllib.parse.quote(str(news_info['link']))
            
            card_html = (
                '<div id="co-' + str(comp['id']) + '" class="news-card">\n'
                '    <h3 style="color: #1e293b; margin-top:0; font-size: 1.1rem;">' + str(comp['name']) + '</h3>\n'
                '    <p style="font-size: 0.8rem; color: #64748b; margin-top: -8px; margin-bottom: 12px;">🕒 발행일: ' + str(news_info['published']) + '</p>\n' # 💡 날짜가 출력되는 부분!
                '    <p><strong>📰 기사 제목:</strong> ' + str(news_info['title']) + '</p>\n'
                '    <p><strong>✨ AI 요약:</strong> ' + str(ai_summary) + '</p>\n'
                '    <div style="margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap;">\n'
                '        <a href="' + str(news_info['link']) + '" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: bold;">[ 📄 원문 보기 ]</a>\n'
                '        <a href="' + translate_link + '" target="_blank" style="color: #10b981; text-decoration: none; font-weight: bold;">[ 🌐 번역 보기 ]</a>\n'
                '        <a href="' + archive_link + '" target="_blank" style="color: #ef4444; text-decoration: none; font-weight: bold;">[ 🔓 유료기사 우회 ]</a>\n'
                '    </div>\n'
                '</div>\n'
            )
            generated_cards += str(card_html)
        time.sleep(1)
            
    if generated_cards:
        update_html(generated_cards)
