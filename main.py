# -*- coding: utf-8 -*-
"""
تشغيل بوت إشارات التداول الحلال (Signals Only - بدون تنفيذ تلقائي)
يراقب كل أزواج USDT الفورية على Binance (باستثناء منتجات الرافعة المالية)
"""

import time
import traceback

import config
from data_fetcher import get_klines, get_all_usdt_symbols
import strategy
import telegram_notifier


def is_symbol_allowed(symbol: str) -> bool:
    if any(bad in symbol for bad in config.EXCLUDE_KEYWORDS):
        return False
    return True


def run():
    print("🚀 بدء تشغيل بوت الإشارات (Spot / بدون تنفيذ تلقائي)...")
    all_symbols = get_all_usdt_symbols()
    symbols = [s for s in all_symbols if is_symbol_allowed(s)]
    print(f"العملات المراقَبة ({len(symbols)}): {symbols[:20]}... (وغيرها)")

    open_positions = {}

    while True:
        for symbol in symbols:
            try:
                df_4h = get_klines(symbol, config.TREND_TIMEFRAME, config.KLINES_LIMIT)
                df_1h = get_klines(symbol, config.ENTRY_TIMEFRAME, config.KLINES_LIMIT)

                if symbol in open_positions:
                    sl_level = open_positions[symbol]["stop_loss_level"]
                    if strategy.check_stop_loss_hit(symbol, df_4h, sl_level):
                        msg = telegram_notifier.format_stop_loss_message(symbol, sl_level)
                        telegram_notifier.send_telegram_message(msg)
                        print(f"[{symbol}] تم تفعيل وقف الخسارة.")
                        del open_positions[symbol]
                    continue

                signal = strategy.analyze_symbol(symbol, df_4h, df_1h)
                if signal:
                    msg = telegram_notifier.format_entry_message(signal)
                    telegram_notifier.send_telegram_message(msg)
                    print(f"[{symbol}] ✅ تم إرسال إشارة دخول جديدة.")
                    open_positions[symbol] = {
                        "stop_loss_level": signal.stop_loss_level,
                        "entry_price": signal.entry_price,
                    }

            except Exception as e:
                print(f"[{symbol}] خطأ أثناء المعالجة: {e}")

        print(f"⏳ انتظار {config.SCAN_INTERVAL_SECONDS} ثانية قبل الفحص التالي...\n")
        time.sleep(config.SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
