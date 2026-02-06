import os, smtplib, time, urllib.parse, requests
import yfinance as yf
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# [환경 변수 설정]
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

# 🔥 [형님 맞춤] 노이즈 제로! 정밀 필터링 맵
STOCK_MAP = {
    "애플": {"ticker": "AAPL", "exclude": "사과 레시피 다이어트 과일"},
    "마이크로소프트": {"ticker": "MSFT", "exclude": ""},
    "엔비디아": {"ticker": "NVDA", "exclude": ""},
    "알파벳": {"ticker": "GOOGL", "exclude": "영어 교육 학습 유치원"},
    "아마존": {"ticker": "AMZN", "exclude": "정글 열대우림 브라질"},
    "메타": {"ticker": "META", "exclude": "메타버스 meta-verse 가상현실"},
    "테슬라": {"ticker": "TSLA", "exclude": "니콜라 발명가"},
    "브로드컴": {"ticker": "AVGO", "exclude": ""},
    "일라이 릴리": {"ticker": "LLY", "exclude": ""},
    "비자": {"ticker": "V", "exclude": "입국 여권 발급 거절 신청 여행"}, # 가장 중요!
    "존슨앤존슨": {"ticker": "JNJ", "exclude": "베이비파우더"}, # 소송 이슈 외 제품 리뷰 제외
    "오라클": {"ticker": "ORCL", "exclude": "예언 점괘 게임"},
    "버크셔 해서웨이": {"ticker": "BRK-B", "exclude": ""},
    "팔란티어": {"ticker": "PLTR", "exclude": "반지의제왕 판타지"},
    "월마트": {"ticker": "WMT", "exclude": "사고 사건"},
    "코스트코": {"ticker": "COST", "exclude": "레시피 요리"}
}

def get_stock_data(ticker):
    """실시간 주가 및 주요 지표 수집"""
    try:
        stock = yf.Ticker(ticker)
        # fast_info를 통해 속도 개선
        fast = stock.fast_info
        current_price = fast['last_price']
        prev_close = fast['previous_close']
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        # 시가총액 (조 단위)
        mkt_cap = stock.info.get('marketCap', 0) / 1_000_000_000_000
        
        return {
            "price": f"{current_price:,.2f}",
            "pct": round(change_pct, 2),
            "cap": round(mkt_cap, 2)
        }
    except:
        return {"price": "-", "pct": "-", "cap": "-"}

def fetch_filtered_news(brand, exclude_words):
    """노이즈 단어를 -키워드로 제외하여 검색합니다."""
    # "브랜드 주식"을 기본으로 하되, 제외 단어들 앞에 -를 붙여 구글 엔진에 전달
    query = f"{brand} 주식"
    if exclude_words:
        for word in exclude_words.split():
            query += f" -{word}"
            
    encoded_query = urllib.parse.quote(query)
    # 구글 뉴스 RSS (한국어/한국 지역 설정)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")[:3]
        return [{"title": i.title.text, "link": i.link.text} for i in items]
    except:
        return []

if __name__ == "__main__":
    print("🚀 작업을 시작합니다, 형님!! (노이즈 필터링 강화 버전)")
    
    html_body = f"""
    <html>
    <body style="font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 650px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 12px;">
            <h2 style="color: #2c3e50; border-bottom: 3px solid #e74c3c; padding-bottom: 10px;">📉 월스트리트 16대 우량주 리포트</h2>
            <p style="font-size: 13px; color: #888; text-align: right;">발행일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    """

    for brand, info in STOCK_MAP.items():
        print(f"📊 {brand} 진행 중...")
        data = get_stock_data(info['ticker'])
        news_data = fetch_filtered_news(brand, info['exclude'])
        
        # 등락률 색상 (상승 빨강, 하락 파랑)
        pct_val = data['pct']
        pct_color = "#e74c3c" if pct_val != "-" and pct_val > 0 else "#2980b9"
        pct_sign = "+" if pct_val != "-" and pct_val > 0 else ""

        html_body += f"""
        <div style="margin-top: 20px; padding: 15px; border-radius: 8px; background-color: #f8f9fa; border: 1px solid #eee;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 18px; font-weight: bold; color: #34495e;">{brand} <small style="color:#999;">({info['ticker']})</small></span>
                <span style="font-size: 17px; font-weight: bold; color: {pct_color};">
                    ${data['price']} ({pct_sign}{pct_val}%)
                </span>
            </div>
            <div style="font-size: 12px; color: #7f8c8d; margin-bottom: 10px;">시가총액: 약 {data['cap']}조 달러</div>
            <ul style="margin: 0; padding-left: 20px; font-size: 14px; border-top: 1px solid #eee; padding-top: 10px;">
        """
        
        if not news_data:
            html_body += "<li style='color:#bbb;'>관련 뉴스가 없습니다.</li>"
        else:
            for news in news_data:
                html_body += f"<li style='margin-bottom: 6px;'><a href='{news['link']}' style='text-decoration: none; color: #34495e;'>{news['title']}</a></li>"
        
        html_body += "</ul></div>"
        time.sleep(1) # 차단 방지

    html_body += "</div></body></html>"

    # 메일 발송
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"[{datetime.now().strftime('%m/%d')}] 형님! 노이즈 제거된 16대 주식 리포트입니다!"
    msg['From'], msg['To'] = EMAIL_ADDRESS, EMAIL_ADDRESS
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.send_message(msg)
        print("✅ 리포트 발송 성공!")
    except Exception as e:
        print(f"❌ 발송 실패: {e}")
