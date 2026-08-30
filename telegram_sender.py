# =========================================================
# TELEGRAM SENDER
# Sends HTML-formatted text messages to Telegram
# Replaces the Apps Script sendTextToTelegram_ function
# =========================================================

import requests
import time
import json


def escape_html(text):
    """Escape special HTML characters for Telegram HTML parse_mode."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def send_text_to_telegram(headline, description, analysis, key_points, config):
    """
    Send a plain-text current affairs message to Telegram using HTML parse_mode.

    analysis: dict with keys: exams (list), source (str), domain (str), link (str)
    Returns dict: {success, status_code, message}
    """
    max_retries = config.get("telegram_retries", 5)
    send_delay = config.get("send_delay", 2.0)

    exam_str = " | ".join(analysis.get("exams", [])) if analysis.get("exams") else "GENERAL"
    source_str = analysis.get("source") or "Unknown"
    domain_str = analysis.get("domain") or "GENERAL"

    # Build HTML message
    msg = "<b>CURRENT AFFAIRS</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "<b>" + escape_html(headline) + "</b>\n\n"

    if description:
        clean = description.replace("\n", " ").strip()
        if len(clean) > config.get("description_chars", 400):
            clean = clean[: config.get("description_chars", 400)] + "..."
        msg += escape_html(clean) + "\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>Exam:</b> " + escape_html(exam_str) + "\n"
    msg += "<b>Source:</b> " + escape_html(source_str) + "\n"
    msg += "<b>Domain:</b> " + escape_html(domain_str) + "\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n"

    if key_points:
        msg += "\n<b>Key Points:</b>\n"
        for kp in key_points[:3]:
            clean_kp = kp.replace("\n", " ").strip()
            if clean_kp:
                msg += "  • " + escape_html(clean_kp) + "\n"

    if analysis.get("link"):
        msg += "\n<b>Read More:</b> " + escape_html(analysis["link"]) + "\n"

    msg += "\n#CurrentAffairs #HarritClasses"
    msg += "\n<i>Source: " + escape_html(source_str) + "</i>"

    for attempt in range(max_retries + 1):
        try:
            url = "https://api.telegram.org/bot" + config["telegram_bot_token"] + "/sendMessage"
            resp = requests.post(
                url,
                data={
                    "chat_id": config["telegram_chat_id"],
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=30,
            )
            status = resp.status_code
            try:
                body = resp.json()
            except Exception:
                body = {"ok": False, "description": resp.text}

            if status == 200 and body.get("ok"):
                if send_delay:
                    time.sleep(send_delay)
                return {"success": True, "status_code": status, "message": "Sent successfully"}

            err = body.get("description", "Unknown error")
            # Telegram flood control
            if status == 429 or "Too Many Requests" in err:
                retry_after = 5
                try:
                    retry_after = int(body.get("parameters", {}).get("retry_after", 5))
                except Exception:
                    pass
                time.sleep(retry_after + 1)
                if attempt < max_retries:
                    continue
                return {"success": False, "status_code": status, "message": err}

            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            return {"success": False, "status_code": status, "message": err}
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            return {"success": False, "status_code": 0, "message": str(e)}

    return {"success": False, "status_code": 0, "message": "Max retries exceeded"}


def test_connection(config):
    """Verify bot token + chat id work."""
    try:
        url = "https://api.telegram.org/bot" + config["telegram_bot_token"] + "/getMe"
        resp = requests.get(url, timeout=15)
        me = resp.json()
        if not me.get("ok"):
            return {"ok": False, "error": me.get("description")}
        return {"ok": True, "bot": me["result"].get("username")}
    except Exception as e:
        return {"ok": False, "error": str(e)}
