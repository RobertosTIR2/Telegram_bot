import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime, timedelta

# Dane Telegram
TELEGRAM_TOKEN = '7692369754:AAH_rFMHyIm0qxHnx8O-8ObE9XhCsYnui7Y'
TELEGRAM_CHAT_ID = '6811345722'


exchange = ccxt.binance()
symbols = [
    'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'SOL/USDT',
    'ADA/USDT', 'AVAX/USDT', 'DOGE/USDT', 'TRX/USDT',
    'DOT/USDT', 'LINK/USDT', 'SUI/USDT'
]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Błąd wysyłania do Telegrama:", e)

def fetch_data(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        print(f"Błąd pobierania danych dla {symbol}: {e}")
        return None

def analyze(symbol):
    df = fetch_data(symbol)
    if df is None or len(df) < 50:
        return None

    df['macd'] = ta.macd(df['close'])['MACD_12_26_9']
    df['signal'] = ta.macd(df['close'])['MACDs_12_26_9']
    bb = ta.bbands(df['close'], length=20)
    df = pd.concat([df, bb], axis=1)
    df['adx'] = ta.adx(df['high'], df['low'], df['close'])['ADX_14']
    df['rsi'] = ta.rsi(df['close'], length=14)
    stoch_rsi = ta.stochrsi(df['close'], length=14)
    df['stoch_k'] = stoch_rsi['STOCHRSIk_14_14_3_3']
    df['stoch_d'] = stoch_rsi['STOCHRSId_14_14_3_3']

    last = df.iloc[-1]
    price = round(last['close'], 4)
    upper = last['BBU_20_2.0']
    lower = last['BBL_20_2.0']

    # Warunki
    trend = "📈 Wzrostowy" if last['macd'] > last['signal'] else "📉 Spadkowy"
    macd_trend = "📈 Wzrasta" if last['macd'] > df['macd'].iloc[-2] else "📉 Spada"
    bb_status = "✅" if (upper - lower)/price < 0.05 else "❌"
    volume_status = "📉 Mały wolumen" if last['volume'] < df['volume'].mean() else "📊 Duży wolumen"
    adx_status = "✅" if last['adx'] > 25 else "❌"
    stoch_signal = "✅" if last['stoch_k'] > 80 else "❌"
    stoch_cross = "✅" if last['stoch_k'] > last['stoch_d'] else "❌"
    rsi_info = f"{last['rsi']:.2f} (wyprzedanie)" if last['rsi'] < 30 else f"{last['rsi']:.2f} (wykupienie)" if last['rsi'] > 70 else f"{last['rsi']:.2f}"

    # Typ sygnału
    signal_type = None
    if price < lower and last['rsi'] < 30:
        signal_type = "LONG"
    elif price > upper and last['rsi'] > 70:
        signal_type = "SHORT"
    else:
        return None

    # Sprawdź czy przynajmniej 2 podstawowe sygnały są spełnione
    basic_signals = sum([bb_status == "✅", stoch_signal == "✅", stoch_cross == "✅"])
    if basic_signals < 2:
        return None

        # Pozycje
    if signal_type == "LONG":
        limit_1 = round(price * 0.99, 4)  # 1% poniżej
        limit_4 = round(price * 0.96, 4)  # 4% poniżej
        stop_loss = round(price * 0.94, 4)  # 6% poniżej
    else:  # SHORT
        limit_1 = round(price * 1.01, 4)  # 1% powyżej
        limit_4 = round(price * 1.04, 4)  # 4% powyżej
        stop_loss = round(price * 1.06, 4)  # 6% powyżej
    emoji = "🟢 SYGNAŁ LONG" if signal_type == "LONG" else "🔴 SYGNAŁ SHORT"
    msg = f"*─── {symbol.replace('/', '')} ───*\n"
    msg += f"🚨 {emoji} ({symbol}) 🚨\n"
    msg += f"💰 Aktualna Cena: {price} USDT\n\n"

    msg += "*🧠 Dodatkowe dane:*\n"
    msg += f"• Trend: {trend}\n"
    msg += f"• Zmienność (BB): {bb_status}\n"
    msg += f"• Wolumen: {volume_status}\n"
    msg += f"• MACD: {macd_trend}\n"
    msg += f"• ADX: {adx_status} (wartość: {last['adx']:.2f})\n"
    msg += f"• RSI: {rsi_info}\n\n"

    msg += "*📊 Potwierdzenie sygnału:*\n"
    msg += f"• Bollinger Bands: {bb_status}\n"
    msg += f"• Stoch RSI: {stoch_signal}\n"
    msg += f"• Przecięcie linii Stoch RSI: {stoch_cross}\n\n"

    msg += "*📉 Zlecenia:*\n"
    msg += f"• Limit (1%): {limit_1} USDT\n"
    msg += f"• Limit (4%): {limit_4} USDT\n"
    msg += f"• Stop Loss (6%): {stop_loss} USDT\n"


    return msg

def wait_until_next_quarter():
    now = datetime.now()
    next_minute = (now + timedelta(minutes=15 - now.minute % 15)).replace(second=0, microsecond=0)
    time_to_wait = (next_minute - now).total_seconds()
    time.sleep(time_to_wait)

def main():
    send_telegram_message("🤖 Bot został uruchomiony i będzie analizował rynek co 15 minut (pełne kwadranse)...")
    while True:
        for symbol in symbols:
            msg = analyze(symbol)
            if msg:
                send_telegram_message(msg)
            time.sleep(1)  # krótka przerwa między parami
        wait_until_next_quarter()

if __name__ == "__main__":
    main()
