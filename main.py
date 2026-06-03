import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import discord
from discord.ext import commands
from dotenv import load_dotenv

from db.database import init_db, process_poll, backfill_duty_overrides
from db.queries import get_watches, get_matching_new_listings, record_notified
from scraper.client import XivpfClient
from scraper.parser import parse_listing
from bot.formatter import format_listing_row
import bot.cog_stats as cog_stats
import bot.cog_watch as cog_watch

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("xivscrapper")

DB_PATH = os.getenv("DB_PATH", "xivpf.db")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

db = init_db(DB_PATH)
_backfilled = backfill_duty_overrides(db)
if _backfilled:
    log.info("Backfilled %d listings with duty name overrides", _backfilled)
xivpf = XivpfClient()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()


async def send_watch_notifications() -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    for watch in get_watches(db):
        matches = get_matching_new_listings(
            db,
            watch_id=watch["id"],
            duty_name=watch["duty_name"],
            strategy_keyword=watch["strategy_keyword"],
            data_center=watch["data_center"],
        )
        if not matches:
            continue

        channel = bot.get_channel(int(watch["channel_id"]))
        if not channel:
            continue

        for row in matches:
            try:
                embed = format_listing_row(row)
                await channel.send(embed=embed)
                record_notified(db, watch["id"], row["id"], now)
            except Exception as e:
                log.warning("Failed to notify listing %s: %s", row["id"], e)


async def poll() -> None:
    try:
        raw = xivpf.fetch_listings()
        listings = [parse_listing(r) for r in raw]
        stats = process_poll(db, listings)
        log.info(
            "Poll: %d listings | +%d new | ~%d updated | -%d expired | %d tokens",
            stats.listing_count, stats.new_listings, stats.updated_listings,
            stats.expired_listings, stats.tokens_added,
        )
        if DISCORD_TOKEN:
            await send_watch_notifications()
    except Exception as e:
        log.error("Poll failed: %s", e)


@bot.event
async def on_ready() -> None:
    log.info("Bot ready as %s", bot.user)
    await cog_stats.setup(bot, db)
    await cog_watch.setup(bot, db)

    if not scheduler.running:
        scheduler.add_job(poll, "interval", seconds=POLL_INTERVAL, id="poll")
        scheduler.start()
        log.info("Scheduler started — polling every %ds", POLL_INTERVAL)

    await poll()


async def run_scraper_only() -> None:
    log.info("Scraper-only mode (no DISCORD_BOT_TOKEN). Polling every %ds.", POLL_INTERVAL)
    scheduler.add_job(poll, "interval", seconds=POLL_INTERVAL, id="poll")
    scheduler.start()
    await poll()
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        scheduler.shutdown()


if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        asyncio.run(run_scraper_only())
