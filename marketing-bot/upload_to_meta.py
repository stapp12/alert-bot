"""
העלאת קריאייטיב וידאו ל-Meta Ads Manager
שימוש: python upload_to_meta.py <נתיב לקובץ וידאו> <טקסט מודעה>
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.adobjects.adcreative import AdCreative

load_dotenv()

ACCESS_TOKEN  = os.environ["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID = os.environ["AD_ACCOUNT_ID"]   # format: act_XXXXXXXXX
PAGE_ID       = os.environ["PAGE_ID"]


def init_api():
    FacebookAdsApi.init(access_token=ACCESS_TOKEN)


def upload_video(video_path: str) -> str:
    """מעלה את קובץ הוידאו ומחזיר video_id"""
    print(f"[Meta] מעלה וידאו: {video_path}")
    account = AdAccount(AD_ACCOUNT_ID)
    video = account.create_ad_video(
        fields=[],
        params={"filepath": video_path},
    )
    video_id = video["id"]
    print(f"[Meta] וידאו הועלה בהצלחה. מזהה: {video_id}")
    return video_id


def wait_for_video_ready(video_id: str, timeout: int = 120):
    """ממתין עד שהוידאו מוכן לשימוש במודעה"""
    print("[Meta] ממתין לעיבוד הוידאו...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        video = AdVideo(video_id)
        video.remote_read(fields=["status"])
        status = video.get("status", {}).get("processing_progress", 0)
        print(f"[Meta] התקדמות עיבוד: {status}%")
        if status >= 100:
            print("[Meta] הוידאו מוכן!")
            return
        time.sleep(5)
    raise TimeoutError("הוידאו לא סיים עיבוד בזמן הנדרש")


def create_ad_creative(video_id: str, ad_text: str) -> str:
    """יוצר Ad Creative ומחזיר creative_id"""
    print("[Meta] יוצר קריאייטיב מודעה...")
    account = AdAccount(AD_ACCOUNT_ID)
    creative = account.create_ad_creative(
        fields=[AdCreative.Field.id],
        params={
            "name": "מודעת וידאו אוטומטית",
            "object_story_spec": {
                "page_id": PAGE_ID,
                "video_data": {
                    "video_id": video_id,
                    "message": ad_text,
                    "call_to_action": {
                        "type": "LEARN_MORE",
                        "value": {"link": "https://www.facebook.com"},
                    },
                },
            },
        },
    )
    creative_id = creative[AdCreative.Field.id]
    print(f"[Meta] קריאייטיב נוצר. מזהה: {creative_id}")
    return creative_id


def upload_ad(video_path: str, ad_text: str) -> dict:
    """פונקציה ראשית — מעלה וידאו ויוצר קריאייטיב"""
    if not Path(video_path).exists():
        raise FileNotFoundError(f"קובץ הוידאו לא נמצא: {video_path}")

    init_api()
    video_id   = upload_video(video_path)
    wait_for_video_ready(video_id)
    creative_id = create_ad_creative(video_id, ad_text)

    return {"video_id": video_id, "creative_id": creative_id}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("שימוש: python upload_to_meta.py <נתיב וידאו> <טקסט מודעה>")
        sys.exit(1)

    result = upload_ad(sys.argv[1], sys.argv[2])
    print(f"\n✅ הושלם בהצלחה!")
    print(f"   video_id:    {result['video_id']}")
    print(f"   creative_id: {result['creative_id']}")
