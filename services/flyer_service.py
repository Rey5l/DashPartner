import os

from dotenv import load_dotenv
from flyerapi import Flyer

load_dotenv()

FLYER_API_KEY = os.getenv("FLYER_API_KEY")
flyer = Flyer(key=FLYER_API_KEY, debug=True) if FLYER_API_KEY else None


async def flyer_get_tasks(user_id, language_code, limit=15):
    if flyer is None:
        return []

    try:
        tasks = await flyer.get_tasks(
            user_id=user_id,
            language_code=language_code,
            limit=limit,
        )

        if tasks:
            print(f"✅ Flyer вернул {len(tasks)} заданий для пользователя {user_id}")

        return tasks or []
    except Exception as error:
        print(f"❌ Flyer get_tasks error: {error}")
        return []


async def flyer_check_task(signature, user_id=None):
    if flyer is None:
        return None

    try:
        status = await flyer.check_task(
            user_id=user_id,
            signature=signature,
        )
        print(f"🔍 Flyer check_task result: {status}")
        return status
    except Exception as error:
        print(f"❌ Flyer check_task error: {error}")
        return None
