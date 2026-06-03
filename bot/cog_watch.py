import sqlite3
from datetime import datetime, timezone

import discord
from discord.ext import commands

from db.queries import get_watches, create_watch, deactivate_watch
from config import resolve_duty


class WatchCog(commands.Cog, name="Watch"):
    def __init__(self, bot: commands.Bot, db: sqlite3.Connection) -> None:
        self.bot = bot
        self.db = db

    @commands.command(name="watch")
    async def watch(self, ctx: commands.Context, *, args: str = "") -> None:
        """Subscribe this channel to matching party finder listings.
        Usage: !watch <duty name> [--strat <keyword>] [--dc <datacenter>]
        Example: !watch "AAC Heavyweight M4" --strat nukemaru --dc Aether
        """
        if not args:
            await ctx.send(
                "Usage: `!watch <duty name> [--strat <keyword>] [--dc <datacenter>]`\n"
                "Example: `!watch AAC Heavyweight M4 --strat nukemaru --dc Aether`"
            )
            return

        duty_name = args
        strategy_keyword: str | None = None
        data_center: str | None = None

        if "--dc" in args:
            parts = args.split("--dc", 1)
            duty_name = parts[0]
            data_center = parts[1].strip().split()[0]
            duty_name = duty_name.replace("--strat", "\0").split("\0")[0] if "--strat" not in duty_name else duty_name

        if "--strat" in args:
            parts = args.split("--strat", 1)
            duty_name = parts[0]
            rest = parts[1].strip()
            if "--dc" in rest:
                strat_parts = rest.split("--dc", 1)
                strategy_keyword = strat_parts[0].strip()
                data_center = strat_parts[1].strip().split()[0]
            else:
                strategy_keyword = rest.split()[0]

        duty_name = resolve_duty(duty_name.strip())

        now = datetime.now(timezone.utc).isoformat()
        watch_id = create_watch(
            self.db,
            guild_id=str(ctx.guild.id),
            channel_id=str(ctx.channel.id),
            duty_name=duty_name,
            strategy_keyword=strategy_keyword,
            data_center=data_center,
            created_by=str(ctx.author),
            created_at=now,
        )

        parts = [f"Watch **#{watch_id}** created for **{duty_name}**"]
        if strategy_keyword:
            parts.append(f"keyword: `{strategy_keyword}`")
        if data_center:
            parts.append(f"DC: `{data_center}`")
        await ctx.send(" · ".join(parts))

    @commands.command(name="unwatch")
    async def unwatch(self, ctx: commands.Context, watch_id: int) -> None:
        """Remove a watch subscription.
        Usage: !unwatch <watch_id>
        """
        removed = deactivate_watch(self.db, watch_id, str(ctx.guild.id))
        if removed:
            await ctx.send(f"Watch **#{watch_id}** removed.")
        else:
            await ctx.send(f"Watch **#{watch_id}** not found or not yours.")

    @commands.command(name="watches")
    async def watches(self, ctx: commands.Context) -> None:
        """List active watches for this server."""
        rows = get_watches(self.db, guild_id=str(ctx.guild.id))

        if not rows:
            await ctx.send("No active watches. Use `!watch <duty name>` to create one.")
            return

        lines = ["**Active watches for this server**", "─" * 36]
        for row in rows:
            parts = [f"`#{row['id']}` **{row['duty_name']}**"]
            if row["strategy_keyword"]:
                parts.append(f"keyword: `{row['strategy_keyword']}`")
            if row["data_center"]:
                parts.append(f"DC: `{row['data_center']}`")
            ch = self.bot.get_channel(int(row["channel_id"]))
            ch_display = ch.mention if ch else f"#channel-{row['channel_id']}"
            parts.append(f"→ {ch_display}")
            lines.append(" · ".join(parts))

        await ctx.send("\n".join(lines))


async def setup(bot: commands.Bot, db: sqlite3.Connection) -> None:
    await bot.add_cog(WatchCog(bot, db))
