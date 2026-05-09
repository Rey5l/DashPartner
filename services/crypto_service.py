import os
import time
import aiohttp
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


class CryptoService:
    """Сервис для работы с CryptoBot API"""

    def __init__(self):
        self.token = os.getenv("CRYPTO_BOT_TOKEN", "")
        self.api_base = "https://pay.crypt.bot/api"

    def set_token(self, token: str):
        """Устанавливает токен CryptoBot"""
        self.token = token

    async def create_invoice(
        self,
        user_id: int,
        amount: float,
        description: str = "Пополнение баланса",
        payload_prefix: str = "topup",
        bot_username: str = None
    ) -> Optional[dict]:
        """
        Создает инвойс для пополнения баланса

        Args:
            user_id: ID пользователя
            amount: Сумма в USDT
            description: Описание платежа
            payload_prefix: Префикс для payload (topup, ad, etc)
            bot_username: Username бота для paid_btn_url

        Returns:
            dict с полями invoice_id и pay_url или None при ошибке
        """
        try:
            payload = {
                "asset": "USDT",
                "amount": str(amount),
                "description": description,
                "hidden_message": f"{payload_prefix}_{user_id}",
                "paid_btn_name": "openBot",
                "payload": f"{payload_prefix}_{user_id}_{int(time.time())}",
                "allow_comments": False,
                "allow_anonymous": False,
            }

            # Добавляем paid_btn_url если передан bot_username
            if bot_username:
                payload["paid_btn_url"] = f"https://t.me/{bot_username}"

            headers = {
                "Crypto-Pay-API-Token": self.token,
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/createInvoice",
                    json=payload,
                    headers=headers
                ) as response:
                    data = await response.json()

                    if data.get("ok"):
                        invoice = data["result"]
                        return {
                            "invoice_id": invoice["invoice_id"],
                            "pay_url": invoice["pay_url"]
                        }
                    else:
                        print(f"❌ Ошибка создания инвойса: {data}")
                        return None

        except Exception as e:
            print(f"❌ Ошибка create_invoice: {e}")
            return None

    async def check_invoice(self, invoice_id: str) -> Optional[dict]:
        """
        Проверяет статус инвойса

        Args:
            invoice_id: ID инвойса

        Returns:
            dict с информацией об инвойсе или None при ошибке
        """
        try:
            headers = {
                "Crypto-Pay-API-Token": self.token,
                "Content-Type": "application/json"
            }

            url = f"{self.api_base}/getInvoices?invoice_ids={invoice_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    data = await response.json()

                    if not data.get("ok"):
                        return None

                    items = data["result"].get("items", [])
                    if not items:
                        return None

                    return items[0]

        except Exception as e:
            print(f"❌ Ошибка check_invoice: {e}")
            return None

    async def create_check(self, amount: float, description: str = "Вывод средств") -> Tuple[bool, Optional[str]]:
        """
        Создает чек для вывода средств

        Args:
            amount: Сумма в USDT
            description: Описание чека

        Returns:
            Tuple (success, check_url)
        """
        try:
            if amount <= 0:
                return False, None

            payload = {
                "asset": "USDT",
                "amount": str(amount),
                "description": description,
            }

            headers = {
                "Crypto-Pay-API-Token": self.token,
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/createCheck",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    if response.status == 200:
                        data = await response.json()

                        if data.get('ok'):
                            check_url = data['result']['bot_check_url']
                            return True, check_url
                        else:
                            return False, None
                    else:
                        return False, None

        except Exception as e:
            print(f"❌ Ошибка create_check: {e}")
            return False, None

    async def get_balance(self) -> float:
        """
        Получает баланс кошелька CryptoBot

        Returns:
            Баланс в USDT
        """
        try:
            headers = {
                "Crypto-Pay-API-Token": self.token,
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base}/getBalance",
                    headers=headers
                ) as response:
                    data = await response.json()

                    if data.get("ok"):
                        balances = data["result"]
                        for balance in balances:
                            if balance["currency_code"] == "USDT":
                                return float(balance["available"])
                        return 0.0
                    else:
                        return 0.0

        except Exception as e:
            print(f"❌ Ошибка get_balance: {e}")
            return 0.0
