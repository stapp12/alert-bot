import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

BOT_TOKEN = "8662594909:AAFUX9KHgLStD2wzYVA6NzC_speQBicDAsA"
ADMIN_ID = 6300100326

OREF_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
OREF_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0"
}
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ערוצים פעילים: {channel_id: name}
channels = {"-1001084391143": "ערוץ ראשי"}

# הגדרות
bot_active = True
area_filter = None          # None = הכל, string = רק אזור זה
blocked_areas = set()       # אזורים מוסתרים
footer_links = ["📢 [קבל התרעות בזמן אמת](https://t.me/beforpakar)"]

# תבנית הודעה
alert_template = "🚨 *אזעקה*\n{area}"

# סטטיסטיקות
seen_alerts = set()
alert_log = []
area_stats = {}
stats = {"total": 0, "last_alert": None, "started_at": datetime.now()}

# תזמון
scheduled = []  # [{text, send_at, channels}]

offset = 0


async def tg(session, method, **kwargs):
    try:
        async with session.post(f"{TG_API}/{method}", json=kwargs, timeout=aiohttp.ClientTimeout(total=15)) as r:
            return await r.json()
    except Exception as e:
        print(f"TG error: {e}")
        return {}


async def send(session, chat_id, text):
    await tg(session, "sendMessage", chat_id=chat_id, text=text, parse_mode="Markdown")


async def broadcast(session, text, channel_list=None):
    targets = channel_list or list(channels.keys())
    for ch in targets:
        await send(session, ch, text)


def build_alert_message(area):
    msg = alert_template.replace("{area}", area)
    if footer_links:
        msg += "\n\n" + "\n".join(footer_links)
    return msg


async def handle_command(session, chat_id, user_id, text):
    global bot_active, area_filter, alert_template

    if user_id != ADMIN_ID:
        await send(session, chat_id, "⛔ אין לך הרשאה.")
        return

    parts = text.strip().split()
    cmd = parts[0].lower().split("@")[0]
    args = parts[1:]
    rest = " ".join(args)

    # ─── סטטוס ─────────────────────────────────────────
    if cmd == "/status":
        uptime = datetime.now() - stats["started_at"]
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m = rem // 60
        last = stats["last_alert"].strftime("%H:%M:%S %d/%m/%Y") if stats["last_alert"] else "אין עדיין"
        status_icon = "🟢 פעיל" if bot_active else "🔴 מושהה"
        filter_text = f"רק: {area_filter}" if area_filter else "הכל"
        blocked_text = ", ".join(blocked_areas) if blocked_areas else "אין"
        await send(session, chat_id,
            f"📊 *סטטוס הבוט*\n\n"
            f"מצב: {status_icon}\n"
            f"סה\"כ התרעות: {stats['total']}\n"
            f"התרעה אחרונה: {last}\n"
            f"פילטור אזור: {filter_text}\n"
            f"אזורים חסומים: {blocked_text}\n"
            f"ערוצים פעילים: {len(channels)}\n"
            f"זמן פעילות: {h}h {m}m"
        )

    # ─── לוג ────────────────────────────────────────────
    elif cmd == "/log":
        if not alert_log:
            await send(session, chat_id, "📋 אין התרעות עדיין.")
        else:
            lines = "\n".join([f"• {a['time']} — {a['area']}" for a in alert_log[-10:]])
            await send(session, chat_id, f"📋 *10 התרעות אחרונות:*\n\n{lines}")

    # ─── עצור/הפעל ──────────────────────────────────────
    elif cmd == "/stop":
        bot_active = False
        await broadcast(session, "🔴 הבוט הושהה זמנית.")
        await send(session, chat_id, "🔴 הבוט הושהה. שלח /start להפעלה.")

    elif cmd == "/start":
        bot_active = True
        await broadcast(session, "🟢 הבוט חזר לפעילות!")
        await send(session, chat_id, "🟢 הבוט פעיל!")

    # ─── ניהול ערוצים ───────────────────────────────────
    elif cmd == "/addchannel":
        # /addchannel -100xxxxxxx שם הערוץ
        if len(args) < 2:
            await send(session, chat_id, "שימוש: /addchannel <channel_id> <שם>")
            return
        ch_id = args[0]
        ch_name = " ".join(args[1:])
        channels[ch_id] = ch_name
        await send(session, chat_id, f"✅ ערוץ נוסף: *{ch_name}* (`{ch_id}`)")

    elif cmd == "/removechannel":
        if not args:
            await send(session, chat_id, "שימוש: /removechannel <channel_id>")
            return
        ch_id = args[0]
        if ch_id in channels:
            name = channels.pop(ch_id)
            await send(session, chat_id, f"✅ ערוץ הוסר: *{name}*")
        else:
            await send(session, chat_id, "❌ ערוץ לא נמצא.")

    elif cmd == "/channels":
        if not channels:
            await send(session, chat_id, "📋 אין ערוצים פעילים.")
        else:
            lines = "\n".join([f"• {name} — `{ch_id}`" for ch_id, name in channels.items()])
            await send(session, chat_id, f"📋 *ערוצים פעילים ({len(channels)}):*\n\n{lines}")

    # ─── עריכת תבנית ────────────────────────────────────
    elif cmd == "/settemplate":
        # /settemplate 🚨 *אזעקה*\n{area}
        if not rest:
            await send(session, chat_id,
                f"תבנית נוכחית:\n`{alert_template}`\n\n"
                "שימוש: /settemplate <תבנית>\n"
                "השתמש ב-`{area}` לשם האזור"
            )
            return
        alert_template = rest.replace("\\n", "\n")
        await send(session, chat_id, f"✅ תבנית עודכנה:\n{alert_template.replace('{area}', 'דוגמה')}")

    # ─── קישורים קבועים ─────────────────────────────────
    elif cmd == "/addlink":
        # /addlink טקסט https://...
        if len(args) < 2:
            await send(session, chat_id, "שימוש: /addlink <טקסט> <url>")
            return
        link_text = " ".join(args[:-1])
        url = args[-1]
        footer_links.append(f"🔗 [{link_text}]({url})")
        await send(session, chat_id, f"✅ קישור נוסף: [{link_text}]({url})")

    elif cmd == "/removelink":
        if not footer_links:
            await send(session, chat_id, "אין קישורים.")
            return
        lines = "\n".join([f"{i+1}. {l}" for i, l in enumerate(footer_links)])
        await send(session, chat_id, f"קישורים קיימים:\n{lines}\n\nשלח: /dellink <מספר>")

    elif cmd == "/dellink":
        if not args or not args[0].isdigit():
            await send(session, chat_id, "שימוש: /dellink <מספר>")
            return
        idx = int(args[0]) - 1
        if 0 <= idx < len(footer_links):
            removed = footer_links.pop(idx)
            await send(session, chat_id, f"✅ קישור הוסר: {removed}")
        else:
            await send(session, chat_id, "❌ מספר לא תקין.")

    elif cmd == "/links":
        if not footer_links:
            await send(session, chat_id, "אין קישורים קבועים.")
        else:
            lines = "\n".join([f"{i+1}. {l}" for i, l in enumerate(footer_links)])
            await send(session, chat_id, f"🔗 *קישורים קבועים:*\n\n{lines}")

    # ─── שידור חופשי ────────────────────────────────────
    elif cmd == "/broadcast":
        if not rest:
            await send(session, chat_id, "שימוש: /broadcast <הודעה>")
            return
        await broadcast(session, rest)
        await send(session, chat_id, f"✅ הודעה שודרה ל-{len(channels)} ערוצים.")

    # ─── תזמון הודעה ────────────────────────────────────
    elif cmd == "/schedule":
        # /schedule HH:MM הודעה
        if len(args) < 2:
            await send(session, chat_id, "שימוש: /schedule <HH:MM> <הודעה>")
            return
        time_str = args[0]
        msg_text = " ".join(args[1:])
        try:
            now = datetime.now()
            send_time = datetime.strptime(time_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            if send_time < now:
                send_time += timedelta(days=1)
            scheduled.append({"text": msg_text, "send_at": send_time})
            await send(session, chat_id, f"✅ הודעה מתוזמנת לשעה {time_str}:\n{msg_text}")
        except:
            await send(session, chat_id, "❌ פורמט שעה לא תקין. השתמש ב-HH:MM")

    elif cmd == "/scheduled":
        if not scheduled:
            await send(session, chat_id, "אין הודעות מתוזמנות.")
        else:
            lines = "\n".join([f"• {s['send_at'].strftime('%H:%M')} — {s['text'][:30]}" for s in scheduled])
            await send(session, chat_id, f"⏰ *הודעות מתוזמנות:*\n\n{lines}")

    # ─── פילטור אזורים ──────────────────────────────────
    elif cmd == "/filter":
        if not args:
            await send(session, chat_id, "שימוש: /filter <אזור> או /filter off")
            return
        if args[0].lower() == "off":
            area_filter = None
            await send(session, chat_id, "✅ פילטור בוטל — כל האזורים פעילים.")
        else:
            area_filter = rest
            await send(session, chat_id, f"✅ פילטור: רק התרעות מ-*{area_filter}*")

    elif cmd == "/blockarea":
        if not rest:
            await send(session, chat_id, "שימוש: /blockarea <אזור>")
            return
        blocked_areas.add(rest)
        await send(session, chat_id, f"🚫 אזור חסום: *{rest}*")

    elif cmd == "/unblockarea":
        if rest in blocked_areas:
            blocked_areas.remove(rest)
            await send(session, chat_id, f"✅ חסימה בוטלה: *{rest}*")
        else:
            await send(session, chat_id, "❌ האזור לא נמצא ברשימת החסומים.")

    elif cmd == "/blocklist":
        if not blocked_areas:
            await send(session, chat_id, "אין אזורים חסומים.")
        else:
            lines = "\n".join([f"• {a}" for a in sorted(blocked_areas)])
            await send(session, chat_id, f"🚫 *אזורים חסומים:*\n\n{lines}")

    # ─── סטטיסטיקות לפי אזור ────────────────────────────
    elif cmd == "/areastats":
        if not area_stats:
            await send(session, chat_id, "אין סטטיסטיקות עדיין.")
        else:
            top = sorted(area_stats.items(), key=lambda x: x[1], reverse=True)[:10]
            lines = "\n".join([f"• {area}: {count} התרעות" for area, count in top])
            await send(session, chat_id, f"📈 *סטטיסטיקות לפי אזור (TOP 10):*\n\n{lines}")

    # ─── עזרה ───────────────────────────────────────────
    elif cmd == "/help":
        await send(session, chat_id,
            "🛠 *פקודות אדמין:*\n\n"
            "*כללי:*\n"
            "/status — סטטוס ומצב הבוט\n"
            "/log — 10 התרעות אחרונות\n"
            "/stop — השהיית הבוט\n"
            "/start — הפעלת הבוט\n\n"
            "*ניהול ערוצים:*\n"
            "/channels — רשימת ערוצים\n"
            "/addchannel <id> <שם> — הוספת ערוץ\n"
            "/removechannel <id> — הסרת ערוץ\n\n"
            "*הודעות:*\n"
            "/settemplate — עריכת תבנית אזעקה\n"
            "/broadcast <טקסט> — שידור לכל הערוצים\n"
            "/schedule <HH:MM> <טקסט> — תזמון הודעה\n"
            "/scheduled — הודעות מתוזמנות\n\n"
            "*קישורים:*\n"
            "/links — רשימת קישורים\n"
            "/addlink <טקסט> <url> — הוספת קישור\n"
            "/removelink — הסרת קישור\n\n"
            "*פילטורים:*\n"
            "/filter <אזור> — פילטור לפי אזור\n"
            "/filter off — ביטול פילטור\n"
            "/blockarea <אזור> — חסימת אזור\n"
            "/unblockarea <אזור> — ביטול חסימה\n"
            "/blocklist — אזורים חסומים\n"
            "/areastats — סטטיסטיקות לפי אזור\n"
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

                        # בדוק חסימות
                        if any(blocked in area for blocked in blocked_areas):
                            continue
                        if area_filter and area_filter not in area:
                            continue

                        msg = build_alert_message(area)
                        await broadcast(session, msg)

                        # עדכן סטטיסטיקות
                        now = datetime.now()
                        stats["total"] += 1
                        stats["last_alert"] = now
                        area_stats[area] = area_stats.get(area, 0) + 1
                        alert_log.append({"time": now.strftime("%H:%M:%S"), "area": area})
                        if len(alert_log) > 100:
                            alert_log.pop(0)

                        # התראה לאדמין
                        await send(session, ADMIN_ID, f"🔔 *אזעקה חדשה:* {area}")
                        print(f"Sent alert: {area}")

                if len(seen_alerts) > 500:
                    seen_alerts.clear()
        except Exception as e:
            print(f"Alert error: {e}")
        await asyncio.sleep(3)


async def scheduler_loop(session):
    print("Scheduler started...")
    while True:
        now = datetime.now()
        for item in scheduled[:]:
            if now >= item["send_at"]:
                await broadcast(session, item["text"])
                scheduled.remove(item)
                await send(session, ADMIN_ID, f"✅ הודעה מתוזמנת נשלחה:\n{item['text']}")
        await asyncio.sleep(10)


async def main():
    print("Bot starting...")
    async with aiohttp.ClientSession() as session:
        print("Bot started! Polling for commands and alerts...")
        await asyncio.gather(
            telegram_loop(session),
            alert_loop(session),
            scheduler_loop(session)
        )

asyncio.run(main())
