from aiohttp import web

from services.partner_store import PartnerStore
from services.task_service import get_aggregated_tasks
from services.tg_rass_service import tgrass_check_subscription, tgrass_get_tasks_by_user


def _json_error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"ok": False, "error": message}, status=status)


async def _read_json(request: web.Request) -> dict | None:
    try:
        payload = await request.json()
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


async def health(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]
    stats = await store.build_stats()
    return web.json_response({"ok": True, "service": "dashpartner-api", "stats": stats})


async def get_tasks(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]

    try:
        user_id = int(request.query.get("user_id", "0"))
    except ValueError:
        return _json_error("user_id must be integer")

    language_code = request.query.get("language_code", "ru")
    target_type = request.query.get("target_type")
    try:
        limit = int(request.query.get("limit", "15"))
    except ValueError:
        return _json_error("limit must be integer")

    tasks = await get_aggregated_tasks(
        user_id=user_id,
        language_code=language_code,
        store=store,
        target_type=target_type,
        limit=limit,
    )

    return web.json_response(
        {
            "ok": True,
            "count": len(tasks),
            "tasks": tasks,
        }
    )


async def get_offers(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]
    offers = await store.list_offers(
        target_type=request.query.get("target_type"),
        active_only=request.query.get("active_only") == "true",
    )
    return web.json_response({"ok": True, "offers": offers})


async def get_offer(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]
    offer = await store.get_offer(request.match_info["offer_id"])
    if offer is None:
        return _json_error("offer not found", status=404)

    return web.json_response({"ok": True, "offer": offer})


async def create_offer(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]
    payload = await _read_json(request)
    if payload is None:
        return _json_error("request body must be valid JSON object")

    required_fields = ("title", "target_type", "destination_url")
    for field in required_fields:
        if not payload.get(field):
            return _json_error(f"{field} is required")

    if payload["target_type"] not in {"channel", "bot"}:
        return _json_error("target_type must be channel or bot")

    offer = await store.create_offer(payload)
    return web.json_response({"ok": True, "offer": offer}, status=201)


async def create_publisher(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]
    payload = await _read_json(request)
    if payload is None:
        return _json_error("request body must be valid JSON object")

    required_fields = ("name", "telegram_type", "telegram_handle")
    for field in required_fields:
        if not payload.get(field):
            return _json_error(f"{field} is required")

    if payload["telegram_type"] not in {"channel", "bot", "chat"}:
        return _json_error("telegram_type must be channel, bot or chat")

    publisher = await store.register_publisher(payload)
    return web.json_response({"ok": True, "publisher": publisher}, status=201)


async def create_placement(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]
    payload = await _read_json(request)
    if payload is None:
        return _json_error("request body must be valid JSON object")

    if not payload.get("publisher_id"):
        return _json_error("publisher_id is required")

    placement = await store.create_placement(request.match_info["offer_id"], payload)
    if placement is None:
        return _json_error("offer or publisher not found", status=404)

    return web.json_response({"ok": True, "placement": placement}, status=201)


async def create_conversion(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]
    payload = await _read_json(request)
    if payload is None:
        return _json_error("request body must be valid JSON object")

    required_fields = ("offer_id", "placement_id", "user_id")
    for field in required_fields:
        if not payload.get(field):
            return _json_error(f"{field} is required")

    conversion = await store.create_conversion(payload)
    if conversion is None:
        return _json_error("offer or placement not found", status=404)

    return web.json_response({"ok": True, "conversion": conversion}, status=201)


async def get_conversions(request: web.Request) -> web.Response:
    store: PartnerStore = request.app["partner_store"]
    conversions = await store.list_conversions(
        offer_id=request.query.get("offer_id"),
        publisher_id=request.query.get("publisher_id"),
    )
    return web.json_response({"ok": True, "conversions": conversions})


async def tgrass_offers(request: web.Request) -> web.Response:
    payload = await _read_json(request)
    if payload is None:
        return _json_error("request body must be valid JSON object")

    if payload.get("tg_user_id") is None:
        return _json_error("tg_user_id is required")

    try:
        tg_user_id = int(payload["tg_user_id"])
    except (TypeError, ValueError):
        return _json_error("tg_user_id must be integer")

    result = await tgrass_get_tasks_by_user(
        tg_user_id=tg_user_id,
        tg_login=payload.get("tg_login"),
        language_code=payload.get("lang"),
        is_premium=payload.get("is_premium"),
        limit=int(payload.get("limit", 15)),
    )
    return web.json_response({"ok": True, **result}, status=200)


async def tgrass_check(request: web.Request) -> web.Response:
    payload = await _read_json(request)
    if payload is None:
        return _json_error("request body must be valid JSON object")

    required_fields = ("tg_user_id", "offer_id")
    for field in required_fields:
        if payload.get(field) is None:
            return _json_error(f"{field} is required")

    try:
        tg_user_id = int(payload["tg_user_id"])
        offer_id = int(payload["offer_id"])
    except (TypeError, ValueError):
        return _json_error("tg_user_id and offer_id must be integer")

    result = await tgrass_check_subscription(tg_user_id=tg_user_id, offer_id=offer_id)
    return web.json_response({"ok": True, **result}, status=200)


def setup_api_routes(app: web.Application, store: PartnerStore) -> None:
    app["partner_store"] = store
    app.router.add_get("/health", health)
    app.router.add_get("/api/tasks", get_tasks)
    app.router.add_get("/api/offers", get_offers)
    app.router.add_get("/api/offers/{offer_id}", get_offer)
    app.router.add_get("/api/conversions", get_conversions)
    app.router.add_post("/api/offers", create_offer)
    app.router.add_post("/api/publishers", create_publisher)
    app.router.add_post("/api/offers/{offer_id}/publishers", create_placement)
    app.router.add_post("/api/conversions", create_conversion)
    app.router.add_post("/api/tgrass/offers", tgrass_offers)
    app.router.add_post("/api/tgrass/check", tgrass_check)
