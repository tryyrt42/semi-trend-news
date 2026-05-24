"""
반도체 산업 뉴스 크롤러 (V8.0)
- Gemini 2.5 Flash-Lite (또는 Flash) 배치 처리
- articles.json / seen_urls.json 로 상태 분리
- index.html 은 매 실행 후 재생성
"""
import feedparser
import requests
import os
import re
import json
import time
import html as htmllib
from datetime import datetime, timedelta, timezone
import email.utils
import urllib.parse

# ============================================================
# 설정
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
# Flash-Lite 가 무료 RPD 가장 큼 (≈1000+). 품질이 더 필요하면 gemini-2.5-flash 로.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()

HTML_FILE = "index.html"
ARTICLES_JSON = "articles.json"
SEEN_URLS_JSON = "seen_urls.json"
STATE_JSON = "crawler_state.json"   # 이어 시작용 — 마지막 처리 위치 저장

MAX_ARTICLES_PER_COMPANY = 8      # 일반 기업: 기업당 RSS 상위 N개 검토
MAX_ARTICLES_FOR_HOT = 20         # 핫 티커: 시세 기사가 도배해서 더 많이 봐야 함
DAYS_TO_KEEP = 30                 # 며칠 치 기사 보관
RPM_LIMIT = 12                    # 분당 호출 안전 한도 (15 RPM 모델 기준 마진)
REQUEST_TIMEOUT = 30
RSS_TIMEOUT = 20

# 핫 티커: 한국어 뉴스 빈도가 매우 높아 시세 기사가 상위를 점령하는 빅네임
HOT_COMPANIES = {
    "NVIDIA", "AMD", "Intel", "Qualcomm", "Broadcom", "Marvell",
    "Apple", "Google", "Amazon", "Microsoft", "Meta", "Tesla", "OpenAI",
    "TSMC", "Samsung Foundry", "MediaTek",
    "Texas Instruments", "Analog Devices",
    "Tenstorrent", "Cerebras", "Groq",  # AI 스타트업 핫
    "리벨리온", "퓨리오사AI", "파두", "딥엑스",  # 국내 AI 스타트업 핫
}

# 파이썬 1차 문지기: 주식 찌라시 키워드 차단 (Gemini 호출 전 컷)
JUNK_KEYWORDS = [
    # 시세/주가
    "주가", "목표가", "특징주", "매수", "매도", "상한가", "하한가",
    "시총", "수혜주", "급등", "급락", "신저가", "신고가",
    # 실적/지표
    "어닝쇼크", "어닝서프라이즈", "PER", "PBR", "공매도",
    # 투자분석/리포트성 (이번에 추가된 핵심)
    "투자분석", "투자 분석", "투자의견", "투자전략", "투자 전략",
    "추천종목", "관심종목", "차트분석", "차트 분석",
    "증권사", "증시", "주식"
]

# 발행처 단위 차단 (자동생성 종목분석 봇 등)
JUNK_SOURCES = [
    "주달",          # 코스닥 종목별 자동 투자분석
    "주식의신",
]

# 빅테크는 회사명만 검색하면 반도체 외 뉴스가 폭증 → 검색어에 "반도체" 추가
BIGTECH_NEEDS_FILTER = {
    "Apple", "Google", "Amazon", "Microsoft", "Meta", "Tesla", "OpenAI",
    "Bosch",  # 가전/자동차 부품으로 더 유명 → 반도체 뉴스만 골라내기
}

COMPANIES = [
    # ============ DSP / Design House ============
    # 🇰🇷 대한민국
    {"id": "알파칩스", "name": "알파칩스"},
    {"id": "에이디테크놀로지", "name": "에이디테크놀로지"},
    {"id": "가온칩스", "name": "가온칩스"},
    {"id": "세미파이브", "name": "세미파이브"},
    {"id": "코아시아", "name": "코아시아"},
    {"id": "에이직랜드", "name": "에이직랜드"},
    {"id": "하나텍", "name": "하나텍"},
    {"id": "에이씨피씨", "name": "에이씨피씨"},
    {"id": "칩스앤미디어", "name": "칩스앤미디어"},
    # 🇹🇼 대만
    {"id": "글로벌유니칩", "name": "글로벌유니칩 (GUC)"},
    {"id": "알칩", "name": "알칩 (Alchip)"},
    {"id": "패러데이", "name": "패러데이"},
    {"id": "m31", "name": "M31 Technology"},
    {"id": "creochip", "name": "CreoChip"},
    # 🇺🇸 미국
    {"id": "opensilicon", "name": "Open-Silicon"},
    # 🇪🇺 유럽
    {"id": "손드렐", "name": "손드렐 (Sondrel)"},
    {"id": "ensilica", "name": "EnSilica"},
    {"id": "dolphin", "name": "Dolphin Design"},
    # 🇯🇵 일본
    {"id": "socionext", "name": "Socionext"},
    # 🇨🇳 중국
    {"id": "베리실리콘", "name": "베리실리콘 (VeriSilicon)"},
    {"id": "innosilicon", "name": "Innosilicon"},
    # 🇮🇳 인도
    {"id": "einfochips", "name": "eInfochips"},

    # ============ Fabless ============
    # 🇰🇷 대한민국 (AI/NPU 스타트업)
    {"id": "퓨리오사ai", "name": "퓨리오사AI"},
    {"id": "리벨리온", "name": "리벨리온"},
    {"id": "딥엑스", "name": "딥엑스"},
    {"id": "파두", "name": "파두"},
    {"id": "망고부스트", "name": "망고부스트"},
    {"id": "사피온", "name": "사피온"},
    {"id": "모빌린트", "name": "모빌린트"},
    {"id": "오픈엣지테크", "name": "오픈엣지테크"},
    # 🇰🇷 대한민국 (기타)
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
    {"id": "자람테크놀로지", "name": "자람테크놀로지"},
    # 🇹🇼 대만
    {"id": "mediatek", "name": "MediaTek"},
    {"id": "novatek", "name": "Novatek"},
    {"id": "realtek", "name": "Realtek"},
    {"id": "himax", "name": "Himax"},
    {"id": "parade", "name": "Parade Tech"},
    {"id": "ite", "name": "ITE Tech"},
    {"id": "elan", "name": "Elan Microelectronics"},
    {"id": "airoha", "name": "Airoha"},
    {"id": "siliconmotion", "name": "Silicon Motion"},
    {"id": "phison", "name": "Phison"},
    {"id": "nuvoton", "name": "Nuvoton"},
    {"id": "andes", "name": "Andes Technology"},
    # 🇺🇸 미국 (메이저)
    {"id": "nvidia", "name": "NVIDIA"},
    {"id": "amd", "name": "AMD"},
    {"id": "qualcomm", "name": "Qualcomm"},
    {"id": "broadcom", "name": "Broadcom"},
    {"id": "marvell", "name": "Marvell"},
    {"id": "intel", "name": "Intel"},
    # 🇺🇸 미국 (애널로그/RF/임베디드)
    {"id": "lattice", "name": "Lattice"},
    {"id": "cirrus", "name": "Cirrus Logic"},
    {"id": "microchip", "name": "Microchip"},
    {"id": "mps", "name": "MPS"},
    {"id": "skyworks", "name": "Skyworks"},
    {"id": "qorvo", "name": "Qorvo"},
    {"id": "wolfspeed", "name": "Wolfspeed"},
    {"id": "silicon", "name": "Silicon Labs"},
    {"id": "maxlinear", "name": "MaxLinear"},
    {"id": "synaptics", "name": "Synaptics"},
    {"id": "ti", "name": "Texas Instruments"},
    {"id": "adi", "name": "Analog Devices"},
    # 🇺🇸 미국 (빅테크 자체 칩)
    {"id": "apple", "name": "Apple"},
    {"id": "google", "name": "Google"},
    {"id": "amazon", "name": "Amazon"},
    {"id": "microsoft", "name": "Microsoft"},
    {"id": "meta", "name": "Meta"},
    {"id": "tesla", "name": "Tesla"},
    {"id": "openai", "name": "OpenAI"},
    # 🇺🇸 미국 (AI 신생 팹리스)
    {"id": "tenstorrent", "name": "Tenstorrent"},
    {"id": "cerebras", "name": "Cerebras"},
    {"id": "groq", "name": "Groq"},
    {"id": "sambanova", "name": "SambaNova"},
    {"id": "lightmatter", "name": "Lightmatter"},
    # 🇪🇺 유럽
    {"id": "nxp", "name": "NXP"},
    {"id": "stmicroelectronics", "name": "STMicroelectronics"},
    {"id": "infineon", "name": "Infineon"},
    {"id": "nordic", "name": "Nordic"},
    {"id": "ublox", "name": "u-blox"},
    {"id": "melexis", "name": "Melexis"},
    {"id": "bosch", "name": "Bosch"},
    # 🇯🇵 일본
    {"id": "renesas", "name": "Renesas"},
    {"id": "sony_semi", "name": "Sony Semiconductor"},
    {"id": "rohm", "name": "Rohm"},
    {"id": "kioxia", "name": "Kioxia"},
    {"id": "megachips", "name": "MegaChips"},

    # ============ Foundry ============
    {"id": "samsung", "name": "Samsung Foundry"},
    {"id": "tsmc", "name": "TSMC"},
    {"id": "globalfoundries", "name": "GlobalFoundries"},
    {"id": "umc", "name": "UMC"},
]


# ============================================================
# 유틸
# ============================================================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ {path} 로드 실패: {e} → 기본값 사용")
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class RateLimiter:
    """슬라이딩 윈도우 방식 RPM 제어."""
    def __init__(self, rpm_limit):
        self.rpm_limit = rpm_limit
        self.timestamps = []

    def wait_if_needed(self):
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < 60]
        if len(self.timestamps) >= self.rpm_limit:
            sleep_time = 60 - (now - self.timestamps[0]) + 1
            if sleep_time > 0:
                print(f"   ⏸️  RPM 한도 근접, {sleep_time:.1f}초 대기")
                time.sleep(sleep_time)
                now = time.time()
                self.timestamps = [t for t in self.timestamps if now - t < 60]
        self.timestamps.append(time.time())


# ============================================================
# RSS 수집
# ============================================================
def build_search_query(company_name):
    base = f"{company_name} 반도체" if company_name in BIGTECH_NEEDS_FILTER else company_name
    return f"{base} when:30d"

def fetch_news(company_name, seen_urls):
    query = build_search_query(company_name)
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"   ⚠️ RSS 실패: {e}")
        return []

    if not getattr(feed, "entries", None):
        return []

    # 핫 티커는 더 많이 가져오기 (시세 기사 도배에 묻히는 진짜 뉴스 회수)
    limit = MAX_ARTICLES_FOR_HOT if company_name in HOT_COMPANIES else MAX_ARTICLES_PER_COMPANY
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_TO_KEEP)
    out = []
    for entry in feed.entries[:limit]:
        title = str(getattr(entry, "title", "")).strip()
        link = str(getattr(entry, "link", "")).strip()
        if not title or not link or link in seen_urls:
            continue

        # 발행처 추출 (Google News RSS 는 <source> 태그 또는 제목 뒤 " - 발행처" 형태)
        source = ""
        src_obj = getattr(entry, "source", None)
        if src_obj is not None:
            try:
                source = (src_obj.get("title") if isinstance(src_obj, dict)
                          else str(getattr(src_obj, "title", ""))) or ""
            except Exception:
                source = ""
        if not source:
            m = re.search(r"\s-\s([^-]+)$", title)
            if m:
                source = m.group(1).strip()

        # 파이썬 1차 문지기 (a) 제목 키워드
        if any(k in title for k in JUNK_KEYWORDS):
            seen_urls.add(link)
            continue
        # (b) 발행처 블랙리스트
        if source and any(js in source for js in JUNK_SOURCES):
            seen_urls.add(link)
            continue

        pub_str = str(getattr(entry, "published", ""))
        pub_ts = 0
        try:
            t = email.utils.parsedate_tz(pub_str)
            if t:
                pub_ts = int(email.utils.mktime_tz(t))
                pub_dt = datetime.fromtimestamp(pub_ts, timezone.utc)
                if pub_dt < cutoff:
                    seen_urls.add(link)
                    continue
                kst = pub_dt + timedelta(hours=9)
                pub_str = kst.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

        out.append({
            "title": title,
            "link": link,
            "published": pub_str,
            "timestamp": pub_ts
        })
    return out


# ============================================================
# Gemini 배치 분석
# ============================================================
def analyze_articles_batch(company_name, articles, rate_limiter):
    """
    반환:
      list[dict]  — 각 기사에 대한 {"verdict": "PASS"/"IRRELEVANT"/"DUPLICATE", "summary": str}
      "QUOTA_DEAD" — 일일 한도 소진
      None        — 일시적 오류, 이번 회차 스킵
    """
    if not articles:
        return []

    items_str = json.dumps(
        [{"id": i, "title": a["title"]} for i, a in enumerate(articles)],
        ensure_ascii=False
    )

    prompt = f"""당신은 깐깐한 반도체 산업 분석가입니다.
대상 기업: {company_name}

다음 기사 후보 목록을 분석하세요:
{items_str}

각 기사를 아래 기준으로 판정하고 **순수 JSON 배열로만** 응답하세요 (앞뒤 설명 금지, 코드블록 금지):

판정:
- "IRRELEVANT": 아래 중 하나라도 해당하면 무조건 IRRELEVANT
   (a) 투자분석/투자의견/종목분석/차트분석/추천종목 등 **투자자·주주 대상** 기사
   (b) "○○ 투자분석 YYYY.MM.DD", "○○ 주가 전망", "관심종목 ○선" 같은 자동생성/리포트성 제목
   (c) 주가·시세·실적 숫자만 다루는 기사 (사업/기술 내용 없음)
   (d) 반도체/팹리스/파운드리/디자인하우스/AI칩 생태계와 무관한 일반 가십·연예·소비재
   (e) 제목이 너무 짧고 모호해서 반도체 사업/기술 관련성 판단이 안 되는 경우
- "DUPLICATE": 같은 목록 안에서 같은 사건을 반복 보도 — 가장 먼저 등장한 1건만 PASS, 나머지는 DUPLICATE
- "PASS": 위 둘 다 아니고, 명백한 반도체 **사업/기술/제품/계약/투자유치/공장/인사/IPO** 관련 기사

핵심 원칙: **애매하면 IRRELEVANT**. 투자분석/리포트류는 어떤 경우에도 PASS 금지.

[summary 작성 규칙 — PASS인 경우에만]
- 2~3문장, 한국어 100자 이내로 짧게.
- **제목에 명시적으로 드러난 사실만** 사용. 산업 배경·시사점·전망 등 추론·추측은 절대 금지.
- 제목에 없는 회사명/숫자/제품명/시점 등을 임의로 보충하지 말 것.
- 제목이 이미 충분히 구체적이면 그대로 자연스러운 문장으로 다듬는 수준이면 됨.
- "~로 보인다", "~할 가능성", "~할 전망" 같은 추정 표현 사용 금지.

응답 포맷:
[
  {{"id": 0, "verdict": "PASS", "summary": "제목 기반 짧은 요약"}},
  {{"id": 1, "verdict": "IRRELEVANT", "summary": ""}}
]
PASS 가 아닌 항목은 summary 빈 문자열로.
"""

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(3):
        rate_limiter.wait_if_needed()
        try:
            r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            res = r.json()
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ 네트워크 오류({attempt+1}/3): {e}")
            time.sleep(5 * (attempt + 1))
            continue
        except Exception as e:
            print(f"   ⚠️ 응답 파싱 실패: {e}")
            return None

        # 에러 처리
        if "error" in res:
            msg = res["error"].get("message", "")
            code = res["error"].get("code", 0)
            low = msg.lower()
            if code == 429 or "quota" in low or "exceed" in low or "resource_exhausted" in low:
                if attempt < 2:
                    wait = 30 * (attempt + 1)
                    if attempt == 0:
                        print(f"   📝 API 응답: {msg[:200]}")  # 첫 회만 진단용 출력
                    print(f"   ⏳ 한도 감지({attempt+1}/3), {wait}초 대기")
                    time.sleep(wait)
                    continue
                return "QUOTA_DEAD"
            print(f"   ⚠️ API 오류: {msg[:200]}")
            return None

        cands = res.get("candidates") or []
        if not cands:
            # safety / blocked 등
            reason = res.get("promptFeedback", {}).get("blockReason", "unknown")
            print(f"   ⚠️ candidates 비어있음 (reason={reason})")
            return None

        # 응답 텍스트 추출
        try:
            parts = cands[0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError, TypeError):
            print(f"   ⚠️ 응답 구조 비정상")
            return None

        # JSON 파싱 (코드블록 펜스 제거)
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\[.*\]", text, re.DOTALL)
            if not m:
                print(f"   ⚠️ JSON 추출 실패: {text[:200]}")
                return None
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                print(f"   ⚠️ JSON 파싱 실패: {text[:200]}")
                return None

        if not isinstance(parsed, list):
            return None

        # 결과 정렬
        results = [None] * len(articles)
        for item in parsed:
            if not isinstance(item, dict):
                continue
            idx = item.get("id")
            if isinstance(idx, int) and 0 <= idx < len(articles):
                results[idx] = {
                    "verdict": str(item.get("verdict", "")).upper().strip(),
                    "summary": str(item.get("summary", "")).strip()
                }
        for i in range(len(results)):
            if results[i] is None:
                results[i] = {"verdict": "IRRELEVANT", "summary": ""}
        return results

    return None


# ============================================================
# HTML 재생성
# ============================================================
def replace_feed_contents(html_str, new_inner):
    """<div id="global-news-feed"> ... </div> 내부를 통째로 교체."""
    marker = '<div id="global-news-feed">'
    start = html_str.find(marker)
    if start == -1:
        return html_str

    content_start = start + len(marker)
    depth = 1
    i = content_start
    n = len(html_str)
    while i < n and depth > 0:
        nxt_open = html_str.find("<div", i)
        nxt_close = html_str.find("</div>", i)
        if nxt_close == -1:
            return html_str  # 깨진 HTML
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
        else:
            depth -= 1
            if depth == 0:
                return html_str[:content_start] + "\n" + new_inner + "        " + html_str[nxt_close:]
            i = nxt_close + 6
    return html_str


def update_timestamp(html_str):
    now_kst = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
    return re.sub(
        r'<div class="updated-time">.*?</div>',
        f'<div class="updated-time">최근 업데이트: {now_kst} (KST)</div>',
        html_str
    )


def render_feed_html(articles_db):
    sorted_articles = sorted(articles_db, key=lambda x: x.get("timestamp", 0), reverse=True)
    if not sorted_articles:
        return ('            <div id="no-news" class="no-news-msg">'
                '아직 수집된 기사가 없습니다. 로봇 가동을 기다려주세요.</div>\n')
    parts = []
    for a in sorted_articles:
        parts.append(
            f'        <div class="article-item" '
            f'data-id="{htmllib.escape(a["company"])}" '
            f'data-timestamp="{a["timestamp"]}">\n'
            f'            <span class="company-badge">{htmllib.escape(a["company"])}</span>\n'
            f'            <p class="news-date">🕒 {htmllib.escape(a["published"])}</p>\n'
            f'            <h4 class="news-title">📰 {htmllib.escape(a["title"])}</h4>\n'
            f'            <p class="news-summary">✨ {htmllib.escape(a["summary"])}</p>\n'
            f'            <a href="{htmllib.escape(a["link"], quote=True)}" '
            f'target="_blank" rel="noopener" class="news-link">[ 📄 원문 기사 보기 ]</a>\n'
            f'        </div>\n'
        )
    # 빈 경우용 마커도 추가 (필터에서 결과 0개일 때 메시지용)
    parts.append('        <div id="no-news" class="no-news-msg" style="display:none;">'
                 '선택한 기업에 해당하는 기사가 없습니다.</div>\n')
    return "".join(parts)


def rebuild_html(articles_db):
    if not os.path.exists(HTML_FILE):
        print(f"⚠️ {HTML_FILE} 없음 — HTML 갱신 스킵")
        return
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    content = replace_feed_contents(content, render_feed_html(articles_db))
    content = update_timestamp(content)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content)


# ============================================================
# 메인
# ============================================================
def main():
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        return 1

    print(f"🚀 크롤러 시작")
    print(f"   모델: {GEMINI_MODEL}")
    print(f"   기업: {len(COMPANIES)}개")
    print(f"   RPM 한도: {RPM_LIMIT}\n")

    articles_db = load_json(ARTICLES_JSON, [])
    seen_urls = set(load_json(SEEN_URLS_JSON, []))
    rate_limiter = RateLimiter(RPM_LIMIT)

    # 기존 articles.json 에서도 새로 추가된 JUNK 기준으로 재청소
    # (예전에 통과됐던 투자분석 기사 등 회수)
    before_clean = len(articles_db)
    articles_db = [
        a for a in articles_db
        if not any(k in a.get("title", "") for k in JUNK_KEYWORDS)
    ]
    junk_removed = before_clean - len(articles_db)
    if junk_removed > 0:
        print(f"🧹 기존 DB 청소: 새 필터 기준으로 {junk_removed}건 제거")

    # 추적 대상에서 빠진 회사(예: 중국 업체 제외 시)의 과거 기사도 정리
    valid_names = {c["name"] for c in COMPANIES}
    before_co = len(articles_db)
    articles_db = [a for a in articles_db if a.get("company") in valid_names]
    co_removed = before_co - len(articles_db)
    if co_removed > 0:
        print(f"🧹 추적 대상 외 기업 기사 {co_removed}건 제거")
    if junk_removed or co_removed:
        print()

    quota_dead = False
    new_count = 0
    api_calls = 0
    start_ts = time.time()

    # 이어 시작: 마지막에 멈춘 위치부터 다시 시작 (한도 소진으로 뒤쪽 기업이 영영 안 잡히는 문제 해결)
    state = load_json(STATE_JSON, {"start_index": 0})
    start_idx = state.get("start_index", 0)
    if not isinstance(start_idx, int) or start_idx < 0:
        start_idx = 0
    start_idx = start_idx % len(COMPANIES)

    if start_idx > 0:
        companies_order = COMPANIES[start_idx:] + COMPANIES[:start_idx]
        print(f"📍 이어 시작: {start_idx+1}번 ({COMPANIES[start_idx]['name']}) 부터\n")
    else:
        companies_order = COMPANIES
        print(f"📍 처음부터 시작 (1번 ~ {len(COMPANIES)}번)\n")

    for ci, comp in enumerate(companies_order, 1):
        actual_idx = (start_idx + ci - 1) % len(COMPANIES)
        name = comp["name"]
        print(f"[{ci}/{len(companies_order)}] {name}")

        # 1) RSS
        candidates = fetch_news(name, seen_urls)
        if not candidates:
            print(f"   💨 신규 후보 없음")
            continue
        print(f"   📦 신규 후보 {len(candidates)}개 → Gemini 배치 분석")

        # 2) Gemini 배치 호출
        results = analyze_articles_batch(name, candidates, rate_limiter)
        api_calls += 1

        if results == "QUOTA_DEAD":
            print(f"\n🚨 일일 한도 소진 감지 — 조기 종료 (수집한 부분까지 저장)")
            print(f"   📍 다음 실행은 {actual_idx+1}번 ({name}) 부터 이어집니다")
            save_json(STATE_JSON, {"start_index": actual_idx})
            quota_dead = True
            break

        if results is None:
            print(f"   ⚠️ 이번 실행에서는 스킵 (다음 실행 시 재시도)")
            continue

        # 3) 결과 반영
        for art, res in zip(candidates, results):
            seen_urls.add(art["link"])
            verdict = res["verdict"]
            if verdict == "PASS" and res["summary"]:
                print(f"   ✅ PASS  | {art['title'][:50]}")
                articles_db.append({
                    "company": name,
                    "title": art["title"],
                    "link": art["link"],
                    "published": art["published"],
                    "timestamp": art["timestamp"],
                    "summary": res["summary"]
                })
                new_count += 1
            elif verdict == "DUPLICATE":
                print(f"   🚫 DUP   | {art['title'][:50]}")
            else:
                print(f"   🗑️  IRR   | {art['title'][:50]}")

    # ============================================================
    # 정리 — 오래된 기사 제거 + 링크 기준 중복 제거
    # ============================================================
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=DAYS_TO_KEEP)).timestamp())
    before = len(articles_db)
    seen_links = set()
    cleaned = []
    for a in sorted(articles_db, key=lambda x: x.get("timestamp", 0), reverse=True):
        if a.get("timestamp", 0) < cutoff_ts:
            continue
        if a["link"] in seen_links:
            continue
        seen_links.add(a["link"])
        cleaned.append(a)
    articles_db = cleaned
    pruned = before - len(articles_db)

    # seen_urls 크기 관리 (10000건 넘으면 최근 7000건만 유지 — 단순 컷)
    if len(seen_urls) > 10000:
        seen_urls = set(list(seen_urls)[-7000:])

    save_json(ARTICLES_JSON, articles_db)
    save_json(SEEN_URLS_JSON, sorted(seen_urls))
    # 정상 완료(118개 다 돌았으면) state 리셋하여 다음 실행은 1번부터
    if not quota_dead:
        save_json(STATE_JSON, {"start_index": 0})
    rebuild_html(articles_db)

    elapsed = time.time() - start_ts
    print(f"\n{'='*60}")
    print(f"✨ 완료 ({elapsed:.1f}초)")
    print(f"   신규 추가: {new_count}건")
    print(f"   API 호출:  {api_calls}회 (Gemini 배치)")
    print(f"   현재 보관: {len(articles_db)}건")
    print(f"   정리 제거: {pruned}건")
    print(f"   조기 종료: {'예' if quota_dead else '아니오'}")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    exit(main())
