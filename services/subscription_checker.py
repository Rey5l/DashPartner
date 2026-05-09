import asyncio
from typing import Callable

from services.flyer_service import flyer_check_task
from services.tg_rass_service import tgrass_check_subscription


class SubscriptionChecker:
    def __init__(self):
        self._active_checks = {}
        self._check_interval = 10

    async def start_checking(
        self,
        user_id: int,
        language_code: str | None,
        tasks: list[dict],
        on_complete: Callable,
    ):
        check_key = f"{user_id}"

        if check_key in self._active_checks:
            self._active_checks[check_key]["cancel"] = True
            await asyncio.sleep(0.5)

        self._active_checks[check_key] = {"cancel": False}

        try:
            await self._check_loop(user_id, language_code, tasks, on_complete, check_key)
        finally:
            if check_key in self._active_checks:
                del self._active_checks[check_key]

    async def _check_loop(
        self,
        user_id: int,
        language_code: str | None,
        tasks: list[dict],
        on_complete: Callable,
        check_key: str,
    ):
        remaining_tasks = tasks.copy()
        max_iterations = 60

        for iteration in range(max_iterations):
            if self._active_checks.get(check_key, {}).get("cancel"):
                print(f"[CHECKER] check cancelled for user_id={user_id}")
                break

            if not remaining_tasks:
                print(f"[CHECKER] all tasks completed for user_id={user_id}")
                await on_complete(user_id, language_code, [])
                break

            completed_tasks = []

            for task in remaining_tasks:
                if self._active_checks.get(check_key, {}).get("cancel"):
                    break

                source = task.get("source")
                is_completed = False

                if source == "tgrass":
                    offer_id = task.get("offer_id")
                    if offer_id:
                        result = await tgrass_check_subscription(
                            tg_user_id=user_id,
                            offer_id=int(offer_id),
                        )
                        is_completed = result.get("status") == "subscribed"
                        print(
                            f"[CHECKER] tgrass check: user_id={user_id}, offer_id={offer_id}, "
                            f"completed={is_completed}"
                        )

                elif source == "flyer":
                    signature = task.get("signature")
                    if signature:
                        result = await flyer_check_task(signature=signature, user_id=user_id)
                        is_completed = result is True
                        print(
                            f"[CHECKER] flyer check: user_id={user_id}, signature={signature}, "
                            f"completed={is_completed}"
                        )

                if is_completed:
                    completed_tasks.append(task)

            for completed in completed_tasks:
                remaining_tasks.remove(completed)

            if completed_tasks:
                print(
                    f"[CHECKER] progress update for user_id={user_id}: "
                    f"completed={len(completed_tasks)}, remaining={len(remaining_tasks)}"
                )
                await on_complete(user_id, language_code, remaining_tasks)

            if not remaining_tasks:
                break

            await asyncio.sleep(self._check_interval)

        if remaining_tasks:
            print(
                f"[CHECKER] check timeout for user_id={user_id}, "
                f"remaining_tasks={len(remaining_tasks)}"
            )

    def stop_checking(self, user_id: int):
        check_key = f"{user_id}"
        if check_key in self._active_checks:
            self._active_checks[check_key]["cancel"] = True
            print(f"[CHECKER] stop requested for user_id={user_id}")


subscription_checker = SubscriptionChecker()
