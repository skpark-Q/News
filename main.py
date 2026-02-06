import os, smtplib, time, urllib.parse, requests
import yfinance as yf # 🔥 주가 데이터용
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# [환경 변수]
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

# 🔥 [형님 설정] 종목명, 티커, 제외 키워드 매핑
STOCK_MAP = {
    "애플": {"ticker": "AAPL", "exclude": ""},
    "마이크로소프트": {"ticker": "MSFT", "exclude": ""},
    "엔비디아": {"ticker": "NVDA", "exclude": ""},
    "알파벳": {"ticker": "GOOGL", "exclude": "유튜브"}, # 예: 유튜브 제외 원하시면 추가
    "아마존": {"ticker": "AMZN", "exclude": "밀림"},
    "메타": {"ticker": "META", "exclude": "메타버스 meta-verse"}, # 🔥 메타버스 제외
    "테슬라": {"ticker": "TSLA", "exclude": ""},
    "브로드컴": {"ticker": "AVGO", "exclude": ""},
    "일라이 릴리": {"ticker": "LLY", "exclude": ""},
    "비자": {"ticker": "V", "exclude": "입국 비자"}, # 🔥 비자 거절 등 뉴스 제외
    "존슨앤존슨": {"ticker": "JNJ", "exclude": ""},
    "오라클": {"ticker": "ORCL", "exclude": ""},
    "버크셔 해서웨이": {"ticker": "BRK-B", "exclude": ""},
    "팔란티어": {"ticker": "PLTR", "exclude": ""},
    "월마트": {"ticker": "WMT", "exclude": ""},
    "코스트코": {"ticker": "COST", "exclude": ""}
}

def get_stock_data(ticker):
    """실시간 주가, 등락률, 시가총액 정보를 가져옵니다."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        # 현재가, 등락률 계산
        current_price = info['last_price']
        prev_close = info['previous_close']
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        # 시가총액 (조 단위로 변환)
        mkt_cap = stock.info.get('marketCap', 0) / 1_000_000_000_000 # 조($) 단위
        
        return {
            "price": round(current_price, 2),
            "pct": round(change_pct, 2),
            "cap": round(mkt_cap, 2)
        }
    except:
        return {"price": "-", "pct": "-", "cap": "-"}

def fetch_filtered_news(brand, exclude_words):
    """불필요한 키워드를 제외하고 뉴스를 검색합니다."""
    query = f"{brand} 주식"
    if exclude_words:
        # 제외할 단어 앞에 -를 붙여 검색 엔진에 전달합니다.
        for word in exclude_words.split():
            query += f" -{word}"
            
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")[:3]
        return [{"title": i.title.text, "link": i.link.text} for i in items]
    except:
        return []

if __name__ == "__main__":
    print("🚀 형님! 고도화된 16개 종목 데이터 분석을 시작합니다!!")
    
    html_body = f"""
    <html>
    <body style="font-family: 'Malgun Gothic', sans-serif; color: #333;">
        <div style="max-width: 650px; margin: auto; padding: 20px; border: 1px solid #eee;">
            <h2 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">📈 월스트리트 오늘의 지표 & 뉴스</h2>
            <p style="font-size: 13px; color: #7f8c8d;">기준일: {datetime.now().strftime('%Y-%m-%d')}</p>
    """

    for brand, info in STOCK_MAP.items():
        print(f"📊 {brand} 데이터 및 뉴스 수집 중...")
        data = get_stock_data(info['ticker'])
        news_data = fetch_filtered_news(brand, info['exclude'])
        
        # 등락률에 따른 색상 결정
        color = "#e74c3c" if str(data['pct']) != "-" and data['pct'] > 0 else "#2980b9"
        
        html_body += f"""
        <div style="margin-top: 25px; padding: 15px; border-radius: 8px; background-color: #f8f9fa;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #ccc; padding-bottom: 8px; margin-bottom: 10px;">
                <strong style="font-size: 18px;">{brand} <span style="font-size: 13px; color: #888;">({info['ticker']})</span></strong>
                <span style="color: {color}; font-weight: bold; font-size: 16px;">
                    ${data['price']} ({data['pct']}%)
                </span>
            </div>
            <div style="font-size: 12px; color: #666; margin-bottom: 10px;">시가총액: 약 {data['cap']}조 달러</div>
            <ul style="margin: 0; padding-left: 18px; font-size: 14px;">
        """
        
        for news in news_data:
            html_body += f"<li style='margin-bottom: 6px;'><a href='{news['link']}' style='text-decoration: none; color: #34495e;'>{news['title']}</a></li>"
        
        html_body += "</ul></div>"
        time.sleep(1)

    html_body += "</div></body></html>"

    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"[{datetime.now().strftime('%m/%d')}] 형님! 16대 우량주 지표 및 필터링 뉴스입니다!"
    msg['From'], msg['To'] = EMAIL_ADDRESS, EMAIL_ADDRESS
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.send_message(msg)
        print("✅ 리포트 발송 완료!")
    except Exception as e:
        print(f"❌ 실패: {e}")
