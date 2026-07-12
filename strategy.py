# -*- coding: utf-8 -*-
"""
strategy.py
===========
إعادة بناء لاستراتيجية "منطقة دخول + 6 أهداف متدرجة + ستوب بإغلاق شمعة 4H"
المستخرجة من تحليل ~10 صفقات حقيقية (TUT, SAGA, WLD, TAO, MANTA, LUMIA, CFG,
SOMI, OG, S, DOT) — 9 ناجحة + 1 خاسرة (DOT، ضربت الستوب).

⚠️ ملاحظة أمانة علمية مهمة — اقرأها قبل الاستخدام الحقيقي بأموال فعلية:
------------------------------------------------------------------------
1) صيغة TP1-TP6: مؤكدة رياضيًا ~100% (نفس النسب طلعت بدقة <0.1% في 6 صفقات
   مستقلة، متضمنة الصفقة الخاسرة DOT — يعني الصيغة ثابتة بغض النظر عن النتيجة).

2) صيغة SL: هذه ليست نسبة ثابتة. رصدنا مدى واسع جدًا من -0.85% إلى -4.39%
   تحت أسفل منطقة الدخول عبر الصفقات. الاستنتاج: الستوب = دعم فني حقيقي
   مختلف بكل شارت (سوينغ لو قريب)، وليس نسبة رياضية. أي رقم ثابت هنا هو
   تقريب وليس قانونًا مؤكدًا.

3) منطق تحديد منطقة الدخول + "تأكيد الزخم الفوري": بمقارنة 9 صفقات ناجحة
   بصفقة DOT الخاسرة، لاحظنا فرقًا نوعيًا:
     - الصفقات الناجحة: الدخول تزامن مع انفجار فوليوم/سعري خلال نفس الشمعة
       أو الشمعة التالية مباشرة (تأكيد فوري للزخم بعد كسر قاعدة/مقاومة صغيرة).
     - DOT الخاسرة: الدخول صار في منطقة تذبذب هادئة "شكلها كويس" لكن بدون
       تأكيد فوري — استمر التذبذب الجانبي لأيام قبل ما يتحرك السعر لاحقًا،
       فضرب الستوب أولاً.
   هذا التمييز هو أفضل تفسير وصلنا له، وهو استنتاج احتمالي من عيّنة صغيرة
   (10 صفقات) — ليس نسخة مؤكدة من الخوارزمية الداخلية الفعلية لأي قناة.
   عدّل الثوابت أدناه بحرية حسب رؤيتك الفنية أو بيانات إضافية تجمعها.
"""

from dataclasses import dataclass
from typing import Optional, List
import pandas as pd


# ============================================================
# الثوابت المؤكدة رياضيًا (لا تُعدَّل إلا إذا وجدت صفقات تنقضها)
# ============================================================
TP_MULTIPLIERS = [1.02, 1.04, 1.07, 1.12, 1.18, 1.25]   # +2% → +25%

# ============================================================
# ثوابت الستوب (تقريبية — دعم فني متغير، راجع الملاحظة #2 فوق)
# ============================================================
SL_LOOKBACK = 10             # عدد الشموع للبحث عن أقرب سوينغ لو كدعم فعلي للستوب
SL_MIN_BUFFER = 0.005        # حد أدنى للهامش تحت الدعم (0.5%) لتفادي ستوب ملاصق جدًا
SL_MAX_BUFFER = 0.045        # حد أقصى للهامش تحت الدعم (4.5%) بناءً على أوسع حالة رصدناها
ATR_PERIOD = 14              # عدد الشموع لحساب متوسط المدى الحقيقي (ATR) - مقياس التذبذب الفعلي

# ============================================================
# ثوابت منطقة الدخول ومنطق "كسر القاعدة"
# ============================================================
BASE_LOOKBACK = 12                # عدد الشموع للبحث عن آخر قاعدة تجميع/مقاومة صغيرة
RESISTANCE_LOOKBACK = 10          # نافذة أضيق لتحديد سقف منطقة الدخول
MIN_VOLUME_USDT = 2_000_000       # حد أدنى لحجم آخر شمعة 4H (رُفع لاستبعاد عملات صغيرة شديدة التقلب)
ENTRY_ZONE_MAX_WIDTH_PCT = 0.08   # لا نقبل منطقة دخول أعرض من 8%

# ---- شرط تأكيد الزخم الفوري (الإضافة الجديدة بناءً على مقارنة DOT) ----
MOMENTUM_VOLUME_MULTIPLIER = 1.8     # فوليوم الشمعة الحالية لازم يكون ≥ 1.8x متوسط آخر N شمعة
MOMENTUM_VOLUME_AVG_WINDOW = 10      # نافذة حساب متوسط الفوليوم للمقارنة
MOMENTUM_MIN_CANDLE_MOVE_PCT = 0.02  # الشمعة الحالية لازم تتحرك 2%+ (إغلاق-فتح) كتأكيد زخم

# ---- فترة تهدئة بعد إغلاق أي صفقة على نفس الرمز (يمنع إعادة الدخول الفوري) ----
COOLDOWN_HOURS = 8   # لا يُسمح بإشارة جديدة لنفس الرمز إلا بعد 8 ساعات من إغلاق آخر صفقة له


@dataclass
class Signal:
    symbol: str
    entry_high: float
    entry_low: float
    entry_price: float          # نستخدم أعلى الدخول كمرجع لعرض السعر بالرسالة
    tp_levels: List[float]
    stop_loss_level: float
    volume_usdt: float
    momentum_volume_ratio: float   # نسبة فوليوم شمعة الدخول لمتوسط الفوليوم (تشخيصي)
    candle_move_pct: float          # قوة حركة شمعة الدخول % (تشخيصي)
    timeframe: str = "4H"


def _find_demand_zone(df_4h: pd.DataFrame):
    """
    يحدد منطقة الدخول بناءً على آخر قاعدة تجميع/مقاومة صغيرة (BASE_LOOKBACK
    شمعة)، بدل قاع أدنى بعيد. هذا أقرب لما لاحظناه بصريًا في LUMIA/CFG/SOMI/
    OG/S: الدخول عند حافة قاعدة قريبة قبل الاختراق، وليس عند قاع عميق قديم.
    يفترض أن df_4h يحتوي أعمدة: open, high, low, close, volume
    """
    base_window = df_4h.tail(BASE_LOOKBACK)
    base_low = base_window["low"].min()

    near_window = df_4h.tail(RESISTANCE_LOOKBACK)
    local_resistance = near_window["high"].max()

    entry_low = base_low
    entry_high = min(local_resistance, base_low * (1 + ENTRY_ZONE_MAX_WIDTH_PCT))

    return entry_low, entry_high


def _calculate_atr_pct(df_4h: pd.DataFrame, period: int = ATR_PERIOD) -> float:
    """
    يحسب متوسط المدى الحقيقي (ATR) كنسبة مئوية من السعر الحالي - هذا مقياس
    تذبذب فعلي وموضوعي (يختلف طبيعياً بين عملة هادئة وعملة متقلبة)، بدل رقم
    ثابت واحد للجميع.
    True Range لكل شمعة = max(high-low, |high-prev_close|, |low-prev_close|)
    """
    recent = df_4h.tail(period + 1).copy()
    if len(recent) < 2:
        return (SL_MIN_BUFFER + SL_MAX_BUFFER) / 2  # احتياط لو البيانات غير كافية

    prev_close = recent["close"].shift(1)
    tr = pd.concat([
        recent["high"] - recent["low"],
        (recent["high"] - prev_close).abs(),
        (recent["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.iloc[1:].mean()  # نتجاهل أول صف (بدون prev_close صالح)
    current_price = float(recent["close"].iloc[-1])
    if current_price <= 0:
        return (SL_MIN_BUFFER + SL_MAX_BUFFER) / 2

    return float(atr / current_price)


def _find_dynamic_stop_loss(df_4h: pd.DataFrame, entry_low: float) -> float:
    """
    الستوب = أقرب سوينغ لو حقيقي تحت منطقة الدخول، ناقص هامش أمان **متغير
    فعلياً** حسب تذبذب العملة (ATR%) - وليس نسبة ثابتة واحدة للجميع.
    نحصر الهامش بين SL_MIN_BUFFER و SL_MAX_BUFFER لأن العينة الحقيقية
    (10 صفقات من Apollo) ما طلعت خارج هذا المدى (0.5% - 4.5%).
    """
    sl_window = df_4h.tail(SL_LOOKBACK)
    swing_low = float(sl_window["low"].min())

    atr_pct = _calculate_atr_pct(df_4h)
    buffer = min(max(atr_pct, SL_MIN_BUFFER), SL_MAX_BUFFER)

    stop_loss = swing_low * (1 - buffer)

    # لا نسمح للستوب يكون أبعد من entry_low نفسه بأكثر من الحد الأقصى المرصود
    floor = entry_low * (1 - SL_MAX_BUFFER)
    return round(max(stop_loss, floor), 8)


def _passes_volume_filter(df_4h: pd.DataFrame) -> Optional[float]:
    last_candle_volume = float(df_4h.iloc[-1]["volume"] * df_4h.iloc[-1]["close"])
    if last_candle_volume < MIN_VOLUME_USDT:
        return None
    return last_candle_volume


def _check_momentum_confirmation(df_4h: pd.DataFrame):
    """
    ✨ الإضافة الجديدة: شرط تأكيد الزخم الفوري.

    استُنتج من مقارنة 9 صفقات ناجحة بصفقة DOT الخاسرة: في الصفقات الناجحة،
    شمعة الدخول (أو التي تليها مباشرة) كانت مصحوبة بفوليوم مرتفع بوضوح عن
    المتوسط، وبحركة سعرية واضحة (إغلاق بعيد عن الفتح). في DOT، الشمعة كانت
    هادئة نسبيًا بدون هذا التأكيد، واستمر التذبذب الجانبي لاحقًا قبل ضرب
    الستوب.

    يرجع (passed: bool, volume_ratio: float, move_pct: float)
    """
    if len(df_4h) < MOMENTUM_VOLUME_AVG_WINDOW + 1:
        return False, 0.0, 0.0

    last_candle = df_4h.iloc[-1]
    avg_volume = df_4h["volume"].tail(MOMENTUM_VOLUME_AVG_WINDOW + 1).iloc[:-1].mean()

    volume_ratio = float(last_candle["volume"] / avg_volume) if avg_volume > 0 else 0.0
    move_pct = abs(float(last_candle["close"] - last_candle["open"]) / last_candle["open"])

    passed = (volume_ratio >= MOMENTUM_VOLUME_MULTIPLIER) and (move_pct >= MOMENTUM_MIN_CANDLE_MOVE_PCT)
    return passed, volume_ratio, move_pct


def analyze_symbol(symbol: str, df_4h: pd.DataFrame, df_1h: pd.DataFrame) -> Optional[Signal]:
    """
    نقطة الدخول الرئيسية التي يستدعيها main.py
    ترجع Signal إذا استوفى الرمز شروط الدخول (منطقة + فوليوم + زخم فوري)،
    وإلا None.
    """
    min_len = max(BASE_LOOKBACK, RESISTANCE_LOOKBACK, SL_LOOKBACK, MOMENTUM_VOLUME_AVG_WINDOW) + 1
    if df_4h is None or len(df_4h) < min_len:
        return None

    volume_usdt = _passes_volume_filter(df_4h)
    if volume_usdt is None:
        return None

    entry_low, entry_high = _find_demand_zone(df_4h)
    if entry_high <= entry_low:
        return None

    current_price = float(df_4h.iloc[-1]["close"])

    # نشترط أن السعر الحالي فعلاً داخل منطقة الدخول
    if not (entry_low <= current_price <= entry_high):
        return None

    # 🔑 الفلتر الجديد: بدون تأكيد زخم فوري، نرفض الإشارة (هذا ما كان غائبًا
    # في حالة DOT الخاسرة)
    momentum_ok, volume_ratio, move_pct = _check_momentum_confirmation(df_4h)
    if not momentum_ok:
        return None

    tp_levels = [round(entry_high * m, 8) for m in TP_MULTIPLIERS]
    stop_loss_level = _find_dynamic_stop_loss(df_4h, entry_low)

    # 🔑 فلتر جديد مهم: نرفض الإشارة لو أعلى سعر بنفس الشمعة الحالية تجاوز
    # أصلاً TP1 - هذا يمنع "إشارات متأخرة" حيث السعر يكون قفز داخل شمعة
    # واحدة شديدة التقلب (عملة صغيرة السيولة) قبل ما نلحق نتتبعه تدريجياً،
    # فتظهر كل الأهداف "متحققة" فوراً وهذا ليس تتبعاً حقيقياً بل خلل توقيت.
    last_high = float(df_4h.iloc[-1]["high"])
    if last_high >= tp_levels[0]:
        return None

    return Signal(
        symbol=symbol,
        entry_high=entry_high,
        entry_low=entry_low,
        entry_price=entry_high,
        tp_levels=tp_levels,
        stop_loss_level=stop_loss_level,
        volume_usdt=volume_usdt,
        momentum_volume_ratio=round(volume_ratio, 2),
        candle_move_pct=round(move_pct * 100, 2),
    )


def check_stop_loss_hit(symbol: str, df_4h: pd.DataFrame, sl_level: float) -> bool:
    """
    الستوب لا يُفعَّل بمجرد ملامسة الفتيل (wick)، بل يشترط
    إغلاق شمعة 4H كاملة تحت مستوى الستوب - لتفادي صيد السيولة.

    🐛 إصلاح مهم: Binance بترجع الشمعة الحالية (اللي لسا عم تتكوّن) كآخر
    صف بالبيانات - سعر "close" فيها هو آخر سعر تداول لحظي، مش إغلاق نهائي
    فعلي. لو اعتمدنا عليها مباشرة، ممكن نعتبر الستوب "انضرب" لمجرد لمسة
    سعرية لحظية أثناء تكوّن الشمعة، حتى لو ارتد السعر وأغلقت الشمعة فعليًا
    فوق الستوب لاحقاً - بالضبط عكس المبدأ اللي بنينا عليه الشرط من الأساس.
    الحل: نعتمد على آخر شمعة **مكتملة فعلياً** (الصف قبل الأخير)، مش الشمعة
    الحالية الجارية.
    """
    if df_4h is None or len(df_4h) < 2:
        return False
    last_closed_candle = df_4h.iloc[-2]  # آخر شمعة مكتملة فعلياً (وليس الجارية)
    last_closed_price = float(last_closed_candle["close"])
    return last_closed_price < sl_level


def check_take_profit_hits(symbol: str, df_4h: pd.DataFrame, tp_levels: List[float]) -> List[int]:
    """
    يرجع قائمة بأرقام الأهداف (1-6) التي تحققت بناءً على أعلى سعر
    (high) لآخر شمعة - هذه فقط مساعدة اختيارية إن رغبت بتتبع الأهداف.
    """
    if df_4h is None or len(df_4h) == 0:
        return []
    last_high = float(df_4h.iloc[-1]["high"])
    hit = [i + 1 for i, tp in enumerate(tp_levels) if last_high >= tp]
    return hit
