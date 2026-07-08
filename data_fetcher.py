# -*- coding: utf-8 -*-
"""جلب بيانات الشموع (Klines) من واجهة Binance العامة - بدون مفتاح API."""

import time
import requests
import pandas as pd
from config import BINANCE_BASE_URL

COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def get_klines(symbol: str, interval: str, limit: int = 300) -> pd.DataFrame:
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    raw = resp.json()

    df = pd.DataFrame(raw, columns=COLUMNS)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    now_ms = int(time.time() * 1000)
    df["is_closed"] = df["close_time"].astype("int64") // 10**6 < now_ms

    return df[["open_time", "open", "high", "low", "close", "volume",
               "close_time", "is_closed"]]


def get_current_price(symbol: str) -> float:
    url = f"{BINANCE_BASE_URL}/api/v3/ticker/price"
    resp = requests.get(url, params={"symbol": symbol}, timeout=10)
    resp.raise_for_status()
    return float(resp.json()["price"])
