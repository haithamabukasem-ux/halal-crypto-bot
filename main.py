# -*- coding: utf-8 -*-
import time
import traceback
import config
import strategy
import telegram_notifier
from data_receiver import get_all_usdt_symbols, get_klines

def is_symbol_allowed(symbol: str) -> bool:
    if any(bad in symbol for bad in config.EXCLUDE_KEYWORDS):
        return False
    return True

def run():
    print("🚀 بدء تشغيل بوت الإشارات (Spot) ... (بدون تنفيذ تلقائي)")
    all_symbols = get_all_usdt_symbols()
    symbols = [s for s in all_symbols if is_symbol_allowed(s)]
    
    # حالة الصفقات المفتوحة حالياً لتجنب تكرار الإشارات
    open_positions = {} 

    while True:
        for symbol in symbols:
            try:
                # سحب البيانات للفريمات المطلوبة بشكل صحيح ونظيف
                df_4h = get_klines(symbol, config.TREND_TIMEFRAME)
                df_1h = get_klines(symbol, config.ENTRY_TIMEFRAME)
                
                # 1 --- مراقبة وقف الخسارة للصفقات المفتوحة
                if symbol in open_positions:
                    sl_level = open_positions[symbol]["stop_loss_level"]
                    if strategy.check_stop_loss_hit(symbol, df_4h, sl_level):
                        # هنا نقوم بمسح الصفقة لإتاحة استقبال إشارات جديدة لها لاحقاً
                        print(f"❌ [{symbol}] تم تفعيل وقف الخسارة بناءً على إغلاق شمعة 4س.")
                        del open_positions[symbol]
                    continue

                # 2 --- الفحص بالاستراتيجية الأولى (القديمة: المؤشرات)
                signal_old = strategy.analyze_strategy_old(symbol, df_4h, df_1h)
                if signal_old:
                    telegram_notifier.send_message(signal_old.reason)
                    open_positions[symbol] = {
                        "stop_loss_level": signal_old.stop_loss_level,
                        "strategy": "old"
                    }
                    print(f"✅ تم إرسال إشارة الاستراتيجية القديمة لعملة {symbol}")
                    time.sleep(1)
                    continue

                # 3 --- الفحص بالاستراتيجية الثانية (الجديدة: القالب الرقمي والسيولة)
                signal_new = strategy.analyze_strategy_new(symbol, df_4h)
                if signal_new:
                    telegram_notifier.send_message(signal_new.reason)
                    open_positions[symbol] = {
                        "stop_loss_level": signal_new.stop_loss_level,
                        "strategy": "new"
                    }
                    print(f"💎 تم إرسال إشارة القالب الرقمي لعملة {symbol}")
                    time.sleep(1)
                    continue

            except Exception as e:
                print(f"⚠️ خطأ أثناء فحص العملة {symbol}: {e}")
                traceback.print_exc()
                
        print(f"⏳ الانتظار {config.LOOP_INTERVAL_SECONDS} ثانية قبل الفحص التالي ...")
        time.sleep(config.LOOP_INTERVAL_SECONDS)

if __name__ == "__main__":
    run()
