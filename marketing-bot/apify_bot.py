"""
בוט אינסטגרם — ממשק כפתורים מלא
• תפריטים ויזואליים במקום פקודות
• גילוי חשבונות דומים אוטומטי לפי האשטאגים
• סריקה יומית אוטומטית
"""

import asyncio
import json
import logging
import os
import textwrap
from collections import Counter
from datetime import datetime, time, timezone
from pathlib import Path

from aiohttp import web
from apify_client import ApifyClientAsync
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters,
)

load_dotenv()

# ── הגדרות ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
APIFY_API_TOKEN  = os.environ["APIFY_API_TOKEN"]
APIFY_ACTOR_ID   = os.getenv("APIFY_ACTOR_ID", "shu8hvrXbJbY3Eb9W")
DAILY_RUN_HOUR   = int(os.getenv("DAILY_RUN_HOUR", "6"))
DAILY_RUN_MINUTE = int(os.getenv("DAILY_RUN_MINUTE", "0"))
WEBHOOK_PORT     = int(os.getenv("WEBHOOK_PORT", "8080"))

PROJECT_DIR  = Path(__file__).parent
HISTORY_FILE = PROJECT_DIR / "seen_posts.json"
CONFIG_FILE  = PROJECT_DIR / "instagram_config.json"

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

pending: dict[str, dict] = {}   # shortcode → item (לכפתורי שמירה)

# שלבי שיחה
WAITING_ADD_ACCOUNT = 1
WAITING_LIKES_THRESHOLD = 2
WAITING_DISCOVER_BASE = 3


# ══════════════════════════════════════════════════════════════════════════════
#  Config — אחסון מתמיד
# ══════════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    defaults = {
        "accounts":         [],
        "min_likes":        0,
        "posts_per_user":   12,
        "suggested":        [],   # חשבונות מוצעים שמחכים לאישור
    }
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {**defaults, **data}
        except Exception:
            pass
    return defaults


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#  היסטוריה
# ══════════════════════════════════════════════════════════════════════════════

def load_seen() -> set[str]:
    if HISTORY_FILE.exists():
        try:
            return set(json.loads(HISTORY_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def save_seen(seen: set[str]):
    HISTORY_FILE.write_text(json.dumps(list(seen)[-5000:]), encoding="utf-8")


def post_uid(item: dict) -> str:
    return (item.get("shortCode") or item.get("id") or item.get("postId")
            or item.get("url") or str(item)[:80])


# ══════════════════════════════════════════════════════════════════════════════
#  עיצוב פוסט
# ══════════════════════════════════════════════════════════════════════════════

def _num(n) -> str:
    try:
        n = int(n)
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000:     return f"{n/1_000:.1f}K"
        return str(n)
    except Exception:
        return str(n) if n else "0"


def _ts(raw) -> str:
    if not raw: return ""
    try:
        if isinstance(raw, (int, float)):
            dt = datetime.fromtimestamp(raw / 1000 if raw > 1e10 else raw, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(raw)


def get_likes(item: dict) -> int:
    try:
        return int(item.get("likesCount") or item.get("likes") or 0)
    except Exception:
        return 0


def format_post(item: dict, index: int) -> tuple[str, list[str]]:
    caption   = (item.get("caption") or item.get("text") or "").strip()
    author    = (item.get("ownerUsername") or item.get("username") or "")
    url       = item.get("url") or item.get("postUrl") or ""
    timestamp = _ts(item.get("timestamp") or item.get("takenAt"))
    likes     = get_likes(item)
    comments  = item.get("commentsCount") or item.get("comments") or 0
    views     = item.get("videoViewCount") or item.get("views") or 0
    post_type = item.get("type") or ""

    images: list[str] = []
    for key in ("displayUrl", "imageUrl", "thumbnailUrl"):
        val = item.get(key)
        if isinstance(val, str) and val.startswith("http"):
            images.append(val); break
    for key in ("images", "mediaUrls"):
        for v in (item.get(key) or []):
            src = v if isinstance(v, str) else v.get("url", "")
            if src.startswith("http") and src not in images:
                images.append(src)

    type_emoji = {"Video": "🎥", "Reel": "🎬", "Image": "🖼", "Sidecar": "🎠"}.get(post_type, "📸")
    parts = [f"{type_emoji} *פוסט #{index}*"]
    if author:    parts.append(f"👤 @{author}")
    if timestamp: parts.append(f"🕐 {timestamp}")
    if caption:
        snippet = caption[:600] + ("…" if len(caption) > 600 else "")
        parts.append(f"\n{snippet}")
    stats = []
    if likes:    stats.append(f"❤️ {_num(likes)}")
    if comments: stats.append(f"💬 {_num(comments)}")
    if views:    stats.append(f"👁 {_num(views)}")
    if stats:    parts.append("  ".join(stats))
    if url:      parts.append(f"🔗 {url}")
    return "\n".join(parts), images[:4]


# ══════════════════════════════════════════════════════════════════════════════
#  שליחת פוסטים לטלגרם
# ══════════════════════════════════════════════════════════════════════════════

def _post_kb(uid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💾 שמור לעיבוד", callback_data=f"save_{uid[:40]}"),
        InlineKeyboardButton("⏭ דלג",          callback_data=f"skip_{uid[:40]}"),
    ]])


async def send_posts(bot: Bot, items: list[dict], label: str = "", min_likes: int = 0):
    seen      = load_seen()
    filtered  = [it for it in items if post_uid(it) not in seen and get_likes(it) >= min_likes]
    total     = len(items)
    new_count = len(filtered)

    if not filtered:
        await bot.send_message(
            TELEGRAM_CHAT_ID,
            f"📭 אין פוסטים חדשים\n_(נסרקו {total}, כולם כבר נשלחו או מתחת לסף)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await bot.send_message(
        TELEGRAM_CHAT_ID,
        f"📲 *{label}*\n{new_count} פוסטים חדשים מתוך {total}",
        parse_mode=ParseMode.MARKDOWN,
    )

    for i, item in enumerate(filtered, 1):
        uid = post_uid(item)
        pending[uid[:40]] = item
        try:
            msg_text, images = format_post(item, i)
            kb = _post_kb(uid)
            if images:
                if len(images) == 1:
                    await bot.send_photo(
                        TELEGRAM_CHAT_ID, photo=images[0],
                        caption=msg_text[:1024], parse_mode=ParseMode.MARKDOWN,
                        reply_markup=kb,
                    )
                else:
                    media = [InputMediaPhoto(images[0], caption=msg_text[:1024], parse_mode=ParseMode.MARKDOWN)]
                    media += [InputMediaPhoto(u) for u in images[1:]]
                    await bot.send_media_group(TELEGRAM_CHAT_ID, media=media)
                    await bot.send_message(
                        TELEGRAM_CHAT_ID,
                        f"👆 @{item.get('ownerUsername','?')}",
                        reply_markup=kb,
                    )
            else:
                chunks = textwrap.wrap(msg_text, 4096, break_long_words=False, replace_whitespace=False) or [msg_text]
                for j, chunk in enumerate(chunks):
                    await bot.send_message(
                        TELEGRAM_CHAT_ID, chunk,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                        reply_markup=kb if j == len(chunks) - 1 else None,
                    )
            seen.add(uid)
            await asyncio.sleep(0.5)
        except Exception as exc:
            log.warning("שגיאה בפוסט %d: %s", i, exc)

    save_seen(seen)
    await bot.send_message(
        TELEGRAM_CHAT_ID,
        f"✅ *{new_count} פוסטים נשלחו*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Apify
# ══════════════════════════════════════════════════════════════════════════════

def _build_input(accounts: list[str], posts_per_user: int) -> dict:
    return {
        "directUrls":   [f"https://www.instagram.com/{a}/" for a in accounts],
        "resultsType":  "posts",
        "resultsLimit": posts_per_user,
        "addParentData": True,
    }


async def apify_run(accounts: list[str], posts_per_user: int = 12) -> list[dict]:
    if not accounts:
        raise ValueError("לא הוגדרו חשבונות לסריקה")
    client    = ApifyClientAsync(APIFY_API_TOKEN)
    run_input = _build_input(accounts, posts_per_user)
    log.info("מריץ סריקה על: %s", accounts)
    run   = await client.actor(APIFY_ACTOR_ID).call(run_input=run_input)
    items = await client.dataset(run["defaultDatasetId"]).list_items()
    if len(items.items) == 1 and "error" in items.items[0]:
        err = items.items[0]
        raise RuntimeError(f"{err.get('error')}: {err.get('errorDescription')}")
    return items.items


async def apify_last_dataset() -> list[dict]:
    client = ApifyClientAsync(APIFY_API_TOKEN)
    runs   = await client.actor(APIFY_ACTOR_ID).runs().list(limit=1, desc=True, status="SUCCEEDED")
    if not runs.items:
        raise ValueError("אין ריצות מוצלחות")
    r      = runs.items[0]
    items  = await client.dataset(r["defaultDatasetId"]).list_items()
    return items.items


async def fetch_dataset(dataset_id: str) -> list[dict]:
    client = ApifyClientAsync(APIFY_API_TOKEN)
    items  = await client.dataset(dataset_id).list_items()
    return items.items


# ══════════════════════════════════════════════════════════════════════════════
#  גילוי חשבונות דומים
# ══════════════════════════════════════════════════════════════════════════════

async def discover_similar(base_accounts: list[str], top_n: int = 8) -> list[str]:
    """
    סורק את הפוסטים של base_accounts,
    מוצא את ה-hashtags הנפוצים ביותר,
    מחפש פוסטים עם אותם tags ומחזיר usernames חדשים.
    """
    # שלב 1 — קבל פוסטים של החשבונות הנוכחיים
    posts = await apify_run(base_accounts, posts_per_user=6)

    # שלב 2 — אסוף hashtags
    tag_counter: Counter = Counter()
    for p in posts:
        caption = p.get("caption") or p.get("text") or ""
        tags    = [w[1:].lower() for w in caption.split() if w.startswith("#") and len(w) > 2]
        tag_counter.update(tags)

    top_tags = [tag for tag, _ in tag_counter.most_common(5)]
    if not top_tags:
        return []

    # שלב 3 — חפש פוסטים עם אותם hashtags
    hashtag_urls = [f"https://www.instagram.com/explore/tags/{t}/" for t in top_tags[:3]]
    client       = ApifyClientAsync(APIFY_API_TOKEN)
    run_input    = {
        "directUrls":   hashtag_urls,
        "resultsType":  "posts",
        "resultsLimit": 30,
        "addParentData": True,
    }
    run   = await client.actor(APIFY_ACTOR_ID).call(run_input=run_input)
    items = await client.dataset(run["defaultDatasetId"]).list_items()

    # שלב 4 — מצא accounts חדשים עם הכי הרבה לייקים
    known     = set(a.lower() for a in base_accounts)
    acc_likes: dict[str, int] = {}
    for p in items.items:
        uname = (p.get("ownerUsername") or p.get("username") or "").lower()
        if uname and uname not in known:
            acc_likes[uname] = acc_likes.get(uname, 0) + get_likes(p)

    sorted_accs = sorted(acc_likes, key=lambda k: acc_likes[k], reverse=True)
    return sorted_accs[:top_n]


# ══════════════════════════════════════════════════════════════════════════════
#  תפריטים
# ══════════════════════════════════════════════════════════════════════════════

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 סרוק עכשיו",          callback_data="scan_now"),
         InlineKeyboardButton("👥 החשבונות שלי",        callback_data="accounts_menu")],
        [InlineKeyboardButton("🔍 גלה חשבונות דומים",   callback_data="discover"),
         InlineKeyboardButton("📊 ריצה אחרונה",         callback_data="latest_run")],
        [InlineKeyboardButton("⚙️ הגדרות",               callback_data="settings_menu")],
    ])


def accounts_menu_kb(accounts: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for a in accounts:
        rows.append([InlineKeyboardButton(f"@{a}", callback_data=f"acc_info_{a}"),
                     InlineKeyboardButton("🗑",     callback_data=f"acc_del_{a}")])
    rows.append([InlineKeyboardButton("➕ הוסף חשבון", callback_data="acc_add")])
    rows.append([InlineKeyboardButton("🔙 חזרה",       callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def settings_kb(cfg: dict) -> InlineKeyboardMarkup:
    min_likes = cfg.get("min_likes", 0)
    ppu       = cfg.get("posts_per_user", 12)
    likes_lbl = f"❤️ סף לייקים: {min_likes:,}" if min_likes else "❤️ סף לייקים: הכל"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(likes_lbl,             callback_data="set_likes")],
        [InlineKeyboardButton(f"📄 פוסטים לחשבון: {ppu}", callback_data="set_ppu")],
        [InlineKeyboardButton("🗑 נקה היסטוריה",      callback_data="reset_history")],
        [InlineKeyboardButton("🔙 חזרה",               callback_data="main_menu")],
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  Handlers — תפריט ראשי
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg      = load_config()
    accounts = cfg["accounts"]
    accs_str = ", ".join(f"@{a}" for a in accounts) if accounts else "לא הוגדרו עדיין"
    text = (
        "👋 *בוט תוכן אינסטגרם*\n\n"
        f"👥 חשבונות: {accs_str}\n"
        f"❤️ סף לייקים: {cfg['min_likes']:,}+" if cfg['min_likes'] else
        "👋 *בוט תוכן אינסטגרם*\n\n"
        f"👥 חשבונות: {accs_str}\n"
        "❤️ סף לייקים: הכל\n"
    )
    text += "\nבחר פעולה:"
    await (update.message or update.callback_query.message).reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb()
    )


async def cb_main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg      = load_config()
    accounts = cfg["accounts"]
    accs_str = ", ".join(f"@{a}" for a in accounts) if accounts else "לא הוגדרו עדיין"
    likes_str = f"{cfg['min_likes']:,}+" if cfg['min_likes'] else "הכל"
    await update.callback_query.edit_message_text(
        f"📲 *בוט תוכן אינסטגרם*\n\n"
        f"👥 חשבונות: {accs_str}\n"
        f"❤️ סף לייקים: {likes_str}\n\n"
        "בחר פעולה:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  Handlers — חשבונות
# ══════════════════════════════════════════════════════════════════════════════

async def cb_accounts_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg      = load_config()
    accounts = cfg["accounts"]
    text     = f"👥 *החשבונות שלי* ({len(accounts)})\n\n"
    if accounts:
        text += "\n".join(f"• @{a}" for a in accounts)
    else:
        text += "_אין חשבונות עדיין — לחץ ➕ להוספה_"
    await update.callback_query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=accounts_menu_kb(accounts),
    )


async def cb_acc_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "➕ *הוסף חשבון*\n\nשלח שם משתמש (ללא @):\n\n_דוגמה: garyvee_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_ADD_ACCOUNT


async def got_account_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lstrip("@").lower()
    if not username:
        await update.message.reply_text("❌ שם לא תקין. נסה שוב:")
        return WAITING_ADD_ACCOUNT

    cfg = load_config()
    if username in cfg["accounts"]:
        await update.message.reply_text(
            f"⚠️ @{username} כבר ברשימה.",
            reply_markup=main_menu_kb(),
        )
        return ConversationHandler.END

    cfg["accounts"].append(username)
    save_config(cfg)
    await update.message.reply_text(
        f"✅ @{username} נוסף!\n\nרשימה נוכחית:\n" +
        "\n".join(f"• @{a}" for a in cfg["accounts"]),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )
    return ConversationHandler.END


async def cb_acc_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    username = update.callback_query.data.replace("acc_del_", "")
    cfg      = load_config()
    if username in cfg["accounts"]:
        cfg["accounts"].remove(username)
        save_config(cfg)
        await update.callback_query.answer(f"✅ @{username} הוסר", show_alert=False)
    # חזור לתפריט חשבונות
    await cb_accounts_menu(update, ctx)


async def cb_acc_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    username = update.callback_query.data.replace("acc_info_", "")
    await update.callback_query.answer(f"@{username} — לחץ 🗑 להסרה", show_alert=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Handlers — סריקה
# ══════════════════════════════════════════════════════════════════════════════

async def cb_scan_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg      = load_config()
    accounts = cfg["accounts"]

    if not accounts:
        await update.callback_query.edit_message_text(
            "❌ *אין חשבונות*\n\nלחץ 👥 להוספת חשבונות קודם.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("👥 הוסף חשבונות", callback_data="accounts_menu"),
                InlineKeyboardButton("🔙 חזרה",          callback_data="main_menu"),
            ]]),
        )
        return

    msg = await update.callback_query.edit_message_text(
        f"⏳ *סורק {len(accounts)} חשבונות...*\n" +
        "\n".join(f"• @{a}" for a in accounts) +
        "\n\n_זה עלול לקחת כמה דקות_",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        items = await apify_run(accounts, posts_per_user=cfg.get("posts_per_user", 12))
        await msg.edit_text(
            f"✅ נמצאו *{len(items)}* פוסטים. שולח...",
            parse_mode=ParseMode.MARKDOWN,
        )
        await send_posts(update.get_bot(), items, label="סריקה ידנית", min_likes=cfg.get("min_likes", 0))
    except Exception as exc:
        await msg.edit_text(
            f"❌ *שגיאה בסריקה:*\n`{exc}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 חזרה", callback_data="main_menu")
            ]]),
        )


async def cb_latest_run(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    msg = await update.callback_query.edit_message_text("🔍 שולף ריצה אחרונה...")
    try:
        cfg   = load_config()
        items = await apify_last_dataset()
        await msg.edit_text(f"✅ נמצאו {len(items)} פריטים. שולח...")
        await send_posts(update.get_bot(), items, label="ריצה אחרונה", min_likes=cfg.get("min_likes", 0))
    except Exception as exc:
        await msg.edit_text(
            f"❌ `{exc}`", parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="main_menu")]]),
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Handlers — גילוי חשבונות דומים
# ══════════════════════════════════════════════════════════════════════════════

async def cb_discover(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg      = load_config()
    accounts = cfg["accounts"]

    if not accounts:
        await update.callback_query.edit_message_text(
            "❌ *הוסף קודם חשבונות מעקב*\nהגילוי עובד לפי האשטאגים שלהם.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("👥 הוסף חשבונות", callback_data="accounts_menu"),
                InlineKeyboardButton("🔙 חזרה",          callback_data="main_menu"),
            ]]),
        )
        return

    msg = await update.callback_query.edit_message_text(
        "🔍 *מחפש חשבונות דומים...*\n\n"
        "מנתח האשטאגים של החשבונות שלך\n"
        "וסורק תוכן פופולרי דומה ⏳",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        suggested = await discover_similar(accounts, top_n=8)
    except Exception as exc:
        await msg.edit_text(
            f"❌ שגיאה בגילוי: `{exc}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="main_menu")]]),
        )
        return

    if not suggested:
        await msg.edit_text(
            "😕 לא נמצאו חשבונות חדשים דומים.\nנסה להוסיף עוד חשבונות ולסרוק שוב.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="main_menu")]]),
        )
        return

    # שמור ב-config לאישור
    cfg["suggested"] = suggested
    save_config(cfg)

    # בנה תפריט הצעות
    rows = []
    for a in suggested:
        rows.append([
            InlineKeyboardButton(f"@{a}",         callback_data=f"sug_view_{a}"),
            InlineKeyboardButton("➕ הוסף",         callback_data=f"sug_add_{a}"),
            InlineKeyboardButton("❌",              callback_data=f"sug_skip_{a}"),
        ])
    rows.append([InlineKeyboardButton("✅ הוסף הכל", callback_data="sug_add_all")])
    rows.append([InlineKeyboardButton("🔙 חזרה",     callback_data="main_menu")])

    await msg.edit_text(
        f"✨ *נמצאו {len(suggested)} חשבונות דומים:*\n\n" +
        "\n".join(f"• @{a}" for a in suggested) +
        "\n\nבחר אילו להוסיף לרשימה:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def cb_sug_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    username = update.callback_query.data.replace("sug_add_", "")
    cfg = load_config()
    if username not in cfg["accounts"]:
        cfg["accounts"].append(username)
        save_config(cfg)
    await update.callback_query.answer(f"✅ @{username} נוסף!", show_alert=False)


async def cb_sug_add_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg       = load_config()
    suggested = cfg.get("suggested", [])
    added     = []
    for a in suggested:
        if a not in cfg["accounts"]:
            cfg["accounts"].append(a)
            added.append(a)
    save_config(cfg)
    await update.callback_query.edit_message_text(
        f"✅ *נוספו {len(added)} חשבונות!*\n\n" +
        "\n".join(f"• @{a}" for a in added),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 תפריט ראשי", callback_data="main_menu")]]),
    )


async def cb_sug_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("⏭ דולג")


async def cb_sug_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.callback_query.data.replace("sug_view_", "")
    await update.callback_query.answer(
        f"instagram.com/{username}", show_alert=True
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Handlers — הגדרות
# ══════════════════════════════════════════════════════════════════════════════

async def cb_settings_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg = load_config()
    await update.callback_query.edit_message_text(
        "⚙️ *הגדרות*", parse_mode=ParseMode.MARKDOWN,
        reply_markup=settings_kb(cfg),
    )


async def cb_set_likes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "❤️ *סף לייקים*\n\nשלח מספר (0 = הכל):\n_דוגמה: 500_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return WAITING_LIKES_THRESHOLD


async def got_likes_threshold(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ מספר שלם בלבד. נסה שוב:")
        return WAITING_LIKES_THRESHOLD

    cfg = load_config()
    cfg["min_likes"] = val
    save_config(cfg)
    lbl = f"{val:,}+" if val else "הכל (ללא סינון)"
    await update.message.reply_text(
        f"✅ סף לייקים עודכן: *{lbl}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )
    return ConversationHandler.END


async def cb_reset_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
    await update.callback_query.edit_message_text(
        "🗑 *ההיסטוריה נמחקה*\n\nהסריקה הבאה תשלח את כל הפוסטים מחדש.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="main_menu")]]),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Handlers — כפתורי פוסט (שמור / דלג)
# ══════════════════════════════════════════════════════════════════════════════

async def cb_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = query.data.replace("save_", "")
    item = pending.get(uid)
    if not item:
        await query.answer("פוסט לא נמצא בזיכרון", show_alert=True)
        return
    status_txt = "💾 נשמר"
    try:
        from sheets_manager import add_post
        added      = add_post(item)
        status_txt = "✅ נשמר ב-Sheets" if added else "⚠️ כבר קיים"
    except Exception:
        pass
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(status_txt, callback_data="noop")]])
    )
    pending.pop(uid, None)


async def cb_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("⏭ דולג")
    uid = update.callback_query.data.replace("skip_", "")
    pending.pop(uid, None)
    await update.callback_query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ דולג", callback_data="noop")]])
    )


async def cb_noop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


# ══════════════════════════════════════════════════════════════════════════════
#  ריצה יומית
# ══════════════════════════════════════════════════════════════════════════════

async def daily_job(bot: Bot):
    cfg      = load_config()
    accounts = cfg["accounts"]
    if not accounts:
        await bot.send_message(
            TELEGRAM_CHAT_ID,
            "⏰ *ריצה יומית*\n\n❌ אין חשבונות מוגדרים.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb(),
        )
        return
    await bot.send_message(
        TELEGRAM_CHAT_ID,
        f"⏰ *ריצה יומית אוטומטית*\nסורק {len(accounts)} חשבונות...",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        items = await apify_run(accounts, posts_per_user=cfg.get("posts_per_user", 12))
        await send_posts(bot, items, label="עדכון יומי", min_likes=cfg.get("min_likes", 0))
    except Exception as exc:
        await bot.send_message(
            TELEGRAM_CHAT_ID,
            f"❌ שגיאה: `{exc}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb(),
        )


# ══════════════════════════════════════════════════════════════════════════════
#  הפעלה
# ══════════════════════════════════════════════════════════════════════════════

async def run_all():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ConversationHandler לקלט טקסט
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_acc_add,   pattern="^acc_add$"),
            CallbackQueryHandler(cb_set_likes, pattern="^set_likes$"),
        ],
        states={
            WAITING_ADD_ACCOUNT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, got_account_name)],
            WAITING_LIKES_THRESHOLD:[MessageHandler(filters.TEXT & ~filters.COMMAND, got_likes_threshold)],
        },
        fallbacks=[CallbackQueryHandler(cb_main_menu, pattern="^main_menu$")],
        per_message=False,
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(conv)

    # ניווט
    app.add_handler(CallbackQueryHandler(cb_main_menu,     pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(cb_accounts_menu, pattern="^accounts_menu$"))
    app.add_handler(CallbackQueryHandler(cb_acc_del,       pattern="^acc_del_"))
    app.add_handler(CallbackQueryHandler(cb_acc_info,      pattern="^acc_info_"))
    app.add_handler(CallbackQueryHandler(cb_scan_now,      pattern="^scan_now$"))
    app.add_handler(CallbackQueryHandler(cb_latest_run,    pattern="^latest_run$"))
    app.add_handler(CallbackQueryHandler(cb_discover,      pattern="^discover$"))
    app.add_handler(CallbackQueryHandler(cb_sug_add,       pattern="^sug_add_(?!all)"))
    app.add_handler(CallbackQueryHandler(cb_sug_add_all,   pattern="^sug_add_all$"))
    app.add_handler(CallbackQueryHandler(cb_sug_skip,      pattern="^sug_skip_"))
    app.add_handler(CallbackQueryHandler(cb_sug_view,      pattern="^sug_view_"))
    app.add_handler(CallbackQueryHandler(cb_settings_menu, pattern="^settings_menu$"))
    app.add_handler(CallbackQueryHandler(cb_reset_history, pattern="^reset_history$"))
    app.add_handler(CallbackQueryHandler(cb_save,          pattern="^save_"))
    app.add_handler(CallbackQueryHandler(cb_skip,          pattern="^skip_"))
    app.add_handler(CallbackQueryHandler(cb_noop,          pattern="^noop$"))

    # Scheduler יומי
    app.job_queue.run_daily(
        callback=lambda ctx: asyncio.create_task(daily_job(ctx.bot)),
        time=time(hour=DAILY_RUN_HOUR, minute=DAILY_RUN_MINUTE, tzinfo=timezone.utc),
        name="daily_instagram",
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    log.info("🤖 בוט פועל")

    # Webhook אופציונלי
    runner = None
    try:
        wapp   = web.Application()
        runner = web.AppRunner(wapp)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT).start()
    except OSError:
        log.warning("Webhook port %d תפוס — מדלג", WEBHOOK_PORT)

    try:
        await app.bot.send_message(
            TELEGRAM_CHAT_ID,
            "✅ *הבוט עלה לאוויר!*\n\nלחץ /start לפתיחת התפריט.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass

    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        if runner:
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run_all())
