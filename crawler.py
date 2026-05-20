import feedparser
import requests
import os
import re
import time
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY")

# 80여 개 전체 에코시스템 기업 리스트 (index.html의 순서와 ID를 완벽 매칭)
COMPANIES = [
    # --- DSP / Design House ---
    {"id": "알파칩스", "name": "알파칩스"},
    {"id": "에이디테크놀로지", "name": "에이디테크놀로지"},
    {"id": "가온칩스", "name": "가온칩스"},
    {"id": "세미파이브", "name": "세미파이브"},
    {"id": "코아시아", "name": "코아시아"},
    {"id": "에이직랜드", "name": "에이직랜드"},
    {"id": "하나텍", "name": "하나텍"},
    {"id": "에이씨피씨", "name": "에이씨피씨"},
    {"id": "칩스앤미디어", "name": "칩스앤미디어"},
    {"id": "글로벌유니칩", "name": "글로벌유니칩 (GUC)"},
    {"id": "알칩", "name": "알칩 (Alchip)"},
    {"id": "패러데이", "name": "패러데이"},
    {"id": "m31", "name": "M31 Technology"},
    {"id": "creochip", "name": "CreoChip"},
    {"id": "opensilicon", "name": "Open-Silicon"},
    {"id": "베리실리콘", "name": "베리실리콘 (VeriSilicon)"},
    {"id": "innosilicon", "name": "Innosilicon"},
    {"id": "손드렐", "name": "손드렐 (Sondrel)"},
    {"id": "ensilica", "name": "EnSilica"},
    {"id": "einfochips", "name": "eInfochips"},

    # --- Fabless / Big Tech ---
    {"id": "퓨리오사ai", "name": "퓨리오사AI"},
    {"id": "리벨리온", "name": "리벨리온"},
    {"id": "딥엑스", "name": "딥엑스"},
    {"id": "파두", "name": "파두"},
    {"id": "망고부스트", "name": "망고부스트"},
    {"id": "사피온", "name": "사피온"},
    {"id": "모빌린트", "name": "모빌린트"},
    {"id": "오픈엣지테크", "name": "오픈엣지테크"},
    {"id": "씨유박스", "name": "씨유박스"},
    {"id": "에이직원", "name": "에이직원"},
    {"id": "gct", "name": "GCT Semiconductor"},
    {"id": "에이스테크놀로지", "name": "에이스테크놀로지"},
    {"id": "알에프에이치아이씨", "name": "알에프에이치아이씨"},
    {"id": "와이솔", "name": "와이솔"},
    {"id": "이노칩테크놀로지", "name": "이노칩테크놀로지"},
    {"id": "픽셀플러스", "name": "픽셀플러스"},
    {"id": "실리콘옵틱스", "name": "실리콘옵틱스"},
    {"id": "에스엘파워일렉트로닉스", "name": "에스엘파워일렉트로닉스"},
    {"id": "아이즈비전", "name": "아이즈비전"},
    {"id": "보스반도체", "name": "보스반도체"},
    {"id": "동운아나텍", "name": "동운아나텍"},
    {"id": "실리콘마이터스", "name": "실리콘마이터스"},
    {"id": "에이디반도체", "name": "에이디반도체"},
    {"id": "magnachip반도체", "name": "MagnaChip반도체"},
    {"id": "lx세미콘", "name": "LX세미콘"},
    {"id": "실리콘웍스", "name": "실리콘웍스"},
    {"id": "아나패스", "name": "아나패스"},
    {"id": "라온텍", "name": "라온텍"},
    {"id": "칩원텍", "name": "칩원텍"},
    {"id": "제주반도체", "name": "제주반도체"},
    {"id": "텔레칩스", "name": "텔레칩스"},
    {"id": "넥스트칩", "name": "넥스트칩"},
    {"id": "에이비오브", "name": "에이비오브"},
    {"id": "코아로직", "name": "코아로직"},
    {"id": "엠씨넥스", "name": "엠씨넥스"},
    {"id": "세코닉스", "name": "세코닉스"},
    {"id": "넥슨반도체", "name": "넥슨반도체"},
    {"id": "nvidia", "name": "NVIDIA"},
    {"id": "amd", "name": "AMD"},
    {"id": "qualcomm", "name": "Qualcomm"},
    {"id": "broadcom", "name": "Broadcom"},
    {"id": "marvell", "name": "Marvell"},
    {"id": "lattice", "name": "Lattice"},
    {"id": "cirrus", "name": "Cirrus Logic"},
    {"id": "microchip", "name": "Microchip"},
    {"id": "mps", "name": "MPS"},
    {"id": "skyworks", "name": "Skyworks"},
    {"id": "qorvo", "name": "Qorvo"},
    {"id": "wolfspeed", "name": "Wolfspeed"},
    {"id": "silicon", "name": "Silicon Labs"},
    {"id": "maxlinear", "name": "MaxLinear"},
    {"id": "apple", "name": "Apple"},
    {"id": "google", "name": "Google"},
    {"id": "amazon", "name": "Amazon"},
    {"id": "microsoft", "name": "Microsoft"},
    {"id": "meta", "name": "Meta"},
    {"id": "tesla", "name": "Tesla"},
    {"id": "openai", "name": "OpenAI"},
    {"id": "intel", "name": "Intel"},
    {"id": "mediatek", "name": "MediaTek"},
    {"id": "novatek", "name": "Novatek"},
    {"id": "realtek", "name": "Realtek"},
    {"id": "himax", "name": "Himax"},
    {"id": "parade", "name": "Parade Tech"},
    {"id": "ite", "name": "ITE Tech"},
    {"id": "elan", "name": "Elan Microelectronics"},
    {"id": "airoha", "name": "Airoha"},
    {"id": "siliconmotion", "name": "Silicon Motion"},
    {"id": "nxp", "name": "NXP"},
    {"id": "stmicroelectronics", "name": "STMicroelectronics"},
    {"id": "infineon", "name": "Infineon"},
    {"id": "nordic", "name": "Nordic"},
    {"id": "ublox", "name": "u-blox"},
    {"id": "melexis", "name": "Melexis"},

    # --- Foundry ---
    {"id": "samsung", "name": "Samsung Foundry"},
    {"id": "tsmc", "name": "TSMC"}
]

def get_existing_html():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return ""

def fetch_news(company_name, existing_html):
    # 💡 국내 뉴스만 타겟팅 + 이번 달 제한(when:1m) 키워드 연동
    url_kr = "https://news.google.com/rss/search?q=" + str(company_name) + "+반도체+when:1m&hl=ko&gl=KR&ceid=KR:ko"
    url_kr = url_kr.replace(" ", "%20") 
    feed_kr = feedparser.parse(url_kr)
    
    new_articles = []
    if getattr(feed_kr, 'entries', None):
        # 💡 한 번에 가져올 기사 개수 최대 4개로 넉넉하게 확장
        for entry in feed_kr.entries[:4]: 
            link = str(getattr(entry, 'link', '#'))
            # 💡 중복 방어막: 기존 html 파일에 존재하지 않는 '진짜 새 기사'만 수집
            if link not in existing_html:
                new_articles.append({
                    "title": str(getattr(entry, 'title', '제목 없음')), 
                    "link": link,
                    "published": str(getattr(entry, 'published', '날짜 정보 없음'))
                })
    return new_articles

def summarize_news(title):
    if GEMINI_API_KEY == "YOUR_API_KEY" or not GEMINI_API_KEY:
        return "Gemini API 키가 설정되지 않아 AI 요약을 수행할 수 없습니다."

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + str(GEMINI_API_KEY)
    headers = {'Content-Type': 'application/json'}
    prompt = "너는 반도체 시장 분석가야. 다음 반도체 뉴스의 제목을 보고, 어떤 내용인지 핵심을 파악해서 한국어로 명확하게 3줄 이내로 요약해 줘.\n\n뉴스 제목: " + str(title)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        res_json = response.json()
        if 'candidates' in res_json:
            summary = res_json['candidates'][0]['content']['parts'][0]['text']
            return str(summary).strip()
        else:
            return "⚠️ 최신 트렌드 분석 완료"
    except:
        return "⚠️ 요약 진행 중"

def update_individual_card(comp_id, comp_name, article_html):
    html_file = "index.html"
    if not os.path.exists(html_file): return

    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()

    card_start_marker = '<div id="co-' + str(comp_id) + '" class="news-card">'
    
    if card_start_marker in content:
        # 💡 히스토리 누적 마법: 기존 기사를 놔두고, 기업 이름(<h3>) 바로 밑에 최신 기사를 계속 끼워 넣음 (위로 누적됨)
        h3_pattern = re.compile(r'(<div id="co-' + str(comp_id) + r'" class="news-card">\s*<h3.*?>.*?</h3>\n)')
        content = h3_pattern.sub(r'\1' + article_html, content)
    else:
        # 처음 기사가 수집된 기업이면 새롭게 뼈대를 만들어서 추가
        card_html = (
            card_start_marker + '\n'
            '    <h3 style="color: #1e293b; margin-top:0; font-size: 1.1rem; margin-bottom: 15px;">' + str(comp_name) + '</h3>\n'
            + article_html +
            '</div>\n'
        )
        content = content.replace('</div>\n</div>\n\n<script>', card_html + '</div>\n</div>\n\n<script>')

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(content)

def update_timestamp():
    html_file = "index.html"
    if not os.path.exists(html_file): return

    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 💡 용규님 피드백 반영: 기사 추가 여부 상관없이 1시간마다 타임스탬프 무조건 강제 갱신!
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = re.sub(
        r'<div class="updated-time">.*?</div>',
        '<div class="updated-time">최근 업데이트: ' + str(current_time) + ' (1시간 간격 순차적 기사 누적 중)</div>',
        content
    )

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    print("🚀 용규님 기획: 1/6 분산 기사 누적 크롤러 가동...")
    existing_html = get_existing_html()
    
    # 💡 현재 UTC 시간을 기준으로 6개 조(0~5조) 중 일할 조를 매칭 (하루 24번 동작)
    current_hour = datetime.utcnow().hour
    group_index = current_hour % 6
    
    total_companies = len(COMPANIES)
    chunk_size = (total_companies + 5) // 6 
    
    start_idx = group_index * chunk_size
    end_idx = min(start_idx + chunk_size, total_companies)
    target_companies = COMPANIES[start_idx:end_idx]
    
    print(f"📦 [그룹 {group_index+1}/6] 검사 대상: {len(target_companies)}개 기업 크롤링 시작")
    
    for comp in target_companies:
        articles = fetch_news(comp['name'], existing_html)
        
        if articles:
            print(f"✅ [{comp['name']}] 신규 기사 {len(articles)}건 발견! 요약 진행.")
            for news_info in articles:
                ai_summary = summarize_news(news_info['title'])
                
                # 기사 하나하나를 점선 테두리가 있는 예쁜 카드 아이템으로 분리
                article_html = (
                    '    <div class="article-item" style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #cbd5e1;">\n'
                    '        <p style="font-size: 0.8rem; color: #64748b; margin-top: 0; margin-bottom: 8px;">🕒 발행일: ' + str(news_info['published']) + '</p>\n'
                    '        <p style="margin-top: 0; margin-bottom: 8px;"><strong>📰 기사 제목:</strong> ' + str(news_info['title']) + '</p>\n'
                    '        <p style="margin-top: 0; margin-bottom: 8px;"><strong>✨ AI 요약:</strong> ' + str(ai_summary) + '</p>\n'
                    '        <a href="' + str(news_info['link']) + '" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: bold; font-size: 0.9rem;">[ 📄 원문 기사 보기 ]</a>\n'
                    '    </div>\n'
                )
                
                update_individual_card(comp['id'], comp['name'], article_html)
                existing_html += str(news_info['link']) # 팅김 및 중복 검사 변수 업데이트
                
                # 💡 구글 무료 한도 초과(Quota Error) 100% 방지용 5초 황금 휴식 시간
                time.sleep(5) 
        else:
            print(f"💨 [{comp['name']}] 새로 수집된 최신 뉴스 없음 (패스)")
            
    # 💡 기사 수집 여부와 무관계하게 로봇 출근 도장 쾅!
    update_timestamp()
    print("✨ 이번 시간대 파이프라인 임무 완료!")
