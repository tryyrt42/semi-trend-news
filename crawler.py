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

def fetch_news(company_name, existing_html):
    url_kr = "https://news.google.com/rss/search?q=\"" + str(company_name) + "\"+(반도체+OR+칩+OR+프로세서)+when:1m&hl=ko&gl=KR&ceid=KR:ko"
    url_kr = url_kr.replace(" ", "%20")
    feed_kr = feedparser.parse(url_kr)
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    new_articles = []
    
    if getattr(feed_kr, 'entries', None):
        # 💡 최대 10개까지 가져와서 AI에게 검사를 맡깁니다.
        for entry in feed_kr.entries[:10]: 
            link = str(getattr(entry, 'link', '#'))
            pub_str = str(getattr(entry, 'published', ''))
            
            try:
                pub_tuple = email.utils.parsedate_tz(pub_str)
                if pub_tuple:
                    pub_timestamp = email.utils.mktime_tz(pub_tuple)
                    pub_date = datetime.fromtimestamp(pub_timestamp, timezone.utc)
                    
                    if pub_date < cutoff_date:
                        continue 
                    
                    # 💡 YYYY-MM-DD HH:MM 포맷으로 깔끔하게 정리 (한국 시간)
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

def is_duplicate_news(new_title, existing_titles):
    """💡 AI를 활용해 기존 기사들과 의미가 완전히 같은지(도배성인지) 판별하는 함수"""
    if not existing_titles:
        return False
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY":
        return False
    
    prompt = f"""다음은 오늘 수집된 반도체 기사 제목들입니다:
{existing_titles}

새로운 기사 제목: '{new_title}'

새로운 기사가 위 수집된 기사들 중 하나와 '완전히 동일한 핵심 사건(보도자료 복붙, 똑같은 실적발표 등)'을 다루고 있습니까? 
맞다면 'YES', 다른 사건이거나 새로운 정보가 있다면 'NO'라고만 대답하세요."""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        answer = res['candidates'][0]['content']['parts'][0]['text'].strip().upper()
        return "YES" in answer
    except:
        return False

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
    
    with open(html_file, "r", encoding="utf-8") as f: 
        content = f.read()
        
    insert_pattern = re.compile(r'(<div id="global-news-feed">)', re.IGNORECASE)
    if insert_pattern.search(content):
        content = insert_pattern.sub(r'\1\n' + article_html, content, count=1)
            
    with open(html_file, "w", encoding="utf-8") as f: 
        f.write(content)

if __name__ == "__main__":
    print("🚀 [Pro V3] AI 중복 필터 장착 크롤링 시작...")
    
    html_file = "index.html"
    existing_html = open(html_file, "r", encoding="utf-8").read() if os.path.exists(html_file) else ""
    
    for comp in COMPANIES:
        articles = fetch_news(comp['name'], existing_html)
        
        if articles:
            print(f"📦 [{comp['name']}] 검토 대기 기사 {len(articles)}개 발견!")
            collected_titles = [] # 💡 이번 턴에 수집한 기사 제목들을 기억하는 메모장
            
            for news in articles:
                # 💡 핵심: AI에게 기사 제목들을 보여주고 중복인지 묻습니다!
                if is_duplicate_news(news['title'], collected_titles):
                    print(f"   🚫 [중복 차단] {news['title']}")
                    existing_html += news['link'] # 다음 턴에서도 무시하기 위해 링크만 기록
                    time.sleep(2) # 짧은 휴식
                    continue
                
                print(f"   ✅ [요약 진행] {news['title']}")
                summary = summarize_news(news['title'])
                collected_titles.append(news['title']) # 수집된 기사 제목을 메모장에 추가
                
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
            print(f"💨 [{comp['name']}] 새로 수집할 기사 없음 (Skip)")
            
    now_kst = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
    
    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    updated_content = re.sub(
        r'<div class="updated-time">.*?</div>', 
        f'<div class="updated-time">최근 업데이트: {now_kst} (KST 기준 업데이트 완료)</div>', 
        content
    )
    
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    print("✨ 글로벌 타임라인 대시보드 업데이트 완료!")
