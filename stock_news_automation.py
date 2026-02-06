import os, json, gspread, smtplib, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from newsapi import NewsApiClient
from google import genai  # 제목 번역을 위해 다시 출근시킵니다!
from datetime import datetime, timedelta

# [환경 변수] 
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
SERVICE_ACCOUNT_JSON = os.environ.get('SERVICE_ACCOUNT_JSON')

newsapi = NewsApiClient(api_key=NEWS_API_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

def get_stock_keywords():
    try:
        service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
        gc = gspread.service_account_from_dict(service_account_info)
        sh = gc.open("test") 
        worksheet = sh.worksheet("주식키워드")
        records = worksheet.get_all_records()
        return [{str(k).strip(): v for k, v in r.items()} for r in records if str(r.get('Status', '')).strip().lower() == 'active']
    except Exception as e:
        print(f"❌ 시트 에러: {e}")
        return []

def translate_titles(ticker, news_list):
    """영문 제목 리스트를 받아서 한글로 번역합니다."""
    if not news_list: return []
    
    # 제목들만 묶어서 한 번에 번역 요청 (API 호출 횟수 절약!)
    titles = "\n".join([f"- {n['title']}" for n in news_list])
    prompt = f"다음은 {ticker} 관련 주식 뉴스 제목이야. 핵심 의미를 살려 자연스러운 한국어로 번역해줘. 다른 설명 없이 번역된 리스트만 보내줘.\n\n{titles}"
    
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        translated = response.text.strip().split('\n')
        # 혹시 모를 개수 차이 방지
        return [t.strip('- ').strip() for t in translated][:len(news_list)]
    except:
        return [n['title'] for n in news_list] # 실패 시 원문 사용

def fetch_formatted_news(ticker, kor_name):
    """뉴스 수집 및 HTML 포맷팅"""
    three_days = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    try:
        news = newsapi.get_everything(q=ticker, from_param=three_days, language='en', sort_by='relevancy')
        articles = news.get('articles', [])[:3]
        
        if not articles:
            return "<p>최근 3일간 신규 뉴스가 없습니다. ✅</p>"
        
        # 제목 번역 실행
        translated_titles = translate_titles(ticker, articles)
        
        formatted_html = "<ul>"
        for i, (art, trans) in enumerate(zip(articles, translated_titles)):
            # 🔗 하이퍼링크 적용 (제목을 누르면 링크로 이동!)
            formatted_html += f"<li style='margin-bottom:10px;'><a href='{art['url']}' style='text-decoration:none; color:#1a73e8; font-weight:bold;'>{trans}</a><br><small style='color:#666;'>{art['title']}</small></li>"
        formatted_html += "</ul>"
        return formatted_html
    except Exception as e:
        return f"<p style='color:red;'>뉴스 수집 중 오류: {e}</p>"

if __name__ == "__main__":
    print("🚀 작업을 시작합니다, 형님!! (고급 번역 버전)")
    stocks = get_stock_keywords()
    
    # HTML 메일 본문 작성
    html_content = f"""
    <html>
    <body>
        <h2 style="color: #2c3e50;">🇺🇸 형님! 오늘의 월스트리트 현지 소식입니다!</h2>
        <p>현지 기사 제목을 한국어로 번역하고, 제목에 링크를 심어 깔끔하게 정리했습니다.</p>
        <hr>
    """
    
    for stock in stocks:
        t, n = stock.get('Ticker'), stock.get('Name')
        print(f"🔍 {n}({t}) 분석 중...")
        news_html = fetch_formatted_news(t, n)
        html_content += f"""
        <div style="margin-bottom: 30px; padding: 15px; border-left: 5px solid #2c3e50; background-color: #f9f9f9;">
            <h3 style="margin-top:0;">📊 [{t} - {n}]</h3>
            {news_html}
        </div>
        """
        time.sleep(12) # 번역 API를 위해 12초씩 휴식!

    html_content += "</body></html>"
    
    # 메일 발송 설정
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"[{datetime.now().strftime('%Y-%m-%d')}] 형님! 오늘의 글로벌 주식 리포트 💰"
    msg['From'], msg['To'] = EMAIL_ADDRESS, EMAIL_ADDRESS
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.send_message(msg)
        print("✅ 형님! 고급 리포트 발송 성공!!")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")
