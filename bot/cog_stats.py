import sqlite3

import discord
from discord.ext import commands

from db.queries import get_top_tokens, get_top_duties, get_active_listing_count, get_last_poll, get_total_listing_count
from bot.formatter import format_token_bar


class StatsCog(commands.Cog, name="Stats"):
    def __init__(self, bot: commands.Bot, db: sqlite3.Connection) -> None:
        self.bot = bot
        self.db = db

    @commands.command(name="strategies", aliases=["strats"])
    async def strategies(self, ctx: commands.Context, *, args: str = "") -> None:
        """Show top discovered tokens for a duty.
        Usage: !strategies <duty name> [--dc <datacenter>]
        """
        dc: str | None = None
        duty_name = args

        if "--dc" in args:
            parts = args.split("--dc", 1)
            duty_name = parts[0].strip()
            dc = parts[1].strip()

        if not duty_name:
            await ctx.send("Usage: `!strategies <duty name> [--dc <datacenter>]`")
            return

        tokens = get_top_tokens(self.db, duty_name, limit=15, data_center=dc)

        if not tokens:
            await ctx.send(f"No token data found for **{duty_name}**. Try collecting data for a few minutes first.")
            return

        max_count = tokens[0][1]
        lines = [f"**Top tokens for \"{duty_name}\"**" + (f" (DC: {dc})" if dc else "")]
        lines.append("─" * 36)
        for i, (token, count) in enumerate(tokens, 1):
            lines.append(format_token_bar(token, count, max_count, i))

        await ctx.send("\n".join(lines))

    @commands.command(name="top")
    async def top(self, ctx: commands.Context, *, args: str = "") -> None:
        """Show most active duties by listing count.
        Usage: !top [--kind Raids|Trials|Dungeons]
        """
        kind: str | None = None
        if "--kind" in args:
            kind = args.split("--kind", 1)[1].strip()

        duties = get_top_duties(self.db, limit=10, content_kind=kind)

        if not duties:
            await ctx.send("No duty data yet.")
            return

        header = "**Most active duties**" + (f" (kind: {kind})" if kind else "")
        lines = [header, "─" * 36]
        for i, (duty, count) in enumerate(duties, 1):
            lines.append(f"`{i:>2}.` {duty} — **{count}** listings")

        await ctx.send("\n".join(lines))

    @commands.command(name="status")
    async def status(self, ctx: commands.Context) -> None:
        """Show scraper status."""
        active = get_active_listing_count(self.db)
        total = get_total_listing_count(self.db)
        last_poll = get_last_poll(self.db)

        lines = ["**Scraper Status**"]
        lines.append(f"Active listings: **{active}**")
        lines.append(f"Total listings in DB: **{total}**")
        if last_poll:
            lines.append(f"Last poll: `{last_poll['polled_at'][:19].replace('T', ' ')} UTC`")
            lines.append(
                f"Last poll stats: {last_poll['new_listings']} new · "
                f"{last_poll['updated_listings']} updated · "
                f"{last_poll['expired_listings']} expired · "
                f"{last_poll['tokens_added']} tokens added"
            )

        await ctx.send("\n".join(lines))


async def setup(bot: commands.Bot, db: sqlite3.Connection) -> None:
    await bot.add_cog(StatsCog(bot, db))
