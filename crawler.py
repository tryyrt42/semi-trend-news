import feedparser
import requests
import os
import re
import time
from datetime import datetime, timedelta

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
    
    new_articles = []
    if getattr(feed_kr, 'entries', None):
        for entry in feed_kr.entries[:5]: 
            link = str(getattr(entry, 'link', '#'))
            if link not in existing_html:
                new_articles.append({
                    "title": str(getattr(entry, 'title', '제목 없음')), 
                    "link": link,
                    "published": str(getattr(entry, 'published', '날짜 정보 없음'))
                })
    return new_articles

def summarize_news(title):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY": 
        return "Gemini API 키가 설정되지 않았습니다."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": f"반도체 시장 분석가로서 다음 뉴스를 핵심만 3줄 이내로 요약해 줘. 제목: {title}"}]}]}
    headers = {'Content-Type': 'application/json'}
    
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            return "⚠️ AI 응답 대기 중"
    except: 
        return "⚠️ 요약 진행 중 시스템 오류"

def update_individual_card(comp_id, comp_name, article_html):
    html_file = "index.html"
    if not os.path.exists(html_file): return
    
    with open(html_file, "r", encoding="utf-8") as f: 
        content = f.read()
        
    card_marker = f'<div id="co-{comp_id}" class="news-card">'
    
    if card_marker in content:
        # 💡 개선: 공백이나 줄바꿈에 구애받지 않고 안전하게 <h3> 태그 아래를 찾아 삽입합니다.
        h3_pattern = re.compile(rf'(<div id="co-{comp_id}" class="news-card">\s*<h3[^>]*>.*?</h3>)', re.IGNORECASE | re.DOTALL)
        content = h3_pattern.sub(r'\1\n' + article_html, content, count=1)
    else:
        new_card = (
            f'{card_marker}\n'
            f'    <h3 style="color: #1e293b; margin-top:0; font-size: 1.1rem; margin-bottom: 15px;">{comp_name}</h3>\n'
            f'{article_html}'
            f'</div>\n'
        )
        # 💡 개선: 이전처럼 하드코딩된 문자열을 찾지 않고, </div> 태그 두 개와 <script> 사이를 정규식으로 유연하게 찾습니다.
        insert_pattern = re.compile(r'(</div>\s*</div>\s*<script>)', re.IGNORECASE)
        if insert_pattern.search(content):
            content = insert_pattern.sub(new_card + r'\n\1', content, count=1)
        else:
            content += new_card # 최악의 경우에도 데이터가 유실되지 않도록 맨 끝에라도 붙임
            
    with open(html_file, "w", encoding="utf-8") as f: 
        f.write(content)

if __name__ == "__main__":
    print("🚀 [PRO MODE] 글로벌 반도체 크롤러 풀가동 시작...")
    
    html_file = "index.html"
    existing_html = open(html_file, "r", encoding="utf-8").read() if os.path.exists(html_file) else ""
    
    for comp in COMPANIES:
        articles = fetch_news(comp['name'], existing_html)
        
        if articles:
            print(f"📦 [{comp['name']}] 신규 기사 {len(articles)}개 발견!")
            for news in articles:
                summary = summarize_news(news['title'])
                
                article_html = (
                    f'    <div class="article-item" style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #cbd5e1;">\n'
                    f'        <p style="font-size: 0.8rem; color: #64748b; margin-top: 0; margin-bottom: 8px;">🕒 발행일: {news["published"]}</p>\n'
                    f'        <p style="margin-top: 0; margin-bottom: 8px;"><strong>📰 기사 제목:</strong> {news["title"]}</p>\n'
                    f'        <p style="margin-top: 0; margin-bottom: 8px;"><strong>✨ AI 요약:</strong> {summary}</p>\n'
                    f'        <a href="{news["link"]}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: bold; font-size: 0.9rem;">[ 📄 원문 기사 보기 ]</a>\n'
                    f'    </div>\n'
                )
                
                update_individual_card(comp['id'], comp['name'], article_html)
                existing_html += news['link']
                time.sleep(5) 
        else:
            print(f"💨 [{comp['name']}] 새로 수집된 기사 없음 (Skip)")
            
    now_kst = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
    
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        updated_content = re.sub(
            r'<div class="updated-time">.*?</div>', 
            f'<div class="updated-time">최근 업데이트: {now_kst} (KST 기준 자동 갱신 완료)</div>', 
            content
        )
        
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(updated_content)
            
    print("✨ 전체 크롤링 및 웹페이지 업데이트가 완벽하게 종료되었습니다!")
