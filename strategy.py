# -*- coding: utf-8 -*-
"""
الاستراتيجية المحسّنة (v2) - طبقات تأكيد متعددة:
1) اتجاه يومي (EMA50 > EMA200) + اتجاه 4 ساعات (EMA21 > EMA50)
2) زخم مزدوج: RSI يخرج من تشبع بيعي + Stochastic RSI يؤكد + MACD Histogram يتحسن
3) تأكيد حجم تداول أعلى من المتوسط
4) وقف خسارة ديناميكي مبني على ATR (يعكس تقلب كل عملة الفعلي)
5) فلتر إلزامي: نسبة العائد للمخاطرة >= 2:1، وإلا تُرفض الإشارة
6) ثلاثة أهداف متدرجة (2% / 4% / 6%)

تنويه: هذا نظام محسّن ومنطقي، وليس ضماناً للربح. لا توجد استراتيجية
تداول بدقة 100% أو نسبة نجاح مضمونة.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import config
import indicators


@dataclass
class Signal:
    symbol: str
    entry_price: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    stop_loss_level: float
    risk_reward_ratio: float
    reference_candle_time: str
    reason: str


def _prepare(df, ema_fast, ema_slow, rsi_p, macd_f, macd_s, macd_sig,
             stoch_p=14, stoch_k=3, stoch_d=3, atr_p=14, vol_ma_p=20):
    return indicators.add_all_indicators(
        df, ema_fast, ema_slow, rsi_p, macd_f, macd_s, macd_sig,
        stoch_p, stoch_k, stoch_d, atr_p, vol_ma_p,
    )


def analyze_symbol(symbol: str, df_daily, df_4h, df_1h) -> Optional[Signal]:
    min_len = max(config.EMA_TREND_DAILY, config.EMA_SLOW) + 5
    if len(df_daily) < min_len or len(df_4h) < config.EMA_SLOW + 5 or len(df_1h) < config.EMA_SLOW + 5:
        return None

    df_daily = _prepare(df_daily, config.EMA_SLOW, config.EMA_TREND_DAILY,
                         config.RSI_PERIOD, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)
    df_4h = _prepare(df_4h, config.EMA_FAST, config.EMA_SLOW,
                      config.RSI_PERIOD, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL,
                      config.STOCH_RSI_PERIOD, config.STOCH_K, config.STOCH_D,
                      config.ATR_PERIOD, config.VOLUME_MA_PERIOD)
    df_1h = _prepare(df_1h, config.EMA_FAST, config.EMA_SLOW,
                      config.RSI_PERIOD, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL,
                      config.STOCH_RSI_PERIOD, config.STOCH_K, config.STOCH_D,
                      config.ATR_PERIOD, config.VOLUME_MA_PERIOD)

    closed_daily = df_daily[df_daily["is_closed"]]
    closed_4h = df_4h[df_4h["is_closed"]]
    closed_1h_rows = df_1h[df_1h["is_closed"]]

    if len(closed_daily) < 2 or len(closed_4h) < 2 or len(closed_1h_rows) < 3:
        return None

    last_daily = closed_daily.iloc[-1]
    last_4h = closed_4h.iloc[-1]
    last_1h = closed_1h_rows.iloc[-1]
    prev_1h = closed_1h_rows.iloc[-2]

    # ---- الطبقة 1: تأكيد الاتجاه (يومي + 4 ساعات) ----
    daily_uptrend = last_daily["ema_fast"] > last_daily["ema_slow"]
    trend_4h_up = last_4h["ema_fast"] > last_4h["ema_slow"]
    if not (daily_uptrend and trend_4h_up):
        return None

    # ---- الطبقة 2: زخم مزدوج ----
    rsi_recovering = prev_1h["rsi"] < config.RSI_OVERSOLD <= last_1h["rsi"]
    stoch_confirms = prev_1h["stoch_k"] < config.STOCH_OVERSOLD + 15
    macd_improving = last_1h["macd_hist"] > prev_1h["macd_hist"]
    macd_cross_up = (prev_1h["macd"] <= prev_1h["macd_signal"]
                      and last_1h["macd"] > last_1h["macd_signal"])
    not_overbought = last_1h["rsi"] < config.RSI_OVERBOUGHT

    momentum_ok = rsi_recovering and stoch_confirms and (macd_improving or macd_cross_up) and not_overbought
    if not momentum_ok:
        return None

    # ---- الطبقة 3: تأكيد حجم التداول ----
    if last_1h["volume_ma"] == 0 or pd.isna(last_1h["volume_ma"]):
        return None
    volume_ratio = last_1h["volume"] / last_1h["volume_ma"]
    if volume_ratio < config.VOLUME_MIN_RATIO:
        return None

    # ---- قرب السعر من دعم EMA50 ----
    near_support = last_1h["close"] <= last_1h["ema_slow"] * 1.015
    if not near_support:
        return None

    entry_price = float(last_1h["close"])

    # ---- الطبقة 4: وقف خسارة ديناميكي مبني على ATR ----
    atr_4h = float(last_4h["atr"])
    if pd.isna(atr_4h) or atr_4h <= 0:
        return None
    stop_loss_level = entry_price - (config.ATR_MULTIPLIER * atr_4h)
    if stop_loss_level >= entry_price:
        return None

    # ---- الأهداف المتدرجة ----
    take_profit_1 = entry_price * (1 + config.TAKE_PROFIT_1_PCT)
    take_profit_2 = entry_price * (1 + config.TAKE_PROFIT_2_PCT)
    take_profit_3 = entry_price * (1 + config.TAKE_PROFIT_3_PCT)

    # ---- الطبقة 5: فلتر نسبة العائد للمخاطرة (إلزامي) ----
    risk = entry_price - stop_loss_level
    reward = take_profit_1 - entry_price
    risk_reward_ratio = reward / risk if risk > 0 else 0
    if risk_reward_ratio < config.MIN_RISK_REWARD_RATIO:
        return None

    reason = (
        f"اتجاه صاعد يومي و4س | RSI+StochRSI+MACD يؤكدون خروج من تشبع بيعي | "
        f"حجم تداول {volume_ratio:.1f}x المتوسط | وقف ديناميكي (ATR) | "
        f"نسبة عائد:مخاطرة {risk_reward_ratio:.1f}:1"
    )

    return Signal(
        symbol=symbol,
        entry_price=entry_price,
        take_profit_1=take_profit_1,
        take_profit_2=take_profit_2,
        take_profit_3=take_profit_3,
        stop_loss_level=stop_loss_level,
        risk_reward_ratio=risk_reward_ratio,
        reference_candle_time=str(last_4h["close_time"]),
        reason=reason,
    )


def check_stop_loss_hit(symbol: str, df_4h, stop_loss_level: float) -> bool:
    """يتحقق فقط بإغلاق شمعة 4 ساعات فعلياً تحت مستوى وقف الخسارة."""
    closed = df_4h[df_4h["is_closed"]]
    if closed.empty:
        return False
    last_closed_close = float(closed.iloc[-1]["close"])
    return last_closed_close < stop_loss_level
