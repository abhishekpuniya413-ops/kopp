import os
import asyncio
import logging
import threading

# Fix for Python 3.14 — must create event loop before pyrogram imports
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from flask import Flask, jsonify
from pyrogram import Client, filters

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
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
    "group_id": GROUP_ID,
    "reactions_sent": 0,
}

# --- Flask (keeps Render web service alive) ---
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return jsonify({
        "status": "ok" if status["running"] else "starting",
        "logged_in_as": status["logged_in_as"],
        "group_id": status["group_id"],
        "reactions_sent": status["reactions_sent"],
    })

@flask_app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

# --- Pyrogram userbot ---
app = Client(
    name="userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

@app.on_message(filters.chat(GROUP_ID) & ~filters.me)
async def react_handler(client, message):
    try:
        await client.send_reaction(
            chat_id=GROUP_ID,
            message_id=message.id,
            emoji=REACTION_EMOJI,
        )
        status["reactions_sent"] += 1
        name = message.from_user.first_name if message.from_user else "unknown"
        logger.info(
            f"Reacted {REACTION_EMOJI} to message from {name} "
            f"(id={message.id}) | total={status['reactions_sent']}"
        )
    except Exception as e:
        logger.warning(f"Could not react to message {message.id}: {e}")

async def main():
    async with app:
        me = await app.get_me()
        status["logged_in_as"] = f"{me.first_name} (@{me.username})"
        logger.info(f"Logged in as: {status['logged_in_as']}")

        await app.send_message(GROUP_ID, "hi 👋")
        logger.info("Sent 'hi' to the group")

        status["running"] = True
        logger.info("Listening for new messages...")
        await asyncio.get_event_loop().create_future()  # run forever

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Web server started on port {PORT}")

    loop.run_until_complete(main())
    
