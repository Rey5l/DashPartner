import asyncio

from services.flyer_service import flyer_get_tasks
from services.partner_store import PartnerStore
from services.tg_rass_service import tg_rass_get_tasks


def _normalize_flyer_task(task: dict) -> dict | None:
    links = task.get("links") or []
    url = links[0] if links else None
    if not url:
        return None

    return {
        "id": str(task.get("signature") or url),
        "source": "flyer",
        "title": task.get("task") or "Открыть задание",
        "description": task.get("description", ""),
        "url": url,
        "target_type": task.get("target_type", "channel"),
        "reward": task.get("price", 0),
        "currency": task.get("currency", "RUB"),
        "signature": task.get("signature"),
        "raw": task,
    }


def _normalize_local_offer(offer: dict) -> dict:
    return {
        "id": offer["id"],
        "source": "local",
        "title": offer["title"],
        "description": offer.get("description", ""),
        "url": offer["destination_url"],
        "target_type": offer["target_type"],
        "reward": offer["reward_per_action"],
        "currency": offer.get("currency", "RUB"),
        "signature": None,
        "raw": offer,
    }


async def get_local_offer_tasks(store: PartnerStore, target_type: str | None = None) -> list[dict]:
    offers = await store.list_offers(target_type=target_type, active_only=True)
    print(
        f"[TASKS] loaded local offers: target_type={target_type}, count={len(offers)}"
    )
    return [_normalize_local_offer(offer) for offer in offers]


async def get_aggregated_tasks(
    user_id: int,
    language_code: str | None,
    store: PartnerStore | None = None,
    target_type: str | None = None,
    limit: int = 15,
) -> list[dict]:
    partner_store = store or PartnerStore()
    print(
        f"[TASKS] aggregating tasks: user_id={user_id}, language_code={language_code}, "
        f"target_type={target_type}, limit={limit}"
    )

    flyer_future = flyer_get_tasks(user_id=user_id, language_code=language_code, limit=limit)
    tg_rass_future = tg_rass_get_tasks(user_id=user_id, language_code=language_code, limit=limit)
    local_future = get_local_offer_tasks(store=partner_store, target_type=target_type)

    flyer_tasks, tg_rass_tasks, local_tasks = await asyncio.gather(
        flyer_future,
        tg_rass_future,
        local_future,
    )

    normalized_flyer = [task for task in (_normalize_flyer_task(item) for item in flyer_tasks) if task]
    print(
        f"[TASKS] source counts for user_id={user_id}: "
        f"flyer_raw={len(flyer_tasks)}, flyer_normalized={len(normalized_flyer)}, "
        f"tgrass={len(tg_rass_tasks)}, local={len(local_tasks)}"
    )
    tasks = normalized_flyer + tg_rass_tasks + local_tasks

    if target_type:
        tasks = [task for task in tasks if task.get("target_type") == target_type]
        print(
            f"[TASKS] filtered by target_type for user_id={user_id}: "
            f"target_type={target_type}, count={len(tasks)}"
        )

    limited_tasks = tasks[:limit]
    print(
        f"[TASKS] final aggregated tasks for user_id={user_id}: count={len(limited_tasks)}, "
        f"sources={[task.get('source') for task in limited_tasks]}"
    )
    return limited_tasks
