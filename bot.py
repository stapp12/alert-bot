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
# מצב המתנה לקלט מהמשתמש: {user_id: "action"}
waiting_input = {}


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


# ─── מקלדות ─────────────────────────────────────────────────────────────────

def kb_main():
    status_btn = "🔴 עצור בוט" if bot_active else "🟢 הפעל בוט"
    status_cb = "stop_bot" if bot_active else "start_bot"
    return {"inline_keyboard": [
        [{"text": "📊 סטטוס",      "callback_data": "status"},
         {"text": "📋 לוג",         "callback_data": "log"}],
        [{"text": status_btn,        "callback_data": status_cb},
         {"text": "📈 סטטיסטיקות", "callback_data": "areastats"}],
        [{"text": "📢 ערוצים",      "callback_data": "menu_channels"},
         {"text": "🔗 קישורים",     "callback_data": "menu_links"}],
        [{"text": "📣 שידור",       "callback_data": "broadcast_prompt"},
         {"text": "⏰ תזמון",       "callback_data": "schedule_prompt"}],
        [{"text": "🚫 חסימות",      "callback_data": "menu_block"},
         {"text": "✏️ תבנית",       "callback_data": "template_prompt"}],
    ]}


def kb_channels():
    rows = [[{"text": f"🗑 הסר: {name}", "callback_data": f"rmch_{ch_id}"}]
            for ch_id, name in channels.items()]
    rows.append([{"text": "➕ הוסף ערוץ", "callback_data": "addch_prompt"}])
    rows.append([{"text": "🔙 חזור",       "callback_data": "main_menu"}])
    return {"inline_keyboard": rows}


def kb_links():
    rows = [[{"text": f"🗑 הסר: {l[:25]}", "callback_data": f"rmlink_{i}"}]
            for i, l in enumerate(footer_links)]
    rows.append([{"text": "➕ הוסף קישור", "callback_data": "addlink_prompt"}])
    rows.append([{"text": "🔙 חזור",        "callback_data": "main_menu"}])
    return {"inline_keyboard": rows}


def kb_block():
    rows = [[{"text": f"✅ בטל חסימה: {a}", "callback_data": f"unblock_{a}"}]
            for a in sorted(blocked_areas)]
    rows.append([{"text": "➕ חסום אזור", "callback_data": "block_prompt"}])
    rows.append([{"text": "🔙 חזור",       "callback_data": "main_menu"}])
    return {"inline_keyboard": rows}


def kb_back():
    return {"inline_keyboard": [[{"text": "🔙 חזור לתפריט", "callback_data": "main_menu"}]]}


# ─── טיפול בלחיצות כפתור ─────────────────────────────────────────────────────

async def handle_callback(session, callback):
    cb_id = callback["id"]
    user_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]
    msg_id = callback["message"]["message_id"]
    data = callback.get("data", "")

    if user_id != ADMIN_ID:
        await answer_callback(session, cb_id, "⛔ אין הרשאה")
        return

    await answer_callback(session, cb_id)

    if data == "main_menu":
        status = "🟢 פעיל" if bot_active else "🔴 מושהה"
        await edit_message(session, chat_id, msg_id,
            f"🛠 *פאנל ניהול*\nמצב: {status} | ערוצים: {len(channels)} | התרעות: {stats['total']}",
            kb_main())

    elif data == "status":
        uptime = datetime.now() - stats["started_at"]
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m = rem // 60
        last = stats["last_alert"].strftime("%H:%M:%S %d/%m/%Y") if stats["last_alert"] else "אין עדיין"
        status_icon = "🟢 פעיל" if bot_active else "🔴 מושהה"
        filter_text = f"רק: {area_filter}" if area_filter else "הכל"
        await edit_message(session, chat_id, msg_id,
            f"📊 *סטטוס הבוט*\n\n"
            f"מצב: {status_icon}\n"
            f"סה\"כ התרעות: {stats['total']}\n"
            f"התרעה אחרונה: {last}\n"
            f"פילטור: {filter_text}\n"
            f"ערוצים: {len(channels)}\n"
            f"זמן פעילות: {h}h {m}m",
            kb_back())

    elif data == "log":
        if not alert_log:
            text = "📋 אין התרעות עדיין."
        else:
            lines = "\n".join([f"• {a['time']} — {a['area']} ({a.get('type','רקטה')})" for a in alert_log[-10:]])
            text = f"📋 *10 התרעות אחרונות:*\n\n{lines}"
        await edit_message(session, chat_id, msg_id, text, kb_back())

    elif data == "stop_bot":
        global bot_active
        bot_active = False
        await broadcast(session, "🔴 הבוט הושהה זמנית.")
        await edit_message(session, chat_id, msg_id,
            "🛠 *פאנל ניהול*\nמצב: 🔴 מושהה | ערוצים: " + str(len(channels)) + " | התרעות: " + str(stats['total']),
            kb_main())

    elif data == "start_bot":
        bot_active = True
        await broadcast(session, "🟢 הבוט חזר לפעילות!")
        await edit_message(session, chat_id, msg_id,
            "🛠 *פאנל ניהול*\nמצב: 🟢 פעיל | ערוצים: " + str(len(channels)) + " | התרעות: " + str(stats['total']),
            kb_main())

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
        await edit_message(session, chat_id, msg_id, f"📢 *ניהול ערוצים:*\n\n{ch_list}", kb_channels())

    elif data.startswith("rmch_"):
        ch_id = data[5:]
        if ch_id in channels:
            name = channels.pop(ch_id)
            ch_list = "\n".join([f"• {n} (`{c}`)" for c, n in channels.items()]) or "אין ערוצים"
            await edit_message(session, chat_id, msg_id, f"✅ הוסר: *{name}*\n\n📢 *ערוצים:*\n{ch_list}", kb_channels())

    elif data == "addch_prompt":
        waiting_input[user_id] = {"action": "addch", "chat_id": chat_id, "msg_id": msg_id}
        await edit_message(session, chat_id, msg_id,
            "📢 שלח את ה-ID של הערוץ ואחריו שם, למשל:\n`-1001234567890 ערוץ חדש`",
            kb_back())

    elif data == "menu_links":
        lnk_list = "\n".join([f"{i+1}. {l}" for i, l in enumerate(footer_links)]) or "אין קישורים"
        await edit_message(session, chat_id, msg_id, f"🔗 *קישורים קבועים:*\n\n{lnk_list}", kb_links())

    elif data.startswith("rmlink_"):
        idx = int(data[7:])
        if 0 <= idx < len(footer_links):
            footer_links.pop(idx)
        lnk_list = "\n".join([f"{i+1}. {l}" for i, l in enumerate(footer_links)]) or "אין קישורים"
        await edit_message(session, chat_id, msg_id, f"✅ קישור הוסר\n\n🔗 *קישורים:*\n{lnk_list}", kb_links())

    elif data == "addlink_prompt":
        waiting_input[user_id] = {"action": "addlink", "chat_id": chat_id, "msg_id": msg_id}
        await edit_message(session, chat_id, msg_id,
            "🔗 שלח טקסט ו-URL, למשל:\n`ערוץ הראשי https://t.me/beforpakar`",
            kb_back())

    elif data == "menu_block":
        bl_list = "\n".join([f"• {a}" for a in sorted(blocked_areas)]) or "אין חסימות"
        await edit_message(session, chat_id, msg_id, f"🚫 *אזורים חסומים:*\n\n{bl_list}", kb_block())

    elif data.startswith("unblock_"):
        area = data[8:]
        blocked_areas.discard(area)
        bl_list = "\n".join([f"• {a}" for a in sorted(blocked_areas)]) or "אין חסימות"
        await edit_message(session, chat_id, msg_id, f"✅ חסימה בוטלה: *{area}*\n\n🚫 *חסומים:*\n{bl_list}", kb_block())

    elif data == "block_prompt":
        waiting_input[user_id] = {"action": "block", "chat_id": chat_id, "msg_id": msg_id}
        await edit_message(session, chat_id, msg_id, "🚫 שלח שם האזור לחסימה:", kb_back())

    elif data == "broadcast_prompt":
        waiting_input[user_id] = {"action": "broadcast", "chat_id": chat_id, "msg_id": msg_id}
        await edit_message(session, chat_id, msg_id, "📣 שלח את ההודעה לשידור לכל הערוצים:", kb_back())

    elif data == "schedule_prompt":
        waiting_input[user_id] = {"action": "schedule", "chat_id": chat_id, "msg_id": msg_id}
        await edit_message(session, chat_id, msg_id,
            "⏰ שלח שעה והודעה בפורמט:\n`HH:MM טקסט ההודעה`",
            kb_back())

    elif data == "template_prompt":
        waiting_input[user_id] = {"action": "template", "chat_id": chat_id, "msg_id": msg_id}
        await edit_message(session, chat_id, msg_id,
            f"✏️ תבנית נוכחית:\n`{alert_template}`\n\nשלח תבנית חדשה (השתמש ב-`{{area}}` לשם האזור):",
            kb_back())


# ─── טיפול בקלט טקסט חופשי ───────────────────────────────────────────────────

async def handle_input(session, chat_id, user_id, text):
    global bot_active, area_filter, alert_template
    state = waiting_input.pop(user_id, None)
    if not state:
        return False

    action = state["action"]
    orig_chat = state["chat_id"]
    orig_msg = state["msg_id"]

    if action == "addch":
        parts = text.strip().split(None, 1)
        if len(parts) < 2:
            await send(session, chat_id, "❌ פורמט שגוי. שלח: `<id> <שם>`")
            return True
        ch_id, ch_name = parts
        channels[ch_id] = ch_name
        await send(session, chat_id, f"✅ ערוץ נוסף: *{ch_name}*")
        ch_list = "\n".join([f"• {n} (`{c}`)" for c, n in channels.items()])
        await edit_message(session, orig_chat, orig_msg, f"📢 *ניהול ערוצים:*\n\n{ch_list}", kb_channels())

    elif action == "addlink":
        parts = text.strip().rsplit(None, 1)
        if len(parts) < 2:
            await send(session, chat_id, "❌ פורמט שגוי. שלח: `<טקסט> <url>`")
            return True
        link_text, url = parts
        footer_links.append(f"🔗 [{link_text}]({url})")
        await send(session, chat_id, f"✅ קישור נוסף.")
        lnk_list = "\n".join([f"{i+1}. {l}" for i, l in enumerate(footer_links)])
        await edit_message(session, orig_chat, orig_msg, f"🔗 *קישורים:*\n\n{lnk_list}", kb_links())

    elif action == "block":
        blocked_areas.add(text.strip())
        await send(session, chat_id, f"🚫 חסום: *{text.strip()}*")
        bl_list = "\n".join([f"• {a}" for a in sorted(blocked_areas)])
        await edit_message(session, orig_chat, orig_msg, f"🚫 *חסומים:*\n\n{bl_list}", kb_block())

    elif action == "broadcast":
        await broadcast(session, text.strip())
        await send(session, chat_id, f"✅ שודר ל-{len(channels)} ערוצים.")
        await edit_message(session, orig_chat, orig_msg,
            f"🛠 *פאנל ניהול*\nמצב: {'🟢' if bot_active else '🔴'} | ערוצים: {len(channels)} | התרעות: {stats['total']}",
            kb_main())

    elif action == "schedule":
        parts = text.strip().split(None, 1)
        if len(parts) < 2:
            await send(session, chat_id, "❌ פורמט שגוי. שלח: `HH:MM הודעה`")
            return True
        time_str, msg_text = parts
        try:
            now = datetime.now()
            send_time = datetime.strptime(time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
            if send_time < now:
                send_time += timedelta(days=1)
            scheduled.append({"text": msg_text, "send_at": send_time})
            await send(session, chat_id, f"✅ מתוזמן לשעה {time_str}.")
        except:
            await send(session, chat_id, "❌ פורמט שעה שגוי.")

    elif action == "template":
        alert_template = text.strip().replace("\\n", "\n")
        await send(session, chat_id, f"✅ תבנית עודכנה.")

    return True


# ─── לולאות ──────────────────────────────────────────────────────────────────

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
                    cb = update["callback_query"]
                    if cb["from"]["id"] == ADMIN_ID:
                        asyncio.create_task(handle_callback(session, cb))
                    continue

                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                user_id = msg.get("from", {}).get("id")
                if not text or not chat_id or not user_id:
                    continue
                if user_id != ADMIN_ID:
                    continue

                # בדוק אם ממתינים לקלט
                if user_id in waiting_input:
                    asyncio.create_task(handle_input(session, chat_id, user_id, text))
                    continue

                # פקודות
                if text.startswith("/start") or text.startswith("/menu"):
                    status = "🟢 פעיל" if bot_active else "🔴 מושהה"
                    await send(session, chat_id,
                        f"🛠 *פאנל ניהול*\nמצב: {status} | ערוצים: {len(channels)} | התרעות: {stats['total']}",
                        kb_main())

        except Exception as e:
            print(f"Telegram error: {e}")
        await asyncio.sleep(1)


async def fetch_alerts(session):
    try:
        async with session.get(OREF_URL, headers=OREF_HEADERS, timeout=aiohttp.ClientTimeout(total=5)) as r:
            text = await r.text(encoding="utf-8-sig")
            if not text.strip():
                return None
            return json.loads(text)
    except:
        return None


async def alert_loop(session):
    print("Alert loop started...")
    while True:
        try:
            if bot_active:
                data = await fetch_alerts(session)
                if data and data.get("data"):
                    alert_id = data.get("id", "")
                    category = data.get("cat", 1)
                    areas = data.get("data", [])
                    for area in areas:
                        key = f"{alert_id}_{area}"
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
