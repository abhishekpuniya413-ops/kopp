import os
import asyncio
import logging
import threading
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Config ---
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
GROUP_ID = int(os.environ["GROUP_ID"])  # e.g. -1001234567890
REACTION_EMOJI = os.environ.get("REACTION_EMOJI", "🤝")
PORT = int(os.environ.get("PORT", 8080))

# --- Shared state ---
status = {
    "running": False,
    "logged_in_as": None,
    "reactions_sent": 0,
}

# --- aiohttp keep-alive (Render web service) ---
async def start_web_server():
    async def handle(request):
        return web.Response(text=str({
            "status": "ok" if status["running"] else "starting",
            "logged_in_as": status["logged_in_as"],
            "reactions_sent": status["reactions_sent"],
        }), content_type="application/json")

    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", lambda r: web.Response(text="ok"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

# --- Main ---
async def main():
    await start_web_server()

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    status["logged_in_as"] = f"{me.first_name} (@{me.username})"
    logger.info(f"Logged in as: {status['logged_in_as']}")

    await client.send_message(GROUP_ID, "hi 👋")
    logger.info("Sent 'hi' to the group")

    status["running"] = True

    @client.on(events.NewMessage(chats=GROUP_ID))
    async def handler(event):
        if event.message.out:
            return
        try:
            await client(SendReactionRequest(
                peer=GROUP_ID,
                msg_id=event.message.id,
                reaction=[ReactionEmoji(emoticon=REACTION_EMOJI)],
            ))
            status["reactions_sent"] += 1
            sender = await event.get_sender()
            name = getattr(sender, "first_name", "unknown")
            logger.info(
                f"Reacted {REACTION_EMOJI} to message from {name} "
                f"(id={event.message.id}) | total={status['reactions_sent']}"
            )
        except Exception as e:
            logger.warning(f"Could not react to message {event.message.id}: {e}")

    logger.info("Listening for new messages...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
    
