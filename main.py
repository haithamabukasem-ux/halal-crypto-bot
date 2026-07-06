# -*- coding: utf-8 -*-
import time, strategy, telegram_notifier
from data_receiver import get_all_usdt_symbols, get_klines
import config

def run():
    symbols = get_all_usdt_symbols()
    while True:
        for symbol in symbols:
            try:
                df_4h = get_klines(symbol, config.TREND_TIMEFRAME)
                sig = strategy.analyze_strategy_new(symbol, df_4h)
                if sig:
                    telegram_notifier.send_message(f"إشارة جديدة لـ {symbol}")
                    print(f"تم إرسال إشارة {symbol}")
            except Exception as e:
                print(f"خطأ: {e}")
        time.sleep(300)

if __name__ == "__main__":
    run()
