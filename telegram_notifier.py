# -*- coding: utf-8 -*-
"""إرسال إشعارات إلى تيليجرام فقط (لا يوجد أي تنفيذ تلقائي للصفقات)."""

import requests
import config


def send_telegram_message(text: str) -> bool:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[تنبيه] لم تُضبط بيانات تيليجرام بعد:\n", text)
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[خطأ إرسال تيليجرام]: {e}")
        return False


def format_entry_message(signal) -> str:
    return (
        f"🟢 <b>إشارة دخول جديدة - Spot فقط (بدون هامش)</b>\n"
        f"العملة: <b>{signal.symbol}</b>\n\n"
        f"💰 سعر الدخول: <code>{signal.entry_price:.6g}</code>\n"
        f"🎯 الهدف الأول (2%): <code>{signal.take_profit_1:.6g}</code>\n"
        f"🎯 الهدف الثاني (4%): <code>{signal.take_profit_2:.6g}</code>\n"
        f"🎯 الهدف الثالث (6%): <code>{signal.take_profit_3:.6g}</code>\n"
        f"🛑 وقف الخسارة (ديناميكي حسب تقلب العملة، تأكيد بإغلاق شمعة 4 ساعات): "
        f"<code>{signal.stop_loss_level:.6g}</code>\n"
        f"⚖️ نسبة العائد للمخاطرة: <b>{signal.risk_reward_ratio:.1f}:1</b>\n\n"
        f"⚠️ الرجاء إدارة رأس المال بحجم مناسب لا يتجاوز ما تتحمل خسارته."
    )


def format_take_profit_message(symbol: str, entry_price: float, target_price: float, target_num: int) -> str:
    pnl_pct = (target_price - entry_price) / entry_price * 100
    return (
        f"🎯 <b>تحقق الهدف {target_num} - ربح {pnl_pct:.1f}%</b>\n"
        f"العملة: <b>{symbol}</b>\n"
        f"سعر الدخول: <code>{entry_price:.6g}</code>\n"
        f"السعر الحالي: <code>{target_price:.6g}</code>\n\n"
        f"✅ ممكن تجني الأرباح الآن أو تراقب الصفقة براحتك."
    )


def format_stop_loss_message(symbol: str, stop_loss_level: float) -> str:
    return (
        f"🔴 <b>تفعيل وقف الخسارة - إغلاق شمعة 4 ساعات مؤكد</b>\n"
        f"العملة: <b>{symbol}</b>\n"
        f"أُغلقت شمعة 4 ساعات تحت مستوى: <code>{stop_loss_level:.6g}</code>\n"
        f"يُنصح بالخروج من الصفقة أو مراجعتها فوراً."
    )


def format_breakeven_exit_message(symbol: str, entry_price: float, exit_level: float) -> str:
    pnl_pct = (exit_level - entry_price) / entry_price * 100
    return (
        f"🟡 <b>خروج بحماية الأرباح - إغلاق شمعة 4 ساعات مؤكد</b>\n"
        f"العملة: <b>{symbol}</b>\n"
        f"أُغلقت شمعة 4 ساعات تحت مستوى الوقف المُحرَّك: <code>{exit_level:.6g}</code>\n"
        f"النتيجة: <b>{pnl_pct:+.1f}%</b> (تم تأمين جزء من الربح بعد تحقق هدف سابق)."
    )
