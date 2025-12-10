import asyncio
from telegram import Bot
from backend.config import settings

async def get_chat_id():
    token = settings.TELEGRAM_TOKEN
    if not token:
        print("No Token found in config.")
        return

    bot = Bot(token=token)
    try:
        updates = await bot.get_updates()
        if not updates:
            print("No updates found. Please send a message '/start' to your bot first!")
            return

        last_update = updates[-1]
        chat_id = last_update.message.chat.id
        username = last_update.message.chat.username
        
        print(f"Latest Message from: @{username}")
        print(f"Chat ID: {chat_id}")
        print("\nPlease update TELEGRAM_CHAT_ID in backend/config.py with this ID.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_chat_id())
