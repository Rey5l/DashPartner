import aiohttp
from typing import Optional


class CurrencyConverter:
    """Сервис для конвертации валют"""

    # Фиксированный курс как fallback (можно обновлять вручную)
    FALLBACK_RATE = 92.0  # 1 USDT = 92 RUB

    @staticmethod
    async def get_usdt_rub_rate() -> float:
        """
        Получает актуальный курс USDT/RUB

        Returns:
            Курс USDT к RUB (например, 92.5 означает 1 USDT = 92.5 RUB)
        """
        try:
            # Пробуем получить курс с API
            async with aiohttp.ClientSession() as session:
                # Используем публичный API для получения курса
                async with session.get(
                    "https://api.exchangerate-api.com/v4/latest/USD",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        rub_rate = data.get("rates", {}).get("RUB")
                        if rub_rate:
                            return float(rub_rate)
        except Exception as e:
            print(f"⚠️ Ошибка получения курса валют: {e}")

        # Возвращаем фиксированный курс если API недоступен
        return CurrencyConverter.FALLBACK_RATE

    @staticmethod
    async def rub_to_usdt(rub_amount: float) -> float:
        """
        Конвертирует рубли в USDT

        Args:
            rub_amount: Сумма в рублях

        Returns:
            Сумма в USDT
        """
        rate = await CurrencyConverter.get_usdt_rub_rate()
        usdt_amount = rub_amount / rate
        return round(usdt_amount, 2)

    @staticmethod
    async def usdt_to_rub(usdt_amount: float) -> float:
        """
        Конвертирует USDT в рубли

        Args:
            usdt_amount: Сумма в USDT

        Returns:
            Сумма в рублях
        """
        rate = await CurrencyConverter.get_usdt_rub_rate()
        rub_amount = usdt_amount * rate
        return round(rub_amount, 2)
