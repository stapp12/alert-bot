"""
בוט תכנון תוכן — ניהול עמודים, משימות, תזכורות, משימות קבועות
"""

import json
import logging
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/planner_bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

TOKEN   = os.environ["PLANNER_BOT_TOKEN"]
CHAT_ID = int(os.environ.get("PLANNER_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "0"))
DATA_FILE = Path(__file__).parent / "planner_data.json"

# ── שלבי שיחה ────────────────────────────────────────────────────────────────
(
    S_TASK_TYPE,
    S_TASK_PAGES,
    S_TASK_RECURRENCE,
    S_TASK_DAYS,
    S_TASK_NAME,
    S_TASK_DATE,
    S_TASK_TIME,
    S_TASK_NOTES,
    S_PAGE_NAME,
    S_PAGE_PLATFORM,
    S_SCHED_HOUR,
    S_POST_NOTE,
) = range(12)

TASK_TYPE_EMOJI = {
    "פוסט":  "🖼",
    "ריל":   "🎬",
    "סטורי": "📖",
    "לייב":  "🔴",
    "אחר":   "📌",
}

DAYS_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
# 0=Monday...6=Sunday (Python weekday)
DAY_MAP = {d: i for i, d in enumerate(DAYS_HE)}

PLATFORMS = ["Instagram", "Facebook", "TikTok", "YouTube", "Twitter/X"]

# ── טעינת / שמירת נתונים ────────────────────────────────────────────────────
def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"pages": [], "tasks": [], "recurring_tasks": [], "settings": {}}


def save_data(data: dict):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── יצירת משימות יומיות ממשימות קבועות ──────────────────────────────────────
def create_recurring_tasks_for_today(data: dict):
    today = date.today()
    today_str = today.isoformat()
    weekday = today.weekday()  # 0=Monday

    for tmpl in data.get("recurring_tasks", []):
        if not tmpl.get("active", True):
            continue

        days = tmpl.get("days", [])
        if days and weekday not in days:
            continue  # לא היום

        # בדוק אם כבר נוצרה משימה היום מהתבנית הזאת
        already = any(
            t.get("from_template") == tmpl["id"] and t.get("date") == today_str
            for t in data.get("tasks", [])
        )
        if already:
            continue

        pages = tmpl.get("page_ids", [])
        if pages == ["all"]:
            pages = [p["id"] for p in data.get("pages", [])]

        for pid in pages:
            task = {
                "id": str(uuid4()),
                "type": tmpl.get("type", "אחר"),
                "name": tmpl.get("name", ""),
                "page_id": pid,
                "date": today_str,
                "time": tmpl.get("time", ""),
                "notes": tmpl.get("notes", ""),
                "status": "pending",
                "from_template": tmpl["id"],
                "created_at": datetime.now().isoformat(),
            }
            data.setdefault("tasks", []).append(task)
    save_data(data)


# ── מקלדות ──────────────────────────────────────────────────────────────────
def main_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ משימה חדשה",        callback_data="new_task"),
            InlineKeyboardButton("📋 משימות היום",       callback_data="today_tasks"),
        ],
        [
            InlineKeyboardButton("📅 כל המשימות",        callback_data="all_tasks"),
            InlineKeyboardButton("🔁 משימות קבועות",     callback_data="recurring_list"),
        ],
        [
            InlineKeyboardButton("📱 ניהול עמודים",      callback_data="pages_menu"),
            InlineKeyboardButton("⚙️ הגדרות",            callback_data="settings"),
        ],
    ])


def _day_picker_kb(selected: list[int]):
    buttons = []
    row = []
    for i, day in enumerate(DAYS_HE):
        check = "✅" if i in selected else "☐"
        row.append(InlineKeyboardButton(f"{check} {day}", callback_data=f"day_toggle_{i}"))
        if len(row) == 3 or i == len(DAYS_HE) - 1:
            buttons.append(row)
            row = []
    buttons.append([
        InlineKeyboardButton("✅ אישור",    callback_data="days_done"),
        InlineKeyboardButton("🔙 ביטול",  callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(buttons)


# ── helper ──────────────────────────────────────────────────────────────────
async def reply(update: Update, text: str, kb=None, edit=False):
    kwargs = dict(text=text, parse_mode=ParseMode.HTML, reply_markup=kb)
    if edit and update.callback_query:
        return await update.callback_query.edit_message_text(**kwargs)
    if update.callback_query:
        return await update.callback_query.message.reply_text(**kwargs)
    return await update.message.reply_text(**kwargs)


def page_name(data: dict, pid: str) -> str:
    for p in data.get("pages", []):
        if p["id"] == pid:
            return p.get("name", pid)
    return pid


def format_task(t: dict, data: dict) -> str:
    emoji = TASK_TYPE_EMOJI.get(t.get("type", ""), "📌")
    pname = page_name(data, t.get("page_id", ""))
    status = {"pending": "🕐", "done": "✅", "skipped": "⏭"}.get(t.get("status", ""), "🕐")
    lines = [
        f"{status} {emoji} <b>{t.get('name', '')}</b>",
        f"📱 {pname}  |  📅 {t.get('date', '')}  ⏰ {t.get('time', '')}",
    ]
    if t.get("notes"):
        lines.append(f"📝 {t['notes']}")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    create_recurring_tasks_for_today(data)
    await reply(update, "👋 <b>בוט תכנון תוכן</b>\nמה תרצה לעשות?", main_kb())


# ════════════════════════════════════════════════════════════════════════════
#  יצירת משימה — ConversationHandler
# ════════════════════════════════════════════════════════════════════════════
async def cb_new_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ctx.user_data.clear()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{v} {k}", callback_data=f"ttype_{k}") for k, v in list(TASK_TYPE_EMOJI.items())[:3]],
        [InlineKeyboardButton(f"{v} {k}", callback_data=f"ttype_{k}") for k, v in list(TASK_TYPE_EMOJI.items())[3:]],
        [InlineKeyboardButton("🔙 ביטול", callback_data="cancel")],
    ])
    await reply(update, "📌 <b>סוג המשימה:</b>", kb, edit=True)
    return S_TASK_TYPE


async def cb_task_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ttype = update.callback_query.data.replace("ttype_", "")
    ctx.user_data["type"] = ttype

    data = load_data()
    pages = data.get("pages", [])
    if not pages:
        await reply(update, "⚠️ אין עמודים שמורים. הוסף עמוד תחילה.", main_kb(), edit=True)
        return ConversationHandler.END

    buttons = [[InlineKeyboardButton(f"📱 {p['name']}", callback_data=f"page_{p['id']}")] for p in pages]
    buttons.append([InlineKeyboardButton("🌐 כל העמודים", callback_data="page_all")])
    buttons.append([InlineKeyboardButton("🔙 ביטול", callback_data="cancel")])
    await reply(update, f"{TASK_TYPE_EMOJI[ttype]} <b>בחר עמוד:</b>", InlineKeyboardMarkup(buttons), edit=True)
    return S_TASK_PAGES


async def cb_task_pages(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    page_data = update.callback_query.data.replace("page_", "")
    ctx.user_data["page_id"] = page_data

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔂 חד פעמי", callback_data="rec_once")],
        [InlineKeyboardButton("🔁 יומי", callback_data="rec_daily")],
        [InlineKeyboardButton("📅 ימים ספציפיים", callback_data="rec_weekly")],
        [InlineKeyboardButton("🔙 ביטול", callback_data="cancel")],
    ])
    await reply(update, "🔄 <b>תדירות המשימה:</b>", kb, edit=True)
    return S_TASK_RECURRENCE


async def cb_task_recurrence(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    rec = update.callback_query.data.replace("rec_", "")
    ctx.user_data["recurrence"] = rec

    if rec == "weekly":
        ctx.user_data["selected_days"] = []
        await reply(update, "📅 <b>בחר ימים:</b>", _day_picker_kb([]), edit=True)
        return S_TASK_DAYS

    await reply(update, "✏️ <b>שם המשימה:</b>", edit=True)
    return S_TASK_NAME


async def cb_day_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    day_idx = int(update.callback_query.data.replace("day_toggle_", ""))
    selected = ctx.user_data.get("selected_days", [])
    if day_idx in selected:
        selected.remove(day_idx)
    else:
        selected.append(day_idx)
    ctx.user_data["selected_days"] = selected
    await update.callback_query.edit_message_reply_markup(_day_picker_kb(selected))
    return S_TASK_DAYS


async def cb_days_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not ctx.user_data.get("selected_days"):
        await update.callback_query.answer("⚠️ בחר יום אחד לפחות!", show_alert=True)
        return S_TASK_DAYS
    await reply(update, "✏️ <b>שם המשימה:</b>", edit=True)
    return S_TASK_NAME


async def msg_task_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["name"] = update.message.text.strip()
    rec = ctx.user_data.get("recurrence", "once")

    if rec == "once":
        await update.message.reply_text("📅 <b>תאריך</b> (DD/MM/YYYY או 'היום'):", parse_mode=ParseMode.HTML)
        return S_TASK_DATE

    await update.message.reply_text("⏰ <b>שעה</b> (HH:MM או דלג עם /):", parse_mode=ParseMode.HTML)
    return S_TASK_TIME


async def msg_task_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() in ("היום", "today"):
        ctx.user_data["date"] = date.today().isoformat()
    else:
        try:
            ctx.user_data["date"] = datetime.strptime(txt, "%d/%m/%Y").date().isoformat()
        except ValueError:
            await update.message.reply_text("❌ פורמט שגוי. נסה שוב (DD/MM/YYYY):")
            return S_TASK_DATE
    await update.message.reply_text("⏰ <b>שעה</b> (HH:MM או / לדלג):", parse_mode=ParseMode.HTML)
    return S_TASK_TIME


async def msg_task_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    ctx.user_data["time"] = "" if txt == "/" else txt
    await update.message.reply_text("📝 <b>הערות</b> (או / לדלג):", parse_mode=ParseMode.HTML)
    return S_TASK_NOTES


async def msg_task_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    ctx.user_data["notes"] = "" if txt == "/" else txt
    await _save_task(update, ctx)
    return ConversationHandler.END


async def _save_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    ud = ctx.user_data
    rec = ud.get("recurrence", "once")
    emoji = TASK_TYPE_EMOJI.get(ud.get("type", ""), "📌")

    if rec == "once":
        task = {
            "id": str(uuid4()),
            "type": ud["type"],
            "name": ud["name"],
            "page_id": ud["page_id"],
            "date": ud.get("date", date.today().isoformat()),
            "time": ud.get("time", ""),
            "notes": ud.get("notes", ""),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        data.setdefault("tasks", []).append(task)
        save_data(data)
        await update.message.reply_text(
            f"✅ <b>משימה נשמרה!</b>\n{emoji} {ud['name']}", parse_mode=ParseMode.HTML, reply_markup=main_kb()
        )
    else:
        days = ud.get("selected_days", []) if rec == "weekly" else []
        tmpl = {
            "id": str(uuid4()),
            "type": ud["type"],
            "name": ud["name"],
            "page_ids": [ud["page_id"]],
            "days": days,
            "time": ud.get("time", ""),
            "notes": ud.get("notes", ""),
            "active": True,
            "created_at": datetime.now().isoformat(),
        }
        data.setdefault("recurring_tasks", []).append(tmpl)
        save_data(data)
        freq = "יומי" if rec == "daily" else f"בימי: {', '.join(DAYS_HE[d] for d in days)}"
        await update.message.reply_text(
            f"🔁 <b>משימה קבועה נשמרה!</b>\n{emoji} {ud['name']}\n📅 {freq}",
            parse_mode=ParseMode.HTML, reply_markup=main_kb()
        )


# ════════════════════════════════════════════════════════════════════════════
#  הצגת משימות
# ════════════════════════════════════════════════════════════════════════════
async def cb_today_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = load_data()
    create_recurring_tasks_for_today(data)
    today = date.today().isoformat()
    tasks = [t for t in data.get("tasks", []) if t.get("date") == today]

    if not tasks:
        await reply(update, "📋 אין משימות להיום.", main_kb(), edit=True)
        return

    lines = [f"📋 <b>משימות {today}:</b>\n"]
    buttons = []
    for t in tasks:
        lines.append(format_task(t, data))
        if t.get("status") == "pending":
            name_short = t.get("name", "")[:18]
            buttons.append([
                InlineKeyboardButton(f"✅ {name_short}", callback_data=f"task_done_{t['id']}"),
                InlineKeyboardButton("⏭ דלג",           callback_data=f"task_skip_{t['id']}"),
            ])

    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="main")])
    kb = InlineKeyboardMarkup(buttons)
    await reply(update, "\n\n".join(lines), kb, edit=True)


async def cb_all_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = load_data()
    tasks = data.get("tasks", [])
    if not tasks:
        await reply(update, "📋 אין משימות שמורות.", main_kb(), edit=True)
        return

    pending = [t for t in tasks if t.get("status") == "pending"]
    done = [t for t in tasks if t.get("status") == "done"]

    lines = [f"📋 <b>כל המשימות:</b> {len(pending)} פתוחות, {len(done)} הושלמו\n"]
    for t in (pending + done)[:20]:
        lines.append(format_task(t, data))

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="main")]])
    await reply(update, "\n\n".join(lines), kb, edit=True)


# ════════════════════════════════════════════════════════════════════════════
#  משימות קבועות
# ════════════════════════════════════════════════════════════════════════════
async def cb_recurring_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = load_data()
    templates = data.get("recurring_tasks", [])

    if not templates:
        await reply(update, "🔁 אין משימות קבועות.", main_kb(), edit=True)
        return

    buttons = []
    for t in templates:
        emoji = TASK_TYPE_EMOJI.get(t.get("type", ""), "📌")
        active = "✅" if t.get("active", True) else "⏸"
        buttons.append([InlineKeyboardButton(
            f"{active} {emoji} {t['name']}", callback_data=f"rec_view_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="main")])
    await reply(update, "🔁 <b>משימות קבועות:</b>", InlineKeyboardMarkup(buttons), edit=True)


async def cb_rec_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    tid = update.callback_query.data.replace("rec_view_", "")
    data = load_data()
    tmpl = next((t for t in data.get("recurring_tasks", []) if t["id"] == tid), None)
    if not tmpl:
        await reply(update, "לא נמצא.", main_kb(), edit=True)
        return

    emoji = TASK_TYPE_EMOJI.get(tmpl.get("type", ""), "📌")
    days_str = ", ".join(DAYS_HE[d] for d in tmpl.get("days", [])) or "יומי"
    active = "✅ פעיל" if tmpl.get("active", True) else "⏸ מושהה"
    text = (
        f"{emoji} <b>{tmpl['name']}</b>\n"
        f"📅 {days_str}\n"
        f"⏰ {tmpl.get('time', '—')}\n"
        f"סטטוס: {active}"
    )
    toggle_label = "⏸ השהה" if tmpl.get("active", True) else "▶️ הפעל"
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(toggle_label, callback_data=f"rec_toggle_{tid}"),
            InlineKeyboardButton("🗑 מחק", callback_data=f"rec_del_{tid}"),
        ],
        [InlineKeyboardButton("🔙 חזרה", callback_data="recurring_list")],
    ])
    await reply(update, text, kb, edit=True)


async def cb_task_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("✅ סומן כבוצע!")
    tid = update.callback_query.data.replace("task_done_", "")
    data = load_data()
    for t in data.get("tasks", []):
        if t["id"] == tid:
            t["status"] = "done"
            break
    save_data(data)
    await cb_today_tasks(update, ctx)


async def cb_task_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("⏭ דולג")
    tid = update.callback_query.data.replace("task_skip_", "")
    data = load_data()
    for t in data.get("tasks", []):
        if t["id"] == tid:
            t["status"] = "skipped"
            break
    save_data(data)
    await cb_today_tasks(update, ctx)


async def cb_rec_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    tid = update.callback_query.data.replace("rec_toggle_", "")
    data = load_data()
    for t in data.get("recurring_tasks", []):
        if t["id"] == tid:
            t["active"] = not t.get("active", True)
            break
    save_data(data)
    await cb_rec_view(update, ctx)


async def cb_rec_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    tid = update.callback_query.data.replace("rec_del_", "")
    data = load_data()
    data["recurring_tasks"] = [t for t in data.get("recurring_tasks", []) if t["id"] != tid]
    save_data(data)
    await reply(update, "🗑 המשימה הקבועה נמחקה.", main_kb(), edit=True)


# ════════════════════════════════════════════════════════════════════════════
#  ניהול עמודים
# ════════════════════════════════════════════════════════════════════════════
async def cb_pages_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = load_data()
    pages = data.get("pages", [])
    lines = ["📱 <b>עמודים שמורים:</b>\n"]
    for p in pages:
        lines.append(f"• {p['name']} ({p.get('platform', '')})")

    buttons = [
        [InlineKeyboardButton("➕ הוסף עמוד", callback_data="add_page")],
    ]
    if pages:
        for p in pages:
            buttons.append([InlineKeyboardButton(f"🗑 מחק: {p['name']}", callback_data=f"del_page_{p['id']}")])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="main")])

    await reply(update, "\n".join(lines), InlineKeyboardMarkup(buttons), edit=True)


async def cb_add_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ctx.user_data.clear()
    await reply(update, "📱 <b>שם העמוד</b> (לדוגמה: @boostlyisrael):", edit=True)
    return S_PAGE_NAME


async def msg_page_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["page_name"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(p, callback_data=f"plat_{p}")] for p in PLATFORMS
    ])
    await update.message.reply_text("🌐 <b>פלטפורמה:</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
    return S_PAGE_PLATFORM


async def cb_page_platform(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    platform = update.callback_query.data.replace("plat_", "")
    data = load_data()
    page = {
        "id": str(uuid4()),
        "name": ctx.user_data["page_name"],
        "platform": platform,
        "created_at": datetime.now().isoformat(),
    }
    data.setdefault("pages", []).append(page)
    save_data(data)
    await reply(
        update,
        f"✅ <b>עמוד נשמר!</b>\n📱 {page['name']} ({platform})",
        main_kb(), edit=True,
    )
    return ConversationHandler.END


async def cb_del_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    pid = update.callback_query.data.replace("del_page_", "")
    data = load_data()
    data["pages"] = [p for p in data.get("pages", []) if p["id"] != pid]
    save_data(data)
    await cb_pages_menu(update, ctx)


# ════════════════════════════════════════════════════════════════════════════
#  תזכורות — Job Queue
# ════════════════════════════════════════════════════════════════════════════
async def job_reminders(ctx: ContextTypes.DEFAULT_TYPE):
    """רץ כל דקה — שולח תזכורת לכל משימה שהגיע זמנה."""
    if not CHAT_ID:
        return
    data = load_data()
    today     = date.today().isoformat()
    now_str   = datetime.now().strftime("%H:%M")

    for t in data.get("tasks", []):
        if (
            t.get("date") == today
            and t.get("time") == now_str
            and t.get("status") == "pending"
        ):
            emoji = TASK_TYPE_EMOJI.get(t.get("type", ""), "📌")
            pname = page_name(data, t.get("page_id", ""))
            text  = (
                f"⏰ <b>תזכורת!</b>\n"
                f"{emoji} <b>{t.get('name', '')}</b>\n"
                f"📱 {pname}"
            )
            if t.get("notes"):
                text += f"\n📝 {t['notes']}"

            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ בוצע", callback_data=f"task_done_{t['id']}"),
                InlineKeyboardButton("⏭ דלג",  callback_data=f"task_skip_{t['id']}"),
            ]])
            await ctx.bot.send_message(CHAT_ID, text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def job_morning_summary(ctx: ContextTypes.DEFAULT_TYPE):
    """שולח סיכום בוקר עם כל משימות היום."""
    if not CHAT_ID:
        return
    data = load_data()
    create_recurring_tasks_for_today(data)
    today = date.today().isoformat()
    tasks = [t for t in data.get("tasks", []) if t.get("date") == today and t.get("status") == "pending"]

    if not tasks:
        await ctx.bot.send_message(CHAT_ID, f"📋 <b>בוקר טוב!</b>\nאין משימות פתוחות להיום.", parse_mode=ParseMode.HTML)
        return

    lines = [f"📋 <b>בוקר טוב! משימות להיום ({today}):</b>\n"]
    for t in tasks:
        lines.append(format_task(t, data))

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 פתח רשימה", callback_data="today_tasks")]])
    await ctx.bot.send_message(CHAT_ID, "\n\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=kb)


# ════════════════════════════════════════════════════════════════════════════
#  ניתוב כללי
# ════════════════════════════════════════════════════════════════════════════
async def cb_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await reply(update, "🏠 <b>תפריט ראשי</b>", main_kb(), edit=True)


async def cb_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ctx.user_data.clear()
    await reply(update, "❌ הפעולה בוטלה.", main_kb(), edit=True)
    return ConversationHandler.END


async def cb_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await reply(update, "⚙️ <b>הגדרות</b> (בפיתוח)", main_kb(), edit=True)


# ════════════════════════════════════════════════════════════════════════════
#  הפעלה
# ════════════════════════════════════════════════════════════════════════════
def main():
    Path("logs").mkdir(exist_ok=True)

    app = Application.builder().token(TOKEN).job_queue_enabled(True).build()

    # ConversationHandler — יצירת משימה
    task_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_new_task, pattern="^new_task$")],
        states={
            S_TASK_TYPE:      [CallbackQueryHandler(cb_task_type,       pattern="^ttype_")],
            S_TASK_PAGES:     [CallbackQueryHandler(cb_task_pages,      pattern="^page_")],
            S_TASK_RECURRENCE:[CallbackQueryHandler(cb_task_recurrence, pattern="^rec_(once|daily|weekly)$")],
            S_TASK_DAYS: [
                CallbackQueryHandler(cb_day_toggle, pattern="^day_toggle_"),
                CallbackQueryHandler(cb_days_done,  pattern="^days_done$"),
            ],
            S_TASK_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_task_name)],
            S_TASK_DATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_task_date)],
            S_TASK_TIME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_task_time)],
            S_TASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_task_notes)],
        },
        fallbacks=[CallbackQueryHandler(cb_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

    # ConversationHandler — הוספת עמוד
    page_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_add_page, pattern="^add_page$")],
        states={
            S_PAGE_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_page_name)],
            S_PAGE_PLATFORM: [CallbackQueryHandler(cb_page_platform, pattern="^plat_")],
        },
        fallbacks=[CallbackQueryHandler(cb_cancel, pattern="^cancel$")],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(task_conv)
    app.add_handler(page_conv)

    app.add_handler(CallbackQueryHandler(cb_main,           pattern="^main$"))
    app.add_handler(CallbackQueryHandler(cb_cancel,         pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(cb_today_tasks,    pattern="^today_tasks$"))
    app.add_handler(CallbackQueryHandler(cb_all_tasks,      pattern="^all_tasks$"))
    app.add_handler(CallbackQueryHandler(cb_recurring_list, pattern="^recurring_list$"))
    app.add_handler(CallbackQueryHandler(cb_rec_view,       pattern="^rec_view_"))
    app.add_handler(CallbackQueryHandler(cb_rec_toggle,     pattern="^rec_toggle_"))
    app.add_handler(CallbackQueryHandler(cb_rec_del,        pattern="^rec_del_"))
    app.add_handler(CallbackQueryHandler(cb_pages_menu,     pattern="^pages_menu$"))
    app.add_handler(CallbackQueryHandler(cb_del_page,       pattern="^del_page_"))
    app.add_handler(CallbackQueryHandler(cb_settings,       pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(cb_task_done,      pattern="^task_done_"))
    app.add_handler(CallbackQueryHandler(cb_task_skip,      pattern="^task_skip_"))

    # ── Jobs ──────────────────────────────────────────────────────────────────
    # בדיקת תזכורות כל דקה
    app.job_queue.run_repeating(job_reminders, interval=60, first=10)
    # סיכום בוקר ב-08:00 בכל יום
    from datetime import time as dtime
    app.job_queue.run_daily(job_morning_summary, time=dtime(hour=8, minute=0))

    logger.info("Planner bot started (reminders active, CHAT_ID=%s)", CHAT_ID)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
