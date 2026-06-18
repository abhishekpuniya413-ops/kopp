import os
import asyncio
import logging
import threading
from flask import Flask, jsonify
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji
from telethon.sessions import StringSession

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Config ---
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
GROUP = os.environ["GROUP_USERNAME"]  # username e.g. "mygroup" or numeric "-1001234567890"
REACTION_EMOJI = os.environ.get("REACTION_EMOJI", "🤝")
PORT = int(os.environ.get("PORT", 8080))

try:
    GROUP_ID = int(GROUP)
except ValueError:
    GROUP_ID = GROUP

# --- Shared state for health endpoint ---
status = {
    "running": False,
    "logged_in_as": None,
    "group": None,
    "reactions_sent": 0,
}

# --- Flask web server (keeps Render web service alive) ---
app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({
        "status": "ok" if status["running"] else "starting",
        "logged_in_as": status["logged_in_as"],
        "group": status["group"],
        "reactions_sent": status["reactions_sent"],
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# --- Telegram userbot ---
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def main():
    await client.start()
    me = await client.get_me()
    status["logged_in_as"] = f"{me.first_name} (@{me.username})"
    logger.info(f"Logged in as: {status['logged_in_as']}")

    group_entity = await client.get_entity(GROUP_ID)
    status["group"] = group_entity.title
    logger.info(f"Target group: {group_entity.title}")

    await client.send_message(group_entity, "hi 👋")
    logger.info("Sent 'hi' to the group")

    status["running"] = True

    @client.on(events.NewMessage(chats=group_entity))
    async def handler(event):
        if event.message.out:
            return
        try:
            await client(SendReactionRequest(
                peer=group_entity,
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
    # Start Flask in a background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Web server started on port {PORT}")

    # Run the Telegram client on the main thread
    asyncio.run(main())
    
