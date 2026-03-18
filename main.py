import os, smtplib, time, urllib.parse, requests, re
import yfinance as yf
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# [환경 변수 및 수신인 설정]
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

# 🔥 형님! 여기에 수신인 메일을 모두 담았습니다!
RECIPIENTS = [
    EMAIL_ADDRESS,           # 형님 본인
    "yhkwon@spigen.com",     # 파트너 1
    "jynoh@spigen.com",      # 파트너 2
    "mako@spigen.com",       # 파트너 3
    "jhkang@spigen.com"      # 파트너 4
]

# 16대 우량주 리스트
STOCK_MAP = {
    "애플": "AAPL", "마이크로소프트": "MSFT", "엔비디아": "NVDA", "알파벳": "GOOGL",
    "아마존": "AMZN", "메타": "META", "테슬라": "TSLA", "브로드컴": "AVGO",
    "일라이 릴리": "LLY", "비자": "V", "존슨앤존슨": "JNJ", "오라클": "ORCL",
    "버크셔 해서웨이": "BRK-B", "팔란티어": "PLTR", "월마트": "WMT", "코스트코": "COST"
}

def get_market_summary():
    """상단 지표: 나스닥, S&P500, VIX 분석"""
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
    except: return "시장 데이터 로딩 중..."

def get_stock_details(ticker):
    """주가, 체력, 한글 투자의견 데이터 수집"""
    try:
        s = yf.Ticker(ticker)
        f, info = s.fast_info, s.info
        curr, prev = f['last_price'], f['previous_close']
        pct = ((curr - prev) / prev) * 100
        
        target = info.get('targetMeanPrice', 0)
        upside_val = ((target / curr) - 1) * 100 if target > 0 else 0
        u_color = "#1a73e8" if upside_val > 15 else ("#d93025" if upside_val < 0 else "#111")
        
        per = info.get('trailingPE', 0)
        p_color = "#1a73e8" if (isinstance(per, (int, float)) and per < 25) else ("#d93025" if (isinstance(per, (int, float)) and per > 40) else "#f9ab00")
        
        div = info.get('dividendYield')
        if div is None: div_val = 0.0
        elif div > 0.1: div_val = div
        else: div_val = div * 100
        d_color = "#1a73e8" if div_val >= 3 else ("#f9ab00" if div_val >= 1 else "#d93025")
        
        dist_low = ((curr / f['year_low']) - 1) * 100
        l_color = "#1a73e8" if dist_low < 10 else ("#d93025" if dist_low > 30 else "#111")
        
        opinion_map = {
            'strong_buy': '강력 매수', 'buy': '매수', 
            'hold': '보유(중립)', 'underperform': '수익률 하회', 
            'sell': '매도', 'strong_sell': '강력 매도'
        }
        kor_opinion = opinion_map.get(info.get('recommendationKey', '').lower(), '의견 없음')

        flags = []
        if abs(pct) >= 3.5: flags.append("⚠️")
        if curr >= (f['year_high'] * 0.98): flags.append("✨")
        try:
            if not s.calendar.empty:
                if 0 <= (s.calendar.iloc[0, 0] - datetime.now().date()).days <= 7: flags.append("🚩")
        except: pass

        return {
            "price": f"{curr:,.2f}", "pct": round(pct, 2), "flags": "".join(flags),
            "upside": f"{upside_val:+.1f}%", "u_color": u_color,
            "per": f"{per:.1f}" if isinstance(per, (int, float)) else "-", "p_color": p_color,
            "div": f"{div_val:.2f}%", "d_color": d_color,
            "dist_low": f"{dist_low:+.1f}%", "l_color": l_color,
            "opinion": kor_opinion,
            "cap": f"{info.get('marketCap', 0) / 1_000_000_000_000:,.1f}T"
        }
    except: return None

def fetch_korean_news(brand):
    """당일 마감 소식 수집 (when:1d)"""
    query = urllib.parse.quote(f"{brand} 주식 (마감 OR 종가 OR 속보) when:1d")
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.content, "xml")
        links = []
        for i in soup.find_all("item"):
            if bool(re.search('[가-힣]', i.title.text)):
                links.append(f"<li style='margin-bottom:5px;'><a href='{i.link.text}' style='color:#111; text-decoration:none; font-size:13px;'>• {i.title.text}</a></li>")
            if len(links) >= 3: break
        
        if not links:
            q_fallback = urllib.parse.quote(f"{brand} 주식 분석 when:1d")
            url_f = f"https://news.google.com/rss/search?q={q_fallback}&hl=ko&gl=KR&ceid=KR:ko"
            res_f = requests.get(url_f, timeout=5)
            soup_f = BeautifulSoup(res_f.content, "xml")
            for i in soup_f.find_all("item")[:3]:
                links.append(f"<li style='margin-bottom:5px;'><a href='{i.link.text}' style='color:#111; text-decoration:none; font-size:13px;'>• {i.title.text}</a></li>")
        return "".join(links)
    except: return "<li>오늘의 분석 뉴스를 불러오지 못했습니다.</li>"

def fetch_general_headlines():
    """
    🔥 [정밀 필터링] 사회와 경제 뉴스를 각각 수집하여 중복 없이 섞어 7개를 만듭니다.
    """
    def get_news_from_query(sub_query, count):
        q = urllib.parse.quote(f"{sub_query} when:1d")
        u = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        found = []
        try:
            r = requests.get(u, timeout=5)
            s = BeautifulSoup(r.content, "xml")
            for item in s.find_all("item"):
                title = item.title.text
                if bool(re.search('[가-힣]', title)):
                    found.append({"title": title, "link": item.link.text})
                if len(found) >= count: break
        except: pass
        return found

    # 1. 사회 4개, 경제 3개를 각각 가져옵니다.
    society_news = get_news_from_query("사회 속보", 4)
    economy_news = get_news_from_query("경제 속보", 4) # 혹시 모를 중복을 대비해 넉넉히 수집

    # 2. 중복 제거 및 믹스
    combined = []
    seen_titles = set()

    for item in (society_news + economy_news):
        # 제목 앞뒤 공백 제거 및 중복 체크
        clean_title = item['title'].strip()
        if clean_title not in seen_titles:
            combined.append(f"<li style='margin-bottom:6px;'><a href='{item['link']}' style='color:#111; text-decoration:none; font-size:13px;'>• {clean_title}</a></li>")
            seen_titles.add(clean_title)
        if len(combined) >= 7: break

    return "".join(combined)

if __name__ == "__main__":
    m_context = get_market_summary()
    headlines_html = fetch_general_headlines()
    
    html = f"""
    <html>
    <body style="font-family: 'Malgun Gothic', sans-serif; background-color: #ffffff; padding: 20px;">
        <div style="max-width: 650px; margin: auto; border: 2px solid #111; padding: 25px; border-radius: 10px;">
            <h1 style="border-bottom: 4px solid #111; padding-bottom: 10px; margin: 0; text-align: center;">🏛️ VIP 주식 전략 리포트</h1>
            
            <div style="background: #f8f9fa; border: 1px solid #ddd; padding: 15px; margin-top: 20px; font-size: 12px; line-height: 1.6;">
                <b style="font-size: 14px; color: #111;">[📊 투자 지표 컬러 가이드]</b><br>
                • <b>상승여력:</b> 전문가 목표가 대비 <span style="color:#1a73e8;">15%↑(🔵기회)</span> / <span style="color:#d93025;">마이너스(🔴위험)</span><br>
                • <b>저점대비:</b> 52주 저점에서 <span style="color:#1a73e8;">10%이내(🔵바닥)</span> / <span style="color:#d93025;">30%↑(🔴과열)</span><br>
                • <b>PER:</b> <span style="color:#1a73e8;">25미만(🔵저평가)</span> / <span style="color:#d93025;">40초과(🔴고평가)</span><br>
                • <b>배당률:</b> <span style="color:#1a73e8;">3%↑(🔵혜자)</span> / <span style="color:#d93025;">1%미만(🔴낮음)</span>
            </div>

            <div style="margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 8px;">
                <b style="font-size: 15px; color: #111;">📰 사회/경제 주요 헤드라인 (7)</b>
                <ul style="margin: 10px 0 0 0; padding-left: 18px;">{headlines_html}</ul>
            </div>

            <p style="padding: 12px; background: #111; color:#fff; font-size: 14px; margin-top: 15px;"><b>🌍 오늘의 전장 상황:</b> {m_context}</p>
    """

    for brand, ticker in STOCK_MAP.items():
        d = get_stock_details(ticker)
        if not d: continue
        news = fetch_korean_news(brand)
        header_bg = "#fce8e6" if d['pct'] > 0 else "#e8f0fe"
        text_color = "#d93025" if d['pct'] > 0 else "#1a73e8"

        html += f"""
        <div style="margin-top: 25px; border: 1px solid #eee; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
            <div style="background: {header_bg}; padding: 15px; display: flex; justify-content: space-between; align-items: center;">
                <b style="font-size: 18px; color: #111;">{brand} <small style="color:#666;">{ticker}</small> {d['flags']}</b>
                <div style="text-align: right;">
                    <b style="color:{text_color}; font-size: 20px;">{d['pct']:+.2f}%</b>
                    <div style="font-size: 14px; font-weight:bold;">${d['price']}</div>
                </div>
            </div>
            <div style="padding: 15px; background: #fff;">
                <table style="width: 100%; font-size: 13px; margin-bottom: 12px;">
                    <tr><td>상승여력: <b style="color:{d['u_color']};">{d['upside']}</b></td><td>저점대비: <b style="color:{d['l_color']};">{d['dist_low']}</b></td></tr>
                    <tr><td>PER: <b style="color:{d['p_color']};">{d['per']}배</b></td><td>배당률: <b style="color:{d['d_color']};">{d['div']}</b></td></tr>
                    <tr><td>투자의견: <b>{d['opinion']}</b></td><td>시가총액: <b>{d['cap']}</b></td></tr>
                </table>
                <ul style="margin: 0; padding-left: 18px; border-top: 1px solid #f5f5f5; padding-top: 10px;">{news}</ul>
            </div>
        </div>
        """
        time.sleep(0.5)

    html += "</div></body></html>"
    
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"[{datetime.now().strftime('%m/%d')}] 🏛️ 형님! 전략 리포트 배달왔습니다!"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = ", ".join(RECIPIENTS)
    msg.attach(MIMEText(html, "html"))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.send_message(msg)
        print(f"✅ 사회/경제 정밀 믹스 및 중복 제거 완료! 총 {len(RECIPIENTS)}명 발송.")
    except Exception as e:
        print(f"❌ 발송 실패: {e}")
