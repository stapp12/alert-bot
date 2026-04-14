"""
Google Sheets Dashboard Manager
---------------------------------
שומר כל פוסט שמור כשורה בגיליון.
עמודות: מזהה | תמונה | כיתוב | לייקים | תגובות | חשבון | תאריך | קטגוריה | סטטוס | לינק
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

SHEETS_ID        = os.getenv("GOOGLE_SHEETS_ID", "")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SHEET_NAME       = os.getenv("GOOGLE_SHEET_NAME", "פוסטים")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "מזהה",
    "URL תמונה",
    "כיתוב",
    "לייקים",
    "תגובות",
    "צפיות",
    "חשבון",
    "תאריך פרסום",
    "תאריך הוספה",
    "קטגוריה",
    "סטטוס",
    "לינק",
]

STATUS_PENDING  = "ממתין לעיבוד"
STATUS_WORKING  = "בעבודה"
STATUS_DONE     = "פורסם"
STATUS_SKIP     = "דחוי"


def _get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    gc    = gspread.authorize(creds)
    sh    = gc.open_by_key(SHEETS_ID)
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=1000, cols=len(HEADERS))
        ws.append_row(HEADERS)
        # עיצוב כותרות
        ws.format("A1:L1", {
            "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 0.84, "blue": 0}},
            "horizontalAlignment": "CENTER",
        })
    return ws


def _num(n) -> str:
    try:
        return str(int(n))
    except Exception:
        return "0"


def _ts(raw) -> str:
    if not raw:
        return ""
    try:
        if isinstance(raw, (int, float)):
            dt = datetime.fromtimestamp(raw / 1000 if raw > 1e10 else raw, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(raw)


def post_to_row(item: dict) -> list:
    pid       = item.get("id") or item.get("shortCode") or item.get("postId") or ""
    image_url = (item.get("displayUrl") or item.get("imageUrl") or item.get("thumbnailUrl") or "")
    caption   = (item.get("caption") or item.get("text") or item.get("description") or "").strip()
    likes     = _num(item.get("likesCount") or item.get("likes") or 0)
    comments  = _num(item.get("commentsCount") or item.get("comments") or 0)
    views     = _num(item.get("videoViewCount") or item.get("views") or 0)
    account   = (item.get("ownerUsername") or item.get("username") or item.get("authorName") or "")
    pub_date  = _ts(item.get("timestamp") or item.get("takenAt") or item.get("createdAt"))
    add_date  = datetime.now().strftime("%d/%m/%Y %H:%M")
    link      = item.get("url") or item.get("postUrl") or ""

    return [pid, image_url, caption, likes, comments, views, account, pub_date, add_date, "", STATUS_PENDING, link]


def add_post(item: dict) -> bool:
    """מוסיף פוסט לגיליון. מחזיר False אם כבר קיים."""
    if not SHEETS_ID or not Path(CREDENTIALS_PATH).exists():
        raise EnvironmentError("Google Sheets לא מוגדר — ראה .env.example")

    ws  = _get_sheet()
    pid = item.get("id") or item.get("shortCode") or item.get("postId") or ""

    # בדוק אם כבר קיים
    if pid:
        col_a = ws.col_values(1)
        if pid in col_a:
            return False

    row = post_to_row(item)
    ws.append_row(row, value_input_option="USER_ENTERED")
    return True


def update_status(post_id: str, status: str):
    """מעדכן את עמודת הסטטוס לפי מזהה פוסט"""
    ws    = _get_sheet()
    col_a = ws.col_values(1)
    try:
        row_idx = col_a.index(post_id) + 1   # 1-based
        ws.update_cell(row_idx, 11, status)   # עמודה K = סטטוס
    except ValueError:
        pass


def get_pending_posts() -> list[dict]:
    """מחזיר את כל הפוסטים בסטטוס 'ממתין לעיבוד'"""
    ws   = _get_sheet()
    rows = ws.get_all_records()
    return [r for r in rows if r.get("סטטוס") == STATUS_PENDING]
