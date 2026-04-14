"""
עטיפה נקייה ל-Meta Business SDK
כל הלוגיקה של ה-API נמצאת כאן, ללא קוד בוט
"""

import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adsinsights import AdsInsights

load_dotenv()

ACCESS_TOKEN  = os.environ.get("META_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("AD_ACCOUNT_ID", "")
PAGE_ID       = os.environ.get("PAGE_ID", "")

OBJECTIVES = {
    "תנועה לאתר":      "OUTCOME_TRAFFIC",
    "מודעות למותג":    "OUTCOME_AWARENESS",
    "לידים":           "OUTCOME_LEADS",
    "מכירות":          "OUTCOME_SALES",
    "מעורבות":         "OUTCOME_ENGAGEMENT",
}

STATUS_EMOJI = {"ACTIVE": "🟢", "PAUSED": "🔴", "ARCHIVED": "⚫"}


@dataclass
class CampaignRow:
    id: str
    name: str
    status: str
    objective: str
    daily_budget: str


@dataclass
class AdSetRow:
    id: str
    name: str
    status: str
    campaign_id: str
    daily_budget: str


@dataclass
class AdRow:
    id: str
    name: str
    status: str
    adset_id: str


class MetaAPI:
    def __init__(self):
        FacebookAdsApi.init(access_token=ACCESS_TOKEN)
        self.account = AdAccount(AD_ACCOUNT_ID)

    # ── קמפיינים ────────────────────────────────────────────────────────────

    def get_campaigns(self) -> list[CampaignRow]:
        fields = [
            Campaign.Field.id,
            Campaign.Field.name,
            Campaign.Field.status,
            Campaign.Field.objective,
            Campaign.Field.daily_budget,
        ]
        rows = self.account.get_campaigns(fields=fields, params={"limit": 50})
        return [
            CampaignRow(
                id=r[Campaign.Field.id],
                name=r[Campaign.Field.name],
                status=r.get(Campaign.Field.status, "UNKNOWN"),
                objective=r.get(Campaign.Field.objective, ""),
                daily_budget=r.get(Campaign.Field.daily_budget, "0"),
            )
            for r in rows
        ]

    def create_campaign(self, name: str, objective_key: str, daily_budget_ils: float) -> CampaignRow:
        objective = OBJECTIVES.get(objective_key, "OUTCOME_TRAFFIC")
        result = self.account.create_campaign(
            fields=[Campaign.Field.id, Campaign.Field.name],
            params={
                "name": name,
                "objective": objective,
                "status": Campaign.Status.paused,
                "special_ad_categories": [],
                "daily_budget": int(daily_budget_ils * 100),  # אגורות
            },
        )
        return CampaignRow(
            id=result[Campaign.Field.id],
            name=result[Campaign.Field.name],
            status="PAUSED",
            objective=objective,
            daily_budget=str(int(daily_budget_ils * 100)),
        )

    def toggle_campaign(self, campaign_id: str, activate: bool) -> None:
        camp = Campaign(campaign_id)
        camp.api_update(params={
            "status": Campaign.Status.active if activate else Campaign.Status.paused
        })

    def delete_campaign(self, campaign_id: str) -> None:
        Campaign(campaign_id).api_delete()

    # ── קבוצות מודעות (Ad Sets) ─────────────────────────────────────────────

    def get_ad_sets(self, campaign_id: str | None = None) -> list[AdSetRow]:
        fields = [
            AdSet.Field.id,
            AdSet.Field.name,
            AdSet.Field.status,
            AdSet.Field.campaign_id,
            AdSet.Field.daily_budget,
        ]
        if campaign_id:
            camp = Campaign(campaign_id)
            rows = camp.get_ad_sets(fields=fields, params={"limit": 50})
        else:
            rows = self.account.get_ad_sets(fields=fields, params={"limit": 50})

        return [
            AdSetRow(
                id=r[AdSet.Field.id],
                name=r[AdSet.Field.name],
                status=r.get(AdSet.Field.status, "UNKNOWN"),
                campaign_id=r.get(AdSet.Field.campaign_id, ""),
                daily_budget=r.get(AdSet.Field.daily_budget, "0"),
            )
            for r in rows
        ]

    def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        daily_budget_ils: float,
        country: str = "IL",
    ) -> AdSetRow:
        result = self.account.create_ad_set(
            fields=[AdSet.Field.id, AdSet.Field.name],
            params={
                "name": name,
                "campaign_id": campaign_id,
                "status": AdSet.Status.paused,
                "daily_budget": int(daily_budget_ils * 100),
                "billing_event": AdSet.BillingEvent.impressions,
                "optimization_goal": AdSet.OptimizationGoal.reach,
                "targeting": {
                    "geo_locations": {"countries": [country]},
                    "age_min": 18,
                    "age_max": 65,
                },
            },
        )
        return AdSetRow(
            id=result[AdSet.Field.id],
            name=result[AdSet.Field.name],
            status="PAUSED",
            campaign_id=campaign_id,
            daily_budget=str(int(daily_budget_ils * 100)),
        )

    def toggle_ad_set(self, adset_id: str, activate: bool) -> None:
        adset = AdSet(adset_id)
        adset.api_update(params={
            "status": AdSet.Status.active if activate else AdSet.Status.paused
        })

    # ── מודעות (Ads) ─────────────────────────────────────────────────────────

    def get_ads(self, adset_id: str | None = None) -> list[AdRow]:
        fields = [Ad.Field.id, Ad.Field.name, Ad.Field.status, Ad.Field.adset_id]
        if adset_id:
            adset = AdSet(adset_id)
            rows = adset.get_ads(fields=fields, params={"limit": 50})
        else:
            rows = self.account.get_ads(fields=fields, params={"limit": 50})

        return [
            AdRow(
                id=r[Ad.Field.id],
                name=r[Ad.Field.name],
                status=r.get(Ad.Field.status, "UNKNOWN"),
                adset_id=r.get(Ad.Field.adset_id, ""),
            )
            for r in rows
        ]

    def toggle_ad(self, ad_id: str, activate: bool) -> None:
        ad = Ad(ad_id)
        ad.api_update(params={
            "status": Ad.Status.active if activate else Ad.Status.paused
        })

    # ── וידאו ─────────────────────────────────────────────────────────────────

    def upload_video(self, video_path: str) -> str:
        video = self.account.create_ad_video(
            fields=[],
            params={"filepath": video_path},
        )
        return video["id"]

    def wait_for_video_ready(self, video_id: str, timeout: int = 180) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            video = AdVideo(video_id)
            video.remote_read(fields=["status"])
            progress = video.get("status", {}).get("processing_progress", 0)
            if progress >= 100:
                return
            time.sleep(4)
        raise TimeoutError("הוידאו לא סיים עיבוד בזמן הנדרש")

    def create_ad_creative(self, video_id: str, ad_text: str, name: str = "קריאייטיב וידאו") -> str:
        creative = self.account.create_ad_creative(
            fields=[AdCreative.Field.id],
            params={
                "name": name,
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
        return creative[AdCreative.Field.id]

    def create_ad(self, adset_id: str, creative_id: str, name: str) -> str:
        ad = self.account.create_ad(
            fields=[Ad.Field.id],
            params={
                "name": name,
                "adset_id": adset_id,
                "creative": {"creative_id": creative_id},
                "status": Ad.Status.paused,
            },
        )
        return ad[Ad.Field.id]

    # ── סטטיסטיקות ────────────────────────────────────────────────────────────

    def get_account_insights(self, days: int = 7) -> dict:
        params = {
            "date_preset": "last_7d" if days == 7 else "last_30d",
            "level": "account",
        }
        fields = [
            AdsInsights.Field.spend,
            AdsInsights.Field.impressions,
            AdsInsights.Field.clicks,
            AdsInsights.Field.ctr,
            AdsInsights.Field.cpc,
            AdsInsights.Field.reach,
        ]
        rows = self.account.get_insights(fields=fields, params=params)
        if not rows:
            return {}
        r = rows[0]
        return {
            "spend":       r.get("spend", "0"),
            "impressions": r.get("impressions", "0"),
            "clicks":      r.get("clicks", "0"),
            "ctr":         r.get("ctr", "0"),
            "cpc":         r.get("cpc", "0"),
            "reach":       r.get("reach", "0"),
        }
