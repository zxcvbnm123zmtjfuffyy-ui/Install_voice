# self-bot.py
# Discord Voice Presence Tool - Multi-Account
# Supports DAVE protocol (March 2026+)
# Library: discord.py-self[voice]

import asyncio
import logging
import os
import random
import sys
import urllib.request
import json
from threading import Thread

import discord
from flask import Flask, jsonify

# ─────────────────────────────────────
# Logging
# ─────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────
# Config
# ─────────────────────────────────────
CHANNEL_ID  = os.environ.get("CHANNEL_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

if not CHANNEL_ID:
    log.error("❌ CHANNEL_ID not set.")
    sys.exit(1)

try:
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    log.error("❌ CHANNEL_ID must be a valid integer.")
    sys.exit(1)

# اقرأ التوكنات: DISCORD_TOKEN_1, DISCORD_TOKEN_2, ...
TOKENS = []
i = 1
while True:
    t = os.environ.get(f"DISCORD_TOKEN_{i}")
    if not t:
        break
    TOKENS.append(t)
    i += 1

# fallback للتوكن القديم DISCORD_TOKEN لو ما في أرقام
if not TOKENS:
    single = os.environ.get("DISCORD_TOKEN")
    if single:
        TOKENS.append(single)

if not TOKENS:
    log.error("❌ No tokens found. Set DISCORD_TOKEN_1, DISCORD_TOKEN_2, ...")
    sys.exit(1)

log.info(f"📋 Loaded {len(TOKENS)} account(s).")

# ─────────────────────────────────────
# Webhook
# ─────────────────────────────────────
async def send_webhook(message: str):
    if not WEBHOOK_URL:
        return
    try:
        data = json.dumps({"content": message}).encode()
        req = urllib.request.Request(
            WEBHOOK_URL, data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot (voice-presence, 1.0)"
            },
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log.warning(f"⚠️ Webhook failed: {e}")

# ─────────────────────────────────────
# AccountBot — كل حساب مستقل بالكامل
# ─────────────────────────────────────
class AccountBot:
    MAX_ATTEMPTS  = 5
    BASE_DELAY    = 8     # ثانية — أساس وقت الانتظار عند reconnect
    JITTER_RANGE  = 12    # ثانية — مدى العشوائية (يمنع التزامن بين الحسابات)

    def __init__(self, index: int, token: str):
        self.index   = index          # رقم الحساب (1-based للـ logs)
        self.token   = token
        self.tag     = f"[Acc#{index}]"
        self.client  = discord.Client()
        self.status  = {
            "username":        None,
            "in_voice":        False,
            "channel_name":    None,
            "guild_name":      None,
            "reconnect_count": 0,
            "failed":          False,  # فشل بعد MAX_ATTEMPTS محاولات
        }
        self._register_events()

    # ── Events ──────────────────────────────────────
    def _register_events(self):

        @self.client.event
        async def on_ready():
            self.status["username"] = str(self.client.user)
            log.info(f"✅ {self.tag} Logged in as {self.client.user}")
            await self._join_voice()

        @self.client.event
        async def on_voice_state_update(member, before, after):
            if member.id != self.client.user.id:
                return
            # خرج من الفويس بدون إرادته
            if before.channel is not None and after.channel is None:
                self.status["in_voice"]     = False
                self.status["channel_name"] = None

                # تأخير عشوائي = base + jitter فريد لكل حساب
                delay = self.BASE_DELAY + random.uniform(0, self.JITTER_RANGE)
                log.warning(
                    f"⚠️ {self.tag} Disconnected! "
                    f"Reconnecting in {delay:.1f}s..."
                )
                await send_webhook(
                    f"⚠️ **{self.tag}** خرج من الفويس، "
                    f"إعادة اتصال خلال {delay:.0f} ثانية..."
                )
                await asyncio.sleep(delay)
                await self._join_voice(retry=True)

    # ── Join Voice ───────────────────────────────────
    async def _join_voice(self, retry: bool = False):
        if self.status["failed"]:
            log.error(f"❌ {self.tag} Marked as failed, skipping.")
            return

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                log.info(
                    f"🎤 {self.tag} Attempt {attempt}/{self.MAX_ATTEMPTS} "
                    f"to join channel {CHANNEL_ID}..."
                )
                channel = self.client.get_channel(CHANNEL_ID)
                if channel is None:
                    channel = await self.client.fetch_channel(CHANNEL_ID)

                if not isinstance(channel, discord.VoiceChannel):
                    log.error(f"❌ {self.tag} Channel is not a voice channel.")
                    return

                await channel.connect(self_mute=True, self_deaf=True)

                self.status["in_voice"]     = True
                self.status["channel_name"] = channel.name
                self.status["guild_name"]   = channel.guild.name
                self.status["failed"]       = False

                log.info(
                    f"✅ {self.tag} Connected to [{channel.name}] "
                    f"in [{channel.guild.name}] 🔇"
                )

                if retry:
                    self.status["reconnect_count"] += 1
                    await send_webhook(
                        f"✅ **{self.tag}** رجع للفويس "
                        f"`{channel.name}` "
                        f"(إعادة اتصال #{self.status['reconnect_count']})"
                    )
                else:
                    await send_webhook(
                        f"✅ **{self.tag}** دخل الفويس `{channel.name}`"
                    )
                return

            except Exception as e:
                log.warning(f"⚠️ {self.tag} Attempt {attempt} failed: {e}")
                if attempt < self.MAX_ATTEMPTS:
                    wait = 10 * attempt
                    log.info(f"⏳ {self.tag} Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    self.status["failed"] = True
                    log.error(f"❌ {self.tag} All attempts failed. Giving up.")
                    await send_webhook(
                        f"❌ **{self.tag}** فشل بعد {self.MAX_ATTEMPTS} محاولات."
                    )

    # ── Start ────────────────────────────────────────
    async def start(self):
        try:
            await self.client.start(self.token)
        except Exception as e:
            log.error(f"❌ {self.tag} Login failed: {e}")
            self.status["failed"] = True

# ─────────────────────────────────────
# Flask — Keep-Alive + Health
# ─────────────────────────────────────
app   = Flask(__name__)
bots: list[AccountBot] = []

@app.route('/')
def home():
    return "✅ Voice Presence Bot (Multi-Account) is running!"

@app.route('/health')
def health():
    accounts = []
    for b in bots:
        accounts.append({
            "account":   f"Acc#{b.index}",
            "username":  b.status["username"],
            "in_voice":  b.status["in_voice"],
            "channel":   b.status["channel_name"],
            "guild":     b.status["guild_name"],
            "reconnects":b.status["reconnect_count"],
            "failed":    b.status["failed"],
        })
    active = sum(1 for b in bots if b.status["in_voice"])
    return jsonify({
        "status":         "alive",
        "total_accounts": len(bots),
        "active_in_voice":active,
        "accounts":       accounts,
    }), 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

Thread(target=run_web, daemon=True).start()

# ─────────────────────────────────────
# Main — تشغيل كل الحسابات معاً
# ─────────────────────────────────────
async def main():
    global bots
    bots = [AccountBot(i + 1, token) for i, token in enumerate(TOKENS)]

    log.info(f"🚀 Starting {len(bots)} account(s)...")
    await send_webhook(f"🚀 بدء تشغيل **{len(bots)} حساب** في الفويس...")

    # كل حساب يشتغل بالتوازي في نفس event loop
    await asyncio.gather(*(b.start() for b in bots))

asyncio.run(main())
