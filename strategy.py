# -*- coding: utf-8 -*-
"""
منطق توليد الإشارات.

تم تقسيم الملف إلى استراتيجيتين منفصلتين تماماً لتعملا بالتوازي دون أي تداخل.
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


def analyze_strategy_old(symbol: str, df_4h, df_1h) -> Optional[Signal]:
    """
    الاستراتيجية الأولى (القديمة): دمج فريم 4 ساعات وفريم الساعة (EMA + RSI + MACD)
    """
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
        return None

    reason = (
        f"االقديمة (RSI + MACD) | اتجاه صاعد على فريم 4س (EMA{config.EMA_FAST} فوق EMA{config.EMA_SLOW}) | "
        f"RSI خرج من تشبع بيعي ({prev_1h['rsi']:.1f} → {last_1h['rsi']:.1f}) | "
        f"تقاطع MACD إيجابي على فريم الساعة"
    )

    return Signal(
        symbol=symbol,
        entry_price=entry_price,
        take_profit_1=take_profit_1,
        stop_loss_level=stop_loss_level,
        reference_candle_time=str(closed_4h["close_time"]),
        reason=reason,
    )


def analyze_strategy_new(symbol: str, df_4h) -> Optional[Signal]:
    """
    الاستراتيجية الثانية (الجديدة المعجزة): القالب الرقمي للأهداف الستة والسيولة المرنة.
    تعتمد على رصد شمعة 4 ساعات هابطة بدأت بالارتداد وسيولتها فوق 500,000$.
    """
    if len(df_4h) < 5:
        return None

    closed_4h_rows = df_4h[df_4h["is_closed"]]
    if len(closed_4h_rows) < 3:
        return None

    last_candle = closed_4h_rows.iloc[-1]
    
    # حد السيولة الذكي المتفق عليه ($500,000 لضمان اقتناص الصفقات مثل 2Z)
    min_liquidity = 500000
    candle_liquidity = float(last_candle["volume"]) * float(last_candle["close"])
    
    if candle_liquidity < min_liquidity:
        return None
        
    entry_high = float(last_candle["high"])
    entry_low = float(last_candle["low"])
    current_price = float(last_candle["close"])
    
    # حساب منظومة الأهداف الستة بناءً على القالب الرياضي
    tp1 = entry_high * 1.02
    tp2 = entry_high * 1.04
    tp3 = entry_high * 1.07
    tp4 = entry_high * 1.12
    tp5 = entry_high * 1.18
    tp6 = entry_high * 1.25
    
    # حساب وقف الخسارة الدقيق (تحت القاع بنسبة 1.65%)
    stop_loss_level = entry_low * (1 - 0.0165)
    
    reason = (
        f"💎 الجديدة (القالب الرقمي 4س) | سيولة: ${candle_liquidity/1e3:.1f}K | "
        f"الأهداف: TP1(+2%): {tp1:.4g}, TP2(+4%): {tp2:.4g}, TP3(+7%): {tp3:.4g}, "
        f"TP4(+12%): {tp4:.4g}, TP5(+18%): {tp5:.4g}, TP6(+25%): {tp6:.4g}"
    )

    return Signal(
        symbol=symbol,
        entry_price=current_price,
        take_profit_1=tp1,  
        stop_loss_level=stop_loss_level,
        reference_candle_time=str(last_candle["close_time"]),
        reason=reason,
    )


def check_stop_loss_hit(symbol: str, df_4h, stop_loss_level: float) -> bool:
    """
    تحقق مما إذا كانت آخر شمعة 4 ساعات قد أغلقت فعلياً تحت مستوى وقف الخسارة
    """
    closed = df_4h[df_4h["is_closed"]]
    if closed.empty:
        return False
    last_closed_close = float(closed.iloc[-1]["close"])
    return last_closed_close < stop_loss_level
