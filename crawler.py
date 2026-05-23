import feedparser
import requests
import os
import re
import time
from datetime import datetime, timedelta, timezone
import email.utils
import urllib.parse

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
    search_query = f"{company_name} when:30d"
    encoded_query = urllib.parse.quote(search_query)
    url_kr = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    feed_kr = feedparser.parse(url_kr)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    new_articles = []
    
    if getattr(feed_kr, 'entries', None):
        for entry in feed_kr.entries[:5]: 
            link = str(getattr(entry, 'link', '#'))
            pub_str = str(getattr(entry, 'published', ''))
            try:
                pub_tuple = email.utils.parsedate_tz(pub_str)
                if pub_tuple:
                    pub_timestamp = email.utils.mktime_tz(pub_tuple)
                    pub_date = datetime.fromtimestamp(pub_timestamp, timezone.utc)
                    if pub_date < cutoff_date: continue 
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

def analyze_and_summarize(company_name, new_title, existing_titles):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY":
        return "ERROR", "API 키 누락"
    
    prompt = f"""당신은 깐깐한 반도체 산업 분석가입니다.
기업: {company_name}
새 기사 제목: '{new_title}'
최근 수집된 기사들: {existing_titles}

다음 3단계로 엄격하게 검열하고, 통과 시에만 요약하세요.

[1단계: 주식/단순투자 뉴스 완벽 차단]
제목에 '주가', '목표가', '특징주', '매수/매도', '상한가', '시총', '수혜주', '실적 발표' 등 단순 투자 지표나 주식 시장 동향이면 무조건 'REJECT_STOCK'을 출력하고 종료하세요.

[2단계: 관련성 및 중복 검사]
- 반도체 칩 설계, 파운드리, AI 인프라 등 핵심 기술 생태계와 무관한 가십/소비재 기사면 'REJECT_IRRELEVANT' 출력 후 종료.
- 똑같은 사건을 다루는 중복 도배 기사면 'REJECT_DUPLICATE' 출력 후 종료.

[3단계: 요약]
오직 이 경우에만 핵심만 3줄 이내로 요약하세요. 반드시 요약문 맨 앞에 'PASS|' 를 붙이세요.
"""
    # 💡 팩트체크: 절대 에러(Not found) 안 나는 구글의 가장 기본 뼈대 모델 'gemini-pro'로 대못 박음!
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        
        if 'candidates' not in res:
            error_msg = res.get('error', {}).get('message', '')
            if "Quota" in error_msg or "exceeded" in error_msg:
                return "QUOTA_DEAD", "API 일일 한도 완전 소진"
            return "ERROR", f"구글 API 거절: {error_msg}"
            
        answer = res['candidates'][0]['content']['parts'][0]['text'].strip()
        
        if "REJECT_STOCK" in answer.upper(): return "REJECT_STOCK", ""
        if "REJECT_IRRELEVANT" in answer.upper(): return "IRRELEVANT", ""
        if "REJECT_DUPLICATE" in answer.upper(): return "DUPLICATE", ""
        
        if "PASS|" in answer:
            return "PASS", answer.split("PASS|")[1].strip()
        else:
            return "PASS", answer.replace("PASS", "").strip()
            
    except Exception as e:
        return "ERROR", f"시스템 오류: {str(e)}"

def insert_into_global_feed(article_html):
    html_file = "index.html"
    if not os.path.exists(html_file): return
    with open(html_file, "r", encoding="utf-8") as f: content = f.read()
    insert_pattern = re.compile(r'(<div id="global-news-feed">)', re.IGNORECASE)
    if insert_pattern.search(content):
        content = insert_pattern.sub(r'\1\n' + article_html, content, count=1)
    with open(html_file, "w", encoding="utf-8") as f: f.write(content)

if __name__ == "__main__":
    print("🚀 [Pro V5.7] 튼튼한 기본 모델(gemini-pro) 고정 패치 가동 시작...")
    
    html_file = "index.html"
    existing_html = open(html_file, "r", encoding="utf-8").read() if os.path.exists(html_file) else ""
    
    quota_dead = False
    
    for comp in COMPANIES:
        if quota_dead: break 
        
        articles = fetch_news(comp['name'], existing_html)
        
        if articles:
            print(f"📦 [{comp['name']}] 무제한 검색 기사 {len(articles)}개 포착! (AI 검열 중...)")
            collected_titles = [] 
            
            for news in articles:
                status, summary = analyze_and_summarize(comp['name'], news['title'], collected_titles)
                
                if status == "QUOTA_DEAD":
                    print(f"\n🚨 [긴급 정지] 오늘 치 구글 API 한도가 0원입니다! 깃허브 시간 낭비를 막기 위해 즉시 퇴근합니다.")
                    quota_dead = True
                    break
                
                elif status == "REJECT_STOCK":
                    print(f"   📉 [주식 차단] {news['title']}")
                    existing_html += news['link']
                elif status == "IRRELEVANT":
                    print(f"   🗑️ [무관 차단] {news['title']}")
                    existing_html += news['link'] 
                elif status == "DUPLICATE":
                    print(f"   🚫 [도배 차단] {news['title']}")
                    existing_html += news['link']
                elif status == "ERROR":
                    print(f"   ⚠️ [에러 발생] 원인: {summary} / 기사: {news['title']}")
                elif status == "PASS":
                    print(f"   ✅ [요약 완료] {news['title']}")
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
                
                time.sleep(4) 
                
        else:
            print(f"💨 [{comp['name']}] 수집할 새 기사 없음 (Skip)")
            
    now_kst = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
    with open(html_file, "r", encoding="utf-8") as f: content = f.read()
    updated_content = re.sub(
        r'<div class="updated-time">.*?</div>', 
        f'<div class="updated-time">최근 업데이트: {now_kst} (KST 기준 업데이트 완료)</div>', 
        content
    )
    with open(html_file, "w", encoding="utf-8") as f: f.write(updated_content)
        
    print("✨ 글로벌 타임라인 대시보드 업데이트 완료 (또는 한도 초과로 조기 퇴근)!")
