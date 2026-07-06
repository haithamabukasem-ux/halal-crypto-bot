# -*- coding: utf-8 -*-
"""
تشغيل بوت إشارات التداول الحلال (Signals Only - بدون تنفيذ تلقائي)

الاستخدام:
    1) ثبّت المتطلبات:  pip install -r requirements.txt
    2) عدّل config.py: ضع توكن بوت تيليجرام و chat_id الخاص بك
    3) شغّل:  python main.py

تنويه مهم:
    - هذا البرنامج لأغراض تعليمية/مساعدة على اتخاذ القرار فقط.
    - لا توجد استراتيجية تداول دقيقة 100%. تداول بحذر وبرأس مال تتحمل خسارته.
    - راجع أهل الاختصاص الشرعي بخصوص فلترة العملات، فالاجتهادات تختلف.
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

    open_positions = {}   # symbol -> {"stop_loss_level": float, "entry_price": float}

    while True:
        for symbol in symbols:
            try:
                df_4h = get_klines(symbol, config.TREND_TIMEFRAME, config.KLINES_LIMIT)
                df_1h = get_klines(symbol, config.ENTRY_TIMEFRAME, config.KLINES_LIMIT)

                # --- إذا عندنا صفقة مفتوحة على هذه العملة: راقب وقف الخسارة فقط ---
                if symbol in open_positions:
                    sl_level = open_positions[symbol]["stop_loss_level"]
                    if strategy.check_stop_loss_hit(symbol, df_4h, sl_level):
                        msg = telegram_notifier.format_stop_loss_message(symbol, sl_level)
                        telegram_notifier.send_telegram_message(msg)
                        print(f"[{symbol}] تم تفعيل وقف الخسارة.")
                        del open_positions[symbol]
                    continue  # لا نبحث عن دخول جديد طالما الصفقة ما زالت مفتوحة

                # --- لا توجد صفقة مفتوحة: ابحث عن إشارة دخول جديدة ---
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
                traceback.print_exc()

        print(f"⏳ انتظار {config.SCAN_INTERVAL_SECONDS} ثانية قبل الفحص التالي...\n")
        time.sleep(config.SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
