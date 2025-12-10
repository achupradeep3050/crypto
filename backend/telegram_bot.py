from telegram import Bot
from telegram.error import TelegramError
import asyncio
import logging

logger = logging.getLogger("TelegramBot")

class TelegramNotifier:
    def __init__(self, token, chat_id=None):
        self.token = token
        self.chat_id = chat_id
        if token:
            self.bot = Bot(token=token)
        else:
            self.bot = None

    async def send_message(self, message):
        if not self.bot or not self.chat_id:
            logger.warning("Telegram Bot not configured (Token or ChatID missing)")
            return

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except TelegramError as e:
            logger.error(f"Telegram Error: {e}")

# We will initialize this with settings in main or strategy engine
notifier = None
