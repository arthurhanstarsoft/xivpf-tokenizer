LISTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS listings (
    id                  INTEGER PRIMARY KEY,
    duty_name_en        TEXT,
    category            TEXT,
    content_kind        TEXT,
    recruiter           TEXT NOT NULL,
    home_world          TEXT NOT NULL,
    current_world       TEXT NOT NULL,
    data_center         TEXT,
    description_en      TEXT,
    min_item_level      INTEGER DEFAULT 0,
    slot_count          INTEGER DEFAULT 8,
    slots_filled_json   TEXT,
    slots_open          INTEGER,
    obj_duty_completion INTEGER DEFAULT 0,
    obj_practice        INTEGER DEFAULT 0,
    obj_loot            INTEGER DEFAULT 0,
    cond_duty_complete  INTEGER DEFAULT 0,
    one_player_per_job  INTEGER DEFAULT 0,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    first_seen_at       TEXT NOT NULL,
    last_seen_at        TEXT NOT NULL,
    is_active           INTEGER DEFAULT 1,
    tokens_indexed      INTEGER DEFAULT 0,
    description_raw     TEXT
)
"""

LISTINGS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_listings_duty ON listings(duty_name_en, is_active)
"""

DUTY_TOKENS_TABLE = """
CREATE TABLE IF NOT EXISTS duty_tokens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    duty_name_en    TEXT NOT NULL,
    token           TEXT NOT NULL,
    count           INTEGER DEFAULT 1,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    UNIQUE(duty_name_en, token)
)
"""

DUTY_TOKENS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_duty_tokens ON duty_tokens(duty_name_en, count DESC)
"""

LISTING_TOKENS_TABLE = """
CREATE TABLE IF NOT EXISTS listing_tokens (
    listing_id  INTEGER NOT NULL REFERENCES listings(id),
    token       TEXT NOT NULL,
    PRIMARY KEY (listing_id, token)
)
"""

POLLS_TABLE = """
CREATE TABLE IF NOT EXISTS polls (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    polled_at         TEXT NOT NULL,
    listing_count     INTEGER NOT NULL,
    new_listings      INTEGER NOT NULL,
    updated_listings  INTEGER NOT NULL,
    expired_listings  INTEGER NOT NULL,
    tokens_added      INTEGER NOT NULL DEFAULT 0
)
"""

WATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS watches (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id         TEXT NOT NULL,
    channel_id       TEXT NOT NULL,
    duty_name        TEXT NOT NULL,
    strategy_keyword TEXT,
    data_center      TEXT,
    require_loot     INTEGER DEFAULT 0,
    require_practice INTEGER DEFAULT 0,
    require_clear    INTEGER DEFAULT 0,
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    is_active        INTEGER DEFAULT 1
)
"""

NOTIFIED_TABLE = """
CREATE TABLE IF NOT EXISTS notified_listings (
    watch_id    INTEGER NOT NULL REFERENCES watches(id),
    listing_id  INTEGER NOT NULL REFERENCES listings(id),
    notified_at TEXT NOT NULL,
    PRIMARY KEY (watch_id, listing_id)
)
"""
