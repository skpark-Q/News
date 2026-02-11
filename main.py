import os, smtplib, time, urllib.parse, requests, re
import yfinance as yf
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# [환경 변수]
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

STOCK_MAP = {
    "애플": "AAPL", "마이크로소프트": "MSFT", "엔비디아": "NVDA", "알파벳": "GOOGL",
    "아마존": "AMZN", "메타": "META", "테슬라": "TSLA", "브로드컴": "AVGO",
    "일라이 릴리": "LLY", "비자": "V", "존슨앤존슨": "JNJ", "오라클": "ORCL",
    "버크셔 해서웨이": "BRK-B", "팔란티어": "PLTR", "월마트": "WMT", "코스트코": "COST"
}

def get_market_summary():
    """상단 시장 지표 (나스닥, S&P500, VIX)"""
    try:
        results = []
        for name, tk in {"나스닥": "^IXIC", "S&P500": "^GSPC", "공포지수(VIX)": "^VIX"}.items():
            s = yf.Ticker(tk)
            f = s.fast_info
            curr = f['last_price']
            pct = ((curr - f['previous_close']) / f['previous_close']) * 100
            
            color = "#111"
            if name == "공포지수(VIX)":
                color = "#1a73e8" if curr < 20 else ("#f9ab00" if curr < 30 else "#d93025")
                results.append(f"{name}: <b style='color:{color};'>{curr:.2f}</b>")
            else:
                idx_color = "#d93025" if pct > 0 else "#1a73e8"
                results.append(f"{name}: <b style='color:{idx_color};'>{pct:+.2f}%</b>")
        return " | ".join(results)
    except: return "데이터 로딩 중..."

def get_stock_details(ticker):
    """주가, 체력, 전문가 의견 등 정밀 수집"""
    try:
        s = yf.Ticker(ticker)
        f, info = s.fast_info, s.info
        curr, prev = f['last_price'], f['previous_close']
        pct = ((curr - prev) / prev) * 100
        
        # 1. 상승여력 (Upside)
        target = info.get('targetMeanPrice', 0)
        upside_val = ((target / curr) - 1) * 100 if target > 0 else 0
        u_color = "#1a73e8" if upside_val > 15 else ("#d93025" if upside_val < 0 else "#333")
        
        # 2. PER 및 배당률 (배당률 오류 수정!)
        per = info.get('trailingPE', 0)
        div = info.get('dividendYield')
        if div is None: div_val = 0.0
        else: div_val = div * 100 if div < 1 else div # 소수점/정수 데이터 구분 대응
        
        # 3. [신규] 52주 저점 대비 현재 위치 (바닥 판단)
        low_52w = f['year_low']
        dist_from_low = ((curr / low_52w) - 1) * 100
        
        # 4. [신규] 전문가 투자의견
        recommend = info.get('recommendationKey', 'N/A').replace('_', ' ').upper()

        flags = []
        if abs(pct) >= 3.5: flags.append("⚠️")
        if curr >= (f['year_high'] * 0.98): flags.append("✨")
        try:
            if not s.calendar.empty:
                days_left = (s.calendar.iloc[0, 0] - datetime.now().date()).days
                if 0 <= days_left <= 7: flags.append("🚩")
        except: pass

        return {
            "price": f"{curr:,.2f}", "pct": round(pct, 2), "flags": "".join(flags),
            "upside": f"{upside_val:+.1f}%", "u_color": u_color,
            "per": f"{per:.1f}" if isinstance(per, (int, float)) else "-",
            "div": f"{div_val:.2f}%",
            "dist_low": f"{dist_from_low:.1f}%",
            "opinion": recommend,
            "cap": f"{info.get('marketCap', 0) / 1_000_000_000_000:,.1f}T"
        }
    except: return None

def fetch_korean_news(brand):
    """뉴스 크롤링"""
    q = urllib.parse.quote(f"{brand} 주식 분석")
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.content, "xml")
        links = []
        for i in soup.find_all("item"):
            if bool(re.search('[가-힣]', i.title.text)):
                links.append(f"<li style='margin-bottom:5px;'><a href='{i.link.text}' style='color:#333; text-decoration:none; font-size:13px;'>• {i.title.text}</a></li>")
            if len(links) >= 3: break
        return "".join(links)
    except: return "<li>뉴스 정보 없음</li>"

if __name__ == "__main__":
    m_context = get_market_summary()
    html = f"""
    <html>
    <body style="font-family: 'Malgun Gothic', sans-serif; background-color: #ffffff; padding: 20px;">
        <div style="max-width: 650px; margin: auto; border: 1px solid #000; padding: 25px;">
            <h1 style="border-bottom: 4px solid #111; padding-bottom: 10px; margin: 0;">🏛️ VIP 주식 전략 리포트</h1>
            
            <div style="background: #f1f1f1; padding: 15px; margin-top: 20px; font-size: 12px; border-left: 5px solid #333;">
                <b>[📊 가이드]</b> VIX 20미만(🔵안정) / PER 25이하(🔵저평가) / 52주 저점 대비(0%에 가까울수록 바닥)<br>
                🚩실적임박 | ⚠️변동성주의 | ✨신고가근접
            </div>
            <p style="padding: 10px; background: #333; color:#fff; font-size: 14px; margin-top: 15px;"><b>🌍 시장 현황:</b> {m_context}</p>
    """

    for brand, ticker in STOCK_MAP.items():
        d = get_stock_details(ticker)
        if not d: continue
        news = fetch_korean_news(brand)
        
        # [형님 요청] 음영 처리: 상승은 연한 빨강, 하락은 연한 파랑
        header_bg = "#fce8e6" if d['pct'] > 0 else "#e8f0fe"
        text_color = "#d93025" if d['pct'] > 0 else "#1a73e8"

        html += f"""
        <div style="margin-top: 25px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
            <div style="background: {header_bg}; padding: 12px; display: flex; justify-content: space-between; align-items: center;">
                <b style="font-size: 18px; color: #111;">{brand} <small style="color:#666;">{ticker}</small> {d['flags']}</b>
                <div style="text-align: right;">
                    <b style="color:{text_color}; font-size: 19px;">{d['pct']:+.2f}%</b>
                    <div style="font-size: 13px; color: #111;">${d['price']}</div>
                </div>
            </div>
            
            <div style="padding: 12px; background: #fff;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px; border-bottom: 1px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 10px;">
                    <div>• 상승여력: <b style="color:{d['u_color']};">{d['upside']}</b></div>
                    <div>• 52주 저점 대비: <b>{d['dist_low']}</b></div>
                    <div>• PER: <b>{d['per']}배</b> / 배당: <b>{d['div']}</b></div>
                    <div>• 투자의견: <b style="color:#d93025;">{d['opinion']}</b></div>
                </div>
                <ul style="margin: 0; padding-left: 18px;">{news}</ul>
            </div>
        </div>
        """
        time.sleep(0.5)

    html += "</div></body></html>"

    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"[{datetime.now().strftime('%m/%d')}] 🏛️ 형님! 바닥권 종목 포함 VIP 리포트입니다."
    msg['From'], msg['To'] = EMAIL_ADDRESS, EMAIL_ADDRESS
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        s.send_message(msg)
    print("✅ 발송 완료!")
