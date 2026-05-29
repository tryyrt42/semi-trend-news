name: Semiconductor News Crawler

on:
  # 2시간마다 자동 실행 (when:1d 검색이라 자주 돌려도 API 부담 없음)
  schedule:
    - cron: '0 */2 * * *'
  # 수동 실행 버튼
  workflow_dispatch:

# 커밋/푸시를 위한 권한
permissions:
  contents: write

# 동시 실행 방지 (이전 실행 끝나기 전 새로 시작되면 대기)
concurrency:
  group: crawler
  cancel-in-progress: false

jobs:
  crawl:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run crawler
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          # 더 안정적인 RPD 한도가 필요하면 그대로, 품질이 더 필요하면 gemini-2.5-flash 로 교체
          GEMINI_MODEL: gemini-2.5-flash-lite
        run: python crawler.py

      - name: Commit & push if changed
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "41898533+github-actions[bot]@users.noreply.github.com"
          git add index.html articles.json seen_urls.json crawler_state.json
          if git diff --staged --quiet; then
            echo "변경 사항 없음 — 푸시 스킵"
          else
            git commit -m "🤖 뉴스 업데이트 $(date -u +'%Y-%m-%d %H:%M UTC')"
            git push
          fi
