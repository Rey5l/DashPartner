import asyncio
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import PARTNER_BOT_USERNAME, PARTNER_STORE_PATH


class PartnerStore:
    def __init__(self, file_path: str = PARTNER_STORE_PATH):
        self.file_path = Path(file_path)
        self._lock = asyncio.Lock()
        self._bootstrap()

    def _bootstrap(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.file_path.exists():
            self._write_data(
                {
                    "offers": [],
                    "publishers": [],
                    "placements": [],
                    "conversions": [],
                }
            )

    def _read_data(self) -> dict:
        with self.file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write_data(self, data: dict) -> None:
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def list_offers(self, target_type: str | None = None, active_only: bool = False) -> list[dict]:
        async with self._lock:
            offers = deepcopy(self._read_data()["offers"])

        if target_type:
            offers = [offer for offer in offers if offer.get("target_type") == target_type]

        if active_only:
            offers = [offer for offer in offers if offer.get("status") == "active"]

        return offers

    async def get_offer(self, offer_id: str) -> dict | None:
        async with self._lock:
            offers = self._read_data()["offers"]

        for offer in offers:
            if offer["id"] == offer_id:
                return deepcopy(offer)

        return None

    async def create_offer(self, payload: dict) -> dict:
        offer = {
            "id": uuid4().hex,
            "title": payload["title"],
            "description": payload.get("description", ""),
            "target_type": payload["target_type"],
            "destination_url": payload["destination_url"],
            "reward_per_action": float(payload.get("reward_per_action", 0)),
            "currency": payload.get("currency", "RUB"),
            "verification_mode": payload.get("verification_mode", "manual"),
            "required_action": payload.get("required_action", "subscribe"),
            "status": payload.get("status", "active"),
            "advertiser_id": payload.get("advertiser_id"),
            "source": "local",
            "created_at": self._now(),
        }

        async with self._lock:
            data = self._read_data()
            data["offers"].append(offer)
            self._write_data(data)

        return deepcopy(offer)

    async def register_publisher(self, payload: dict) -> dict:
        publisher = {
            "id": uuid4().hex,
            "name": payload["name"],
            "telegram_type": payload["telegram_type"],
            "telegram_handle": payload["telegram_handle"],
            "telegram_url": payload.get("telegram_url"),
            "status": payload.get("status", "active"),
            "created_at": self._now(),
        }

        async with self._lock:
            data = self._read_data()
            data["publishers"].append(publisher)
            self._write_data(data)

        return deepcopy(publisher)

    async def create_placement(self, offer_id: str, payload: dict) -> dict | None:
        async with self._lock:
            data = self._read_data()
            offer = next((item for item in data["offers"] if item["id"] == offer_id), None)
            publisher = next(
                (item for item in data["publishers"] if item["id"] == payload["publisher_id"]),
                None,
            )
            if offer is None or publisher is None:
                return None

            placement = {
                "id": uuid4().hex,
                "offer_id": offer_id,
                "publisher_id": payload["publisher_id"],
                "invite_link": payload.get("invite_link", offer["destination_url"]),
                "deeplink_token": uuid4().hex[:12],
                "status": payload.get("status", "active"),
                "created_at": self._now(),
            }

            if PARTNER_BOT_USERNAME:
                placement["deeplink_url"] = (
                    f"https://t.me/{PARTNER_BOT_USERNAME}"
                    f"?start=offer_{offer_id}_pub_{publisher['id']}_pl_{placement['id']}"
                )
            else:
                placement["deeplink_url"] = placement["invite_link"]

            data["placements"].append(placement)
            self._write_data(data)

        return deepcopy(placement)

    async def list_conversions(
        self,
        offer_id: str | None = None,
        publisher_id: str | None = None,
    ) -> list[dict]:
        async with self._lock:
            conversions = deepcopy(self._read_data()["conversions"])

        if offer_id:
            conversions = [item for item in conversions if item["offer_id"] == offer_id]

        if publisher_id:
            conversions = [item for item in conversions if item["publisher_id"] == publisher_id]

        return conversions

    async def create_conversion(self, payload: dict) -> dict | None:
        async with self._lock:
            data = self._read_data()
            offer = next((item for item in data["offers"] if item["id"] == payload["offer_id"]), None)
            if offer is None:
                return None

            placement = next(
                (item for item in data["placements"] if item["id"] == payload["placement_id"]),
                None,
            )
            if placement is None:
                return None

            existing = next(
                (
                    item
                    for item in data["conversions"]
                    if item["offer_id"] == payload["offer_id"]
                    and item["placement_id"] == payload["placement_id"]
                    and str(item["user_id"]) == str(payload["user_id"])
                ),
                None,
            )
            if existing is not None:
                return deepcopy(existing)

            conversion = {
                "id": uuid4().hex,
                "offer_id": payload["offer_id"],
                "placement_id": payload["placement_id"],
                "publisher_id": placement["publisher_id"],
                "user_id": str(payload["user_id"]),
                "action_type": payload.get("action_type", offer.get("required_action", "subscribe")),
                "proof": payload.get("proof"),
                "status": "approved" if offer.get("verification_mode") == "auto" else "pending",
                "payout": offer["reward_per_action"],
                "currency": offer.get("currency", "RUB"),
                "created_at": self._now(),
            }

            data["conversions"].append(conversion)
            self._write_data(data)

        return deepcopy(conversion)

    async def build_stats(self) -> dict:
        async with self._lock:
            data = deepcopy(self._read_data())

        approved = [item for item in data["conversions"] if item["status"] == "approved"]
        pending = [item for item in data["conversions"] if item["status"] == "pending"]

        return {
            "offers": len(data["offers"]),
            "publishers": len(data["publishers"]),
            "placements": len(data["placements"]),
            "conversions_total": len(data["conversions"]),
            "conversions_pending": len(pending),
            "conversions_approved": len(approved),
            "approved_payout_total": round(sum(item["payout"] for item in approved), 2),
        }
