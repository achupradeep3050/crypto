import asyncio
from backend.telegram_bot import TelegramNotifier
from backend.config import settings

async def send_test():
    notifier = TelegramNotifier(settings.TELEGRAM_TOKEN, settings.TELEGRAM_CHAT_ID)
    await notifier.send_message("✅ *System Online*: Your Trading Bot is connected and running!")

if __name__ == "__main__":
    asyncio.run(send_test())
