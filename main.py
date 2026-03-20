import requests
import os
import time
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def get_markets():
    url = "https://api.upbit.com/v1/market/all"
    res = requests.get(url)
    return [m["market"] for m in res.json() if m["market"].startswith("KRW-")]

def get_weekly_candles(market):
    url = "https://api.upbit.com/v1/candles/weeks"
    res = requests.get(url, params={"market": market, "count": 70})
    return res.json()

def calc_ma(candles, period):
    if len(candles) < period:
        return None
    return sum(c["trade_price"] for c in candles[:period]) / period

def check_signal(market):
    try:
        candles = get_weekly_candles(market)
        if len(candles) < 65:
            return None
        ma7  = calc_ma(candles, 7)
        ma30 = calc_ma(candles, 30)
        ma60 = calc_ma(candles, 60)
        if not all([ma7, ma30, ma60]):
            return None
        latest = candles[0]
        open_price  = latest["opening_price"]
        close_price = latest["trade_price"]
        is_reverse      = ma60 > ma30 > ma7
        is_below_ma7    = close_price < ma7
        body_pct        = abs(close_price - open_price) / open_price * 100
        is_small_candle = body_pct < 1.0
        if is_reverse and is_below_ma7 and is_small_candle:
            return {"market": market, "close": close_price, "ma7": ma7, "ma30": ma30, "ma60": ma60, "body_pct": body_pct}
    except Exception as e:
        print(f"{market} 오류: {e}")
    return None

def scan_all():
    print(f"스캔 시작: {datetime.now()}")
    send_telegram("🔍 업비트 주봉 스캔 시작...")
    markets = get_markets()
    signals = []
    for market in markets:
        result = check_signal(market)
        if result:
            signals.append(result)
        time.sleep(0.1)
    if signals:
        msg = f"📊 <b>주봉 스캔 완료</b> — {datetime.now().strftime('%Y.%m.%d')}\n"
        msg += f"총 {len(markets)}개 중 <b>{len(signals)}개 신호</b>\n\n"
        for s in signals:
            coin = s["market"].replace("KRW-", "")
            msg += f"🎯 <b>{coin}</b>\n"
            msg += f"   종가: {int(s['close']):,}원\n"
            msg += f"   7일선: {int(s['ma7']):,}원\n"
            msg += f"   30일선: {int(s['ma30']):,}원\n"
            msg += f"   60일선: {int(s['ma60']):,}원\n"
            msg += f"   몸통: {s['body_pct']:.2f}%\n\n"
        send_telegram(msg)
    else:
        send_telegram(f"📊 스캔 완료 — 신호 없음 ({len(markets)}개 검사)")
    print("스캔 완료!")

scan_all()
