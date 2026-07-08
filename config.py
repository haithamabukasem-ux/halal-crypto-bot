# -*- coding: utf-8 -*-
"""إعدادات بوت التداول الحلال - النسخة المحسّنة (v2)."""

import os

# ---------------------------------------------------------------------------
# 1) نطاق العملات: أعلى العملات سيولةً بدل كل عملات بايننس
#    (يمكن تعديل القائمة براحتك)
# ---------------------------------------------------------------------------
HIGH_LIQUIDITY_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "TRXUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
    "LTCUSDT", "BCHUSDT", "UNIUSDT", "ATOMUSDT", "XLMUSDT", "ETCUSDT",
    "FILUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "NEARUSDT", "ICPUSDT",
    "INJUSDT", "SUIUSDT", "AAVEUSDT", "ALGOUSDT", "VETUSDT", "SANDUSDT",
]

EXCLUDE_KEYWORDS = ["UP", "DOWN", "BULL", "BEAR"]

# ---------------------------------------------------------------------------
# 2) الأطر الزمنية
# ---------------------------------------------------------------------------
DAILY_TIMEFRAME = "1d"
TREND_TIMEFRAME = "4h"
ENTRY_TIMEFRAME = "1h"

# ---------------------------------------------------------------------------
# 3) إعدادات المؤشرات
# ---------------------------------------------------------------------------
EMA_FAST = 21
EMA_SLOW = 50
EMA_TREND_DAILY = 200

RSI_PERIOD = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 70

STOCH_RSI_PERIOD = 14
STOCH_K = 3
STOCH_D = 3
STOCH_OVERSOLD = 20

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5

VOLUME_MA_PERIOD = 20
VOLUME_MIN_RATIO = 1.2

# ---------------------------------------------------------------------------
# 4) إدارة الصفقة والمخاطر
# ---------------------------------------------------------------------------
MIN_RISK_REWARD_RATIO = 2.0

TAKE_PROFIT_1_PCT = 0.02
TAKE_PROFIT_2_PCT = 0.04
TAKE_PROFIT_3_PCT = 0.06

# ---------------------------------------------------------------------------
# 5) تيليجرام
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# 6) التشغيل
# ---------------------------------------------------------------------------
SCAN_INTERVAL_SECONDS = 300
KLINES_LIMIT = 300

BINANCE_BASE_URL = "https://api.binance.com"
