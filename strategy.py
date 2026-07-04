# -*- coding: utf-8 -*-
"""
منطق توليد الإشارات.

فكرة الاستراتيجية (بسيطة، منضبطة، وقابلة للتفسير الكامل - لا "صندوق أسود"):
1) الاتجاه العام على فريم 4 ساعات: EMA21 فوق EMA50  => الاتجاه صاعد (نبحث عن شراء فقط)
2) الدخول على فريم ساعة: RSI يخرج من تشبع بيعي (يعبر فوق 35 صعوداً)
   + تقاطع MACD إيجابي (macd يعبر فوق خط الإشارة)
   + السعر قريب من دعم EMA50 على فريم الساعة (منطقة قيمة، وليس ملاحقة للسعر)
3) الهدف الأول: 2% من سعر الدخول
4) وقف الخسارة: ليس نقطة سعرية تُفعّل لحظياً، بل "تأكيد إغلاق شمعة 4 ساعات"
   تحت أدنى نقطة الشمعة المرجعية (لتفادي الخروج بسبب فتيل عابر/تقلب لحظي).
   البوت يراقب باستمرار، وعندما تُغلق شمعة 4 ساعات فعلياً تحت مستوى الإبطال،
   يرسل تنبيه "تفعيل وقف الخسارة" فوراً.

هذا النظام لا يدّعي دقة 100% (لا توجد استراتيجية كذلك)، لكنه منطقي،
قابل للتبرير الفني الكامل، ومحكوم بإدارة مخاطر واضحة.
"""

from dataclasses import dataclass
from typing import Optional

import config
import indicators


@dataclass
class Signal:
    symbol: str
    entry_price: float
    take_profit_1: float
    stop_loss_level: float          # المستوى الذي إن أُغلقت شمعة 4س تحته => خروج
    reference_candle_time: str
    reason: str


def analyze_symbol(symbol: str, df_4h, df_1h) -> Optional[Signal]:
    if len(df_4h) < config.EMA_SLOW + 5 or len(df_1h) < config.EMA_SLOW + 5:
        return None

    df_4h = indicators.add_all_indicators(
        df_4h, config.EMA_FAST, config.EMA_SLOW, config.RSI_PERIOD,
        config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL,
    )
    df_1h = indicators.add_all_indicators(
        df_1h, config.EMA_FAST, config.EMA_SLOW, config.RSI_PERIOD,
        config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL,
    )

    # نعتمد فقط على الشموع المغلقة لتفادي إشارات كاذبة من شمعة لم تكتمل بعد
    closed_4h = df_4h[df_4h["is_closed"]].iloc[-1]
    closed_1h_rows = df_1h[df_1h["is_closed"]]
    if len(closed_1h_rows) < 3:
        return None
    last_1h = closed_1h_rows.iloc[-1]
    prev_1h = closed_1h_rows.iloc[-2]

    # 1) شرط الاتجاه العام على 4 ساعات
    uptrend_4h = closed_4h["ema_fast"] > closed_4h["ema_slow"]
    if not uptrend_4h:
        return None

    # 2) شرط الدخول على فريم الساعة
    rsi_recovering = prev_1h["rsi"] < config.RSI_OVERSOLD <= last_1h["rsi"]
    macd_cross_up = (prev_1h["macd"] <= prev_1h["macd_signal"]
                      and last_1h["macd"] > last_1h["macd_signal"])
    near_support = last_1h["close"] <= last_1h["ema_slow"] * 1.01  # قريب من EMA50 (ضمن 1%)
    not_overbought = last_1h["rsi"] < config.RSI_OVERBOUGHT

    if not (rsi_recovering and macd_cross_up and near_support and not_overbought):
        return None

    entry_price = float(last_1h["close"])
    take_profit_1 = entry_price * (1 + config.TAKE_PROFIT_1_PCT)

    # 3) وقف الخسارة: أدنى نقطة آخر شمعة 4 ساعات مغلقة، مع هامش أمان بسيط
    stop_loss_level = float(closed_4h["low"]) * (1 - config.SL_BUFFER_PCT)

    if stop_loss_level >= entry_price:
        # لو المستوى غير منطقي (نادر) نتجاهل الإشارة لحماية المستخدم
        return None

    reason = (
        f"اتجاه صاعد على فريم 4س (EMA{config.EMA_FAST} فوق EMA{config.EMA_SLOW}) | "
        f"RSI خرج من تشبع بيعي ({prev_1h['rsi']:.1f} → {last_1h['rsi']:.1f}) | "
        f"تقاطع MACD إيجابي على فريم الساعة | السعر قريب من دعم EMA{config.EMA_SLOW}"
    )

    return Signal(
        symbol=symbol,
        entry_price=entry_price,
        take_profit_1=take_profit_1,
        stop_loss_level=stop_loss_level,
        reference_candle_time=str(closed_4h["close_time"]),
        reason=reason,
    )


def check_stop_loss_hit(symbol: str, df_4h, stop_loss_level: float) -> bool:
    """
    يتحقق مما إذا كانت آخر شمعة 4 ساعات (المغلقة فعلياً) قد أغلقت
    تحت مستوى وقف الخسارة المرجعي => يعني تفعيل الخروج.
    """
    closed = df_4h[df_4h["is_closed"]]
    if closed.empty:
        return False
    last_closed_close = float(closed.iloc[-1]["close"])
    return last_closed_close < stop_loss_level
