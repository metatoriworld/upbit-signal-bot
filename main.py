import requests
import schedule
import time
from datetime import datetime

# ── 설정 ──
TELEGRAM_TOKEN = "여기에_토큰_입력"
CHAT_ID = "5054034975"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{8636493325:AAG5p1YUGQ71xVuLi0h8iyiOswA2rYIS3yM}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def get_markets():
    url = "https://api.upbit.com/v1/market/all"
    res = requests.get(url)
    markets = [m["market"] for m in res.json() if m["market"].startswith("KRW-")]
    return markets

def get_weekly_candles(market):
    url = f"https://api.upbit.com/v1/candles/weeks"
    params = {"market": market, "count": 70}
    res = requests.get(url, params=params)
    return res.json()

def calc_ma(candles, period):
    if len(candles) < period:
        return None
    closes = [c["trade_price"] for c in candles[:period]]
    return sum(closes) / period

def check_signal(market):
    try:
        candles = get_weekly_candles(market)
        if len(candles) < 65:
            return None

        # 이동평균 계산
        ma7  = calc_ma(candles, 7)
        ma30 = calc_ma(candles, 30)
        ma60 = calc_ma(candles, 60)

        if not all([ma7, ma30, ma60]):
            return None

        # 최신 캔들
        latest = candles[0]
        open_price  = latest["opening_price"]
        close_price = latest["trade_price"]

        # 조건 1: 역배열 (60 > 30 > 7)
        is_reverse = ma60 > ma30 > ma7

        # 조건 2: 캔들이 7일선 아래
        is_below_ma7 = close_price < ma7

        # 조건 3: 캔들 몸통 1% 미만
        body_pct = abs(close_price - open_price) / open_price * 100
        is_small_candle = body_pct < 1.0

        if is_reverse and is_below_ma7 and is_small_candle:
            return {
                "market": market,
                "close": close_price,
                "ma7": ma7,
                "ma30": ma30,
                "ma60": ma60,
                "body_pct": body_pct
            }
    except Exception as e:
        print(f"{market} 오류: {e}")
    return None

def scan_all():
    print(f"[{datetime.now()}] 스캔 시작...")
    send_telegram("🔍 주봉 스캔 시작...")

    markets = get_markets()
    signals = []

    for market in markets:
        result = check_signal(market)
        if result:
            signals.append(result)
        time.sleep(0.1)  # API 딜레이

    if signals:
        msg = f"📊 <b>주봉 스캔 완료</b> — {datetime.now().strftime('%Y.%m.%d')}\n"
        msg += f"총 {len(markets)}개 중 <b>{len(signals)}개 신호</b>\n"
        msg += "─" * 20 + "\n\n"

        for s in signals:
            coin = s["market"].replace("KRW-", "")
            msg += f"🎯 <b>{coin}</b>\n"
            msg += f"   종가:  {int(s['close']):,}원\n"
            msg += f"   7일선: {int(s['ma7']):,}원\n"
            msg += f"   30일선: {int(s['ma30']):,}원\n"
            msg += f"   60일선: {int(s['ma60']):,}원\n"
            msg += f"   몸통:  {s['body_pct']:.2f}%\n"
            msg += f"   배열:  🔴 역배열 60>30>7\n\n"

        send_telegram(msg)
    else:
        send_telegram(f"📊 스캔 완료 — 신호 없음 ({len(markets)}개 검사)")

    print(f"스캔 완료. 신호 {len(signals)}개")

# 매주 월요일 오전 9시 실행
schedule.every().monday.at("09:00").do(scan_all)

# 시작하자마자 1회 즉시 실행
print("봇 시작!")
send_telegram("✅ 업비트 신호봇 시작!")
scan_all()

while True:
    schedule.run_pending()
    time.sleep(60)
