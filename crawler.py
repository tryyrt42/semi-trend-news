import feedparser
import requests
import os
import re
import time
from datetime import datetime, timedelta, timezone
import email.utils

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY")

COMPANIES = [
    {"id": "알파칩스", "name": "알파칩스"}, {"id": "에이디테크놀로지", "name": "에이디테크놀로지"},
    {"id": "가온칩스", "name": "가온칩스"}, {"id": "세미파이브", "name": "세미파이브"},
    {"id": "코아시아", "name": "코아시아"}, {"id": "에이직랜드", "name": "에이직랜드"},
    {"id": "하나텍", "name": "하나텍"}, {"id": "에이씨피씨", "name": "에이씨피씨"},
    {"id": "칩스앤미디어", "name": "칩스앤미디어"}, {"id": "글로벌유니칩", "name": "글로벌유니칩 (GUC)"},
    {"id": "알칩", "name": "알칩 (Alchip)"}, {"id": "패러데이", "name": "패러데이"},
    {"id": "m31", "name": "M31 Technology"}, {"id": "creochip", "name": "CreoChip"},
    {"id": "opensilicon", "name": "Open-Silicon"}, {"id": "베리실리콘", "name": "베리실리콘 (VeriSilicon)"},
    {"id": "innosilicon", "name": "Innosilicon"}, {"id": "손드렐", "name": "손드렐 (Sondrel)"},
    {"id": "ensilica", "name": "EnSilica"}, {"id": "einfochips", "name": "eInfochips"},
    {"id": "퓨리오사ai", "name": "퓨리오사AI"}, {"id": "리벨리온", "name": "리벨리온"},
    {"id": "딥엑스", "name": "딥엑스"}, {"id": "파두", "name": "파두"},
    {"id": "망고부스트", "name": "망고부스트"}, {"id": "사피온", "name": "사피온"},
    {"id": "모빌린트", "name": "모빌린트"}, {"id": "오픈엣지테크", "name": "오픈엣지테크"},
    {"id": "씨유박스", "name": "씨유박스"}, {"id": "에이직원", "name": "에이직원"},
    {"id": "gct", "name": "GCT Semiconductor"}, {"id": "에이스테크놀로지", "name": "에이스테크놀로지"},
    {"id": "알에프에이치아이씨", "name": "알에프에이치아이씨"}, {"id": "와이솔", "name": "와이솔"},
    {"id": "이노칩테크놀로지", "name": "이노칩테크놀로지"}, {"id": "픽셀플러스", "name": "픽셀플러스"},
    {"id": "실리콘옵틱스", "name": "실리콘옵틱스"}, {"id": "에스엘파워일렉트로닉스", "name": "에스엘파워일렉트로닉스"},
    {"id": "아이즈비전", "name": "아이즈비전"}, {"id": "보스반도체", "name": "보스반도체"},
    {"id": "동운아나텍", "name": "동운아나텍"}, {"id": "실리콘마이터스", "name": "실리콘마이터스"},
    {"id": "에이디반도체", "name": "에이디반도체"}, {"id": "magnachip반도체", "name": "MagnaChip반도체"},
    {"id": "lx세미콘", "name": "LX세미콘"}, {"id": "실리콘웍스", "name": "실리콘웍스"},
    {"id": "아나패스", "name": "아나패스"}, {"id": "라온텍", "name": "라온텍"},
    {"id": "칩원텍", "name": "칩원텍"}, {"id": "제주반도체", "name": "제주반도체"},
    {"id": "텔레칩스", "name": "텔레칩스"}, {"id": "넥스트칩", "name": "넥스트칩"},
    {"id": "에이비오브", "name": "에이비오브"}, {"id": "코아로직", "name": "코아로직"},
    {"id": "엠씨넥스", "name": "엠씨넥스"}, {"id": "세코닉스", "name": "세코닉스"},
    {"id": "넥슨반도체", "name": "넥슨반도체"}, {"id": "nvidia", "name": "NVIDIA"},
    {"id": "amd", "name": "AMD"}, {"id": "qualcomm", "name": "Qualcomm"},
    {"id": "broadcom", "name": "Broadcom"}, {"id": "marvell", "name": "Marvell"},
    {"id": "lattice", "name": "Lattice"}, {"id": "cirrus", "name": "Cirrus Logic"},
    {"id": "microchip", "name": "Microchip"}, {"id": "mps", "name": "MPS"},
    {"id": "skyworks", "name": "Skyworks"}, {"id": "qorvo", "name": "Qorvo"},
    {"id": "wolfspeed", "name": "Wolfspeed"}, {"id": "silicon", "name": "Silicon Labs"},
    {"id": "maxlinear", "name": "MaxLinear"}, {"id": "apple", "name": "Apple"},
    {"id": "google", "name": "Google"}, {"id": "amazon", "name": "Amazon"},
    {"id": "microsoft", "name": "Microsoft"}, {"id": "meta", "name": "Meta"},
    {"id": "tesla", "name": "Tesla"}, {"id": "openai", "name": "OpenAI"},
    {"id": "intel", "name": "Intel"}, {"id": "mediatek", "name": "MediaTek"},
    {"id": "novatek", "name": "Novatek"}, {"id": "realtek", "name": "Realtek"},
    {"id": "himax", "name": "Himax"}, {"id": "parade", "name": "Parade Tech"},
    {"id": "ite", "name": "ITE Tech"}, {"id": "elan", "name": "Elan Microelectronics"},
    {"id": "airoha", "name": "Airoha"}, {"id": "siliconmotion", "name": "Silicon Motion"},
    {"id": "nxp", "name": "NXP"}, {"id": "stmicroelectronics", "name": "STMicroelectronics"},
    {"id": "infineon", "name": "Infineon"}, {"id": "nordic", "name": "Nordic"},
    {"id": "ublox", "name": "u-blox"}, {"id": "melexis", "name": "Melexis"},
    {"id": "samsung", "name": "Samsung Foundry"}, {"id": "tsmc", "name": "TSMC"}
]

# ... (위쪽 import 모듈들과 COMPANIES 리스트 부분은 그대로 유지하세요) ...

def fetch_news(company_name, existing_html):
    # 💡 [검색어 봉인 해제] 반도체, 칩 이런 거 다 빼고 '오직 기업명'으로만 싹쓸이 검색!
    search_query = f"{company_name} when:30d"
    encoded_query = urllib.parse.quote(search_query)
    
    url_kr = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    feed_kr = feedparser.parse(url_kr)
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    new_articles = []
    
    if getattr(feed_kr, 'entries', None):
        # 💡 무식하게 다 긁어오므로 가져오는 양을 15개로 넉넉하게 늘림
        for entry in feed_kr.entries[:15]: 
            link = str(getattr(entry, 'link', '#'))
            pub_str = str(getattr(entry, 'published', ''))
            
            try:
                pub_tuple = email.utils.parsedate_tz(pub_str)
                if pub_tuple:
                    pub_timestamp = email.utils.mktime_tz(pub_tuple)
                    pub_date = datetime.fromtimestamp(pub_timestamp, timezone.utc)
                    
                    if pub_date < cutoff_date:
                        continue 
                    
                    kst_date = pub_date + timedelta(hours=9)
                    pub_str = kst_date.strftime("%Y-%m-%d %H:%M")
            except:
                pub_timestamp = 0
                
            if link not in existing_html:
                new_articles.append({
                    "title": str(getattr(entry, 'title', '제목 없음')), 
                    "link": link,
                    "published": pub_str,
                    "timestamp": int(pub_timestamp)
                })
    return new_articles

def ai_super_filter(company_name, new_title, existing_titles):
    """💡 [초강화] 반도체 관련성 검사와 도배성 중복 검사를 동시에 수행하는 철통 필터"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY":
        return "PASS" # 키가 없으면 일단 통과시킴
    
    prompt = f"""당신은 깐깐한 반도체 산업 분석가입니다.
검색 대상 기업: {company_name}
새로 들어온 기사 제목: '{new_title}'
최근 수집 완료된 기사 제목들: {existing_titles}

이 기사에 대해 다음 두 가지를 엄격하게 판별하세요:
1. 관련성: 이 기사가 반도체(Semiconductor), 칩 설계, 파운드리, AI 하드웨어, 데이터센터 인프라 등 '반도체 생태계'와 명확히 관련이 있습니까? (단순한 기업 주가 등락, 스마트폰/자동차 같은 일반 소비재 출시, 관계없는 가십 등은 무조건 관련 없음으로 간주하세요).
2. 중복성: 이 기사가 '수집 완료된 기사 제목들' 중 하나와 완전히 동일한 사건을 다루는 복붙/도배성 기사입니까?

출력 규칙 (반드시 아래 3가지 영단어 중 하나만 출력하세요):
- 반도체 생태계와 관련이 없다면: REJECT_IRRELEVANT
- 반도체와 관련은 있지만, 기존 기사와 겹치는 도배성 기사라면: REJECT_DUPLICATE
- 반도체 관련 기사가 맞고, 완전히 새롭고 중요한 소식이라면: PASS
"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        answer = res['candidates'][0]['content']['parts'][0]['text'].strip().upper()
        
        if "REJECT_IRRELEVANT" in answer: return "IRRELEVANT"
        if "REJECT_DUPLICATE" in answer: return "DUPLICATE"
        return "PASS"
    except:
        return "PASS" # 에러 시 안전하게 통과

def summarize_news(title):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY": 
        return "AI 설정 확인 필요"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": f"반도체 분석가로서 다음 뉴스를 핵심만 3줄 이내로 요약해 줘. 제목: {title}"}]}]}
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text'].strip()
        return "요약 대기 중"
    except: 
        return "시스템 오류"

def insert_into_global_feed(article_html):
    html_file = "index.html"
    if not os.path.exists(html_file): return
    with open(html_file, "r", encoding="utf-8") as f: content = f.read()
    insert_pattern = re.compile(r'(<div id="global-news-feed">)', re.IGNORECASE)
    if insert_pattern.search(content):
        content = insert_pattern.sub(r'\1\n' + article_html, content, count=1)
    with open(html_file, "w", encoding="utf-8") as f: f.write(content)

if __name__ == "__main__":
    print("🚀 [Pro V4] 키워드 제한 해제 & AI 초강력 검열 크롤링 시작...")
    
    html_file = "index.html"
    existing_html = open(html_file, "r", encoding="utf-8").read() if os.path.exists(html_file) else ""
    
    for comp in COMPANIES:
        articles = fetch_news(comp['name'], existing_html)
        
        if articles:
            print(f"📦 [{comp['name']}] 무제한 검색 기사 {len(articles)}개 포착! (AI 검열 중...)")
            collected_titles = [] 
            
            for news in articles:
                # 💡 초강력 AI 필터가 잡스러운 기사와 중복을 동시에 걸러냅니다.
                filter_status = ai_super_filter(comp['name'], news['title'], collected_titles)
                
                if filter_status == "IRRELEVANT":
                    print(f"   🗑️ [잡음 삭제] 반도체 무관 기사: {news['title']}")
                    existing_html += news['link'] 
                    time.sleep(1)
                    continue
                elif filter_status == "DUPLICATE":
                    print(f"   🚫 [중복 차단] 도배성 기사: {news['title']}")
                    existing_html += news['link']
                    time.sleep(1)
                    continue
                
                print(f"   ✅ [검열 통과/요약 진행] {news['title']}")
                summary = summarize_news(news['title'])
                collected_titles.append(news['title']) 
                
                article_html = (
                    f'        <div class="article-item" data-id="{comp["name"]}" data-timestamp="{news["timestamp"]}">\n'
                    f'            <span class="company-badge">{comp["name"]}</span>\n'
                    f'            <p class="news-date">🕒 {news["published"]}</p>\n'
                    f'            <h4 class="news-title">📰 {news["title"]}</h4>\n'
                    f'            <p class="news-summary">✨ {summary}</p>\n'
                    f'            <a href="{news["link"]}" target="_blank" class="news-link">[ 📄 원문 기사 보기 ]</a>\n'
                    f'        </div>\n'
                )
                
                insert_into_global_feed(article_html)
                existing_html += news['link']
                time.sleep(5) 
        else:
            print(f"💨 [{comp['name']}] 수집할 새 기사 없음 (Skip)")
            
    now_kst = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
    with open(html_file, "r", encoding="utf-8") as f: content = f.read()
    updated_content = re.sub(
        r'<div class="updated-time">.*?</div>', 
        f'<div class="updated-time">최근 업데이트: {now_kst} (KST 기준 업데이트 완료)</div>', 
        content
    )
    with open(html_file, "w", encoding="utf-8") as f: f.write(updated_content)
        
    print("✨ 초대형 투망 & AI 정밀 필터링 완료!")
