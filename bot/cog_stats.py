import sqlite3

import discord
from discord.ext import commands

from db.queries import get_top_tokens, get_top_duties, get_active_listing_count, get_last_poll, get_total_listing_count, get_active_parties
from bot.formatter import format_token_bar, format_listing_row
from config import resolve_duty


class StatsCog(commands.Cog, name="Stats"):
    def __init__(self, bot: commands.Bot, db: sqlite3.Connection) -> None:
        self.bot = bot
        self.db = db

    @commands.command(name="strategies", aliases=["strats"])
    async def strategies(self, ctx: commands.Context, *, args: str = "") -> None:
        """Show top discovered tokens for a duty.
        Usage: !strategies <duty name> [--dc <datacenter>]
        """
        dc: str = "Aether"
        duty_name = args

        if "--dc" in args:
            parts = args.split("--dc", 1)
            duty_name = parts[0].strip()
            dc = parts[1].strip()

        if not duty_name:
            await ctx.send("Usage: `!strategies <duty name> [--dc <datacenter>]`")
            return

        duty_name = resolve_duty(duty_name)
        tokens = get_top_tokens(self.db, duty_name, limit=20, data_center=dc)

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


    @commands.command(name="parties", aliases=["pf"])
    async def parties(self, ctx: commands.Context, *, args: str = "") -> None:
        """List active party finder listings for a duty.
        Usage: !parties <duty> [--slots <n>] [--strat <keyword>] [--dc <DC>]
        """
        dc: str = "Aether"
        duty_name = args
        open_slots: int | None = None
        strategy_keyword: str | None = None

        if "--dc" in args:
            parts = args.split("--dc", 1)
            duty_name = parts[0]
            dc = parts[1].strip().split()[0]
            args = args.replace(f"--dc {dc}", "")

        if "--slots" in args:
            parts = args.split("--slots", 1)
            duty_name = parts[0]
            try:
                open_slots = int(parts[1].strip().split()[0])
            except ValueError:
                pass
            args = args.replace(f"--slots {open_slots}", "")

        if "--strat" in args:
            parts = args.split("--strat", 1)
            duty_name = parts[0]
            strategy_keyword = parts[1].strip().split()[0]

        duty_name = resolve_duty(duty_name.strip())

        if not duty_name:
            await ctx.send("Usage: `!parties <duty> [--slots <n>] [--strat <keyword>] [--dc <DC>]`")
            return

        rows = get_active_parties(
            self.db, duty_name,
            data_center=dc,
            open_slots=open_slots,
            strategy_keyword=strategy_keyword,
            limit=10,
        )

        if not rows:
            await ctx.send(f"No active listings found for **{duty_name}**.")
            return

        header_parts = [f"**Active parties for \"{duty_name}\"**"]
        if dc:
            header_parts.append(f"DC: {dc}")
        if open_slots is not None:
            header_parts.append(f"{open_slots} slot(s) open")
        if strategy_keyword:
            header_parts.append(f"strat: {strategy_keyword}")

        await ctx.send(" · ".join(header_parts))
        for row in rows:
            await ctx.send(embed=format_listing_row(row))

    @commands.command(name="dump")
    async def dump(self, ctx: commands.Context, *, args: str = "") -> None:
        """Export all descriptions for a duty to a .txt file.
        Usage: !dump <duty> [--dc <DC>]
        """
        dc: str = "Aether"
        duty_name = args

        if "--dc" in args:
            parts = args.split("--dc", 1)
            duty_name = parts[0].strip()
            dc = parts[1].strip().split()[0]

        duty_name = resolve_duty(duty_name.strip())

        if not duty_name:
            await ctx.send("Usage: `!dump <duty> [--dc <DC>]`")
            return

        query = "SELECT recruiter, current_world, description_en, created_at FROM listings WHERE duty_name_en LIKE ?"
        params = [f"%{duty_name}%"]
        if dc:
            query += " AND data_center = ?"
            params.append(dc)
        query += " ORDER BY created_at DESC"

        rows = self.db.execute(query, params).fetchall()

        if not rows:
            await ctx.send(f"No descriptions found for **{duty_name}**.")
            return

        lines = [f"Descriptions for: {duty_name}" + (f" (DC: {dc})" if dc else "")]
        lines.append(f"Total: {len(rows)}")
        lines.append("=" * 60)
        for row in rows:
            lines.append(f"[{row['created_at'][:16].replace('T', ' ')} UTC] {row['recruiter']} @ {row['current_world']}")
            lines.append(row['description_en'] or "(no description)")
            lines.append("-" * 40)

        content = "\n".join(lines).encode("utf-8")
        filename = f"{duty_name.replace(' ', '_').replace('(', '').replace(')', '')}_{dc}.txt"

        await ctx.send(
            f"**{len(rows)}** descriptions for **{duty_name}**",
            file=discord.File(fp=__import__('io').BytesIO(content), filename=filename),
        )

    @commands.command(name="commands")
    async def list_commands(self, ctx: commands.Context) -> None:
        """Show all available commands."""
        lines = [
            "**XIVPF Scraper Commands**",
            "─" * 36,
            "`!strategies <duty>` — top strategy tokens for a duty",
            "`!strategies <duty> --dc <DC>` — same, filtered by data center",
            "`!top` — most active duties by listing count",
            "`!top --kind <Raids|Trials|Dungeons>` — filter by content type",
            "`!status` — last poll time, active listings, DB stats",
            "─" * 36,
            "`!watch <duty>` — post to this channel when a matching listing appears",
            "`!watch <duty> --strat <keyword>` — only post listings mentioning keyword",
            "`!watch <duty> --dc <DC>` — filter by data center",
            "`!watch <duty> --loot` — only loot-tagged listings (fancy embed)",
            "`!watch <duty> --practice` — only practice-tagged listings",
            "`!watch <duty> --clear` — only duty-completion listings",
            "`!unwatch <id>` — remove a watch by its ID",
            "`!watches` — list active watches for this server",
            "─" * 36,
            "`!parties <duty>` — list active PF listings for a duty",
            "`!parties <duty> --slots <n>` — only show listings with n open slots",
            "`!parties <duty> --strat <keyword>` — filter by strategy keyword",
            "`!parties <duty> --dc <DC>` — filter by data center",
        ]
        await ctx.send("\n".join(lines))


async def setup(bot: commands.Bot, db: sqlite3.Connection) -> None:
    await bot.add_cog(StatsCog(bot, db))
