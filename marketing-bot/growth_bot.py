"""
בוט צמיחה לאינסטגרם — Telegram + Instagrapi
פעולות: עקוב, לייק, צפייה בסטוריז
מגבלות בטוחות + השהיות אנושיות
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, date
from pathlib import Path

from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired
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

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN      = os.environ.get("GROWTH_BOT_TOKEN") or os.environ["TELEGRAM_TOKEN"]
CHAT_ID    = int(os.environ.get("TELEGRAM_CHAT_ID", 0))
IG_USERNAME = os.environ.get("IG_USERNAME", "")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "")
IG_PROXY    = os.environ.get("IG_PROXY", "")
CONFIG_FILE   = Path("growth_config.json")
SESSION_FILE  = Path("ig_session.json")
STATS_FILE    = Path("growth_stats.json")

# ── מגבלות יומיות בטוחות ────────────────────────────────────────────────────
LIMITS = {
    "follows":     150,
    "likes":       300,
    "story_views": 200,
    "unfollows":   150,
}

# השהיות בשניות בין פעולות (min, max)
DELAYS = {
    "follow":      (25, 65),
    "like":        (15, 45),
    "story_view":  (8,  20),
    "unfollow":    (20, 55),
    "between_batch": (180, 360),  # בין קבוצות פעולות
}

# שלבי שיחה
S_IG_USER, S_IG_PASS, S_IG_CODE, S_IG_CHALLENGE, S_ADD_TARGET, S_SET_LIMIT, S_SET_PROXY = range(7)

# ── config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    default = {
        "ig_username": "",
        "targets": [],
        "active": False,
        "actions": {"follow": True, "like": True, "story_view": True, "unfollow": False},
        "limits": dict(LIMITS),
        "active_hours": {"start": 8, "end": 23},
    }
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            default.update(data)
            return default
        except Exception:
            pass
    return default

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def load_stats() -> dict:
    default = {"date": "", "follows": 0, "likes": 0, "story_views": 0, "unfollows": 0, "errors": 0}
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default

def save_stats(stats: dict):
    STATS_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

def today_stats() -> dict:
    stats = load_stats()
    today = str(date.today())
    if stats.get("date") != today:
        stats = {"date": today, "follows": 0, "likes": 0, "story_views": 0, "unfollows": 0, "errors": 0}
        save_stats(stats)
    return stats

# ── Instagram Client ──────────────────────────────────────────────────────────

_ig_client: Client | None = None

def get_ig_client() -> Client | None:
    return _ig_client

def init_ig_client() -> Client:
    cl = Client()
    cl.delay_range = [2, 5]
    cl.request_timeout = 30
    # פרוקסי — מה-.env או מה-config
    proxy = IG_PROXY or load_config().get("proxy", "")
    if proxy:
        cl.set_proxy(proxy)
        logger.info(f"פרוקסי פעיל: {proxy.split('@')[-1] if '@' in proxy else proxy}")
    return cl

async def ig_login(username: str, password: str) -> tuple[bool, str]:
    global _ig_client
    import json as _json

    # מחק session ישן אם קיים — נתחיל מחדש
    if SESSION_FILE.exists():
        SESSION_FILE.unlink(missing_ok=True)

    cl = init_ig_client()

    try:
        cl.login(username, password)
        cl.dump_settings(SESSION_FILE)
        _ig_client = cl
        logger.info(f"התחברות חדשה: {username}")
        return True, "התחברת בהצלחה ✅"

    except TwoFactorRequired:
        _ig_client = cl
        return False, "2FA"
    except ChallengeRequired:
        _ig_client = cl
        return False, "CHALLENGE"
    except _json.JSONDecodeError:
        _ig_client = cl
        return False, "CHALLENGE"
    except Exception as e:
        err = str(e)
        if "challenge" in err.lower() or "Expecting value" in err:
            _ig_client = cl
            return False, "CHALLENGE"
        logger.error(f"שגיאת התחברות: {e}")
        return False, f"שגיאה: {e}"


async def ig_login_by_session(session_id: str) -> tuple[bool, str]:
    global _ig_client
    from urllib.parse import unquote
    import asyncio

    if SESSION_FILE.exists():
        SESSION_FILE.unlink(missing_ok=True)

    # URL-decode: %3A → :
    session_id = unquote(session_id)
    logger.info(f"session id (decoded): {session_id[:20]}...")

    cl = init_ig_client()

    def _do_login():
        cl.login_by_sessionid(session_id)
        return cl.username

    try:
        username = await asyncio.to_thread(_do_login)
        cl.dump_settings(SESSION_FILE)
        _ig_client = cl
        logger.info(f"התחברות מ-session cookie: {username}")
        return True, username
    except Exception as e:
        logger.error(f"שגיאת session login: {e}")
        return False, str(e)


# ── פעולות אינסטגרם ───────────────────────────────────────────────────────────

async def run_growth_cycle(app, chat_id: int):
    """מחזור צמיחה אחד — עקוב/לייק/סטוריז על עוקבי חשבונות מטרה"""
    cfg   = load_config()
    stats = today_stats()
    cl    = get_ig_client()

    if not cl:
        await app.bot.send_message(chat_id, "❌ לא מחובר לאינסטגרם. עצור את הבוט והתחבר מחדש.")
        return

    if not cfg.get("targets"):
        await app.bot.send_message(chat_id, "❌ אין חשבונות מטרה. הוסף דרך התפריט.")
        return

    now = datetime.now().hour
    active_start = cfg["active_hours"]["start"]
    active_end   = cfg["active_hours"]["end"]
    if not (active_start <= now < active_end):
        logger.info(f"מחוץ לשעות פעילות ({now}:00)")
        return

    limits  = cfg.get("limits", LIMITS)
    actions = cfg.get("actions", {})

    await app.bot.send_message(chat_id, "🔄 מתחיל מחזור צמיחה...")

    total_follows = 0
    total_likes   = 0
    total_stories = 0

    for target_username in cfg["targets"]:
        if not cfg.get("active"):
            break

        try:
            target_id = cl.user_id_from_username(target_username)
            followers = cl.user_followers(target_id, amount=50)
        except Exception as e:
            logger.error(f"שגיאה בשליפת עוקבים של {target_username}: {e}")
            stats["errors"] += 1
            continue

        for user_id, user_info in followers.items():
            if not cfg.get("active"):
                break

            # בדוק מגבלות יומיות
            if stats["follows"] >= limits.get("follows", LIMITS["follows"]):
                await app.bot.send_message(chat_id, "✅ הגעת למגבלת עקיבה יומית")
                break

            username = user_info.username

            # ── עקוב ──
            if actions.get("follow", True) and stats["follows"] < limits.get("follows", LIMITS["follows"]):
                try:
                    cl.user_follow(user_id)
                    stats["follows"] += 1
                    total_follows += 1
                    logger.info(f"עקב: @{username}")
                    delay = random.uniform(*DELAYS["follow"])
                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(f"שגיאת עקיבה @{username}: {e}")
                    stats["errors"] += 1

            # ── לייק על פוסט אחרון ──
            if actions.get("like", True) and stats["likes"] < limits.get("likes", LIMITS["likes"]):
                try:
                    medias = cl.user_medias(user_id, amount=2)
                    for media in medias[:1]:
                        cl.media_like(media.id)
                        stats["likes"] += 1
                        total_likes += 1
                        logger.info(f"לייק: @{username}")
                        await asyncio.sleep(random.uniform(*DELAYS["like"]))
                except Exception as e:
                    logger.error(f"שגיאת לייק @{username}: {e}")
                    stats["errors"] += 1

            # ── צפה בסטוריז ──
            if actions.get("story_view", True) and stats["story_views"] < limits.get("story_views", LIMITS["story_views"]):
                try:
                    stories = cl.user_stories(user_id)
                    if stories:
                        story_ids = [s.id for s in stories[:3]]
                        cl.story_seen(story_ids)
                        stats["story_views"] += len(story_ids)
                        total_stories += len(story_ids)
                        logger.info(f"סטוריז: @{username} ({len(story_ids)})")
                        await asyncio.sleep(random.uniform(*DELAYS["story_view"]))
                except Exception as e:
                    logger.error(f"שגיאת סטוריז @{username}: {e}")

            save_stats(stats)

        # הפסקה בין חשבונות מטרה
        await asyncio.sleep(random.uniform(*DELAYS["between_batch"]))

    save_stats(stats)
    summary = (
        f"✅ *סיכום מחזור*\n"
        f"👥 עקיבות: {total_follows}\n"
        f"❤️ לייקים: {total_likes}\n"
        f"👁 סטוריז: {total_stories}\n\n"
        f"📊 *סה״כ היום:*\n"
        f"👥 {stats['follows']}/{limits.get('follows', LIMITS['follows'])}\n"
        f"❤️ {stats['likes']}/{limits.get('likes', LIMITS['likes'])}\n"
        f"👁 {stats['story_views']}/{limits.get('story_views', LIMITS['story_views'])}"
    )
    await app.bot.send_message(chat_id, summary, parse_mode=ParseMode.MARKDOWN)


# ── תפריטים ───────────────────────────────────────────────────────────────────

def main_menu_kb(cfg: dict) -> InlineKeyboardMarkup:
    status = "🟢 פועל" if cfg.get("active") else "🔴 כבוי"
    ig_user = cfg.get("ig_username") or "לא מחובר"
    connected = "✅" if get_ig_client() else "❌"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'⏹ עצור' if cfg.get('active') else '▶️ הפעל'}", callback_data="toggle_active"),
         InlineKeyboardButton(f"{connected} {ig_user}", callback_data="ig_status")],
        [InlineKeyboardButton("🎯 חשבונות מטרה", callback_data="targets"),
         InlineKeyboardButton("⚙️ הגדרות", callback_data="settings")],
        [InlineKeyboardButton("📊 סטטיסטיקות היום", callback_data="stats"),
         InlineKeyboardButton("🔑 התחבר לאינסטגרם", callback_data="ig_login")],
        [InlineKeyboardButton("▶️ הרץ עכשיו", callback_data="run_now")],
    ])


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    await update.message.reply_text(
        "🤖 *בוט צמיחה לאינסטגרם*\n\nמנהל עקיבות, לייקים וצפיות בסטוריז בצורה בטוחה ואוטומטית.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(cfg)
    )


async def cb_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg = load_config()
    await update.callback_query.edit_message_text(
        "🤖 *בוט צמיחה לאינסטגרם*\n\nבחר פעולה:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(cfg)
    )
    return ConversationHandler.END


# ── התחברות לאינסטגרם ─────────────────────────────────────────────────────────

async def cb_ig_login(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🔑 *התחברות לאינסטגרם*\n\nשלח את *שם המשתמש* שלך:",
        parse_mode=ParseMode.MARKDOWN
    )
    return S_IG_USER


async def got_ig_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["ig_username"] = update.message.text.strip().lstrip("@")
    await update.message.reply_text("🔒 עכשיו שלח את *הסיסמה* (ההודעה נמחקת מיד):", parse_mode=ParseMode.MARKDOWN)
    return S_IG_PASS


async def got_ig_pass(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    username = ctx.user_data.get("ig_username", "")

    # מחק את הודעת הסיסמה מיד
    try:
        await update.message.delete()
    except Exception:
        pass

    msg = await update.message.reply_text("⏳ מתחבר לאינסטגרם...")
    ctx.user_data["ig_password"] = password

    success, result = await ig_login(username, password)

    if result == "2FA":
        await msg.edit_text("📱 *אימות דו-שלבי*\n\nשלח את קוד האימות מהאפליקציה/SMS:", parse_mode=ParseMode.MARKDOWN)
        return S_IG_CODE

    if result == "CHALLENGE":
        # שלח קוד אימות למייל/SMS של האינסטגרם
        cl = get_ig_client()
        try:
            cl.challenge_resolve(cl.last_json)
            await msg.edit_text(
                "📧 *אינסטגרם שלחה קוד אימות*\n\n"
                "בדוק את המייל או ה-SMS שמחובר לחשבון האינסטגרם ושלח את הקוד:",
                parse_mode=ParseMode.MARKDOWN
            )
            return S_IG_CHALLENGE
        except Exception as e:
            await msg.edit_text(
                f"⚠️ *אינסטגרם דורשת אימות*\n\n"
                f"פתח את אפליקציית האינסטגרם, אשר את ההתחברות ואז נסה שוב.\n\n"
                f"פרטים: `{e}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 נסה שוב", callback_data="ig_login")],
                    [InlineKeyboardButton("🔙 חזרה", callback_data="main")],
                ])
            )
            return ConversationHandler.END

    if success:
        cfg = load_config()
        cfg["ig_username"] = username
        save_config(cfg)
        await msg.edit_text(result, reply_markup=main_menu_kb(cfg))
    else:
        await msg.edit_text(f"❌ {result}", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 נסה שוב", callback_data="ig_login")],
            [InlineKeyboardButton("🔙 חזרה", callback_data="main")],
        ]))

    return ConversationHandler.END


async def got_ig_challenge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    username = ctx.user_data.get("ig_username", "")
    cl = get_ig_client()
    if not cl:
        await update.message.reply_text("❌ שגיאה, נסה להתחבר מחדש.")
        return ConversationHandler.END
    try:
        cl.challenge_resolve_simple(code)
        cl.dump_settings(SESSION_FILE)
        cfg = load_config()
        cfg["ig_username"] = username
        save_config(cfg)
        await update.message.reply_text("✅ האימות הצליח! מחובר לאינסטגרם.", reply_markup=main_menu_kb(cfg))
    except Exception as e:
        await update.message.reply_text(
            f"❌ קוד שגוי או פג תוקף: `{e}`\n\nנסה שוב.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 התחבר מחדש", callback_data="ig_login")],
            ])
        )
    return ConversationHandler.END


async def got_ig_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    username = ctx.user_data.get("ig_username", "")
    password = ctx.user_data.get("ig_password", "")

    global _ig_client
    if _ig_client:
        try:
            _ig_client.two_factor_login(code)
            _ig_client.dump_settings(SESSION_FILE)
            cfg = load_config()
            cfg["ig_username"] = username
            save_config(cfg)
            await update.message.reply_text("✅ התחברת בהצלחה!", reply_markup=main_menu_kb(cfg))
        except Exception as e:
            await update.message.reply_text(f"❌ קוד שגוי: {e}")

    return ConversationHandler.END


# ── הפעל/עצור ─────────────────────────────────────────────────────────────────

async def cb_toggle_active(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg = load_config()

    if not get_ig_client() and not cfg.get("active"):
        await update.callback_query.answer("❌ התחבר לאינסטגרם תחילה", show_alert=True)
        return

    cfg["active"] = not cfg.get("active")
    save_config(cfg)

    status = "🟢 הבוט הופעל!" if cfg["active"] else "🔴 הבוט נעצר"
    await update.callback_query.edit_message_text(
        f"*{status}*\n\nבחר פעולה:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(cfg)
    )

    if cfg["active"] and CHAT_ID:
        ctx.application.create_task(run_growth_cycle(ctx.application, CHAT_ID))


async def cb_run_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not get_ig_client():
        await update.callback_query.answer("❌ התחבר לאינסטגרם תחילה", show_alert=True)
        return
    await update.callback_query.edit_message_text("⏳ מריץ מחזור...")
    chat_id = update.callback_query.message.chat_id
    await run_growth_cycle(ctx.application, chat_id)


# ── חשבונות מטרה ──────────────────────────────────────────────────────────────

async def cb_targets(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg = load_config()
    targets = cfg.get("targets", [])

    buttons = []
    for t in targets:
        buttons.append([
            InlineKeyboardButton(f"@{t}", callback_data=f"noop"),
            InlineKeyboardButton("🗑", callback_data=f"del_target_{t}"),
        ])
    buttons.append([InlineKeyboardButton("➕ הוסף חשבון מטרה", callback_data="add_target")])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="main")])

    await update.callback_query.edit_message_text(
        f"🎯 *חשבונות מטרה* ({len(targets)})\n\nהבוט יעקוב אחרי העוקבים שלהם:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cb_add_target(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "✏️ שלח את *שם החשבון* (ללא @):",
        parse_mode=ParseMode.MARKDOWN
    )
    return S_ADD_TARGET


async def got_target(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lstrip("@")
    cfg = load_config()
    if username not in cfg["targets"]:
        cfg["targets"].append(username)
        save_config(cfg)
        await update.message.reply_text(f"✅ @{username} נוסף!", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ הוסף עוד", callback_data="add_target")],
            [InlineKeyboardButton("🔙 חזרה", callback_data="targets")],
        ]))
    else:
        await update.message.reply_text(f"@{username} כבר קיים.")
    return ConversationHandler.END


async def cb_del_target(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    target = update.callback_query.data.replace("del_target_", "")
    cfg = load_config()
    cfg["targets"] = [t for t in cfg["targets"] if t != target]
    save_config(cfg)
    await cb_targets(update, ctx)


# ── הגדרות ────────────────────────────────────────────────────────────────────

async def cb_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg = load_config()
    actions = cfg.get("actions", {})
    limits  = cfg.get("limits", LIMITS)
    hours   = cfg.get("active_hours", {"start": 8, "end": 23})

    def tog(key): return "✅" if actions.get(key) else "❌"

    await update.callback_query.edit_message_text(
        f"⚙️ *הגדרות*\n\n"
        f"שעות פעילות: {hours['start']}:00 — {hours['end']}:00\n\n"
        f"מגבלות יומיות:\n"
        f"👥 עקיבות: {limits.get('follows', 150)}\n"
        f"❤️ לייקים: {limits.get('likes', 300)}\n"
        f"👁 סטוריז: {limits.get('story_views', 200)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{tog('follow')} עקיבה", callback_data="tog_follow"),
             InlineKeyboardButton(f"{tog('like')} לייק", callback_data="tog_like")],
            [InlineKeyboardButton(f"{tog('story_view')} סטוריז", callback_data="tog_story_view"),
             InlineKeyboardButton(f"{tog('unfollow')} ביטול עקיבה", callback_data="tog_unfollow")],
            [InlineKeyboardButton("📉 הורד מגבלות (מצב בטוח)", callback_data="safe_mode"),
             InlineKeyboardButton("📈 מגבלות רגילות", callback_data="normal_mode")],
            [InlineKeyboardButton(f"🌐 פרוקסי: {'פעיל ✅' if (IG_PROXY or load_config().get('proxy')) else 'כבוי ❌'}", callback_data="set_proxy")],
            [InlineKeyboardButton("🔙 חזרה", callback_data="main")],
        ])
    )


async def cb_toggle_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    key = update.callback_query.data.replace("tog_", "")
    cfg = load_config()
    cfg["actions"][key] = not cfg["actions"].get(key, True)
    save_config(cfg)
    await cb_settings(update, ctx)


async def cb_safe_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("🛡 מצב בטוח הופעל")
    cfg = load_config()
    cfg["limits"] = {"follows": 80, "likes": 150, "story_views": 100, "unfollows": 50}
    save_config(cfg)
    await cb_settings(update, ctx)


async def cb_set_proxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cfg = load_config()
    current = IG_PROXY or cfg.get("proxy", "")
    await update.callback_query.edit_message_text(
        f"🌐 *הגדרת פרוקסי*\n\n"
        f"פרוקסי נוכחי: `{current or 'אין'}`\n\n"
        f"שלח את כתובת הפרוקסי בפורמט:\n"
        f"`http://user:pass@host:port`\n"
        f"`socks5://user:pass@host:port`\n\n"
        f"או שלח `נקה` להסרת הפרוקסי:",
        parse_mode=ParseMode.MARKDOWN
    )
    return S_SET_PROXY


def normalize_proxy(raw: str) -> str:
    """ממיר כל פורמט פרוקסי ל-http://user:pass@host:port"""
    raw = raw.strip()
    # כבר בפורמט מלא
    if raw.startswith(("http://", "https://", "socks5://")):
        return raw
    parts = raw.replace(" ", "").split(":")
    # host:port:user:pass
    if len(parts) == 4:
        host, port, user, pwd = parts
        return f"http://{user}:{pwd}@{host}:{port}"
    # user:pass@host:port
    if "@" in raw:
        return f"http://{raw}"
    # host:port בלי auth
    if len(parts) == 2:
        return f"http://{raw}"
    return raw


async def got_proxy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    cfg  = load_config()

    if text == "נקה":
        cfg["proxy"] = ""
        save_config(cfg)
        await update.message.reply_text("✅ הפרוקסי הוסר.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 הגדרות", callback_data="settings")]
        ]))
        return ConversationHandler.END

    proxy = normalize_proxy(text)
    await update.message.reply_text(f"⏳ בודק פרוקסי...\n`{proxy}`", parse_mode=ParseMode.MARKDOWN)

    try:
        import httpx
        async with httpx.AsyncClient(proxies={"all://": proxy}, timeout=15) as client:
            r = await client.get("https://httpbin.org/ip", timeout=10)
            ip_info = r.json().get("origin", "?")
            cfg["proxy"] = proxy
            save_config(cfg)
            await update.message.reply_text(
                f"✅ *פרוקסי עובד!*\n\n"
                f"IP דרך הפרוקסי: `{ip_info}`\n\n"
                f"לחץ 🔑 התחבר לאינסטגרם עכשיו.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 התחבר לאינסטגרם", callback_data="ig_login")],
                    [InlineKeyboardButton("🔙 הגדרות", callback_data="settings")],
                ])
            )
    except Exception as e:
        await update.message.reply_text(
            f"❌ *הפרוקסי לא עובד:*\n`{e}`\n\n"
            f"ודא שהפורמט נכון ושהפרוקסי פעיל.\n\n"
            f"פורמטים נתמכים:\n"
            f"• `host:port:user:pass`\n"
            f"• `http://user:pass@host:port`\n"
            f"• `socks5://user:pass@host:port`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 נסה שוב", callback_data="set_proxy")]])
        )
    return ConversationHandler.END


async def cb_normal_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("📈 מגבלות רגילות")
    cfg = load_config()
    cfg["limits"] = dict(LIMITS)
    save_config(cfg)
    await cb_settings(update, ctx)


# ── סטטיסטיקות ───────────────────────────────────────────────────────────────

async def cb_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    stats  = today_stats()
    limits = load_config().get("limits", LIMITS)

    def bar(done, total):
        pct   = min(done / max(total, 1), 1)
        filled = int(pct * 10)
        return "█" * filled + "░" * (10 - filled) + f" {done}/{total}"

    await update.callback_query.edit_message_text(
        f"📊 *סטטיסטיקות היום — {stats['date']}*\n\n"
        f"👥 עקיבות:  {bar(stats['follows'], limits.get('follows', 150))}\n"
        f"❤️ לייקים:  {bar(stats['likes'], limits.get('likes', 300))}\n"
        f"👁 סטוריז:  {bar(stats['story_views'], limits.get('story_views', 200))}\n"
        f"🔄 ביטולים: {bar(stats['unfollows'], limits.get('unfollows', 150))}\n"
        f"⚠️ שגיאות: {stats['errors']}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 חזרה", callback_data="main")]
        ])
    )


async def cb_ig_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    cl  = get_ig_client()
    if cl:
        await update.callback_query.answer(f"✅ מחובר כ-@{cfg.get('ig_username', '')}", show_alert=True)
    else:
        await update.callback_query.answer("❌ לא מחובר — לחץ 'התחבר לאינסטגרם'", show_alert=True)


async def cb_noop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


# ── scheduler: הרץ כל שעה ─────────────────────────────────────────────────────

async def scheduled_cycle(ctx: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    if cfg.get("active") and CHAT_ID:
        await run_growth_cycle(ctx.application, CHAT_ID)


# ══════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_ig_login,   pattern="^ig_login$"),
            CallbackQueryHandler(cb_add_target, pattern="^add_target$"),
            CallbackQueryHandler(cb_set_proxy,  pattern="^set_proxy$"),
        ],
        states={
            S_IG_USER:      [MessageHandler(filters.TEXT & ~filters.COMMAND, got_ig_user)],
            S_IG_PASS:      [MessageHandler(filters.TEXT & ~filters.COMMAND, got_ig_pass)],
            S_IG_CODE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, got_ig_code)],
            S_IG_CHALLENGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_ig_challenge)],
            S_ADD_TARGET:   [MessageHandler(filters.TEXT & ~filters.COMMAND, got_target)],
            S_SET_PROXY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, got_proxy)],
        },
        fallbacks=[CallbackQueryHandler(cb_main, pattern="^main$")],
        per_message=False,
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(cb_main,          pattern="^main$"))
    app.add_handler(CallbackQueryHandler(cb_toggle_active, pattern="^toggle_active$"))
    app.add_handler(CallbackQueryHandler(cb_run_now,       pattern="^run_now$"))
    app.add_handler(CallbackQueryHandler(cb_targets,       pattern="^targets$"))
    app.add_handler(CallbackQueryHandler(cb_del_target,    pattern="^del_target_"))
    app.add_handler(CallbackQueryHandler(cb_settings,      pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(cb_toggle_action, pattern="^tog_"))
    app.add_handler(CallbackQueryHandler(cb_safe_mode,     pattern="^safe_mode$"))
    app.add_handler(CallbackQueryHandler(cb_normal_mode,   pattern="^normal_mode$"))
    app.add_handler(CallbackQueryHandler(cb_set_proxy,     pattern="^set_proxy$"))
    app.add_handler(CallbackQueryHandler(cb_stats,         pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(cb_ig_status,     pattern="^ig_status$"))
    app.add_handler(CallbackQueryHandler(cb_noop,          pattern="^noop$"))

    # הרץ כל 60 דקות
    app.job_queue.run_repeating(scheduled_cycle, interval=3600, first=60)

    # התחברות אוטומטית בתוך event loop של הבוט
    async def auto_login(application):
        # לא מתחבר אוטומטית בלי פרוקסי — מונע חסימת IP
        proxy = IG_PROXY or load_config().get("proxy", "")
        if not proxy:
            if CHAT_ID:
                await application.bot.send_message(
                    CHAT_ID,
                    "🤖 *בוט הצמיחה מוכן!*\n\n"
                    "כדי להתחבר לאינסטגרם:\n"
                    "1. הגדר פרוקסי: ⚙️ הגדרות → 🌐 פרוקסי\n"
                    "2. לחץ 🔑 התחבר לאינסטגרם",
                    parse_mode=ParseMode.MARKDOWN
                )
            return

        ig_session = os.environ.get("IG_SESSION_ID", "")
        if ig_session:
            logger.info("מתחבר לאינסטגרם מ-session cookie...")
            success, result = await ig_login_by_session(ig_session)
            if success:
                cfg = load_config()
                cfg["ig_username"] = result
                save_config(cfg)
                if CHAT_ID:
                    await application.bot.send_message(
                        CHAT_ID,
                        f"✅ *מחובר לאינסטגרם כ-@{result}*\n\nהבוט מוכן לפעולה!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                return
            else:
                logger.error(f"שגיאת session: {result}")

        if IG_USERNAME and IG_PASSWORD:
            logger.info(f"מתחבר לאינסטגרם כ-{IG_USERNAME}...")
            success, result = await ig_login(IG_USERNAME, IG_PASSWORD)
            if success:
                logger.info(f"✅ מחובר לאינסטגרם: {IG_USERNAME}")
                cfg = load_config()
                cfg["ig_username"] = IG_USERNAME
                save_config(cfg)
                if CHAT_ID:
                    await application.bot.send_message(
                        CHAT_ID,
                        f"✅ *מחובר לאינסטגרם כ-@{IG_USERNAME}*\n\nהבוט מוכן לפעולה!",
                        parse_mode=ParseMode.MARKDOWN
                    )
            elif result == "CHALLENGE":
                logger.warning("⚠️ אינסטגרם דורשת אימות")
                if CHAT_ID:
                    await application.bot.send_message(
                        CHAT_ID,
                        "⚠️ *אינסטגרם דורשת אימות*\n\n"
                        "בדוק מייל/SMS של החשבון ושלח את הקוד כאן:",
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                logger.error(f"❌ שגיאת התחברות: {result}")
                if CHAT_ID:
                    await application.bot.send_message(
                        CHAT_ID, f"❌ שגיאת התחברות לאינסטגרם: {result}"
                    )

    app.post_init = auto_login

    logger.info("בוט הצמיחה מופעל...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
