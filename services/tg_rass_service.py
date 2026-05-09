from typing import Any

from aiohttp import ClientSession, ClientTimeout

from config import TGRASS_AUTH_KEY, TGRASS_CHECK_URL, TGRASS_OFFERS_URL, load_tg_rass_demo_tasks


def _extract_records(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("tasks", "offers", "results", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []


def _normalize_record(record: dict) -> dict | None:
    url = record.get("url") or record.get("link") or record.get("deep_link")
    if not url:
        return None

    offer_id = record.get("offer_id") or record.get("id")

    return {
        "id": str(offer_id or record.get("signature") or url),
        "offer_id": offer_id,
        "source": "tgrass",
        "title": record.get("title") or record.get("task") or record.get("name") or "Tgrass task",
        "description": record.get("description", ""),
        "url": url,
        "target_type": record.get("target_type") or record.get("type") or "channel",
        "reward": record.get("reward") or record.get("price") or 0,
        "currency": record.get("currency", "RUB"),
        "signature": record.get("signature"),
        "raw": record,
    }


async def tg_rass_get_tasks(user_id: int, language_code: str | None, limit: int = 15) -> list[dict]:
    if not TGRASS_AUTH_KEY:
        demo_tasks = load_tg_rass_demo_tasks()
        print(
            f"[TGRASS] auth key is not configured, using demo tasks for user_id={user_id}, "
            f"language_code={language_code}, demo_count={len(demo_tasks)}"
        )
        return [task for task in (_normalize_record(item) for item in demo_tasks[:limit]) if task]

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Auth": TGRASS_AUTH_KEY,
    }
    payload = {
        "tg_user_id": int(user_id),
        "tg_login": None,
        "lang": language_code or "ru",
        "is_premium": False,
    }
    print(f"[TGRASS] requesting offers: url={TGRASS_OFFERS_URL}, payload={payload}")

    timeout = ClientTimeout(total=10)

    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.post(TGRASS_OFFERS_URL, json=payload, headers=headers, ssl=False) as response:
                if response.status >= 400:
                    print(f"[TGRASS] offers request failed: http_status={response.status}")
                    return []

                payload = await response.json(content_type=None)
    except Exception as error:
        print(f"❌ Tgrass get_tasks error: {error}")
        return []

    print(f"[TGRASS] offers response for user_id={user_id}: {payload}")

    if payload.get("status") == "ok":
        print(f"[TGRASS] user_id={user_id} has no pending offers")
        return []

    normalized_tasks = [task for task in (_normalize_record(item) for item in _extract_records(payload)) if task][:limit]
    print(f"[TGRASS] normalized offers for user_id={user_id}: count={len(normalized_tasks)}")
    return normalized_tasks


async def tgrass_get_tasks_by_user(
    tg_user_id: int,
    tg_login: str | None = None,
    language_code: str | None = None,
    is_premium: bool | None = None,
    limit: int = 15,
) -> dict:
    if not TGRASS_AUTH_KEY:
        tasks = await tg_rass_get_tasks(tg_user_id, language_code, limit=limit)
        print(f"[TGRASS] get_tasks_by_user fallback: user_id={tg_user_id}, count={len(tasks)}")
        return {"status": "not_ok" if tasks else "ok", "offers": tasks}

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Auth": TGRASS_AUTH_KEY,
    }
    payload = {
        "tg_user_id": int(tg_user_id),
        "tg_login": tg_login,
        "lang": language_code or "ru",
        "is_premium": bool(is_premium) if is_premium is not None else False,
    }
    print(f"[TGRASS] direct offers request: url={TGRASS_OFFERS_URL}, payload={payload}")

    timeout = ClientTimeout(total=10)

    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.post(TGRASS_OFFERS_URL, json=payload, headers=headers, ssl=False) as response:
                response_payload = await response.json(content_type=None)
                print(
                    f"[TGRASS] direct offers response: user_id={tg_user_id}, "
                    f"http_status={response.status}, payload={response_payload}"
                )
                return {
                    "http_status": response.status,
                    "status": response_payload.get("status"),
                    "offers": [
                        task
                        for task in (_normalize_record(item) for item in _extract_records(response_payload))
                        if task
                    ][:limit],
                    "raw": response_payload,
                }
    except Exception as error:
        print(f"❌ Tgrass offers error: {error}")
        return {"http_status": 500, "status": "error", "offers": [], "raw": {"error": str(error)}}


async def tgrass_check_subscription(tg_user_id: int, offer_id: int) -> dict:
    if not TGRASS_AUTH_KEY:
        print(f"[TGRASS] check skipped, auth key is not configured: user_id={tg_user_id}, offer_id={offer_id}")
        return {"http_status": 200, "status": "not_configured"}

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Auth": TGRASS_AUTH_KEY,
    }
    payload = {
        "tg_user_id": int(tg_user_id),
        "offer_id": int(offer_id),
    }
    print(f"[TGRASS] checking subscription: url={TGRASS_CHECK_URL}, payload={payload}")

    timeout = ClientTimeout(total=10)

    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.post(TGRASS_CHECK_URL, json=payload, headers=headers, ssl=False) as response:
                response_payload = await response.json(content_type=None)
                print(
                    f"[TGRASS] check response: user_id={tg_user_id}, offer_id={offer_id}, "
                    f"http_status={response.status}, payload={response_payload}"
                )
                return {
                    "http_status": response.status,
                    "status": response_payload.get("status"),
                    "raw": response_payload,
                }
    except Exception as error:
        print(f"❌ Tgrass check error: {error}")
        return {"http_status": 500, "status": "error", "raw": {"error": str(error)}}
