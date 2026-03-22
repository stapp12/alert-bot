import asyncio, aiohttp, json, logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = "8662594909:AAFUX9KHgLStD2wzYVA6NzC_speQBicDAsA"
ADMIN_ID = 6300100326

OREF_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
# עדכון ה-Headers לפורמט שעבד ב-PowerShell
OREF_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9",
}

CATEGORY_INFO = {
    1:  {"emoji": "🚀", "title": "ירי רקטות וטילים"},
    2:  {"emoji": "✈️", "title": "חדירת כלי טיס עוין"},
    3:  {"emoji": "☢️", "title": "אירוע רדיולוגי"},
    4:  {"emoji": "🧪", "title": "חומרים מסוכנים"},
    5:  {"emoji": "🌊", "title": "צונאמי"},
    6:  {"emoji": "🌍", "title": "רעידת אדמה"},
    7:  {"emoji": "⚠️", "title": "אירוע בטחוני"},
    9:  {"emoji": "🛸", "title": "כטב\"מ עוין"},
    13: {"emoji": "🚨", "title": "טיל בליסטי"},
}

# מיפוי ערים למחוזות
CITY_TO_DISTRICT = {
    # מחוז דן
    "תל אביב": "מחוז דן", "תל אביב - מרכז העיר": "מחוז דן", "תל אביב - דרום העיר": "מחוז דן",
    "תל אביב - צפון העיר": "מחוז דן", "תל אביב - מזרח": "מחוז דן",
    "רמת גן": "מחוז דן", "גבעתיים": "מחוז דן", "בני ברק": "מחוז דן",
    "פתח תקווה": "מחוז דן", "אור יהודה": "מחוז דן", "אזור": "מחוז דן",
    "בת ים": "מחוז דן", "חולון": "מחוז דן", "יהוד": "מחוז דן",
    "קריית אונו": "מחוז דן", "גבעת שמואל": "מחוז דן", "אלעד": "מחוז דן",
    "ראש העין": "מחוז דן",
    # מחוז ירושלים
    "ירושלים": "מחוז ירושלים", "ירושלים - מרכז": "מחוז ירושלים",
    "ירושלים - דרום": "מחוז ירושלים", "ירושלים - צפון": "מחוז ירושלים",
    "ירושלים - מזרח": "מחוז ירושלים", "בית שמש": "מחוז ירושלים",
    "מבשרת ציון": "מחוז ירושלים", "מודיעין עילית": "מחוז ירושלים",
    # מחוז חיפה
    "חיפה": "מחוז חיפה", "חיפה - כרמל": "מחוז חיפה", "חיפה - מרכז הכרמל": "מחוז חיפה",
    "חיפה - כרמל ועיר תחתית": "מחוז חיפה", "חיפה - נווה שאנן": "מחוז חיפה",
    "חיפה - קריית חיים": "מחוז חיפה", "קריית אתא": "מחוז חיפה",
    "קריית ביאליק": "מחוז חיפה", "קריית מוצקין": "מחוז חיפה",
    "קריית ים": "מחוז חיפה", "טירת כרמל": "מחוז חיפה",
    "נשר": "מחוז חיפה", "עכו": "מחוז חיפה", "נהריה": "מחוז חיפה",
    "כרמיאל": "מחוז חיפה", "עפולה": "מחוז חיפה",
    # מחוז צפון
    "צפת": "מחוז צפון", "טבריה": "מחוז צפון", "קצרין": "מחוז צפון",
    "קריית שמונה": "מחוז צפון", "מטולה": "מחוז צפון", "שלומי": "מחוז צפון",
    "מעלות תרשיחא": "מחוז צפון", "נהריה": "מחוז צפון",
    "בית שאן": "מחוז צפון", "אפולה": "מחוז צפון",
    # מחוז המרכז
    "ראשון לציון": "מחוז המרכז", "נס ציונה": "מחוז המרכז",
    "רחובות": "מחוז המרכז", "לוד": "מחוז המרכז", "רמלה": "מחוז המרכז",
    "מודיעין": "מחוז המרכז", "רעננה": "מחוז המרכז", "כפר סבא": "מחוז המרכז",
    "הוד השרון": "מחוז המרכז", "נתניה": "מחוז המרכז", "הרצליה": "מחוז המרכז",
    "רמת השרון": "מחוז המרכז", "גדרה": "מחוז המרכז", "יבנה": "מחוז המרכז",
    # מחוז דרום
    "באר שבע": "מחוז דרום", "אשדוד": "מחוז דרום", "אשקלון": "מחוז דרום",
    "קריית גת": "מחוז דרום", "דימונה": "מחוז דרום", "ערד": "מחוז דרום",
    "נתיבות": "מחוז דרום", "שדרות": "מחוז דרום", "אופקים": "מחוז דרום",
    "קריית מלאכי": "מחוז דרום", "רהט": "מחוז דרום",
    # עוטף עזה
    "שדרות, איבים, ניר עם": "עוטף עזה", "ניר עם": "עוטף עזה",
    "כיסופים": "עוטף עזה", "נחל עוז": "עוטף עזה", "כפר עזה": "עוטף עזה",
    "בארי": "עוטף עזה", "רעים": "עוטף עזה",
    # ערבה ואילת
    "אילת": "ערבה ואילת", "יטבתה": "ערבה ואילת", "עין יהב": "ערבה ואילת",
}

def get_district(city):
    """מחזיר מחוז לפי שם עיר — בדיקה חלקית"""
    for key, district in CITY_TO_DISTRICT.items():
        if key in city or city in key:
            return district
    return None

def group_by_district(areas):
    """מקבץ רשימת ערים לפי מחוזות"""
    districts = {}
    unknown = []
    for area in areas:
        district = get_district(area)
        if district:
            districts.setdefault(district, []).append(area)
        else:
            unknown.append(area)
    return districts, unknown

BALLISTIC = {13}

# קטגוריות מותרות — ברירת מחדל: הכל
allowed_categories = set(CATEGORY_INFO.keys())

channels = {"-1001084391143": "ערוץ ראשי"}
bot_active = True
blocked_areas = set()
area_filter = None
footer = "📢 [קבל התרעות בזמן אמת](https://t.me/beforpakar)"
scheduled = []

seen_ids = set()
alert_log = []
area_stats = {}
stats = {"total": 0, "last": None, "start": datetime.now()}

offset = 0
waiting_for = {}


async def tg(session, method, **kwargs):
    try:
        async with session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=kwargs,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as r:
            return await r.json()
    except Exception as e:
        logger.error(f"TG error: {e}")
        return {}


async def send(session, chat_id, text, markup=None):
    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    if markup:
        kwargs["reply_markup"] = markup
    await tg(session, "sendMessage", **kwargs)


async def edit(session, chat_id, msg_id, text, markup=None):
    kwargs = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    if markup:
        kwargs["reply_markup"] = markup
    await tg(session, "editMessageText", **kwargs)


async def broadcast(session, text):
    for ch in list(channels.keys()):
        await send(session, ch, text)


def build_msg(areas, category=1):
    info = CATEGORY_INFO.get(category, {"emoji": "🚨", "title": "אזעקה"})
    if isinstance(areas, str):
        areas = [areas]
    
    # קיבוץ לפי מחוזות
    districts, unknown = group_by_district(areas)
    
    lines = []
    for district, cities in sorted(districts.items()):
        lines.append(f"📍 *{district}*")
        for city in cities:
            lines.append(f"   • {city}")
    for city in unknown:
        lines.append(f"📍 {city}")
    
    location_text = "\n".join(lines)
    
    if category in BALLISTIC:
        msg = f"⚡️ *התרעה קיצונית — {info['title']}*\n\n{location_text}\n\n_זמן הגעה: כ-3-5 דקות. היכנסו למרחב מוגן מיידית!_"
    else:
        count = len(areas)
        district_count = len(districts)
        summary = f"{count} יישובים ב-{district_count} מחוזות" if district_count > 1 else f"{count} יישובים"
        msg = f"{info['emoji']} *{info['title']}*\n_{summary}_\n\n{location_text}"
    
    msg += f"\n\n{footer}"
    return msg


def kb_main():
    label = "🔴 עצור בוט" if bot_active else "🟢 הפעל בוט"
    return {"inline_keyboard": [
        [{"text": "📊 סטטוס", "callback_data": "status"},
         {"text": "📋 לוג", "callback_data": "log"}],
        [{"text": label, "callback_data": "toggle"},
         {"text": "🧪 טסט", "callback_data": "test"}],
        [{"text": "📢 ערוצים", "callback_data": "channels"},
         {"text": "🔗 קישורים", "callback_data": "links"}],
        [{"text": "📣 שידור", "callback_data": "ask_broadcast"},
         {"text": "⏰ תזמון", "callback_data": "ask_schedule"}],
        [{"text": "🚫 חסימות", "callback_data": "blocks"},
         {"text": "📈 סטטיסטיקות", "callback_data": "areastats"}],
        [{"text": "🔔 סוגי התרעות", "callback_data": "categories"}],
        [{"text": "❌ סגור", "callback_data": "close"}],
    ]}


def kb_back():
    return {"inline_keyboard": [[{"text": "🔙 חזרה לתפריט", "callback_data": "home"}]]}


def kb_channels():
    rows = [[{"text": f"🗑 הסר: {name}", "callback_data": f"rmch_{cid}"}]
            for cid, name in channels.items()]
    rows.append([{"text": "➕ הוסף ערוץ", "callback_data": "ask_addchannel"}])
    rows.append([{"text": "🔙 חזרה לתפריט", "callback_data": "home"}])
    return {"inline_keyboard": rows}


def kb_blocks():
    rows = [[{"text": f"✅ בטל: {a}", "callback_data": f"unblock_{a}"}]
            for a in sorted(blocked_areas)]
    rows.append([{"text": "➕ חסום אזור", "callback_data": "ask_block"}])
    filter_txt = f"🔍 פילטור: {area_filter}" if area_filter else "🔍 הגדר פילטור"
    rows.append([{"text": filter_txt, "callback_data": "ask_filter"}])
    rows.append([{"text": "🔙 חזרה לתפריט", "callback_data": "home"}])
    return {"inline_keyboard": rows}



def kb_categories():
    rows = []
    for cat_id, info in CATEGORY_INFO.items():
        status = "✅" if cat_id in allowed_categories else "❌"
        rows.append([{"text": f"{status} {info['emoji']} {info['title']}", "callback_data": f"togglecat_{cat_id}"}])
    rows.append([{"text": "✅ הפעל הכל", "callback_data": "allcats_on"},
                 {"text": "❌ כבה הכל", "callback_data": "allcats_off"}])
    rows.append([{"text": "🔙 חזרה לתפריט", "callback_data": "home"}])
    return {"inline_keyboard": rows}

async def handle_callback(session, cb):
    global bot_active, area_filter
    cid = cb["message"]["chat"]["id"]
    mid = cb["message"]["message_id"]
    uid = cb["from"]["id"]
    d = cb.get("data", "")
    cbid = cb["id"]

    if uid != ADMIN_ID:
        await tg(session, "answerCallbackQuery", callback_query_id=cbid, text="⛔ אין הרשאה")
        return

    await tg(session, "answerCallbackQuery", callback_query_id=cbid)

    if d in ("home", "main"):
        await edit(session, cid, mid, "🛠 *פאנל ניהול*", kb_main())

    elif d == "status":
        uptime = str(datetime.now() - stats["start"]).split(".")[0]
        last = stats["last"].strftime("%H:%M:%S %d/%m") if stats["last"] else "אין"
        status = "🟢 פעיל" if bot_active else "🔴 כבוי"
        txt = (f"📊 *סטטוס מערכת*\n\n"
               f"מצב: {status}\n"
               f"התרעות שנשלחו: {stats['total']}\n"
               f"התרעה אחרונה: {last}\n"
               f"ערוצים: {len(channels)}\n"
               f"זמן ריצה: {uptime}")
        await edit(session, cid, mid, txt, kb_back())

    elif d == "log":
        if not alert_log:
            await edit(session, cid, mid, "📋 אין התרעות עדיין.", kb_back())
        else:
            lines = "\n".join([f"• {a['time']} — {a['area']} ({a['type']})" for a in alert_log[-10:]])
            await edit(session, cid, mid, f"📋 *10 התרעות אחרונות:*\n\n{lines}", kb_back())

    elif d == "toggle":
        bot_active = not bot_active
        status = "🟢 הופעל" if bot_active else "🔴 הושהה"
        await broadcast(session, f"{status} הבוט.")
        await edit(session, cid, mid, "🛠 *פאנל ניהול*", kb_main())

    elif d == "test":
        await broadcast(session, "🧪 *בדיקת מערכת*\nהבוט מחובר ופעיל ✅")
        await tg(session, "answerCallbackQuery", callback_query_id=cbid, text="✅ טסט נשלח!")
        await edit(session, cid, mid, "🛠 *פאנל ניהול*", kb_main())

    elif d == "channels":
        lines = "\n".join([f"• {name} (`{cid2}`)" for cid2, name in channels.items()]) or "אין ערוצים"
        await edit(session, cid, mid, f"📢 *ערוצים פעילים:*\n\n{lines}", kb_channels())

    elif d.startswith("rmch_"):
        chid = d[5:]
        if chid in channels:
            channels.pop(chid)
        lines = "\n".join([f"• {name} (`{c}`)" for c, name in channels.items()]) or "אין ערוצים"
        await edit(session, cid, mid, f"📢 *ערוצים פעילים:*\n\n{lines}", kb_channels())

    elif d == "ask_addchannel":
        waiting_for[cid] = "addchannel"
        await edit(session, cid, mid, "שלח: `<channel_id> <שם>`\nלדוגמה: `-1001234567890 ערוץ שני`", kb_back())

    elif d == "links":
        await edit(session, cid, mid, f"🔗 *קישור קבוע:*\n\n{footer}\n\nלשינוי — שלח `/setfooter <טקסט>`", kb_back())

    elif d == "ask_broadcast":
        waiting_for[cid] = "broadcast"
        await edit(session, cid, mid, "✍️ שלח את ההודעה לשידור לכל הערוצים:", kb_back())

    elif d == "ask_schedule":
        waiting_for[cid] = "schedule"
        await edit(session, cid, mid, "⏰ שלח: `HH:MM טקסט ההודעה`\nלדוגמה: `20:00 בדיקת מערכת`", kb_back())

    elif d == "blocks":
        blocked = "\n".join([f"• {a}" for a in sorted(blocked_areas)]) or "אין חסימות"
        filt = f"פילטור פעיל: {area_filter}" if area_filter else "פילטור: כבוי"
        await edit(session, cid, mid, f"🚫 *חסימות:*\n\n{blocked}\n\n{filt}", kb_blocks())

    elif d.startswith("unblock_"):
        blocked_areas.discard(d[8:])
        blocked = "\n".join([f"• {a}" for a in sorted(blocked_areas)]) or "אין חסימות"
        filt = f"פילטור פעיל: {area_filter}" if area_filter else "פילטור: כבוי"
        await edit(session, cid, mid, f"🚫 *חסימות:*\n\n{blocked}\n\n{filt}", kb_blocks())

    elif d == "ask_block":
        waiting_for[cid] = "block"
        await edit(session, cid, mid, "שלח שם האזור לחסימה:", kb_back())

    elif d == "ask_filter":
        waiting_for[cid] = "filter"
        await edit(session, cid, mid, "שלח שם אזור לפילטור, או `off` לביטול:", kb_back())

    elif d == "areastats":
        if not area_stats:
            await edit(session, cid, mid, "📈 אין סטטיסטיקות עדיין.", kb_back())
        else:
            top = sorted(area_stats.items(), key=lambda x: x[1], reverse=True)[:10]
            lines = "\n".join([f"• {a}: {c}" for a, c in top])
            await edit(session, cid, mid, f"📈 *TOP 10 אזורים:*\n\n{lines}", kb_back())

    elif d == "categories":
        lines = "\n".join([f"{'✅' if c in allowed_categories else '❌'} {info['emoji']} {info['title']}" for c, info in CATEGORY_INFO.items()])
        await edit(session, cid, mid, f"🔔 *סוגי התרעות:*\n\n{lines}", kb_categories())

    elif d.startswith("togglecat_"):
        cat_id = int(d[10:])
        if cat_id in allowed_categories:
            allowed_categories.discard(cat_id)
        else:
            allowed_categories.add(cat_id)
        lines = "\n".join([f"{'✅' if c in allowed_categories else '❌'} {info['emoji']} {info['title']}" for c, info in CATEGORY_INFO.items()])
        await edit(session, cid, mid, f"🔔 *סוגי התרעות:*\n\n{lines}", kb_categories())

    elif d == "allcats_on":
        allowed_categories.update(CATEGORY_INFO.keys())
        lines = "\n".join([f"✅ {info['emoji']} {info['title']}" for info in CATEGORY_INFO.values()])
        await edit(session, cid, mid, f"🔔 *סוגי התרעות:*\n\n{lines}", kb_categories())

    elif d == "allcats_off":
        allowed_categories.clear()
        lines = "\n".join([f"❌ {info['emoji']} {info['title']}" for info in CATEGORY_INFO.values()])
        await edit(session, cid, mid, f"🔔 *סוגי התרעות:*\n\n{lines}", kb_categories())

    elif d == "close":
        await tg(session, "deleteMessage", chat_id=cid, message_id=mid)


async def handle_input(session, chat_id, uid, text):
    global area_filter, footer
    if uid != ADMIN_ID:
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
            channels[parts[0]] = " ".join(parts[1:])
            await send(session, chat_id, f"✅ ערוץ נוסף.", kb_main())
        else:
            waiting_for[chat_id] = action
            await send(session, chat_id, "❌ פורמט שגוי. נסה: `-100xxx שם`")

    elif action == "block":
        blocked_areas.add(text.strip())
        await send(session, chat_id, f"🚫 חסום: *{text.strip()}*", kb_main())

    elif action == "filter":
        if text.strip().lower() == "off":
            area_filter = None
            await send(session, chat_id, "✅ פילטור בוטל.", kb_main())
        else:
            area_filter = text.strip()
            await send(session, chat_id, f"✅ פילטור: *{area_filter}*", kb_main())

    elif action == "schedule":
        if len(parts) >= 2:
            try:
                now = datetime.now()
                st = datetime.strptime(parts[0], "%H:%M").replace(year=now.year, month=now.month, day=now.day)
                if st < now:
                    st += timedelta(days=1)
                scheduled.append({"text": " ".join(parts[1:]), "at": st})
                await send(session, chat_id, f"✅ מתוזמן לשעה {parts[0]}.", kb_main())
            except:
                waiting_for[chat_id] = action
                await send(session, chat_id, "❌ פורמט שגוי. נסה: `20:00 טקסט`")
        else:
            waiting_for[chat_id] = action
            await send(session, chat_id, "❌ פורמט שגוי.")


async def alert_loop(session):
    logger.info("Alert loop started")
    while True:
        try:
            if bot_active:
                async with session.get(OREF_URL, headers=OREF_HEADERS, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        raw_text = await r.text(encoding="utf-8-sig")
                        text = raw_text.strip()
                        # בדיקה אם יש תוכן (לפי ה-Content-Length שראינו בבדיקה)
                        if text and len(text) > 2:
                            data = json.loads(text)
                            alert_id = data.get("id", "")
                            category = data.get("cat", 1)
                            areas = data.get("data", [])
                            
                            # בדוק אם ההתרעה הזו כבר נשלחה
                            alert_key = f"{alert_id}"
                            if alert_key and alert_key not in seen_ids:
                                seen_ids.add(alert_key)
                                
                                if category not in allowed_categories:
                                    pass
                                else:
                                    # סנן ערים חסומות ופילטר
                                    filtered = [
                                        a for a in areas
                                        if not any(b in a for b in blocked_areas)
                                        and (not area_filter or area_filter in a)
                                    ]
                                    
                                    if filtered:
                                        msg = build_msg(filtered, category)
                                        await broadcast(session, msg)
                                        now = datetime.now()
                                        stats["total"] += len(filtered)
                                        stats["last"] = now
                                        info = CATEGORY_INFO.get(category, {"title": "אזעקה"})
                                        for area in filtered:
                                            area_stats[area] = area_stats.get(area, 0) + 1
                                            alert_log.append({"time": now.strftime("%H:%M:%S"), "area": area, "type": info["title"]})
                                        if len(alert_log) > 100:
                                            alert_log = alert_log[-100:]
                                        await send(session, ADMIN_ID, f"🔔 *{info['title']}*\n{len(filtered)} יישובים")
                                        logger.info(f"Sent: [{info['title']}] {len(filtered)} areas")
                    elif r.status == 403:
                        logger.error("403 blocked! Check IP or User-Agent.")
            if len(seen_ids) > 1000:
                seen_ids.clear()
        except Exception as e:
            logger.error(f"Alert error: {e}")
        await asyncio.sleep(1)


async def telegram_loop(session):
    global offset
    logger.info("Telegram polling started")
    while True:
        try:
            res = await tg(session, "getUpdates", offset=offset, timeout=10)
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                if "callback_query" in u:
                    asyncio.create_task(handle_callback(session, u["callback_query"]))
                elif "message" in u:
                    m = u["message"]
                    text = m.get("text", "")
                    cid = m["chat"]["id"]
                    uid = m.get("from", {}).get("id")
                    if not text or not uid:
                        continue
                    if text in ("/start", "/menu"):
                        await send(session, cid, "🛠 *פאנל ניהול*", kb_main())
                    elif text.startswith("/setfooter "):
                        if uid == ADMIN_ID:
                            footer = text[11:]
                            await send(session, cid, "✅ קישור עודכן.")
                    elif cid in waiting_for:
                        asyncio.create_task(handle_input(session, cid, uid, text))
        except Exception as e:
            logger.error(f"TG loop error: {e}")
        await asyncio.sleep(1)


async def scheduler_loop(session):
    while True:
        now = datetime.now()
        for item in scheduled[:]:
            if now >= item["at"]:
                await broadcast(session, item["text"])
                scheduled.remove(item)
                await send(session, ADMIN_ID, "✅ הודעה מתוזמנת נשלחה.")
        await asyncio.sleep(10)


async def main():
    logger.info("Bot starting...")
    async with aiohttp.ClientSession() as s:
        await asyncio.gather(
            alert_loop(s),
            telegram_loop(s),
            scheduler_loop(s)
        )

if __name__ == "__main__":
    asyncio.run(main())