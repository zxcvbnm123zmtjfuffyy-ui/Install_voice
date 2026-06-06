# self-bot.py
# Discord Voice Presence Tool - 24/7
# Supports DAVE protocol (March 2026+)
# Library: discord.py-self[voice]

import asyncio
import logging
import os
import sys
from threading import Thread

import discord
from flask import Flask, jsonify

# -------------------------------
# Logging Setup
# -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# -------------------------------
# Read configuration from environment
# -------------------------------
TOKEN       = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID  = os.environ.get("CHANNEL_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # اختياري

if not TOKEN:
    log.error("❌ DISCORD_TOKEN not set.")
    sys.exit(1)
if not CHANNEL_ID:
    log.error("❌ CHANNEL_ID not set.")
    sys.exit(1)

try:
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    log.error("❌ CHANNEL_ID must be a valid integer.")
    sys.exit(1)

# -------------------------------
# Global State
# -------------------------------
bot_status = {
    "in_voice": False,
    "channel_name": None,
    "guild_name": None,
    "reconnect_count": 0
}

# -------------------------------
# Flask Web Server (Render Keep-Alive)
# -------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Voice Presence Bot is running!"

@app.route('/health')
def health():
    return jsonify({
        "status": "alive",
        "in_voice": bot_status["in_voice"],
        "channel": bot_status["channel_name"],
        "guild": bot_status["guild_name"],
        "reconnects": bot_status["reconnect_count"]
    }), 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

Thread(target=run_web, daemon=True).start()

# -------------------------------
# Discord Self-Bot Client
# -------------------------------
client = discord.Client()

async def send_webhook(message: str):
    """إرسال إشعار عبر Discord Webhook (اختياري)"""
    if not WEBHOOK_URL:
        return
    try:
        import urllib.request, json as _json
        data = _json.dumps({"content": message}).encode()
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot (voice-presence, 1.0)"
            },
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
        log.info("🔔 Webhook sent successfully.")
    except Exception as e:
        log.warning(f"⚠️ Webhook failed: {e}")

async def join_voice(retry: bool = False):
    """الدخول للروم الصوتي مع إعادة المحاولة"""
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            log.info(f"🎤 Attempt {attempt}/{max_attempts} to join channel {CHANNEL_ID}...")
            channel = client.get_channel(CHANNEL_ID)
            if channel is None:
                channel = await client.fetch_channel(CHANNEL_ID)

            if not isinstance(channel, discord.VoiceChannel):
                log.error(f"❌ Channel {CHANNEL_ID} is not a voice channel.")
                await client.close()
                return

            await channel.connect(self_mute=True, self_deaf=True)

            bot_status["in_voice"]     = True
            bot_status["channel_name"] = channel.name
            bot_status["guild_name"]   = channel.guild.name

            log.info(f"✅ Connected to [{channel.name}] in [{channel.guild.name}]")
            log.info("🔇 Microphone and headset muted.")
            log.info("🔊 Staying in voice channel indefinitely...")

            if retry:
                bot_status["reconnect_count"] += 1
                await send_webhook(
                    f"✅ **Reconnected** to `{channel.name}` "
                    f"(Reconnect #{bot_status['reconnect_count']})"
                )
            else:
                await send_webhook(f"✅ **Bot started** and joined `{channel.name}`")
            return

        except Exception as e:
            log.warning(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                wait = 10 * attempt  # انتظار تدريجي: 10s, 20s, 30s...
                log.info(f"⏳ Retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                log.error("❌ All attempts failed.")
                await send_webhook("❌ **Bot failed** to join voice after 5 attempts.")

@client.event
async def on_ready():
    log.info(f"✅ Logged in as {client.user} (ID: {client.user.id})")
    await join_voice()

@client.event
async def on_voice_state_update(member, before, after):
    """إعادة الدخول تلقائياً لو طاح من الفويس"""
    if member.id != client.user.id:
        return
    if before.channel is not None and after.channel is None:
        bot_status["in_voice"]     = False
        bot_status["channel_name"] = None
        log.warning("⚠️ Disconnected from voice! Reconnecting in 5s...")
        await send_webhook("⚠️ **Disconnected** from voice. Reconnecting...")
        await asyncio.sleep(5)
        await join_voice(retry=True)

log.info("🚀 Starting Discord Voice Presence Bot...")
client.run(TOKEN)
