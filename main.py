import pandas as pd
import numpy as np
import time
import requests
from flask import Flask
from threading import Thread
import os

# --- కాన్ఫిగరేషన్ ---
TELEGRAM_TOKEN = '8531878411:AAGjmDFuQZ40KAGqn68MQh9UccgBBZUt-KY'
CHAT_ID = '5356787589'

app = Flask('')
@app.route('/')
def home(): return "Pro MTF Bot is Active!"

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except: pass

def get_binance_data(symbol, timeframe='15m'):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={timeframe}&limit=100"
        response = requests.get(url, timeout=15)
        df = pd.DataFrame(response.json(), columns=['time', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qav', 'nt', 'tbv', 'tqv', 'i'])
        df[['close', 'high', 'low', 'vol']] = df[['close', 'high', 'low', 'vol']].astype(float)
        return df
    except: return None

# ఇండికేటర్ లెక్కలు
def apply_indicators(df):
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    # SMA for Trend
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    return df

def scan_pro_market():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
    for s in symbols:
        # 1. Multi-Timeframe: 1 గంట చార్ట్ లో ట్రెండ్ చెక్ చేయడం
        df_1h = get_binance_data(s, '1h')
        df_15m = get_binance_data(s, '15m')
        
        if df_1h is not None and df_15m is not None:
            df_1h = apply_indicators(df_1h)
            df_15m = apply_indicators(df_15m)
            
            trend_1h = "BULLISH" if df_1h['close'].iloc[-1] > df_1h['SMA_50'].iloc[-1] else "BEARISH"
            last_15m = df_15m.iloc[-1]
            vol_avg = df_15m['vol'].tail(10).mean()

            # --- BUY STRATEGY (Trend + RSI + Volume) ---
            if trend_1h == "BULLISH" and last_15m['RSI'] < 35 and last_15m['vol'] > vol_avg:
                price = last_15m['close']
                sl = round(price * 0.985, 2) # 1.5% Stop Loss
                tp = round(price * 1.045, 2) # 4.5% Take Profit
                
                msg = (f"🚀 *PRO BUY SIGNAL* 🚀\n\n*Coin:* {s}\n*Price:* {price}\n"
                       f"*Trend (1h):* {trend_1h}\n*RSI:* {round(last_15m['RSI'], 2)}\n"
                       f"-------------------\n🛡️ *SL:* {sl}\n🎯 *TP:* {tp}")
                send_telegram_msg(msg)

            # --- SELL STRATEGY ---
            elif trend_1h == "BEARISH" and last_15m['RSI'] > 65 and last_15m['vol'] > vol_avg:
                price = last_15m['close']
                sl = round(price * 1.015, 2)
                tp = round(price * 0.955, 2)
                
                msg = (f"⚠️ *PRO SELL SIGNAL* ⚠️\n\n*Coin:* {s}\n*Price:* {price}\n"
                       f"*Trend (1h):* {trend_1h}\n*RSI:* {round(last_15m['RSI'], 2)}\n"
                       f"-------------------\n🛡️ *SL:* {sl}\n🎯 *TP:* {tp}")
                send_telegram_msg(msg)
        time.sleep(1)

def main_loop():
    send_telegram_msg("⚡ *Pro MTF Bot with Risk Management Active!* \nAnalyzing Trends & Volume...")
    while True:
        scan_pro_market()
        time.sleep(300)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    main_loop()
