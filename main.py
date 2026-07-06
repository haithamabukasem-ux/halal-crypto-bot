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
    
    # حالة الصفقات المفتوحة حالياً (لكل عملة نتابعها لوقف الخسارة، ونمنع تكرار الإشارة)
    open_positions = {}  # symbol -> {"stop_loss_level": float, "entry_price": float}
    
    while True:
        for symbol in symbols:
            try:
                # سحب البيانات للفريمات المطلوبة
                df_4h = get_klines(symbol, config.TREND_TIMEFRAME, config.KLINES_LIMIT)
                df_1h = get_klines(symbol, config.ENTRY_TIMEFRAME, config.KLINES_LIMIT)
                
                # --- 1. إذا عندنا صفقة مفتوحة على هذه العملة: راقب وقف الخسارة فقط ---
                if symbol in open_positions:
                    sl_level = open_positions[symbol]["stop_loss_level"]
                    if strategy.check_stop_loss_hit(symbol, df_4h, sl_level):
                        msg = telegram_notifier.format_stop_loss_message(symbol, sl_level)
                        telegram_notifier.send_telegram_message(msg)
                        print(f"❌ [{symbol}] تم تفعيل وقف الخسارة (إغلاق 4H).")
                        del open_positions[symbol]
                    continue  # لا نبحث عن دخول جديد طالما الصفقة ما زالت مفتوحة
                
                # --- 2. لا توجد صفقة مفتوحة: ابحث عن إشارة دخول جديدة ---
                
                # فحص الاستراتيجية الأولى (القديمة)
                signal = strategy.analyze_strategy_old(symbol, df_4h, df_1h)
                
                # إذا لم تطلق الاستراتيجية الأولى إشارة، نفحص الاستراتيجية الثانية (الجديدة)
                if not signal:
                    signal = strategy.analyze_strategy_new(symbol, df_4h)
                    
                if signal:
                    msg = telegram_notifier.format_entry_message(signal)
                    telegram_notifier.send_telegram_message(msg)
                    print(f"✅ [{symbol}] تم إرسال إشارة دخول جديدة 🎉")
                    
                    open_positions[symbol] = {
                        "stop_loss_level": signal.stop_loss_level,
                        "entry_price": signal.entry_price
                    }
                    
            except Exception as e:
                print(f"❌ خطأ أثناء المعالجة للعملة [{symbol}]: {e}")
                traceback.printexc()
        
        print(f"\n⏳ انتظار {config.SCAN_INTERVAL_SECONDS} ثانية قبل الفحص التالي... ⏳\n")
        time.sleep(config.SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    run()
