"""Select menus for the desktop Vault. Choices come from profiles already stored."""
from __future__ import annotations

from typing import Any

from core import (
    GOTRAM_ALIASES,
    PLACE_ALIASES,
    RASHI_ALIASES,
    SAKA_ALIASES,
    field_value_counts,
)
from vault.parser import GENDER_ALIASES, STAR_ALIASES_VAULT

ANY = "Any"

# (label, min_age, max_age). Any means do not filter by age.
AGE_CHOICES: list[tuple[str, int | None, int | None]] = [
    (ANY, None, None),
    ("18-22", 18, 22),
    ("22-26", 22, 26),
    ("23-28", 23, 28),
    ("24-30", 24, 30),
    ("25-32", 25, 32),
    ("28-35", 28, 35),
    ("30-40", 30, 40),
    ("35-45", 35, 45),
    ("40-60", 40, 60),
]

# key: widget id, label: menu title, search: search_profiles argument, field: DB column.
FIELD_MENUS: list[dict[str, Any]] = [
    {"key": "gender", "label": "Gender", "search": "gender", "field": "gender", "aliases": GENDER_ALIASES},
    {"key": "name", "label": "Name", "search": "name", "field": "name", "aliases": None},
    {"key": "phone", "label": "Phone", "search": "phone", "field": "phone", "aliases": None},
    {"key": "stars", "label": "Nakshatram", "search": "stars", "field": "nakshatram", "aliases": STAR_ALIASES_VAULT},
    {"key": "padam", "label": "Padam", "search": "padam", "field": "padam", "aliases": None},
    {"key": "rashi", "label": "Rashi", "search": "rashi", "field": "rashi", "aliases": RASHI_ALIASES},
    {"key": "gotram", "label": "Gotram", "search": "gotram", "field": "gotram", "aliases": GOTRAM_ALIASES},
    {"key": "saka", "label": "Saka", "search": "saka", "field": "saka", "aliases": SAKA_ALIASES},
    {"key": "father_name", "label": "Father", "search": "father_name", "field": "father_name", "aliases": None},
    {"key": "mother_name", "label": "Mother", "search": "mother_name", "field": "mother_name", "aliases": None},
    {"key": "birthplace", "label": "Birthplace", "search": "birthplace", "field": "birthplace", "aliases": PLACE_ALIASES},
    {"key": "education", "label": "Education", "search": "education", "field": "education", "aliases": None},
    {"key": "location", "label": "Present place", "search": "location", "field": "location", "aliases": None},
]

MENU_SECTIONS: list[tuple[str, tuple[str, ...]]] = [
    ("Personal", ("gender", "name", "phone")),
    ("Family", ("father_name", "mother_name", "gotram", "saka")),
    ("Astrology", ("stars", "padam", "rashi", "birthplace")),
    ("Education and place", ("education", "location")),
]


def display_value(value: str) -> str:
    return value.replace("_", " ").strip().title()


def age_labels() -> list[str]:
    return [label for label, _lo, _hi in AGE_CHOICES]


def age_bounds(label: str) -> tuple[int | None, int | None]:
    for name, lo, hi in AGE_CHOICES:
        if name == label:
            return lo, hi
    return None, None


def menu_options(profiles: list[dict], spec: dict) -> list[str]:
    """Any, then values that actually appear on stored profiles."""
    counted = field_value_counts(
        profiles,
        field=spec["field"],
        alias_map=spec["aliases"],
        limit=300,
    )
    labels: list[str] = []
    seen: set[str] = set()
    for key, _count in counted:
        label = display_value(str(key))
        token = label.casefold()
        if not label or token in seen or token == ANY.casefold():
            continue
        seen.add(token)
        labels.append(label)
    return [ANY, *labels]


def search_kwargs(selected: dict[str, str], age_label: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {spec["search"]: "" for spec in FIELD_MENUS}
    for spec in FIELD_MENUS:
        value = (selected.get(spec["key"]) or ANY).strip()
        if value and value != ANY:
            kwargs[spec["search"]] = value
    lo, hi = age_bounds(age_label)
    kwargs["min_age"] = lo
    kwargs["max_age"] = hi
    return kwargs


def describe_selection(selected: dict[str, str], age_label: str) -> str:
    parts: list[str] = []
    if age_label and age_label != ANY:
        parts.append(f"Age {age_label}")
    for spec in FIELD_MENUS:
        value = (selected.get(spec["key"]) or ANY).strip()
        if value and value != ANY:
            parts.append(f"{spec['label']}: {value}")
    return " · ".join(parts) if parts else "All stored profiles"
