import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from .schema import (
    LISTINGS_TABLE, LISTINGS_INDEX,
    DUTY_TOKENS_TABLE, DUTY_TOKENS_INDEX,
    LISTING_TOKENS_TABLE,
    POLLS_TABLE, WATCHES_TABLE, NOTIFIED_TABLE,
)
from scraper.parser import Listing


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    for stmt in (
        LISTINGS_TABLE, LISTINGS_INDEX,
        DUTY_TOKENS_TABLE, DUTY_TOKENS_INDEX,
        LISTING_TOKENS_TABLE,
        POLLS_TABLE, WATCHES_TABLE, NOTIFIED_TABLE,
    ):
        conn.execute(stmt)
    # Migrations — safe to run on existing DBs
    try:
        conn.execute("ALTER TABLE listings ADD COLUMN description_raw TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists

    conn.commit()
    return conn


@dataclass
class PollStats:
    polled_at: str
    listing_count: int
    new_listings: int
    updated_listings: int
    expired_listings: int
    tokens_added: int = 0


def upsert_listing(conn: sqlite3.Connection, listing: Listing, now: str) -> str:
    """Returns 'new', 'updated', or 'unchanged'."""
    row = conn.execute(
        "SELECT updated_at, tokens_indexed FROM listings WHERE id = ?", (listing.id,)
    ).fetchone()

    if row is None:
        conn.execute(
            """
            INSERT INTO listings (
                id, duty_name_en, category, content_kind, recruiter,
                home_world, current_world, data_center, description_en, description_raw,
                min_item_level, slot_count, slots_filled_json, slots_open,
                obj_duty_completion, obj_practice, obj_loot,
                cond_duty_complete, one_player_per_job,
                created_at, updated_at, first_seen_at, last_seen_at, is_active, tokens_indexed
            ) VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?, ?,?,?, ?,?, ?,?,?,?,1,0)
            """,
            (
                listing.id, listing.duty_name_en, listing.category, listing.content_kind, listing.recruiter,
                listing.home_world, listing.current_world, listing.data_center, listing.description_en, listing.description_raw,
                listing.min_item_level, listing.slot_count,
                json.dumps(listing.slots_filled), listing.slots_open,
                int(listing.obj_duty_completion), int(listing.obj_practice), int(listing.obj_loot),
                int(listing.cond_duty_complete), int(listing.one_player_per_job),
                listing.created_at, listing.updated_at, now, now,
            ),
        )
        return "new"

    if row["updated_at"] != listing.updated_at:
        conn.execute(
            """
            UPDATE listings SET
                duty_name_en=?, category=?, content_kind=?, recruiter=?,
                home_world=?, current_world=?, data_center=?, description_en=?, description_raw=?,
                min_item_level=?, slot_count=?, slots_filled_json=?, slots_open=?,
                obj_duty_completion=?, obj_practice=?, obj_loot=?,
                cond_duty_complete=?, one_player_per_job=?,
                updated_at=?, last_seen_at=?, is_active=1
            WHERE id=?
            """,
            (
                listing.duty_name_en, listing.category, listing.content_kind, listing.recruiter,
                listing.home_world, listing.current_world, listing.data_center, listing.description_en, listing.description_raw,
                listing.min_item_level, listing.slot_count,
                json.dumps(listing.slots_filled), listing.slots_open,
                int(listing.obj_duty_completion), int(listing.obj_practice), int(listing.obj_loot),
                int(listing.cond_duty_complete), int(listing.one_player_per_job),
                listing.updated_at, now, listing.id,
            ),
        )
        return "updated"

    conn.execute(
        "UPDATE listings SET last_seen_at=?, is_active=1 WHERE id=?",
        (now, listing.id),
    )
    return "unchanged"


def index_listing_tokens(conn: sqlite3.Connection, listing: Listing, now: str) -> int:
    """Tokenize a listing and update duty_tokens + listing_tokens. Returns token count."""
    # Only index if the listing has a duty name
    if not listing.duty_name_en:
        conn.execute("UPDATE listings SET tokens_indexed=1 WHERE id=?", (listing.id,))
        return 0

    from analysis.tokenizer import tokenize
    tokens = tokenize(listing.description_en or "")

    for token in tokens:
        conn.execute(
            """
            INSERT INTO duty_tokens (duty_name_en, token, count, first_seen_at, last_seen_at)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(duty_name_en, token) DO UPDATE SET
                count = count + 1,
                last_seen_at = excluded.last_seen_at
            """,
            (listing.duty_name_en, token, now, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO listing_tokens (listing_id, token) VALUES (?, ?)",
            (listing.id, token),
        )

    conn.execute("UPDATE listings SET tokens_indexed=1 WHERE id=?", (listing.id,))
    return len(tokens)


def backfill_duty_overrides(conn: sqlite3.Connection) -> int:
    """Re-label and re-tokenize existing DB listings that had duty_name_en=NULL.
    Returns number of listings updated."""
    from scraper.parser import _apply_override

    rows = conn.execute(
        "SELECT id, category, min_item_level, description_en FROM listings WHERE duty_name_en IS NULL"
    ).fetchall()

    updated = 0
    now = _now_utc()
    for row in rows:
        name = _apply_override(row["category"], row["min_item_level"] or 0, row["description_en"] or "")
        if name:
            conn.execute("UPDATE listings SET duty_name_en=?, tokens_indexed=0 WHERE id=?", (name, row["id"]))
            updated += 1

    # Now tokenize any listing that has a duty name but hasn't been indexed yet
    unindexed = conn.execute(
        "SELECT id, duty_name_en, description_en FROM listings WHERE tokens_indexed=0 AND duty_name_en IS NOT NULL"
    ).fetchall()

    from scraper.parser import Listing as _Listing
    from dataclasses import fields as _fields
    from analysis.tokenizer import tokenize

    for row in unindexed:
        tokens = tokenize(row["description_en"] or "")
        for token in tokens:
            conn.execute(
                """
                INSERT INTO duty_tokens (duty_name_en, token, count, first_seen_at, last_seen_at)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(duty_name_en, token) DO UPDATE SET
                    count = count + 1,
                    last_seen_at = excluded.last_seen_at
                """,
                (row["duty_name_en"], token, now, now),
            )
            conn.execute(
                "INSERT OR IGNORE INTO listing_tokens (listing_id, token) VALUES (?, ?)",
                (row["id"], token),
            )
        conn.execute("UPDATE listings SET tokens_indexed=1 WHERE id=?", (row["id"],))

    conn.commit()
    return updated


def mark_expired(conn: sqlite3.Connection, active_ids: set[int]) -> int:
    if not active_ids:
        conn.execute("UPDATE listings SET is_active=0 WHERE is_active=1")
        return conn.execute("SELECT changes()").fetchone()[0]
    placeholders = ",".join("?" * len(active_ids))
    conn.execute(
        f"UPDATE listings SET is_active=0 WHERE is_active=1 AND id NOT IN ({placeholders})",
        list(active_ids),
    )
    return conn.execute("SELECT changes()").fetchone()[0]


def record_poll(conn: sqlite3.Connection, stats: PollStats) -> None:
    conn.execute(
        """
        INSERT INTO polls (polled_at, listing_count, new_listings, updated_listings, expired_listings, tokens_added)
        VALUES (?,?,?,?,?,?)
        """,
        (stats.polled_at, stats.listing_count, stats.new_listings,
         stats.updated_listings, stats.expired_listings, stats.tokens_added),
    )


def process_poll(conn: sqlite3.Connection, listings: list[Listing]) -> PollStats:
    now = _now_utc()
    new = updated = tokens_added = 0
    active_ids: set[int] = set()

    for listing in listings:
        active_ids.add(listing.id)
        result = upsert_listing(conn, listing, now)
        if result == "new":
            new += 1
            # Tokenize immediately for new listings
            tokens_added += index_listing_tokens(conn, listing, now)
        elif result == "updated":
            updated += 1

    expired = mark_expired(conn, active_ids)
    stats = PollStats(
        polled_at=now,
        listing_count=len(listings),
        new_listings=new,
        updated_listings=updated,
        expired_listings=expired,
        tokens_added=tokens_added,
    )
    record_poll(conn, stats)
    conn.commit()
    return stats
