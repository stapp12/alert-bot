import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

BOT_TOKEN = "8662594909:AAFUX9KHgLStD2wzYVA6NzC_speQBicDAsA"
ADMIN_ID = 6300100326

OREF_URL = "https://api.tzevaadom.co.il/alerts"
OREF_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0"
}
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

CATEGORY_INFO = {
    1:  {"emoji": "🚀", "title": "ירי רקטות וטילים"},
    2:  {"emoji": "✈️", "title": "חדירת כלי טיס עוין"},
    3:  {"emoji": "☢️", "title": "אירוע רדיולוגי"},
    4:  {"emoji": "🧪", "title": "חומרים מסוכנים"},
    5:  {"emoji": "🌊", "title": "צונאמי"},
    6:  {"emoji": "🌍", "title": "רעידת אדמה"},
    7:  {"emoji": "⚠️",  "title": "אירוע בטחוני"},
    9:  {"emoji": "🛸", "title": "כטב\"מ עוין"},
    13: {"emoji": "🚨", "title": "טיל בליסטי"},
}
BALLISTIC_CATEGORIES = {13}

channels = {"-1001084391143": "ערוץ ראשי"}
bot_active = True
area_filter = None
blocked_areas = set()
footer_links = ["📢 [קבל התרעות בזמן אמת](https://t.me/beforpakar)"]
alert_template = "🚨 *אזעקה*\n{area}"

seen_alerts = set()
alert_log = []
area_stats = {}
stats = {"total": 0, "last_alert": None, "started_at": datetime.now()}
scheduled = []
offset = 0

# מצב המתנה לקלט מהמשתמש
waiting_for = {}  # {chat_id: action}


async def tg(session, method, **kwargs):
    try:
        async with session.post(f"{TG_API}/{method}", json=kwargs, timeout=aiohttp.ClientTimeout(total=15)) as r:
            return await r.json()
    except Exception as e:
        print(f"TG error: {e}")
        return {}


async def send(session, chat_id, text, reply_markup=None):
    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    await tg(session, "sendMessage", **kwargs)


async def edit_message(session, chat_id, message_id, text, reply_markup=None):
    kwargs = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    await tg(session, "editMessageText", **kwargs)


async def answer_callback(session, callback_id, text=""):
    await tg(session, "answerCallbackQuery", callback_query_id=callback_id, text=text)


async def broadcast(session, text, channel_list=None):
    targets = channel_list or list(channels.keys())
    for ch in targets:
        await send(session, ch, text)


def build_alert_message(area, category=1):
    info = CATEGORY_INFO.get(category, {"emoji": "🚨", "title": "אזעקה"})
    if category in BALLISTIC_CATEGORIES:
        msg = f"⚡️ *התרעה קיצונית — {info['title']}*\n🌍 {area}\n\n_זמן הגעה: כ-3-5 דקות. היכנסו למרחב מוגן מיידית!_"
    else:
        msg = f"{info['emoji']} *{info['title']}*\n{area}"
    if footer_links:
        msg += "\n\n" + "\n".join(footer_links)
    return msg


# ─── מקלדות ──────────────────────────────────────────────

def kb_main():
    status_btn = "🔴 עצור" if bot_active else "🟢 הפעל"
    status_cb = "stop" if bot_active else "start"
    return {"inline_keyboard": [
        [{"text": "📊 סטטוס", "callback_data": "status"},
         {"text": "📋 לוג", "callback_data": "log"}],
        [{"text": status_btn, "callback_data": status_cb},
         {"text": "📈 סטטיסטיקות", "callback_data": "areastats"}],
        [{"text": "📢 ערוצים", "callback_data": "menu_channels"},
         {"text": "🔗 קישורים", "callback_data": "menu_links"}],
        [{"text": "📣 שידור", "callback_data": "ask_broadcast"},
         {"text": "⏰ תזמון", "callback_data": "ask_schedule"}],
        [{"text": "🚫 חסימות", "callback_data": "menu_block"},
         {"text": "✏️ תבנית", "callback_data": "ask_template"}],
    ]}


def kb_channels():
    rows = [[{"text": f"🗑 הסר: {name}", "callback_data": f"rmch_{ch_id}"}]
            for ch_id, name in channels.items()]
    rows.append([{"text": "➕ הוסף ערוץ", "callback_data": "ask_addchannel"}])
    rows.append([{"text": "🔙 חזרה", "callback_data": "main"}])
    return {"inline_keyboard": rows}


def kb_links():
    rows = [[{"text": f"🗑 הסר: {l[l.find('[')+1:l.find(']')]}", "callback_data": f"rmlink_{i}"}]
            for i, l in enumerate(footer_links)]
    rows.append([{"text": "➕ הוסף קישור", "callback_data": "ask_addlink"}])
    rows.append([{"text": "🔙 חזרה", "callback_data": "main"}])
    return {"inline_keyboard": rows}


def kb_block():
    rows = [[{"text": f"✅ בטל חסימה: {a}", "callback_data": f"unblock_{a}"}]
            for a in sorted(blocked_areas)]
    rows.append([{"text": "➕ חסום אזור", "callback_data": "ask_blockarea"}])
    rows.append([{"text": f"🔍 פילטור: {'כבוי' if not area_filter else area_filter}", "callback_data": "ask_filter"}])
    rows.append([{"text": "🔙 חזרה", "callback_data": "main"}])
    return {"inline_keyboard": rows}


def kb_back():
    return {"inline_keyboard": [[{"text": "🔙 חזרה", "callback_data": "main"}]]}


# ─── טיפול בלחיצות כפתורים ───────────────────────────────

async def handle_callback(session, callback):
    global bot_active, area_filter, alert_template
    cb_id = callback["id"]
    chat_id = callback["message"]["chat"]["id"]
    msg_id = callback["message"]["message_id"]
    user_id = callback["from"]["id"]
    data = callback.get("data", "")

    if user_id != ADMIN_ID:
        await answer_callback(session, cb_id, "⛔ אין הרשאה")
        return

    await answer_callback(session, cb_id)

    if data == "main":
        await edit_message(session, chat_id, msg_id, "🛠 *פאנל ניהול*", kb_main())

    elif data == "status":
        uptime = datetime.now() - stats["started_at"]
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m = rem // 60
        last = stats["last_alert"].strftime("%H:%M:%S %d/%m/%Y") if stats["last_alert"] else "אין עדיין"
        status_icon = "🟢 פעיל" if bot_active else "🔴 מושהה"
        filter_text = f"רק: {area_filter}" if area_filter else "הכל"
        text = (
            f"📊 *סטטוס הבוט*\n\n"
            f"מצב: {status_icon}\n"
            f"סה\"כ התרעות: {stats['total']}\n"
            f"התרעה אחרונה: {last}\n"
            f"פילטור: {filter_text}\n"
            f"ערוצים: {len(channels)}\n"
            f"זמן פעילות: {h}h {m}m"
        )
        await edit_message(session, chat_id, msg_id, text, kb_back())

    elif data == "log":
        if not alert_log:
            text = "📋 אין התרעות עדיין."
        else:
            lines = "\n".join([f"• {a['time']} — {a['area']} ({a.get('type','רקטה')})" for a in alert_log[-10:]])
            text = f"📋 *10 התרעות אחרונות:*\n\n{lines}"
        await edit_message(session, chat_id, msg_id, text, kb_back())

    elif data == "stop":
        bot_active = False
        await broadcast(session, "🔴 הבוט הושהה זמנית.")
        await edit_message(session, chat_id, msg_id, "🛠 *פאנל ניהול*", kb_main())

    elif data == "start":
        bot_active = True
        await broadcast(session, "🟢 הבוט חזר לפעילות!")
        await edit_message(session, chat_id, msg_id, "🛠 *פאנל ניהול*", kb_main())

    elif data == "areastats":
        if not area_stats:
            text = "📈 אין סטטיסטיקות עדיין."
        else:
            top = sorted(area_stats.items(), key=lambda x: x[1], reverse=True)[:10]
            lines = "\n".join([f"• {area}: {count}" for area, count in top])
            text = f"📈 *TOP 10 אזורים:*\n\n{lines}"
        await edit_message(session, chat_id, msg_id, text, kb_back())

    elif data == "menu_channels":
        ch_list = "\n".join([f"• {name} (`{ch_id}`)" for ch_id, name in channels.items()]) or "אין ערוצים"
        await edit_message(session, chat_id, msg_id, f"📢 *ערוצים פעילים:*\n\n{ch_list}", kb_channels())

    elif data.startswith("rmch_"):
        ch_id = data[5:]
        if ch_id in channels:
            name = channels.pop(ch_id)
            await answer_callback(session, cb_id, f"✅ הוסר: {name}")
        ch_list = "\n".join([f"• {name} (`{cid}`)" for cid, name in channels.items()]) or "אין ערוצים"
        await edit_message(session, chat_id, msg_id, f"📢 *ערוצים פעילים:*\n\n{ch_list}", kb_channels())

    elif data == "ask_addchannel":
        waiting_for[chat_id] = "addchannel"
        await edit_message(session, chat_id, msg_id, "שלח: `<channel_id> <שם>`\nלדוגמה: `-1001234567890 ערוץ שני`", kb_back())

    elif data == "menu_links":
        links_text = "\n".join([f"{i+1}. {l}" for i, l in enumerate(footer_links)]) or "אין קישורים"
        await edit_message(session, chat_id, msg_id, f"🔗 *קישורים קבועים:*\n\n{links_text}", kb_links())

    elif data.startswith("rmlink_"):
        idx = int(data[7:])
        if 0 <= idx < len(footer_links):
            footer_links.pop(idx)
        links_text = "\n".join([f"{i+1}. {l}" for i, l in enumerate(footer_links)]) or "אין קישורים"
        await edit_message(session, chat_id, msg_id, f"🔗 *קישורים קבועים:*\n\n{links_text}", kb_links())

    elif data == "ask_addlink":
        waiting_for[chat_id] = "addlink"
        await edit_message(session, chat_id, msg_id, "שלח: `<טקסט> <url>`\nלדוגמה: `הצטרף לערוץ https://t.me/beforpakar`", kb_back())

    elif data == "menu_block":
        blocked_text = "\n".join([f"• {a}" for a in sorted(blocked_areas)]) or "אין חסימות"
        filter_text = f"פילטור פעיל: {area_filter}" if area_filter else "פילטור: כבוי"
        await edit_message(session, chat_id, msg_id, f"🚫 *חסימות ופילטורים*\n\n{blocked_text}\n\n{filter_text}", kb_block())

    elif data.startswith("unblock_"):
        area = data[8:]
        blocked_areas.discard(area)
        blocked_text = "\n".join([f"• {a}" for a in sorted(blocked_areas)]) or "אין חסימות"
        filter_text = f"פילטור פעיל: {area_filter}" if area_filter else "פילטור: כבוי"
        await edit_message(session, chat_id, msg_id, f"🚫 *חסימות ופילטורים*\n\n{blocked_text}\n\n{filter_text}", kb_block())

    elif data == "ask_blockarea":
        waiting_for[chat_id] = "blockarea"
        await edit_message(session, chat_id, msg_id, "שלח שם האזור לחסימה:", kb_back())

    elif data == "ask_filter":
        waiting_for[chat_id] = "filter"
        await edit_message(session, chat_id, msg_id, "שלח שם אזור לפילטור, או `off` לביטול:", kb_back())

    elif data == "ask_broadcast":
        waiting_for[chat_id] = "broadcast"
        await edit_message(session, chat_id, msg_id, "✍️ שלח את ההודעה לשידור לכל הערוצים:", kb_back())

    elif data == "ask_schedule":
        waiting_for[chat_id] = "schedule"
        await edit_message(session, chat_id, msg_id, "⏰ שלח: `HH:MM טקסט ההודעה`\nלדוגמה: `20:00 בדיקת מערכת`", kb_back())

    elif data == "ask_template":
        waiting_for[chat_id] = "template"
        await edit_message(session, chat_id, msg_id,
            f"✏️ תבנית נוכחית:\n`{alert_template}`\n\nשלח תבנית חדשה. השתמש ב-`{{area}}` לשם האזור:", kb_back())


# ─── טיפול בקלט חופשי (אחרי לחיצת כפתור) ────────────────

async def handle_free_input(session, chat_id, user_id, text):
    global bot_active, area_filter, alert_template

    if user_id != ADMIN_ID:
        return

    action = waiting_for.pop(chat_id, None)
    if not action:
        return

    parts = text.strip().split()

    if action == "broadcast":
        await broadcast(session, text)
        await send(session, chat_id, f"✅ שודר ל-{len(channels)} ערוצים.", kb_main())

    elif action == "addchannel":
        if len(parts) >= 2:
            ch_id = parts[0]
            ch_name = " ".join(parts[1:])
            channels[ch_id] = ch_name
            await send(session, chat_id, f"✅ ערוץ נוסף: *{ch_name}*", kb_main())
        else:
            await send(session, chat_id, "❌ פורמט שגוי. נסה: `-100xxx שם`")
            waiting_for[chat_id] = action

    elif action == "addlink":
        if len(parts) >= 2:
            url = parts[-1]
            link_text = " ".join(parts[:-1])
            footer_links.append(f"🔗 [{link_text}]({url})")
            await send(session, chat_id, f"✅ קישור נוסף.", kb_main())
        else:
            await send(session, chat_id, "❌ פורמט שגוי.")
            waiting_for[chat_id] = action

    elif action == "blockarea":
        blocked_areas.add(text.strip())
        await send(session, chat_id, f"🚫 אזור חסום: *{text.strip()}*", kb_main())

    elif action == "filter":
        if text.strip().lower() == "off":
            area_filter = None
            await send(session, chat_id, "✅ פילטור בוטל.", kb_main())
        else:
            area_filter = text.strip()
            await send(session, chat_id, f"✅ פילטור: *{area_filter}*", kb_main())

    elif action == "schedule":
        if len(parts) >= 2:
            time_str = parts[0]
            msg_text = " ".join(parts[1:])
            try:
                now = datetime.now()
                send_time = datetime.strptime(time_str, "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                if send_time < now:
                    send_time += timedelta(days=1)
                scheduled.append({"text": msg_text, "send_at": send_time})
                await send(session, chat_id, f"✅ מתוזמן לשעה {time_str}.", kb_main())
            except:
                await send(session, chat_id, "❌ פורמט שגוי. נסה: `20:00 טקסט`")
                waiting_for[chat_id] = action
        else:
            await send(session, chat_id, "❌ פורמט שגוי.")
            waiting_for[chat_id] = action

    elif action == "template":
        alert_template = text.replace("\\n", "\n")
        await send(session, chat_id, "✅ תבנית עודכנה.", kb_main())


# ─── לולאות ──────────────────────────────────────────────

async def telegram_loop(session):
    global offset
    print("Telegram polling started...")
    while True:
        try:
            result = await tg(session, "getUpdates", offset=offset, timeout=5)
            for update in result.get("result", []):
                offset = update["update_id"] + 1

                # callback מכפתור
                if "callback_query" in update:
                    asyncio.create_task(handle_callback(session, update["callback_query"]))
                    continue

                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                user_id = msg.get("from", {}).get("id")
                if not text or not chat_id or not user_id:
                    continue

                if text == "/start" or text == "/menu":
                    await send(session, chat_id, "🛠 *פאנל ניהול*", kb_main())
                elif text.startswith("/"):
                    await send(session, chat_id, "השתמש ב /menu לפאנל הניהול.")
                elif chat_id in waiting_for:
                    asyncio.create_task(handle_free_input(session, chat_id, user_id, text))

        except Exception as e:
            print(f"Telegram error: {e}")
        await asyncio.sleep(1)


async def fetch_alerts(session):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        async with session.get(OREF_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as r:
            text = await r.text()
            if not text.strip():
                return []
            data = json.loads(text)
            # tzevaadom מחזיר list של objects עם name, threat_id וכו
            if isinstance(data, list):
                return data
            # oref מחזיר dict עם data
            if isinstance(data, dict) and data.get("data"):
                return [{"name": a, "threat_id": data.get("cat", 1), "id": data.get("id","")} for a in data["data"]]
            return []
    except Exception as e:
        print(f"Fetch error: {e}")
        return []


async def alert_loop(session):
    print("Alert loop started...")
    while True:
        try:
            if bot_active:
                alerts = await fetch_alerts(session)
                for alert in alerts:
                    # tzevaadom format: {notifications: [{cities:[...], threat:N}], id:...}
                    # או list פשוטה
                    if isinstance(alert, dict):
                        area = alert.get("name") or alert.get("city") or str(alert)
                        category = alert.get("threat_id") or alert.get("threat") or 1
                        alert_id = str(alert.get("id", ""))
                    else:
                        area = str(alert)
                        category = 1
                        alert_id = ""
                    
                    key = f"{alert_id}_{area}" if alert_id else area
                    if key not in seen_alerts:
                        seen_alerts.add(key)
                        if any(blocked in area for blocked in blocked_areas):
                            continue
                        if area_filter and area_filter not in area:
                            continue
                        msg = build_alert_message(area, category)
                        await broadcast(session, msg)
                        now = datetime.now()
                        stats["total"] += 1
                        stats["last_alert"] = now
                        area_stats[area] = area_stats.get(area, 0) + 1
                        cat_info = CATEGORY_INFO.get(category, {"title": "אזעקה"})
                        alert_log.append({"time": now.strftime("%H:%M:%S"), "area": area, "type": cat_info["title"]})
                        if len(alert_log) > 100:
                            alert_log.pop(0)
                        await send(session, ADMIN_ID, f"🔔 *{cat_info['title']}*\nאזור: {area}")
                        print(f"Sent [{cat_info['title']}]: {area}")
                if len(seen_alerts) > 1000:
                    seen_alerts.clear()
        except Exception as e:
            print(f"Alert error: {e}")
        await asyncio.sleep(1)


async def scheduler_loop(session):
    print("Scheduler started...")
    while True:
        now = datetime.now()
        for item in scheduled[:]:
            if now >= item["send_at"]:
                await broadcast(session, item["text"])
                scheduled.remove(item)
                await send(session, ADMIN_ID, f"✅ הודעה מתוזמנת נשלחה.")
        await asyncio.sleep(10)


async def main():
    print("Bot starting...")
    async with aiohttp.ClientSession() as session:
        print("Bot started!")
        await asyncio.gather(
            telegram_loop(session),
            alert_loop(session),
            scheduler_loop(session)
        )

asyncio.run(main())
