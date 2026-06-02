"""
반도체 산업 뉴스 크롤러 (V8.0)
- Gemini 3.1 Flash-Lite (또는 Flash) 배치 처리
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
# 3.1-flash-lite: RPD 500 / 2.5-flash-lite: RPD 1000
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
# 모델별 일일 한도 (env 로 덮어쓰기 가능). 3.1-flash-lite=500
RPD_LIMIT = int(os.environ.get("RPD_LIMIT", "500"))

HTML_FILE = "index.html"
ARTICLES_JSON = "articles.json"
SEEN_URLS_JSON = "seen_urls.json"
STATE_JSON = "crawler_state.json"   # 이어 시작용 — 마지막 처리 위치 저장
DAILY_STATS_JSON = "daily_stats.json" # 오늘 누적 API 호출 수 추적

MAX_ARTICLES_PER_COMPANY = 8      # 일반 기업: 기업당 RSS 상위 N개 검토
MAX_ARTICLES_FOR_HOT = 20         # 핫 티커: 시세 기사가 도배해서 더 많이 봐야 함
DAYS_TO_KEEP = 30                 # 며칠 치 기사 보관 (DB 표시용)
SEARCH_DAYS = 2                   # RSS 검색 범위: 어제+오늘 (이틀치)
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
    {"id": "노바칩스", "name": "노바칩스"},
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
    # ============ EDA ============       # <--- 여기서부터
    {"id": "synopsys", "name": "Synopsys"},
    {"id": "cadence", "name": "Cadence"},
    {"id": "siemens", "name": "Siemens"}, # <--- 여기까지 추가하세요
]


# ============================================================
# 회사명 별칭 (한글 ↔ 영어 양방향 검색용)
# name 으로 검색 + 아래 별칭으로도 검색 → 결과 합침
# RSS 검색만 늘 뿐 Gemini 호출(RPD)은 회사당 1회로 동일
# ============================================================
ALIASES = {
    # --- 한국 (한글명 → 영문 별칭) ---
    "알파칩스": ["AlphaChips"],
    "에이디테크놀로지": ["ADTechnology", "AD Technology"],
    "가온칩스": ["Gaonchips"],
    "세미파이브": ["SemiFive"],
    "코아시아": ["CoAsia"],
    "에이직랜드": ["ASICLAND"],
    "칩스앤미디어": ["Chips&Media", "Chipsnmedia"],
    "패러데이": ["Faraday"],
    "퓨리오사AI": ["FuriosaAI", "Furiosa"],
    "리벨리온": ["Rebellions"],
    "딥엑스": ["DEEPX", "DeepX"],
    "파두": ["FADU"],
    "망고부스트": ["MangoBoost"],
    "사피온": ["SAPEON"],
    "모빌린트": ["Mobilint"],
    "오픈엣지테크": ["Openedges", "OpenEdges"],
    "씨유박스": ["CUbox"],
    "에이스테크놀로지": ["ACE Technologies"],
    "알에프에이치아이씨": ["RFHIC"],
    "와이솔": ["Wisol"],
    "이노칩테크놀로지": ["Innochips"],
    "픽셀플러스": ["Pixelplus"],
    "에스엘파워일렉트로닉스": ["SL Power"],
    "보스반도체": ["BOS Semiconductor"],
    "동운아나텍": ["Dongwoon Anatech"],
    "실리콘마이터스": ["Silicon Mitus"],
    "에이디반도체": ["AD Semiconductor"],
    "MagnaChip반도체": ["MagnaChip", "매그나칩"],
    "LX세미콘": ["LX Semicon"],
    "실리콘웍스": ["Silicon Works"],
    "아나패스": ["Anapass"],
    "라온텍": ["RAONTECH"],
    "제주반도체": ["Jeju Semiconductor"],
    "텔레칩스": ["Telechips"],
    "넥스트칩": ["Nextchip"],
    "에이비오브": ["ABOV", "어보브반도체"],
    "엠씨넥스": ["MCNEX"],
    "세코닉스": ["SEKONIX"],
    "자람테크놀로지": ["Jaram Technology"],
    "노바칩스": ["Novachips"],
    # --- 대만/해외 영문명 → 한글 별칭 ---
    "글로벌유니칩 (GUC)": ["GUC"],
    "Socionext": ["소시오넥스트"],
    "GCT Semiconductor": ["GCT", "지씨티"],
    "MediaTek": ["미디어텍"],
    "Novatek": ["노바텍"],
    "Realtek": ["리얼텍"],
    "Himax": ["하이맥스"],
    "Silicon Motion": ["실리콘모션"],
    "Phison": ["파이슨"],
    "Nuvoton": ["누보톤"],
    "Andes Technology": ["안데스"],
    # --- 미국 메이저 (영문 → 한글) ---
    "NVIDIA": ["엔비디아"],
    "AMD": ["에이엠디"],
    "Qualcomm": ["퀄컴"],
    "Broadcom": ["브로드컴"],
    "Marvell": ["마벨"],
    "Intel": ["인텔"],
    "Lattice": ["래티스"],
    "Cirrus Logic": ["시러스로직"],
    "Microchip": ["마이크로칩"],
    "Skyworks": ["스카이웍스"],
    "Qorvo": ["코보"],
    "Wolfspeed": ["울프스피드"],
    "Silicon Labs": ["실리콘랩스"],
    "MaxLinear": ["맥스리니어"],
    "Synaptics": ["시냅틱스"],
    "Texas Instruments": ["TI", "텍사스인스트루먼트"],
    "Analog Devices": ["ADI", "아나로그디바이스"],
    # --- 빅테크 (영문 → 한글) ---
    "Apple": ["애플"],
    "Google": ["구글"],
    "Amazon": ["아마존"],
    "Microsoft": ["마이크로소프트"],
    "Meta": ["메타"],
    "Tesla": ["테슬라"],
    "OpenAI": ["오픈AI"],
    # --- AI 신생 팹리스 ---
    "Tenstorrent": ["텐스토렌트"],
    "Cerebras": ["세레브라스"],
    "Groq": ["그록"],
    "SambaNova": ["삼바노바"],
    "Lightmatter": ["라이트매터"],
    # --- 유럽 ---
    "NXP": ["엔엑스피"],
    "STMicroelectronics": ["ST마이크로", "ST마이크로일렉트로닉스"],
    "Infineon": ["인피니언"],
    "Nordic": ["노르딕 반도체"],
    "u-blox": ["유블럭스"],
    "Melexis": ["멜렉시스"],
    "Bosch": ["보쉬"],
    # --- 일본 ---
    "Renesas": ["르네사스"],
    "Sony Semiconductor": ["소니 반도체"],
    "Rohm": ["로옴 반도체"],
    "Kioxia": ["키오시아"],
    "MegaChips": ["메가칩스"],
    # --- 파운드리 ---
    "Samsung Foundry": ["삼성 파운드리"],
    "TSMC": ["대만 TSMC"],
    "GlobalFoundries": ["글로벌파운드리"],
    "UMC": ["UMC 파운드리"],
    # --- EDA ---
    "Synopsys": ["시높시스", "시놉시스"],
    "Cadence": ["케이던스"],
    "Siemens": ["지멘스 EDA"],
}


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


def get_pacific_date():
    """Google API 한도 리셋 기준 — 태평양 자정 (KST 오후 4시)"""
    return (datetime.now(timezone.utc) - timedelta(hours=7)).strftime("%Y-%m-%d")

def load_daily_stats():
    stats = load_json(DAILY_STATS_JSON, {"date": "", "calls": 0})
    today = get_pacific_date()
    if stats.get("date") != today:
        stats = {"date": today, "calls": 0}
    return stats

def save_daily_stats(stats):
    save_json(DAILY_STATS_JSON, stats)


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
def build_search_query(term, company_name):
    """term(회사명 또는 별칭) 기준 검색어 생성"""
    base = f"{term} 반도체" if company_name in BIGTECH_NEEDS_FILTER else term
    return f"{base} when:{SEARCH_DAYS}d"

def get_search_terms(company_name):
    """회사명 + 별칭 전부 (중복 제거)"""
    terms = [company_name] + ALIASES.get(company_name, [])
    seen = set()
    uniq = []
    for t in terms:
        if t and t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq

def resolve_company(main_company_str, fallback_name):
    """
    Gemini가 준 주인공 회사명을 우리 리스트와 대조.
    - 주인공이 우리 리스트에 있으면 → 그 회사로 분류 (우선순위)
    - 없으면 → fallback_name (곁다리로 검색된 현재 회사)로 분류
    """
    if not main_company_str:
        return fallback_name
    s = main_company_str.lower()
    for comp in COMPANIES:
        cname = comp["name"]
        for term in get_search_terms(cname):
            t = term.lower()
            # 주인공 문자열에 회사명/별칭이 포함되거나 그 반대
            if t in s or s in t:
                return cname
    return fallback_name

def _parse_entry(entry, company_name, seen_urls, out_links, cutoff):
    """RSS 항목 1개를 검증·파싱. 통과하면 dict 반환, 아니면 None."""
    title = str(getattr(entry, "title", "")).strip()
    link = str(getattr(entry, "link", "")).strip()
    if not title or not link or link in seen_urls or link in out_links:
        return None

    # 발행처 추출
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

    # 1차 문지기
    if any(k in title for k in JUNK_KEYWORDS):
        seen_urls.add(link)
        return None
    if source and any(js in source for js in JUNK_SOURCES):
        seen_urls.add(link)
        return None

    pub_str = str(getattr(entry, "published", ""))
    pub_ts = 0
    try:
        t = email.utils.parsedate_tz(pub_str)
        if t:
            pub_ts = int(email.utils.mktime_tz(t))
            pub_dt = datetime.fromtimestamp(pub_ts, timezone.utc)
            if pub_dt < cutoff:
                seen_urls.add(link)
                return None
            kst = pub_dt + timedelta(hours=9)
            pub_str = kst.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass

    return {"title": title, "link": link, "published": pub_str, "timestamp": pub_ts}

def fetch_news(company_name, seen_urls):
    # 핫 티커는 더 많이 / 별칭 합산이 너무 커지지 않게 총량 캡
    limit = MAX_ARTICLES_FOR_HOT if company_name in HOT_COMPANIES else MAX_ARTICLES_PER_COMPANY
    total_cap = limit * 2  # 별칭 합산 시 후보 상한
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEARCH_DAYS + 1)

    out = []
    out_links = set()
    for term in get_search_terms(company_name):
        if len(out) >= total_cap:
            break
        query = build_search_query(term, company_name)
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"   ⚠️ RSS 실패 ({term}): {e}")
            continue
        if not getattr(feed, "entries", None):
            continue
        for entry in feed.entries[:limit]:
            parsed = _parse_entry(entry, company_name, seen_urls, out_links, cutoff)
            if parsed:
                out.append(parsed)
                out_links.add(parsed["link"])
                if len(out) >= total_cap:
                    break
    return out


# ============================================================
# Gemini 배치 분석
# ============================================================
def analyze_articles_batch(company_name, articles, rate_limiter, search_terms=None):
    """
    반환:
      list[dict]  — 각 기사에 대한 {"verdict": "PASS"/"IRRELEVANT"/"DUPLICATE", "summary": str}
      "QUOTA_DEAD" — 일일 한도 소진
      None        — 일시적 오류, 이번 회차 스킵
    """
    if not articles:
        return []

    # 검색에 쓴 이름들(회사명+별칭) — 제목 매칭 검증용
    if not search_terms:
        search_terms = [company_name]
    names_str = ", ".join(f'"{t}"' for t in search_terms)

    items_str = json.dumps(
        [{"id": i, "title": a["title"]} for i, a in enumerate(articles)],
        ensure_ascii=False
    )

    prompt = f"""당신은 깐깐한 반도체 산업 분석가입니다.
대상 기업: {company_name}
이 기업의 표기 명칭(별칭 포함): {names_str}

다음 기사 후보 목록을 분석하세요:
{items_str}

각 기사를 아래 기준으로 판정하고 **순수 JSON 배열로만** 응답하세요 (앞뒤 설명 금지, 코드블록 금지):

판정:
- "IRRELEVANT": 아래 중 하나라도 해당하면 무조건 IRRELEVANT
   (a) **제목에 대상 기업명({names_str}) 중 하나가 전혀 등장하지 않는 기사** — 본문에 언급됐을 것 같아도 제목에 없으면 IRRELEVANT.
   (b) 투자분석/투자의견/종목분석/차트분석/추천종목 등 **투자자·주주 대상** 기사
   (c) "○○ 투자분석 YYYY.MM.DD", "○○ 주가 전망", "관심종목 ○선" 같은 자동생성/리포트성 제목
   (d) 주가·시세·실적 숫자만 다루는 기사 (사업/기술 내용 없음)
   (e) 반도체/팹리스/파운드리/디자인하우스/AI칩 생태계와 무관한 일반 가십·연예·소비재
   (f) 제목이 너무 짧고 모호해서 반도체 사업/기술 관련성 판단이 안 되는 경우
- "DUPLICATE": 같은 목록 안에서 같은 사건을 반복 보도 — 가장 먼저 등장한 1건만 PASS, 나머지는 DUPLICATE
- "PASS": 위에 안 걸리고, 제목에 대상 기업명이 있으며, 명백한 반도체 **사업/기술/제품/계약/투자유치/공장/인사/IPO** 관련 기사

[중요 — 주인공(main_company) 판별]
각 기사 제목의 **진짜 주인공(주어)** 회사명을 "main_company" 필드에 적으세요.
- 제목 맨 앞 또는 핵심 주체가 되는 회사명을 그대로 (제목에 쓰인 표기 그대로)
- 대상 기업({company_name})이 주인공이면 그 이름을, 다른 회사가 주인공이면 그 회사명을 적기
- 곁다리(비교 대상·협력사·단순 언급)는 주인공이 아님

예시:
- 제목="하나마이크론, ECTC 우수논문상...삼성·TSMC와 나란히 선정"
  → main_company="하나마이크론" (TSMC는 곁다리)
- 제목="엔비디아, 신형 GPU 공개"
  → main_company="엔비디아"
- 제목="어드밴텍, NVIDIA-퀄컴과 손잡고 AI 확대"
  → main_company="어드밴텍" (NVIDIA·퀄컴은 곁다리)

핵심 원칙: 애매하면 IRRELEVANT. 투자분석/리포트류는 어떤 경우에도 PASS 금지.

[summary 작성 규칙 — PASS인 경우에만]
- 2~3문장, 한국어 100자 이내로 짧게.
- **제목에 명시적으로 드러난 사실만** 사용. 산업 배경·시사점·전망 등 추론·추측은 절대 금지.
- 제목에 없는 회사명/숫자/제품명/시점 등을 임의로 보충하지 말 것.
- 제목이 이미 충분히 구체적이면 그대로 자연스러운 문장으로 다듬는 수준이면 됨.
- "~로 보인다", "~할 가능성", "~할 전망" 같은 추정 표현 사용 금지.

응답 포맷:
[
  {{"id": 0, "verdict": "PASS", "summary": "제목 기반 짧은 요약", "main_company": "주인공 회사명"}},
  {{"id": 1, "verdict": "IRRELEVANT", "summary": "", "main_company": ""}}
]
PASS 가 아닌 항목은 summary, main_company 모두 빈 문자열로.
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
                    "summary": str(item.get("summary", "")).strip(),
                    "main_company": str(item.get("main_company", "")).strip()
                }
        for i in range(len(results)):
            if results[i] is None:
                results[i] = {"verdict": "IRRELEVANT", "summary": "", "main_company": ""}
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


def update_timestamp(html_str, new_count=0, quota_dead=False, total_count=0):
    """타임스탬프를 정직하게 표시. 신규 0건이면 '시도만 함' 명시."""
    now_kst = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
    if quota_dead and new_count == 0:
        status = f"⚠️ {now_kst} (KST) · 한도 소진으로 신규 0건 · 보관 {total_count}건"
    elif new_count == 0:
        status = f"{now_kst} (KST) · 신규 0건 · 보관 {total_count}건"
    else:
        status = f"{now_kst} (KST) · 신규 {new_count}건 추가 · 보관 {total_count}건"
    return re.sub(
        r'<div class="updated-time">.*?</div>',
        f'<div class="updated-time">최근 업데이트: {status}</div>',
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


def rebuild_html(articles_db, new_count=0, quota_dead=False):
    if not os.path.exists(HTML_FILE):
        print(f"⚠️ {HTML_FILE} 없음 — HTML 갱신 스킵")
        return
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    content = replace_feed_contents(content, render_feed_html(articles_db))
    content = update_timestamp(content, new_count=new_count, quota_dead=quota_dead, total_count=len(articles_db))
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
    daily_stats = load_daily_stats()

    # 오늘 누적 RPD 현황 출력
    rpd_used = daily_stats["calls"]
    rpd_pct = (rpd_used / RPD_LIMIT * 100) if RPD_LIMIT else 0
    if rpd_used == 0 or rpd_pct < 50:
        rpd_status = "✅ 여유"
    elif rpd_pct < 80:
        rpd_status = "⚠️ 주의"
    else:
        rpd_status = "🚨 위험"
    print(f"📊 오늘 RPD: {rpd_used} / ~{RPD_LIMIT:,}회 ({rpd_pct:.0f}%) {rpd_status}\n")

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

    # 제목에 회사명/별칭이 전혀 없는 기사 제거 (별칭 검색 부작용 청소)
    before_name = len(articles_db)
    kept = []
    for a in articles_db:
        company = a.get("company", "")
        title = a.get("title", "")
        terms = get_search_terms(company)
        # 대소문자 무시 매칭
        title_low = title.lower()
        if any(t.lower() in title_low for t in terms):
            kept.append(a)
    articles_db = kept
    name_removed = before_name - len(articles_db)
    if name_removed > 0:
        print(f"🧹 제목에 회사명 없는 기사 {name_removed}건 제거")

    if junk_removed or co_removed or name_removed:
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
        results = analyze_articles_batch(name, candidates, rate_limiter, get_search_terms(name))
        api_calls += 1
        daily_stats["calls"] += 1

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
                # 주인공 우선순위: 주인공이 리스트에 있으면 그 회사, 없으면 현재 검색 회사
                assigned = resolve_company(res.get("main_company", ""), name)
                tag = "" if assigned == name else f" → {assigned}"
                print(f"   ✅ PASS  | {art['title'][:50]}{tag}")
                articles_db.append({
                    "company": assigned,
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
    save_daily_stats(daily_stats)
    # 정상 완료(118개 다 돌았으면) state 리셋하여 다음 실행은 1번부터
    if not quota_dead:
        save_json(STATE_JSON, {"start_index": 0})
    rebuild_html(articles_db, new_count=new_count, quota_dead=quota_dead)

    elapsed = time.time() - start_ts
    print(f"\n{'='*60}")
    print(f"✨ 완료 ({elapsed:.1f}초)")
    print(f"   신규 추가: {new_count}건")
    print(f"   API 호출:  {api_calls}회 (이번 실행) / 오늘 누적 {daily_stats['calls']}회 / ~{RPD_LIMIT:,}회 한도")
    print(f"   현재 보관: {len(articles_db)}건")
    print(f"   정리 제거: {pruned}건")
    print(f"   조기 종료: {'예' if quota_dead else '아니오'}")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    exit(main())
