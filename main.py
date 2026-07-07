# -*- coding: utf-8 -*-
"""
تشغيل بوت إشارات التداول الحلال (Signals Only - بدون تنفيذ تلقائي)
"""

import time

import config
from data_fetcher import get_klines, get_all_usdt_symbols, get_current_price
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

                # --- صفقة مفتوحة: افحص الهدف أولاً، ثم وقف الخسارة ---
                if symbol in open_positions:
                    pos = open_positions[symbol]

                    # 1) الهدف: فحص فوري بالسعر اللحظي
                    current_price = get_current_price(symbol)
                    if current_price >= pos["take_profit_1"]:
                        msg = telegram_notifier.format_take_profit_message(
                            symbol, pos["entry_price"], pos["take_profit_1"]
                        )
                        telegram_notifier.send_telegram_message(msg)
                        print(f"[{symbol}] 🎯 تحقق الهدف!")
                        del open_positions[symbol]
                        continue  # لا نفحص وقف الخسارة لهذه الصفقة بعد الآن

                    # 2) وقف الخسارة: فقط إذا لم يتحقق الهدف بعد
                    if strategy.check_stop_loss_hit(symbol, df_4h, pos["stop_loss_level"]):
                        msg = telegram_notifier.format_stop_loss_message(symbol, pos["stop_loss_level"])
                        telegram_notifier.send_telegram_message(msg)
                        print(f"[{symbol}] 🔴 تم تفعيل وقف الخسارة.")
                        del open_positions[symbol]
                    continue

                # --- لا توجد صفقة مفتوحة: ابحث عن إشارة دخول جديدة ---
                signal = strategy.analyze_symbol(symbol, df_4h, df_1h)
                if signal:
                    msg = telegram_notifier.format_entry_message(signal)
                    telegram_notifier.send_telegram_message(msg)
                    print(f"[{symbol}] ✅ تم إرسال إشارة دخول جديدة.")
                    open_positions[symbol] = {
                        "stop_loss_level": signal.stop_loss_level,
                        "entry_price": signal.entry_price,
                        "take_profit_1": signal.take_profit_1,
                    }

            except Exception as e:
                print(f"[{symbol}] خطأ أثناء المعالجة: {e}")

        print(f"⏳ انتظار {config.SCAN_INTERVAL_SECONDS} ثانية قبل الفحص التالي...\n")
        time.sleep(config.SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
