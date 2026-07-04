# -*- coding: utf-8 -*-
"""إرسال إشعارات إلى تيليجرام فقط (لا يوجد أي تنفيذ تلقائي للصفقات)."""

import requests
import config


def send_telegram_message(text: str) -> bool:
    if "ضع_" in config.TELEGRAM_BOT_TOKEN or "ضع_" in config.TELEGRAM_CHAT_ID:
        print("[تنبيه] لم تُضبط بيانات تيليجرام بعد في config.py:\n", text)
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
        f"🛑 مستوى وقف الخسارة (تأكيد بإغلاق شمعة 4 ساعات تحته): "
        f"<code>{signal.stop_loss_level:.6g}</code>\n\n"
        f"📊 سبب الإشارة:\n{signal.reason}\n\n"
        f"⚠️ هذه إشارة اجتهادية وليست توصية مضمونة. الرجاء إدارة رأس المال "
        f"بحجم مناسب لا يتجاوز ما تتحمل خسارته."
    )


def format_stop_loss_message(symbol: str, stop_loss_level: float) -> str:
    return (
        f"🔴 <b>تفعيل وقف الخسارة - إغلاق شمعة 4 ساعات مؤكد</b>\n"
        f"العملة: <b>{symbol}</b>\n"
        f"أُغلقت شمعة 4 ساعات تحت مستوى: <code>{stop_loss_level:.6g}</code>\n"
        f"يُنصح بالخروج من الصفقة أو مراجعتها فوراً."
    )
