import json
from dataclasses import dataclass, field

from .worlds import WORLD_TO_DC
from config import DUTY_OVERRIDES, DUTY_NAME_NORMALIZATIONS


def _normalize_duty_name(name: str) -> str:
    lower = name.lower()
    for key, canonical in DUTY_NAME_NORMALIZATIONS.items():
        if key in lower:
            return canonical
    return name


def _apply_override(category: str | None, min_item_level: int, description_en: str) -> str | None:
    for override in DUTY_OVERRIDES:
        if override.get("category") and override["category"] != category:
            continue
        if "min_item_level_gte" in override and min_item_level < override["min_item_level_gte"]:
            continue
        if "description_contains" in override:
            desc_lower = description_en.lower()
            if not any(kw in desc_lower for kw in override["description_contains"]):
                continue
        return override["name"]
    return None


@dataclass
class Listing:
    id: int
    recruiter: str
    home_world: str
    current_world: str
    data_center: str | None
    description_en: str
    duty_name_en: str | None
    category: str | None
    content_kind: str | None
    min_item_level: int
    slot_count: int
    slots_filled: list[str | None]
    slots_open: int
    obj_duty_completion: bool
    obj_practice: bool
    obj_loot: bool
    cond_duty_complete: bool
    one_player_per_job: bool
    created_at: str
    updated_at: str
    tags: list[str] = field(default_factory=list)


def parse_listing(raw: dict) -> Listing:
    lst = raw["listing"]

    duty_name_en: str | None = None
    category: str | None = lst.get("category")
    content_kind: str | None = None
    if lst.get("duty_info"):
        duty_info = lst["duty_info"]
        names = duty_info.get("name") or {}
        duty_name_en = names.get("en") or names.get("ja") or names.get("de") or names.get("fr")
        if duty_name_en:
            duty_name_en = _normalize_duty_name(duty_name_en)
        content_kind = duty_info.get("content_kind")

    desc_for_override = (lst.get("description") or {}).get("en", "") or ""
    if duty_name_en is None:
        duty_name_en = _apply_override(category, lst.get("min_item_level") or 0, desc_for_override)

    current_world = lst["current_world"]["name"]
    home_world = lst["home_world"]["name"]
    data_center = WORLD_TO_DC.get(current_world)

    slots_filled: list[str | None] = lst.get("slots_filled") or []
    slots_open = sum(1 for s in slots_filled if s is None)

    desc = lst.get("description") or {}
    description_en = desc.get("en") or desc.get("ja") or desc.get("de") or desc.get("fr") or ""

    obj = lst.get("objective") or {}
    cond = lst.get("conditions") or {}
    search = lst.get("search_area") or {}

    obj_duty_completion = bool(obj.get("duty_completion"))
    obj_practice = bool(obj.get("practice"))
    obj_loot = bool(obj.get("loot"))
    cond_duty_complete = bool(cond.get("duty_complete"))
    one_player_per_job = bool(search.get("one_player_per_job"))

    tags: list[str] = []
    if obj_duty_completion:
        tags.append("Duty Completion")
    if obj_practice:
        tags.append("Practice")
    if obj_loot:
        tags.append("Loot")
    if cond_duty_complete:
        tags.append("Duty Complete")
    if one_player_per_job:
        tags.append("One Player per Job")
    loot_rules = lst.get("loot_rules") or {}
    if loot_rules.get("lootmaster"):
        tags.append("Lootmaster")

    return Listing(
        id=lst["id"],
        recruiter=lst.get("recruiter", ""),
        home_world=home_world,
        current_world=current_world,
        data_center=data_center,
        description_en=description_en,
        duty_name_en=duty_name_en,
        category=category,
        content_kind=content_kind,
        min_item_level=lst.get("min_item_level") or 0,
        slot_count=lst.get("slot_count") or 8,
        slots_filled=slots_filled,
        slots_open=slots_open,
        obj_duty_completion=obj_duty_completion,
        obj_practice=obj_practice,
        obj_loot=obj_loot,
        cond_duty_complete=cond_duty_complete,
        one_player_per_job=one_player_per_job,
        created_at=raw.get("created_at") or lst.get("created_at") or "",
        updated_at=raw.get("updated_at") or lst.get("updated_at") or "",
        tags=tags,
    )
