import os
import json
import gspread
import smtplib
from email.mime.text import MIMEText
from newsapi import NewsApiClient
from google import genai  # 최신 구글 제미나이 SDK
from datetime import datetime, timedelta

# =================================================================
# 1. 환경 변수 설정
# =================================================================
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
SERVICE_ACCOUNT_JSON = os.environ.get('SERVICE_ACCOUNT_JSON')

# 비서들을 깨웁니다!
newsapi = NewsApiClient(api_key=NEWS_API_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

def get_stock_keywords():
    """구글 시트에서 감시할 주식 리스트를 읽어옵니다."""
    try:
        service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
        gc = gspread.service_account_from_dict(service_account_info)
        
        # [형님 확인] 시트 이름("test")과 탭 이름("주식키워드") 확인!
        sh = gc.open("test") 
        worksheet = sh.worksheet("주식키워드")
        
        records = worksheet.get_all_records()
        if not records:
            return []

        # 열 이름 공백 제거 (안전장치)
        clean_records = []
        for r in records:
            clean_row = {str(k).strip(): v for k, v in r.items()}
            clean_records.append(clean_row)
        return clean_records
    except Exception as e:
        print(f"시트 읽기 에러: {e}")
        return []

def fetch_news(ticker, name):
    """
    최신 뉴스를 가져옵니다. 
    [수정] 검색 기간을 최근 3일로 늘려 데이터 부족 문제를 해결했습니다!
    """
    # 3일 전 날짜 계산
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    
    try:
        news = newsapi.get_everything(
            q=f"{ticker} OR {name}", 
            from_param=three_days_ago, 
            language='en', 
            sort_by='relevancy'
        )
        return news['articles'][:5]
    except Exception as e:
        print(f"뉴스 수집 에러: {e}")
        return []

def summarize_with_gemini(ticker, news_list):
    """
    [핵심 수정] 제미나이 모델 이름을 'gemini-2.0-flash'로 변경했습니다.
    또한 요약 실패 시 뉴스 원문 제목이라도 반환하도록 개선했습니다.
    """
    # 수집된 뉴스 제목들을 합칩니다.
    news_titles = "\n".join([f"- {n['title']}" for n in news_list])
    news_full_text = "\n".join([f"제목: {n['title']}\n내용: {n['description']}" for n in news_list])
    
    prompt = f"""
    당신은 세계 최고의 주식 분석가입니다. {ticker} 관련 뉴스를 읽고 한국어로 정리해 주세요.
    1. 핵심 요약 3줄 (강렬하게!)
    2. 투자 심리 (긍정/중립/부정 중 선택)
    
    뉴스 내용:
    {news_full_text}
    """
    
    try:
        # [모델 이름 변경] 1.5-flash 대신 2.0-flash를 사용해 404 에러를 방지합니다!
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        # AI 요약이 실패하면 뉴스 제목 리스트라도 보여줍니다!
        return f"⚠️ AI 요약 시도 중 에러가 났지만, 수집된 뉴스 제목은 이렇습니다:\n{news_titles}\n(에러 내용: {e})"

def send_email(content):
    """최종 리포트 발송"""
    msg = MIMEText(content)
    msg['Subject'] = f"[{datetime.now().strftime('%Y-%m-%d')}] 형님! 오늘의 주식 리포트 (A/S 완료!) 💰"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# =================================================================
# 실행부
# =================================================================
if __name__ == "__main__":
    print("🚀 작업을 시작합니다, 형님!!")
    
    stocks = get_stock_keywords()
    
    if not stocks:
        print("데이터가 없습니다.")
    else:
        total_report = "🌟 형님! A/S 완료된 오늘의 주식 분석입니다! 🌟\n\n"
        
        for stock in stocks:
            if stock.get('Status') == 'Active':
                ticker = stock.get('Ticker')
                name = stock.get('Name')
                
                print(f"🔍 {name}({ticker}) 분석 중...")
                news = fetch_news(ticker, name)
                
                if news:
                    summary = summarize_with_gemini(ticker, news)
                    total_report += f"📊 [{ticker} - {name}]\n{summary}\n"
                else:
                    total_report += f"📊 [{ticker} - {name}]\n최근 3일간 큰 뉴스가 없네요. 평온한 상태입니다! 😎\n"
                
                total_report += "="*40 + "\n"
        
        send_email(total_report)
        print("✅ 형님! 메일 다시 보냈습니다! 이번엔 성공일 겁니다!!")
