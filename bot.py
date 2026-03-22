import asyncio
import aiohttp
import json
from datetime import datetime

BOT_TOKEN = "8662594909:AAFUX9KHgLStD2wzYVA6NzC_speQBicDAsA"
CHANNEL_ID = "-1001084391143"
ADMIN_ID = 6300100326

OREF_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
OREF_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0"
}
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

seen_alerts = set()
alert_log = []
stats = {"total": 0, "last_alert": None, "started_at": datetime.now()}
bot_active = True
area_filter = None
offset = 0


async def tg(session, method, **kwargs):
    try:
        async with session.post(f"{TG_API}/{method}", json=kwargs, timeout=aiohttp.ClientTimeout(total=15)) as r:
            return await r.json()
    except:
        return {}


async def send(session, chat_id, text):
    await tg(session, "sendMessage", chat_id=chat_id, text=text, parse_mode="Markdown")


async def handle_command(session, chat_id, user_id, text):
    global bot_active, area_filter

    if user_id != ADMIN_ID:
        await send(session, chat_id, "⛔ אין לך הרשאה.")
        return

    parts = text.strip().split()
    cmd = parts[0].lower().split("@")[0]
    args = parts[1:]

    if cmd == "/status":
        uptime = datetime.now() - stats["started_at"]
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m = rem // 60
        last = stats["last_alert"].strftime("%H:%M:%S %d/%m/%Y") if stats["last_alert"] else "אין עדיין"
        status_icon = "🟢 פעיל" if bot_active else "🔴 מושהה"
        filter_text = f"רק: {area_filter}" if area_filter else "הכל"
        await send(session, chat_id,
            f"📊 *סטטוס הבוט*\n\n"
            f"מצב: {status_icon}\n"
            f"סה\"כ התרעות: {stats['total']}\n"
            f"התרעה אחרונה: {last}\n"
            f"פילטור אזור: {filter_text}\n"
            f"זמן פעילות: {h}h {m}m"
        )

    elif cmd == "/log":
        if not alert_log:
            await send(session, chat_id, "📋 אין התרעות עדיין.")
        else:
            lines = "\n".join([f"• {a['time']} — {a['area']}" for a in alert_log[-10:]])
            await send(session, chat_id, f"📋 *10 התרעות אחרונות:*\n\n{lines}")

    elif cmd == "/stop":
        bot_active = False
        await send(session, chat_id, "🔴 הבוט הושהה. שלח /start להפעלה מחדש.")

    elif cmd == "/start":
        bot_active = True
        await send(session, chat_id, "🟢 הבוט פעיל שוב!")

    elif cmd == "/filter":
        if not args:
            await send(session, chat_id, "שימוש: /filter <אזור> או /filter off")
        elif args[0].lower() == "off":
            area_filter = None
            await send(session, chat_id, "✅ פילטור בוטל — מקבל התרעות מכל האזורים.")
        else:
            area_filter = " ".join(args)
            await send(session, chat_id, f"✅ פילטור הוגדר: רק התרעות מ-*{area_filter}*")

    elif cmd == "/help":
        await send(session, chat_id,
            "🛠 *פקודות אדמין:*\n\n"
            "/status — סטטיסטיקות ומצב הבוט\n"
            "/log — 10 התרעות אחרונות\n"
            "/stop — השהיית הבוט\n"
            "/start — הפעלת הבוט\n"
            "/filter <אזור> — פילטור לפי אזור\n"
            "/filter off — ביטול פילטור\n"
            "/help — הצגת עזרה זו"
        )


async def telegram_loop(session):
    global offset
    print("Telegram polling started...")
    while True:
        try:
            result = await tg(session, "getUpdates", offset=offset, timeout=5)
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                user_id = msg.get("from", {}).get("id")
                if text and text.startswith("/") and chat_id and user_id:
                    asyncio.create_task(handle_command(session, chat_id, user_id, text))
        except Exception as e:
            print(f"Telegram error: {e}")
        await asyncio.sleep(1)


async def fetch_alerts(session):
    try:
        async with session.get(OREF_URL, headers=OREF_HEADERS, timeout=aiohttp.ClientTimeout(total=5)) as r:
            text = await r.text(encoding="utf-8-sig")
            if not text.strip():
                return []
            return json.loads(text).get("data", [])
    except:
        return []


async def alert_loop(session):
    print("Alert loop started...")
    while True:
        try:
            if bot_active:
                alerts = await fetch_alerts(session)
                for area in alerts:
                    if area not in seen_alerts:
                        seen_alerts.add(area)
                        if area_filter and area_filter not in area:
                            continue
                        await send(session, CHANNEL_ID, f"🚨 *אזעקה*\n{area}\n\n📢 [קבל התרעות בזמן אמת](https://t.me/beforpakar)")
                        now = datetime.now()
                        stats["total"] += 1
                        stats["last_alert"] = now
                        alert_log.append({"time": now.strftime("%H:%M:%S"), "area": area})
                        if len(alert_log) > 100:
                            alert_log.pop(0)
                        print(f"Sent alert: {area}")
                if len(seen_alerts) > 500:
                    seen_alerts.clear()
        except Exception as e:
            print(f"Alert error: {e}")
        await asyncio.sleep(3)


async def main():
    print("Bot starting...")
    async with aiohttp.ClientSession() as session:
        print("Bot started! Polling for commands and alerts...")
        await asyncio.gather(
            telegram_loop(session),
            alert_loop(session)
        )

asyncio.run(main())
