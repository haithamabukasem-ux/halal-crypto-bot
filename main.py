# -*- coding: utf-8 -*-
"""
تشغيل بوت إشارات التداول - النسخة المحسّنة (v2)
- نطاق: أعلى 30 عملة سيولة على Binance
- طبقات تأكيد: اتجاه يومي+4س، زخم مزدوج (RSI+StochRSI+MACD)، حجم تداول
- وقف خسارة ديناميكي (ATR) + فلتر نسبة عائد:مخاطرة >= 2:1
- 3 أهداف متدرجة (2%/4%/6%) مع تحريك وقف الخسارة تلقائياً لحماية الأرباح
"""

import time
import traceback

import config
from data_fetcher import get_klines, get_current_price
import strategy
import telegram_notifier


def is_symbol_allowed(symbol: str) -> bool:
    if any(bad in symbol for bad in config.EXCLUDE_KEYWORDS):
        return False
    return True


def scan_once(symbols, open_positions):
    for symbol in symbols:
        try:
            if symbol in open_positions:
                pos = open_positions[symbol]
                current_price = get_current_price(symbol)
                df_4h = get_klines(symbol, config.TREND_TIMEFRAME, config.KLINES_LIMIT)

                if pos["tp2_hit"] and current_price >= pos["tp3"]:
                    msg = telegram_notifier.format_take_profit_message(
                        symbol, pos["entry_price"], pos["tp3"], 3)
                    telegram_notifier.send_telegram_message(msg)
                    print(f"[{symbol}] 🎯 تحقق الهدف الثالث - إغلاق الصفقة.")
                    del open_positions[symbol]
                    continue

                if pos["tp1_hit"] and not pos["tp2_hit"] and current_price >= pos["tp2"]:
                    msg = telegram_notifier.format_take_profit_message(
                        symbol, pos["entry_price"], pos["tp2"], 2)
                    telegram_notifier.send_telegram_message(msg)
                    pos["tp2_hit"] = True
                    pos["stop_loss_level"] = pos["tp1"]
                    print(f"[{symbol}] 🎯 تحقق الهدف الثاني - تحريك الوقف.")
                    continue

                if not pos["tp1_hit"] and current_price >= pos["tp1"]:
                    msg = telegram_notifier.format_take_profit_message(
                        symbol, pos["entry_price"], pos["tp1"], 1)
                    telegram_notifier.send_telegram_message(msg)
                    pos["tp1_hit"] = True
                    pos["stop_loss_level"] = pos["entry_price"]
                    print(f"[{symbol}] 🎯 تحقق الهدف الأول - تحريك الوقف لنقطة التعادل.")
                    continue

                if strategy.check_stop_loss_hit(symbol, df_4h, pos["stop_loss_level"]):
                    if pos["tp1_hit"]:
                        msg = telegram_notifier.format_breakeven_exit_message(
                            symbol, pos["entry_price"], pos["stop_loss_level"])
                    else:
                        msg = telegram_notifier.format_stop_loss_message(symbol, pos["stop_loss_level"])
                    telegram_notifier.send_telegram_message(msg)
                    print(f"[{symbol}] 🔴 خروج من الصفقة.")
                    del open_positions[symbol]
                continue

            df_daily = get_klines(symbol, config.DAILY_TIMEFRAME, config.KLINES_LIMIT)
            df_4h = get_klines(symbol, config.TREND_TIMEFRAME, config.KLINES_LIMIT)
            df_1h = get_klines(symbol, config.ENTRY_TIMEFRAME, config.KLINES_LIMIT)

            signal = strategy.analyze_symbol(symbol, df_daily, df_4h, df_1h)
            if signal:
                msg = telegram_notifier.format_entry_message(signal)
                telegram_notifier.send_telegram_message(msg)
                print(f"[{symbol}] ✅ إشارة دخول جديدة (عائد:مخاطرة {signal.risk_reward_ratio:.1f}:1).")
                open_positions[symbol] = {
                    "entry_price": signal.entry_price,
                    "stop_loss_level": signal.stop_loss_level,
                    "tp1": signal.take_profit_1,
                    "tp2": signal.take_profit_2,
                    "tp3": signal.take_profit_3,
                    "tp1_hit": False,
                    "tp2_hit": False,
                }

        except Exception as e:
            print(f"[{symbol}] خطأ أثناء المعالجة: {e}")

        time.sleep(0.15)


def run():
    print("🚀 بدء تشغيل بوت الإشارات (النسخة المحسّنة v2 - Spot / بدون تنفيذ تلقائي)...")
    symbols = [s for s in config.HIGH_LIQUIDITY_SYMBOLS if is_symbol_allowed(s)]
    print(f"العملات المراقَبة ({len(symbols)}): {symbols}")

    open_positions = {}

    while True:
        try:
            scan_once(symbols, open_positions)
        except Exception as e:
            print(f"[خطأ عام بالدورة]: {e}")
            traceback.print_exc()

        print(f"⏳ انتظار {config.SCAN_INTERVAL_SECONDS} ثانية قبل الفحص التالي...\n")
        time.sleep(config.SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
