import sqlite3
from datetime import datetime, timedelta, timezone


def get_top_tokens(
    conn: sqlite3.Connection,
    duty_name: str,
    limit: int = 15,
    data_center: str | None = None,
) -> list[tuple[str, int]]:
    if data_center:
        # Recompute from listing_tokens filtered by DC
        rows = conn.execute(
            """
            SELECT lt.token, COUNT(*) as cnt
            FROM listing_tokens lt
            JOIN listings l ON l.id = lt.listing_id
            WHERE l.duty_name_en LIKE ? AND l.data_center = ?
            GROUP BY lt.token
            ORDER BY cnt DESC
            LIMIT ?
            """,
            (f"%{duty_name}%", data_center, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT token, count FROM duty_tokens
            WHERE duty_name_en LIKE ?
            ORDER BY count DESC
            LIMIT ?
            """,
            (f"%{duty_name}%", limit),
        ).fetchall()
    return [(row[0], row[1]) for row in rows]


def get_top_duties(conn: sqlite3.Connection, limit: int = 10, content_kind: str | None = None) -> list[tuple[str, int]]:
    if content_kind:
        rows = conn.execute(
            """
            SELECT duty_name_en, COUNT(*) as cnt FROM listings
            WHERE duty_name_en IS NOT NULL AND content_kind = ?
            GROUP BY duty_name_en ORDER BY cnt DESC LIMIT ?
            """,
            (content_kind, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT duty_name_en, COUNT(*) as cnt FROM listings
            WHERE duty_name_en IS NOT NULL
            GROUP BY duty_name_en ORDER BY cnt DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [(row[0], row[1]) for row in rows]


def get_active_parties(
    conn: sqlite3.Connection,
    duty_name: str,
    data_center: str | None = None,
    open_slots: int | None = None,
    strategy_keyword: str | None = None,
    limit: int = 10,
) -> list[sqlite3.Row]:
    query = """
        SELECT * FROM listings
        WHERE is_active=1 AND duty_name_en LIKE ?
    """
    params: list = [f"%{duty_name}%"]

    if data_center:
        query += " AND data_center = ?"
        params.append(data_center)

    if open_slots is not None:
        query += " AND slots_open = ?"
        params.append(open_slots)

    if strategy_keyword:
        query += " AND LOWER(description_en) LIKE ?"
        params.append(f"%{strategy_keyword.lower()}%")

    query += " ORDER BY slots_open ASC, last_seen_at DESC LIMIT ?"
    params.append(limit)

    return conn.execute(query, params).fetchall()


def get_active_listing_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM listings WHERE is_active=1").fetchone()[0]


def get_total_listing_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]


def get_last_poll(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM polls ORDER BY id DESC LIMIT 1").fetchone()


def get_watches(conn: sqlite3.Connection, guild_id: str | None = None) -> list[sqlite3.Row]:
    if guild_id:
        return conn.execute(
            "SELECT * FROM watches WHERE is_active=1 AND guild_id=?", (guild_id,)
        ).fetchall()
    return conn.execute("SELECT * FROM watches WHERE is_active=1").fetchall()


def get_matching_new_listings(
    conn: sqlite3.Connection,
    watch_id: int,
    duty_name: str,
    strategy_keyword: str | None,
    data_center: str | None,
) -> list[sqlite3.Row]:
    query = """
        SELECT l.* FROM listings l
        WHERE l.is_active=1
          AND l.duty_name_en LIKE ?
          AND l.id NOT IN (SELECT listing_id FROM notified_listings WHERE watch_id=?)
    """
    params: list = [f"%{duty_name}%", watch_id]

    if strategy_keyword:
        query += " AND LOWER(l.description_en) LIKE ?"
        params.append(f"%{strategy_keyword.lower()}%")

    if data_center:
        query += " AND l.data_center = ?"
        params.append(data_center)

    return conn.execute(query, params).fetchall()


def record_notified(conn: sqlite3.Connection, watch_id: int, listing_id: int, now: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO notified_listings (watch_id, listing_id, notified_at) VALUES (?,?,?)",
        (watch_id, listing_id, now),
    )
    conn.commit()


def create_watch(
    conn: sqlite3.Connection,
    guild_id: str,
    channel_id: str,
    duty_name: str,
    strategy_keyword: str | None,
    data_center: str | None,
    created_by: str,
    created_at: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO watches (guild_id, channel_id, duty_name, strategy_keyword, data_center, created_by, created_at)
        VALUES (?,?,?,?,?,?,?)
        """,
        (guild_id, channel_id, duty_name, strategy_keyword, data_center, created_by, created_at),
    )
    conn.commit()
    return cur.lastrowid


def deactivate_watch(conn: sqlite3.Connection, watch_id: int, guild_id: str) -> bool:
    conn.execute(
        "UPDATE watches SET is_active=0 WHERE id=? AND guild_id=?",
        (watch_id, guild_id),
    )
    conn.commit()
    return conn.execute("SELECT changes()").fetchone()[0] > 0
