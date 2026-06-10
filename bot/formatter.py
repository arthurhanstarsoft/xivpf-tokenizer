import json
import sqlite3

import discord

COLOR_PRACTICE = discord.Color.blue()
COLOR_LOOT = discord.Color.green()
COLOR_CLEAR = discord.Color.gold()
COLOR_DEFAULT = discord.Color.greyple()
COLOR_LOOT_ALERT = discord.Color.from_rgb(255, 215, 0)  # bright gold for loot alerts

JOB_ICONS = {
    "PLD": "🛡️", "WAR": "🛡️", "DRK": "🛡️", "GNB": "🛡️",
    "WHM": "❇️", "SCH": "❇️", "AST": "❇️", "SGE": "❇️",
    "MNK": "👊", "DRG": "🐉", "NIN": "🗡️", "SAM": "⚔️", "RPR": "💀", "VPR": "🐍",
    "BRD": "🎵", "MCH": "🔫", "DNC": "💃",
    "BLM": "🔥", "SMN": "🌟", "RDM": "🌹", "PCT": "🎨",
}

_SLOT_OPEN = "○"
_SLOT_FILLED = "●"


def _slots_display(slots_filled: list) -> str:
    parts = []
    for slot in slots_filled:
        if slot is None:
            parts.append("`----`")
        else:
            parts.append(f"`{slot}`")
    return " ".join(parts)


def _slots_compact(slots_filled: list) -> str:
    """Compact open/filled indicator: ●●●●○○○○"""
    return "".join(_SLOT_FILLED if s is not None else _SLOT_OPEN for s in slots_filled)


def format_listing_row(row: sqlite3.Row) -> discord.Embed:
    slots_filled = json.loads(row["slots_filled_json"] or "[]")
    filled_count = sum(1 for s in slots_filled if s is not None)
    total = row["slot_count"] or 8

    duty = row["duty_name_en"] or "Unknown Duty"
    desc = row["description_en"] or ""
    dc = row["data_center"] or "?"
    world = row["current_world"] or "?"
    recruiter = row["recruiter"] or "?"

    if row["obj_practice"]:
        color = COLOR_PRACTICE
    elif row["obj_loot"]:
        color = COLOR_LOOT
    elif row["obj_duty_completion"]:
        color = COLOR_CLEAR
    else:
        color = COLOR_DEFAULT

    embed = discord.Embed(
        title=duty,
        description=desc[:500] + ("…" if len(desc) > 500 else "") or "_No description_",
        color=color,
    )
    embed.add_field(name="Party", value=f"{filled_count}/{total}  {_slots_display(slots_filled)}", inline=False)
    embed.add_field(name="Leader", value=f"{recruiter} @ {world}", inline=True)
    embed.add_field(name="Data Center", value=dc, inline=True)
    if row["min_item_level"]:
        embed.add_field(name="Min iLvl", value=str(row["min_item_level"]), inline=True)

    tag_parts = []
    if row["obj_practice"]:
        tag_parts.append("Practice")
    if row["obj_loot"]:
        tag_parts.append("Loot")
    if row["obj_duty_completion"]:
        tag_parts.append("Duty Completion")
    if row["cond_duty_complete"]:
        tag_parts.append("Duty Complete")
    if row["one_player_per_job"]:
        tag_parts.append("One Player per Job")
    if tag_parts:
        embed.add_field(name="Tags", value=" · ".join(tag_parts), inline=False)

    embed.set_footer(text=f"Listing #{row['id']} · {row['created_at'][:16].replace('T', ' ')} UTC")
    return embed


def format_loot_alert(row: sqlite3.Row) -> discord.Embed:
    """Fancy embed for loot-tagged party alerts (e.g. Cloud of Darkness bonus runs)."""
    slots_filled = json.loads(row["slots_filled_json"] or "[]")
    open_slots = [s for s in slots_filled if s is None]
    filled_slots = [s for s in slots_filled if s is not None]
    total = row["slot_count"] or 8

    duty = row["duty_name_en"] or "Unknown Duty"
    desc = row["description_en"] or ""
    dc = row["data_center"] or "?"
    world = row["current_world"] or "?"
    recruiter = row["recruiter"] or "?"

    open_count = len(open_slots)
    filled_count = len(filled_slots)

    compact = _slots_compact(slots_filled)

    embed = discord.Embed(
        title=f"Loot Run  —  {duty}",
        description=f">>> {desc[:400]}{'…' if len(desc) > 400 else ''}" if desc else "_No description provided_",
        color=COLOR_LOOT_ALERT,
    )

    embed.add_field(
        name="Slots",
        value=f"`{compact}`\n{filled_count} filled · **{open_count} open**",
        inline=True,
    )
    embed.add_field(
        name="Leader",
        value=f"{recruiter}\n{world}  ·  {dc}",
        inline=True,
    )

    conditions = []
    if row["cond_duty_complete"]:
        conditions.append("Duty Complete required")
    if row["one_player_per_job"]:
        conditions.append("One per job")
    if row["min_item_level"]:
        conditions.append(f"iLvl {row['min_item_level']}+")
    if conditions:
        embed.add_field(name="Conditions", value="\n".join(conditions), inline=True)

    embed.set_footer(text=f"Listing #{row['id']}  ·  first seen {row['first_seen_at'][:16].replace('T', ' ')} UTC")
    return embed


def format_token_bar(token: str, count: int, max_count: int, rank: int) -> str:
    pct = count / max_count
    filled = round(pct * 10)
    bar = "▰" * filled + "▱" * (10 - filled)
    return f"`{rank:>2}.` {bar} **{token}** ({count})"
