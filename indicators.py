# -*- coding: utf-8 -*-
"""حساب المؤشرات الفنية - النسخة المحسّنة (يشمل ATR وStochastic RSI)."""

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def stoch_rsi(series: pd.Series, period: int = 14, k: int = 3, d: int = 3):
    """يرجع (%K, %D) لمؤشر Stochastic RSI."""
    rsi_series = rsi(series, period)
    min_rsi = rsi_series.rolling(period).min()
    max_rsi = rsi_series.rolling(period).max()
    stoch = (rsi_series - min_rsi) / (max_rsi - min_rsi).replace(0, 1e-10) * 100
    k_line = stoch.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    return k_line, d_line


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """متوسط المدى الحقيقي - لقياس تقلب العملة الفعلي."""
    high_low = df["high"] - df["low"]
    high_close_prev = (df["high"] - df["close"].shift(1)).abs()
    low_close_prev = (df["low"] - df["close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def add_all_indicators(df: pd.DataFrame, ema_fast: int, ema_slow: int,
                        rsi_period: int, macd_fast: int, macd_slow: int,
                        macd_signal: int, stoch_period: int = 14,
                        stoch_k: int = 3, stoch_d: int = 3,
                        atr_period: int = 14, volume_ma_period: int = 20) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = ema(df["close"], ema_fast)
    df["ema_slow"] = ema(df["close"], ema_slow)
    df["rsi"] = rsi(df["close"], rsi_period)
    df["stoch_k"], df["stoch_d"] = stoch_rsi(df["close"], stoch_period, stoch_k, stoch_d)
    df["macd"], df["macd_signal"], df["macd_hist"] = macd(
        df["close"], macd_fast, macd_slow, macd_signal
    )
    df["atr"] = atr(df, atr_period)
    df["volume_ma"] = df["volume"].rolling(volume_ma_period).mean()
    return df
