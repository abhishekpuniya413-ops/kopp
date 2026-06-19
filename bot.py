import os
import asyncio
import logging
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji, User

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Config ---
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
GROUP_ID = int(os.environ["GROUP_ID"])
REACTION_EMOJI = os.environ.get("REACTION_EMOJI", "🤝")
AUTO_REPLY = os.environ.get("AUTO_REPLY", "hi, how are you? 👋")
PORT = int(os.environ.get("PORT", 8080))

# --- Shared state ---
status = {
    "running": False,
    "logged_in_as": None,
    "reactions_sent": 0,
    "auto_replies_sent": 0,
}

# --- Web server ---
async def start_web_server():
    async def handle(request):
        return web.Response(text=str(status), content_type="application/json")

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
    my_id = me.id
    status["logged_in_as"] = f"{me.first_name} (@{me.username})"
    logger.info(f"Logged in as: {status['logged_in_as']}")

    # Send "hi" on startup — skip silently if slow mode is active
    try:
        await client.send_message(GROUP_ID, "hi 👋")
        logger.info("Sent 'hi' to the group")
    except Exception as e:
        logger.warning(f"Could not send greeting (slow mode?): {e}")

    status["running"] = True

    # --- React to every message in the group ---
    @client.on(events.NewMessage(chats=GROUP_ID))
    async def group_handler(event):
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

    # --- Auto-reply to non-contacts who DM you (once per person) ---
    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def dm_handler(event):
        sender = await event.get_sender()

        if not isinstance(sender, User):
            return
        if sender.id == my_id:
            return

        # Skip contacts
        if getattr(sender, "contact", False):
            logger.info(f"DM from contact {sender.first_name} — skipping.")
            return

        # Skip if already replied before
        async for _ in client.iter_messages(event.chat_id, from_user=my_id, limit=1):
            logger.info(f"Already messaged {sender.first_name} before — skipping.")
            return

        await event.reply(AUTO_REPLY)
        status["auto_replies_sent"] += 1
        logger.info(
            f"Auto-replied to {sender.first_name} (@{sender.username}) "
            f"| total={status['auto_replies_sent']}"
        )

    logger.info("Listening for messages...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
