"""
מנהל מודעות — בוט Telegram מלא
תפריטים: קמפיינים | קבוצות מודעות | מודעות | עריכת וידאו | סטטיסטיקות
"""

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from meta_api import MetaAPI, OBJECTIVES, STATUS_EMOJI

load_dotenv()

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("BOT_MANAGER_TOKEN") or os.environ["TELEGRAM_TOKEN"]
PROJECT_DIR    = Path(__file__).parent
OUT_DIR        = PROJECT_DIR / "out"
OUT_DIR.mkdir(exist_ok=True)

# ── שלבי שיחה ─────────────────────────────────────────────────────────────────
(
    S_CAMP_NEW_NAME, S_CAMP_NEW_OBJ, S_CAMP_NEW_BUDGET,
    S_ADSET_NEW_NAME, S_ADSET_NEW_BUDGET,
    S_AD_WAIT_VIDEO, S_AD_WAIT_TEXT,
    S_VID_WAIT_TEXT,
) = range(8)


# ── עזר: שלח/ערוך הודעה ───────────────────────────────────────────────────────
async def _reply(update: Update, text: str, kb=None, edit=False):
    kwargs = dict(text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    if edit and update.callback_query:
        return await update.callback_query.edit_message_text(**kwargs)
    if update.callback_query:
        return await update.callback_query.message.reply_text(**kwargs)
    return await update.message.reply_text(**kwargs)


def _back(label="🔙 חזרה"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="main")]])


# ══════════════════════════════════════════════════════════════════════════════
#  תפריט ראשי
# ══════════════════════════════════════════════════════════════════════════════

MAIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("📢 קמפיינים",          callback_data="camps"),
     InlineKeyboardButton("🗂 קבוצות מודעות",     callback_data="adsets")],
    [InlineKeyboardButton("📣 מודעות",             callback_data="ads"),
     InlineKeyboardButton("🎬 עריכת וידאו",        callback_data="video_editor")],
    [InlineKeyboardButton("📊 סטטיסטיקות",         callback_data="stats"),
     InlineKeyboardButton("⚙️ הגדרות",             callback_data="settings")],
])


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _reply(update,
        "👋 *ברוך הבא למנהל המודעות!*\n\nבחר קטגוריה:",
        MAIN_KB)


async def cb_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "בחר קטגוריה:", parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB
    )
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  📢 קמפיינים
# ══════════════════════════════════════════════════════════════════════════════

async def cb_camps(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 רשימת קמפיינים",   callback_data="camps_list")],
        [InlineKeyboardButton("➕ קמפיין חדש",        callback_data="camps_new")],
        [InlineKeyboardButton("🔙 חזרה",              callback_data="main")],
    ])
    await update.callback_query.edit_message_text("📢 *ניהול קמפיינים*\nבחר פעולה:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def cb_camps_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        api = MetaAPI()
        camps = api.get_campaigns()
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ שגיאה: `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=_back())
        return

    if not camps:
        await update.callback_query.edit_message_text("אין קמפיינים בחשבון עדיין.", reply_markup=_back("🔙 קמפיינים"))
        return

    ctx.user_data["camps"] = {c.id: c for c in camps}
    buttons = []
    for c in camps:
        emoji = STATUS_EMOJI.get(c.status, "⚪")
        budget = int(c.daily_budget) / 100 if c.daily_budget else 0
        buttons.append([InlineKeyboardButton(
            f"{emoji} {c.name}  |  ₪{budget:.0f}/יום",
            callback_data=f"camp_view_{c.id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="camps")])
    await update.callback_query.edit_message_text(
        f"📋 *קמפיינים ({len(camps)})*:", parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cb_camp_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    camp_id = update.callback_query.data.split("_", 2)[2]
    camps   = ctx.user_data.get("camps", {})
    c       = camps.get(camp_id)

    if not c:
        await update.callback_query.answer("לא נמצא, רענן את הרשימה", show_alert=True)
        return

    emoji  = STATUS_EMOJI.get(c.status, "⚪")
    budget = int(c.daily_budget) / 100 if c.daily_budget else 0

    # כפתורי פעולה על הקמפיין
    toggle_label = "⏸ השהה" if c.status == "ACTIVE" else "▶️ הפעל"
    toggle_cb    = f"camp_pause_{camp_id}" if c.status == "ACTIVE" else f"camp_activate_{camp_id}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label,            callback_data=toggle_cb),
         InlineKeyboardButton("🗑 מחק",               callback_data=f"camp_del_{camp_id}")],
        [InlineKeyboardButton("🗂 קבוצות מודעות",     callback_data=f"adsets_camp_{camp_id}")],
        [InlineKeyboardButton("🔙 רשימת קמפיינים",   callback_data="camps_list")],
    ])
    await update.callback_query.edit_message_text(
        f"{emoji} *{c.name}*\n"
        f"סטטוס: `{c.status}`\n"
        f"תקציב יומי: ₪{budget:.2f}\n"
        f"יעד: `{c.objective}`",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )


async def cb_camp_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    parts     = update.callback_query.data.split("_")   # camp_pause_ID or camp_activate_ID
    action    = parts[1]   # pause / activate
    camp_id   = parts[2]
    activate  = action == "activate"
    try:
        MetaAPI().toggle_campaign(camp_id, activate)
        # עדכן cache
        if camp_id in ctx.user_data.get("camps", {}):
            ctx.user_data["camps"][camp_id].status = "ACTIVE" if activate else "PAUSED"
        await update.callback_query.answer("✅ הסטטוס עודכן")
    except Exception as e:
        await update.callback_query.answer(f"❌ {e}", show_alert=True)
    await cb_camp_view(update, ctx)


async def cb_camp_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    camp_id = update.callback_query.data.split("_", 2)[2]
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ כן, מחק",  callback_data=f"camp_del_confirm_{camp_id}"),
        InlineKeyboardButton("❌ ביטול",    callback_data=f"camp_view_{camp_id}"),
    ]])
    await update.callback_query.edit_message_text(
        "⚠️ *אישור מחיקה*\nהקמפיין ימחק לצמיתות. להמשיך?",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )


async def cb_camp_del_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    camp_id = update.callback_query.data.split("_", 3)[3]
    try:
        MetaAPI().delete_campaign(camp_id)
        ctx.user_data.get("camps", {}).pop(camp_id, None)
        await update.callback_query.edit_message_text("✅ הקמפיין נמחק.", reply_markup=_back("📋 רשימת קמפיינים"))
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=_back())


# ── יצירת קמפיין חדש (שיחה) ──────────────────────────────────────────────────

async def cb_camps_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("✏️ *קמפיין חדש*\n\nשלח את *שם הקמפיין*:", parse_mode=ParseMode.MARKDOWN)
    return S_CAMP_NEW_NAME


async def camp_got_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_camp_name"] = update.message.text.strip()
    buttons = [[InlineKeyboardButton(k, callback_data=f"camp_obj_{k}")] for k in OBJECTIVES]
    await update.message.reply_text(
        "🎯 בחר את *יעד הקמפיין*:", parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return S_CAMP_NEW_OBJ


async def camp_got_obj(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ctx.user_data["new_camp_obj"] = update.callback_query.data.replace("camp_obj_", "")
    await update.callback_query.edit_message_text("💰 הזן *תקציב יומי* בשקלים (לדוג׳: 50):", parse_mode=ParseMode.MARKDOWN)
    return S_CAMP_NEW_BUDGET


async def camp_got_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        budget = float(update.message.text.strip().replace("₪", ""))
    except ValueError:
        await update.message.reply_text("❌ יש להזין מספר בלבד (לדוג׳: 50)")
        return S_CAMP_NEW_BUDGET

    name = ctx.user_data.pop("new_camp_name")
    obj  = ctx.user_data.pop("new_camp_obj")
    try:
        api  = MetaAPI()
        camp = api.create_campaign(name, obj, budget)
        if "camps" not in ctx.user_data:
            ctx.user_data["camps"] = {}
        ctx.user_data["camps"][camp.id] = camp
        await update.message.reply_text(
            f"✅ *הקמפיין נוצר!*\n\nשם: {camp.name}\nמזהה: `{camp.id}`\nסטטוס: ⏸ מושהה",
            parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB
        )
    except Exception as e:
        await update.message.reply_text(f"❌ שגיאה: `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB)
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  🗂 קבוצות מודעות
# ══════════════════════════════════════════════════════════════════════════════

async def cb_adsets(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 כל קבוצות המודעות",  callback_data="adsets_list_all")],
        [InlineKeyboardButton("➕ קבוצה חדשה",          callback_data="adsets_pick_camp")],
        [InlineKeyboardButton("🔙 חזרה",               callback_data="main")],
    ])
    await update.callback_query.edit_message_text("🗂 *ניהול קבוצות מודעות*\nבחר פעולה:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_adsets(update: Update, ctx: ContextTypes.DEFAULT_TYPE, campaign_id=None):
    try:
        api    = MetaAPI()
        adsets = api.get_ad_sets(campaign_id)
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=_back())
        return

    if not adsets:
        await update.callback_query.edit_message_text("אין קבוצות מודעות.", reply_markup=_back())
        return

    ctx.user_data["adsets"] = {a.id: a for a in adsets}
    buttons = []
    for a in adsets:
        emoji  = STATUS_EMOJI.get(a.status, "⚪")
        budget = int(a.daily_budget) / 100 if a.daily_budget else 0
        buttons.append([InlineKeyboardButton(f"{emoji} {a.name}  |  ₪{budget:.0f}/יום", callback_data=f"adset_view_{a.id}")])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="adsets")])
    await update.callback_query.edit_message_text(
        f"📋 *קבוצות מודעות ({len(adsets)})*:", parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cb_adsets_list_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await _show_adsets(update, ctx)


async def cb_adsets_camp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """רשימת ad sets לפי קמפיין ספציפי"""
    await update.callback_query.answer()
    camp_id = update.callback_query.data.split("_", 2)[2]
    await _show_adsets(update, ctx, campaign_id=camp_id)


async def cb_adset_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    adset_id = update.callback_query.data.split("_", 2)[2]
    adsets   = ctx.user_data.get("adsets", {})
    a        = adsets.get(adset_id)
    if not a:
        await update.callback_query.answer("לא נמצא", show_alert=True)
        return

    emoji  = STATUS_EMOJI.get(a.status, "⚪")
    budget = int(a.daily_budget) / 100 if a.daily_budget else 0

    toggle_label = "⏸ השהה" if a.status == "ACTIVE" else "▶️ הפעל"
    toggle_cb    = f"adset_pause_{adset_id}" if a.status == "ACTIVE" else f"adset_activate_{adset_id}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label,          callback_data=toggle_cb)],
        [InlineKeyboardButton("📣 מודעות בקבוצה",   callback_data=f"ads_adset_{adset_id}")],
        [InlineKeyboardButton("🔙 רשימת קבוצות",    callback_data="adsets_list_all")],
    ])
    await update.callback_query.edit_message_text(
        f"{emoji} *{a.name}*\nסטטוס: `{a.status}`\nתקציב: ₪{budget:.2f}/יום",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )


async def cb_adset_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    parts    = update.callback_query.data.split("_")
    action   = parts[1]
    adset_id = parts[2]
    activate = action == "activate"
    try:
        MetaAPI().toggle_ad_set(adset_id, activate)
        if adset_id in ctx.user_data.get("adsets", {}):
            ctx.user_data["adsets"][adset_id].status = "ACTIVE" if activate else "PAUSED"
        await update.callback_query.answer("✅ עודכן")
    except Exception as e:
        await update.callback_query.answer(f"❌ {e}", show_alert=True)
    await cb_adset_view(update, ctx)


# ── יצירת קבוצה חדשה ─────────────────────────────────────────────────────────

async def cb_adsets_pick_camp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """בחירת קמפיין לפני יצירת ad set חדש"""
    await update.callback_query.answer()
    try:
        camps = MetaAPI().get_campaigns()
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=_back())
        return
    if not camps:
        await update.callback_query.edit_message_text("אין קמפיינים — צור קמפיין קודם.", reply_markup=_back())
        return
    buttons = [[InlineKeyboardButton(c.name, callback_data=f"adset_new_{c.id}")] for c in camps]
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="adsets")])
    await update.callback_query.edit_message_text("בחר קמפיין לקבוצה החדשה:", reply_markup=InlineKeyboardMarkup(buttons))


async def cb_adset_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    camp_id = update.callback_query.data.split("_", 2)[2]
    ctx.user_data["new_adset_camp"] = camp_id
    await update.callback_query.edit_message_text("✏️ שלח את *שם קבוצת המודעות*:", parse_mode=ParseMode.MARKDOWN)
    return S_ADSET_NEW_NAME


async def adset_got_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_adset_name"] = update.message.text.strip()
    await update.message.reply_text("💰 הזן *תקציב יומי* בשקלים:", parse_mode=ParseMode.MARKDOWN)
    return S_ADSET_NEW_BUDGET


async def adset_got_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        budget = float(update.message.text.strip().replace("₪", ""))
    except ValueError:
        await update.message.reply_text("❌ מספר בלבד (לדוג׳: 30)")
        return S_ADSET_NEW_BUDGET

    name     = ctx.user_data.pop("new_adset_name")
    camp_id  = ctx.user_data.pop("new_adset_camp")
    try:
        adset = MetaAPI().create_ad_set(camp_id, name, budget)
        await update.message.reply_text(
            f"✅ *הקבוצה נוצרה!*\n\nשם: {adset.name}\nמזהה: `{adset.id}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB
        )
    except Exception as e:
        await update.message.reply_text(f"❌ `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB)
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  📣 מודעות
# ══════════════════════════════════════════════════════════════════════════════

async def cb_ads(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 כל המודעות",            callback_data="ads_list_all")],
        [InlineKeyboardButton("⬆️ העלאת וידאו מוכן",      callback_data="ads_upload_start")],
        [InlineKeyboardButton("🔙 חזרה",                   callback_data="main")],
    ])
    await update.callback_query.edit_message_text("📣 *ניהול מודעות*\nבחר פעולה:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_ads(update: Update, ctx: ContextTypes.DEFAULT_TYPE, adset_id=None):
    try:
        ads = MetaAPI().get_ads(adset_id)
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=_back())
        return
    if not ads:
        await update.callback_query.edit_message_text("אין מודעות.", reply_markup=_back())
        return
    ctx.user_data["ads"] = {a.id: a for a in ads}
    buttons = []
    for a in ads:
        emoji = STATUS_EMOJI.get(a.status, "⚪")
        buttons.append([InlineKeyboardButton(f"{emoji} {a.name}", callback_data=f"ad_view_{a.id}")])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="ads")])
    await update.callback_query.edit_message_text(
        f"📋 *מודעות ({len(ads)})*:", parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cb_ads_list_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await _show_ads(update, ctx)


async def cb_ads_adset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    adset_id = update.callback_query.data.split("_", 2)[2]
    await _show_ads(update, ctx, adset_id=adset_id)


async def cb_ad_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ad_id = update.callback_query.data.split("_", 2)[2]
    ads   = ctx.user_data.get("ads", {})
    a     = ads.get(ad_id)
    if not a:
        await update.callback_query.answer("לא נמצא", show_alert=True)
        return
    emoji        = STATUS_EMOJI.get(a.status, "⚪")
    toggle_label = "⏸ השהה" if a.status == "ACTIVE" else "▶️ הפעל"
    toggle_cb    = f"ad_pause_{ad_id}" if a.status == "ACTIVE" else f"ad_activate_{ad_id}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=toggle_cb)],
        [InlineKeyboardButton("🔙 רשימת מודעות", callback_data="ads_list_all")],
    ])
    await update.callback_query.edit_message_text(
        f"{emoji} *{a.name}*\nסטטוס: `{a.status}`\nAd Set: `{a.adset_id}`",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )


async def cb_ad_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    parts    = update.callback_query.data.split("_")
    action   = parts[1]
    ad_id    = parts[2]
    activate = action == "activate"
    try:
        MetaAPI().toggle_ad(ad_id, activate)
        if ad_id in ctx.user_data.get("ads", {}):
            ctx.user_data["ads"][ad_id].status = "ACTIVE" if activate else "PAUSED"
        await update.callback_query.answer("✅ עודכן")
    except Exception as e:
        await update.callback_query.answer(f"❌ {e}", show_alert=True)
    await cb_ad_view(update, ctx)


# ── העלאת וידאו מוכן ─────────────────────────────────────────────────────────

async def cb_ads_upload_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📤 *העלאת וידאו מוכן*\n\nשלח לי את קובץ הוידאו (MP4):",
        parse_mode=ParseMode.MARKDOWN
    )
    return S_AD_WAIT_VIDEO


async def ad_got_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # קבלת הקובץ מטלגרם (וידאו או מסמך)
    file_obj = update.message.video or update.message.document
    if not file_obj:
        await update.message.reply_text("❌ יש לשלוח קובץ וידאו (MP4).")
        return S_AD_WAIT_VIDEO

    await update.message.reply_text("⬇️ מוריד את הקובץ...")
    tg_file = await file_obj.get_file()
    tmp     = PROJECT_DIR / "out" / f"upload_{update.message.message_id}.mp4"
    await tg_file.download_to_drive(str(tmp))
    ctx.user_data["upload_video_path"] = str(tmp)

    await update.message.reply_text(
        "✅ הקובץ התקבל!\n\n✏️ עכשיו שלח את *טקסט המודעה*:",
        parse_mode=ParseMode.MARKDOWN
    )
    return S_AD_WAIT_TEXT


async def ad_got_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["upload_ad_text"] = update.message.text.strip()

    # בחירת Ad Set לפרסום
    try:
        adsets = MetaAPI().get_ad_sets()
    except Exception as e:
        await update.message.reply_text(f"❌ `{e}`", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if not adsets:
        await update.message.reply_text("❌ אין קבוצות מודעות. צור קבוצה קודם.", reply_markup=MAIN_KB)
        return ConversationHandler.END

    buttons = [[InlineKeyboardButton(a.name, callback_data=f"ad_publish_{a.id}")] for a in adsets]
    buttons.append([InlineKeyboardButton("❌ ביטול", callback_data="main")])
    await update.message.reply_text(
        "🗂 בחר *קבוצת מודעות* לפרסום:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ConversationHandler.END


async def cb_ad_publish(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    adset_id   = update.callback_query.data.split("_", 2)[2]
    video_path = ctx.user_data.pop("upload_video_path", None)
    ad_text    = ctx.user_data.pop("upload_ad_text", "")

    if not video_path:
        await update.callback_query.edit_message_text("❌ לא נמצא קובץ וידאו. התחל מחדש.")
        return

    msg = await update.callback_query.edit_message_text("⏳ *שלב 1/3 — מעלה וידאו ל-Meta...*", parse_mode=ParseMode.MARKDOWN)

    try:
        api      = MetaAPI()
        video_id = api.upload_video(video_path)

        await msg.edit_text("⏳ *שלב 2/3 — ממתין לעיבוד הוידאו...*", parse_mode=ParseMode.MARKDOWN)
        api.wait_for_video_ready(video_id)

        await msg.edit_text("⏳ *שלב 3/3 — יוצר מודעה...*", parse_mode=ParseMode.MARKDOWN)
        creative_id = api.create_ad_creative(video_id, ad_text)
        ad_id       = api.create_ad(adset_id, creative_id, name=ad_text[:40])

        await msg.edit_text(
            f"🎉 *המודעה נוצרה בהצלחה!*\n\n"
            f"🆔 Ad ID: `{ad_id}`\n"
            f"🎨 Creative ID: `{creative_id}`\n"
            f"📹 Video ID: `{video_id}`\n\n"
            "המודעה במצב ⏸ מושהה — הפעל אותה מרשימת המודעות.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB
        )
    except Exception as e:
        await msg.edit_text(f"❌ שגיאה: `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB)
    finally:
        # ניקוי קובץ זמני
        try:
            Path(video_path).unlink(missing_ok=True)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  🎬 עריכת וידאו (Remotion)
# ══════════════════════════════════════════════════════════════════════════════

async def cb_video_editor(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 רנדר מודעה עם טקסט חדש", callback_data="vid_render_start")],
        [InlineKeyboardButton("🔙 חזרה",                    callback_data="main")],
    ])
    await update.callback_query.edit_message_text(
        "🎬 *עריכת וידאו — Remotion*\n\nבחר פעולה:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )


async def cb_vid_render_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "✏️ שלח את *הטקסט שיופיע בוידאו* (עברית מומלצת):", parse_mode=ParseMode.MARKDOWN
    )
    return S_VID_WAIT_TEXT


async def vid_got_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ad_text  = update.message.text.strip()
    ctx.user_data["vid_text"] = ad_text
    props    = json.dumps({"text": ad_text})
    out_path = OUT_DIR / "video.mp4"

    msg = await update.message.reply_text("⏳ *מרנדר וידאו...* (כ-30 שניות)", parse_mode=ParseMode.MARKDOWN)

    proc = await asyncio.create_subprocess_exec(
        "npx", "remotion", "render", "src/index.ts", "Ad",
        str(out_path), "--props", props,
        cwd=str(PROJECT_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")[-500:]
        await msg.edit_text(f"❌ שגיאת רנדור:\n`{err}`", parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB)
        return ConversationHandler.END

    await msg.edit_text("✅ *הרנדור הושלם!*\nשולח תצוגה מקדימה...", parse_mode=ParseMode.MARKDOWN)

    with open(out_path, "rb") as f:
        await update.message.reply_video(
            video=f,
            caption=f"🎬 תצוגה מקדימה\n\n_{ad_text}_",
            parse_mode=ParseMode.MARKDOWN,
        )

    # בחירת ad set לפרסום
    try:
        adsets = MetaAPI().get_ad_sets()
    except Exception:
        adsets = []

    if adsets:
        buttons = [[InlineKeyboardButton(a.name, callback_data=f"vid_pub_{a.id}")] for a in adsets]
        buttons.append([InlineKeyboardButton("💾 שמור בלבד (אל תפרסם)", callback_data="main")])
        await update.message.reply_text(
            "📤 לפרסם ל-Meta? בחר קבוצת מודעות:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await update.message.reply_text("✅ הוידאו שמור ב-`out/video.mp4`.", parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB)

    return ConversationHandler.END


async def cb_vid_pub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """פרסום הוידאו המרונדר ל-Meta"""
    await update.callback_query.answer()
    adset_id = update.callback_query.data.split("_", 2)[2]
    ad_text  = ctx.user_data.get("vid_text", "מודעת וידאו")
    ctx.user_data["upload_video_path"] = str(OUT_DIR / "video.mp4")
    ctx.user_data["upload_ad_text"]    = ad_text
    # שימוש חוזר בפונקציית הפרסום
    update.callback_query.data = f"ad_publish_{adset_id}"
    await cb_ad_publish(update, ctx)


# ══════════════════════════════════════════════════════════════════════════════
#  📊 סטטיסטיקות
# ══════════════════════════════════════════════════════════════════════════════

async def cb_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 7 ימים אחרונים",   callback_data="stats_7"),
         InlineKeyboardButton("📅 30 ימים אחרונים",  callback_data="stats_30")],
        [InlineKeyboardButton("🔙 חזרה",              callback_data="main")],
    ])
    await update.callback_query.edit_message_text("📊 *סטטיסטיקות*\nבחר טווח:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def cb_stats_range(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    days = 7 if update.callback_query.data == "stats_7" else 30
    await update.callback_query.edit_message_text(f"⏳ טוען נתונים ({days} ימים)...", parse_mode=ParseMode.MARKDOWN)
    try:
        data = MetaAPI().get_account_insights(days)
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=_back())
        return
    if not data:
        await update.callback_query.edit_message_text("אין נתונים לתקופה זו.", reply_markup=_back())
        return

    ctr = float(data.get("ctr", 0))
    cpc = float(data.get("cpc", 0))
    await update.callback_query.edit_message_text(
        f"📊 *סטטיסטיקות — {days} ימים*\n\n"
        f"💰 הוצאה:      `₪{float(data['spend']):.2f}`\n"
        f"👁 חשיפות:     `{int(data['impressions']):,}`\n"
        f"🖱 קליקים:     `{int(data['clicks']):,}`\n"
        f"📈 CTR:        `{ctr:.2f}%`\n"
        f"💵 CPC:        `₪{cpc:.2f}`\n"
        f"🎯 הגעה:       `{int(data['reach']):,}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_back("🔙 סטטיסטיקות")
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ⚙️ הגדרות
# ══════════════════════════════════════════════════════════════════════════════

async def cb_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ad_account = os.environ.get("AD_ACCOUNT_ID", "לא הוגדר")
    page_id    = os.environ.get("PAGE_ID", "לא הוגדר")
    await update.callback_query.edit_message_text(
        "⚙️ *הגדרות מערכת*\n\n"
        f"🆔 AD\\_ACCOUNT\\_ID: `{ad_account}`\n"
        f"📄 PAGE\\_ID: `{page_id}`\n\n"
        "לשינוי הגדרות — ערוך את קובץ `.env` בשרת והפעל מחדש.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_back()
    )


# ══════════════════════════════════════════════════════════════════════════════
#  הפעלת הבוט
# ══════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # שיחות עם קלט טקסט/קובץ
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_camps_new,          pattern="^camps_new$"),
            CallbackQueryHandler(cb_adset_new,          pattern="^adset_new_"),
            CallbackQueryHandler(cb_ads_upload_start,   pattern="^ads_upload_start$"),
            CallbackQueryHandler(cb_vid_render_start,   pattern="^vid_render_start$"),
        ],
        states={
            S_CAMP_NEW_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, camp_got_name)],
            S_CAMP_NEW_OBJ:    [CallbackQueryHandler(camp_got_obj, pattern="^camp_obj_")],
            S_CAMP_NEW_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, camp_got_budget)],
            S_ADSET_NEW_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, adset_got_name)],
            S_ADSET_NEW_BUDGET:[MessageHandler(filters.TEXT & ~filters.COMMAND, adset_got_budget)],
            S_AD_WAIT_VIDEO:   [MessageHandler(filters.VIDEO | filters.Document.VIDEO, ad_got_video)],
            S_AD_WAIT_TEXT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ad_got_text)],
            S_VID_WAIT_TEXT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, vid_got_text)],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        per_message=False,
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(conv)

    # ניווט ראשי
    app.add_handler(CallbackQueryHandler(cb_main,              pattern="^main$"))
    app.add_handler(CallbackQueryHandler(cb_camps,             pattern="^camps$"))
    app.add_handler(CallbackQueryHandler(cb_camps_list,        pattern="^camps_list$"))
    app.add_handler(CallbackQueryHandler(cb_camp_view,         pattern="^camp_view_"))
    app.add_handler(CallbackQueryHandler(cb_camp_toggle,       pattern="^camp_(pause|activate)_"))
    app.add_handler(CallbackQueryHandler(cb_camp_del,          pattern="^camp_del_(?!confirm)"))
    app.add_handler(CallbackQueryHandler(cb_camp_del_confirm,  pattern="^camp_del_confirm_"))
    app.add_handler(CallbackQueryHandler(cb_adsets,            pattern="^adsets$"))
    app.add_handler(CallbackQueryHandler(cb_adsets_list_all,   pattern="^adsets_list_all$"))
    app.add_handler(CallbackQueryHandler(cb_adsets_camp,       pattern="^adsets_camp_"))
    app.add_handler(CallbackQueryHandler(cb_adsets_pick_camp,  pattern="^adsets_pick_camp$"))
    app.add_handler(CallbackQueryHandler(cb_adset_view,        pattern="^adset_view_"))
    app.add_handler(CallbackQueryHandler(cb_adset_toggle,      pattern="^adset_(pause|activate)_"))
    app.add_handler(CallbackQueryHandler(cb_ads,               pattern="^ads$"))
    app.add_handler(CallbackQueryHandler(cb_ads_list_all,      pattern="^ads_list_all$"))
    app.add_handler(CallbackQueryHandler(cb_ads_adset,         pattern="^ads_adset_"))
    app.add_handler(CallbackQueryHandler(cb_ad_view,           pattern="^ad_view_"))
    app.add_handler(CallbackQueryHandler(cb_ad_toggle,         pattern="^ad_(pause|activate)_"))
    app.add_handler(CallbackQueryHandler(cb_ad_publish,        pattern="^ad_publish_"))
    app.add_handler(CallbackQueryHandler(cb_video_editor,      pattern="^video_editor$"))
    app.add_handler(CallbackQueryHandler(cb_vid_pub,           pattern="^vid_pub_"))
    app.add_handler(CallbackQueryHandler(cb_stats,             pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(cb_stats_range,       pattern="^stats_(7|30)$"))
    app.add_handler(CallbackQueryHandler(cb_settings,          pattern="^settings$"))

    logger.info("🚀 הבוט פועל")
    app.run_polling()


if __name__ == "__main__":
    main()
