import os
import smtplib
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# =================================================================
# [형님 설정 포인트] 깃허브 Secrets에 이 두가지만 정확히 있으면 됩니다!
# =================================================================
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

# 형님이 지정하신 무적의 16개 브랜드 리스트
BRANDS = [
    "애플", "마이크로소프트", "엔비디아", "알파벳", "아마존", 
    "메타", "테슬라", "브로드컴", "일라이 릴리", "비자", 
    "존슨앤존슨", "오라클", "버크셔 해서웨이", "팔란티어", "월마트", "코스트코"
]

def fetch_google_news(brand):
    """
    구글 뉴스에서 브랜드별 주식 관련 뉴스를 3개씩 크롤링합니다.
    한국어로 검색하므로 별도의 번역이 필요 없습니다!
    """
    query = f"{brand} 주식"
    # 구글 뉴스 RSS URL (한국어 설정)
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")[:3] # 상위 3개 추출
        
        news_list = []
        for item in items:
            title = item.title.text
            # 구글 뉴스 링크는 정제가 필요할 수 있지만 RSS 링크는 바로 사용 가능합니다.
            link = item.link.text
            news_list.append({"title": title, "link": link})
        return news_list
    except Exception as e:
        print(f"❌ {brand} 크롤링 실패: {e}")
        return []

if __name__ == "__main__":
    print("🚀 형님! 무적의 16개 종목 크롤링을 시작합니다!!")
    
    # HTML 이메일 본문 시작
    html_body = f"""
    <html>
    <body style="font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
            <h2 style="color: #2c3e50; border-bottom: 3px solid #e74c3c; padding-bottom: 10px;">🔥 오늘의 필승 종목 뉴스 (16선)</h2>
            <p style="font-size: 14px; color: #666;">제목을 클릭하면 해당 뉴스 페이지로 즉시 이동합니다.</p>
    """

    for brand in BRANDS:
        print(f"🔍 {brand} 뉴스 수집 중...")
        news_data = fetch_google_news(brand)
        
        html_body += f"""
        <div style="margin-top: 20px; padding: 10px; background-color: #f9f9f9; border-radius: 5px;">
            <strong style="font-size: 17px; color: #2980b9;">📍 {brand}</strong>
            <ul style="margin-top: 10px; padding-left: 20px;">
        """
        
        if not news_data:
            html_body += "<li>최근 소식이 없습니다.</li>"
        else:
            for news in news_data:
                # 🔗 하이퍼링크 적용: 제목에 링크를 걸어 깔끔하게 만듭니다.
                html_body += f"""
                <li style="margin-bottom: 8px;">
                    <a href="{news['link']}" style="text-decoration: none; color: #34495e; font-weight: bold;">
                        {news['title']}
                    </a>
                </li>
                """
        
        html_body += "</ul></div>"
        time.sleep(1) # 차단 방지를 위한 짧은 휴식

    html_body += """
            <p style="margin-top: 30px; font-size: 12px; color: #999; text-align: center;">
                형님! 오늘도 성투하십시오! 본 리포트는 실시간 크롤링으로 제작되었습니다.
            </p>
        </div>
    </body>
    </html>
    """

    # 메일 발송 로직
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"[{datetime.now().strftime('%m월 %d일')}] 형님! 요청하신 16대 우량주 뉴스 리포트입니다!"
    msg['From'], msg['To'] = EMAIL_ADDRESS, EMAIL_ADDRESS
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.send_message(msg)
        print("✅ 형님! 깔끔하게 메일 쏴드렸습니다!!")
    except Exception as e:
        print(f"❌ 발송 실패: {e}")
