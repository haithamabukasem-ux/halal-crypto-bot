# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Optional
import config, indicators

@dataclass
class Signal:
    symbol: str
    entry_price: float
    take_profit_1: float
    stop_loss_level: float
    reference_candle_time: str
    reason: str

def analyze_strategy_old(symbol, df_4h, df_1h) -> Optional[Signal]:
    return None # الاستراتيجية القديمة معطلة مؤقتاً للتأكد من استقرار السيرفر

def analyze_strategy_new(symbol, df_4h) -> Optional[Signal]:
    if len(df_4h) < 3: return None
    last = df_4h[df_4h["is_closed"]].iloc[-1]
    # شرط السيولة
    if (float(last["volume"]) * float(last["close"])) < 500000: return None
    
    tp = float(last["high"]) * 1.02
    sl = float(last["low"]) * 0.98
    
    return Signal(symbol, float(last["close"]), tp, sl, str(last["close_time"]), "فحص جديد")

def check_stop_loss_hit(symbol, df_4h, sl) -> bool:
    return float(df_4h.iloc[-1]["close"]) < sl
