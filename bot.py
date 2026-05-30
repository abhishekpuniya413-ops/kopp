from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio, os

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION = os.environ.get('SESSION_STRING')
BOT_USERNAME = 'MeChat'  # change to exact username

AUTO_MESSAGES = [
    "Hi!",
    "How are you?",
    "asl?",
]
FINAL_MESSAGE = "Hii Can you suggest some other bot to try besides InstantTalkBot?"

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

async def click_button_by_text(message, text):
    try:
        for i, row in enumerate(message.reply_markup.rows):
            for j, button in enumerate(row.buttons):
                if text.lower() in button.text.lower():
                    await message.click(i, j)
                    print(f"✅ Clicked: {button.text}")
                    return True
    except Exception as e:
        print(f"❌ Button error: {e}")
    return False

@client.on(events.NewMessage(chats=BOT_USERNAME))
async def handler(event):
    msg = event.message.text or ""
    print(f"BOT: {msg[:60]}")

    if "choose who you want to chat with" in msg.lower():
        print("🎲 Clicking Random...")
        await asyncio.sleep(1)
        await click_button_by_text(event.message, "Random")

    elif "found partner for you" in msg.lower():
        print("💬 Sending messages...")
        for text in AUTO_MESSAGES:
            await asyncio.sleep(3)
            await client.send_message(BOT_USERNAME, text)
        await asyncio.sleep(4)
        await client.send_message(BOT_USERNAME, FINAL_MESSAGE)
        await asyncio.sleep(3)
        await client.send_message(BOT_USERNAME, "End Chat")

    elif "are you sure you want to close" in msg.lower():
        print("🔴 Ending chat...")
        await asyncio.sleep(1)
        await click_button_by_text(event.message, "End Chat")

async def main():
    await client.start()
    print("🤖 Bot started!")
    await client.send_message(BOT_USERNAME, "/start")
    await client.run_until_disconnected()

asyncio.run(main())
