"""Interactive Telegram filter menu built from values present in the local DB."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core import (
    STAR_ALIASES, RASHI_ALIASES, GOTRAM_ALIASES, SAKA_ALIASES, PLACE_ALIASES,
    GENDER_ALIASES, field_value_counts, load_profiles,
)
from preferences import describe_filters, read_filters

# callback_data must stay <= 64 bytes. Use short codes + option index.
FIELD_SPECS = {
    "gender": {"label": "Gender", "profile_field": "gender", "aliases": GENDER_ALIASES, "filter_key": "gender"},
    "stars": {"label": "Nakshatram (star)", "profile_field": "nakshatram", "aliases": STAR_ALIASES, "filter_key": "stars"},
    "padam": {"label": "Padam", "profile_field": "padam", "aliases": None, "filter_key": "padam"},
    "rashi": {"label": "Rashi", "profile_field": "rashi", "aliases": RASHI_ALIASES, "filter_key": "rashi"},
    "gotram": {"label": "Gotram", "profile_field": "gotram", "aliases": GOTRAM_ALIASES, "filter_key": "gotram"},
    "saka": {"label": "Saka / Velanadu", "profile_field": "saka", "aliases": SAKA_ALIASES, "filter_key": "saka"},
    "birthplace": {"label": "Birthplace", "profile_field": "birthplace", "aliases": PLACE_ALIASES, "filter_key": "birthplace"},
    "education": {"label": "Education", "profile_field": "education", "aliases": None, "filter_key": "education"},
    "group": {"label": "Source group", "profile_field": "source_name", "aliases": None, "filter_key": "group"},
}

AGE_PRESETS = [
    ("18-22", 18, 22),
    ("22-26", 22, 26),
    ("23-28", 23, 28),
    ("24-30", 24, 30),
    ("25-32", 25, 32),
    ("28-35", 28, 35),
]


def display_value(value: str) -> str:
    return value.replace("_", " ").strip().title()


def home_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Gender", callback_data="menu:list:gender"),
            InlineKeyboardButton("Age range", callback_data="menu:list:age"),
        ],
        [
            InlineKeyboardButton("Nakshatram", callback_data="menu:list:stars"),
            InlineKeyboardButton("Padam", callback_data="menu:list:padam"),
        ],
        [
            InlineKeyboardButton("Rashi", callback_data="menu:list:rashi"),
            InlineKeyboardButton("Gotram", callback_data="menu:list:gotram"),
        ],
        [
            InlineKeyboardButton("Saka", callback_data="menu:list:saka"),
            InlineKeyboardButton("Birthplace", callback_data="menu:list:birthplace"),
        ],
        [
            InlineKeyboardButton("Education", callback_data="menu:list:education"),
            InlineKeyboardButton("Source group", callback_data="menu:list:group"),
        ],
        [
            InlineKeyboardButton("Show matches", callback_data="menu:act:matches"),
            InlineKeyboardButton("Clear filters", callback_data="menu:act:clear"),
        ],
        [InlineKeyboardButton("Show my filters", callback_data="menu:act:filters")],
    ]
    return InlineKeyboardMarkup(rows)


def home_text(user_id: int, profile_count: int | None = None) -> str:
    profiles = load_profiles() if profile_count is None else None
    count = profile_count if profile_count is not None else len(profiles or [])
    current = describe_filters(read_filters(user_id))
    return (
        f"Filter menu — tap a category, then pick a value from your imported profiles.\n"
        f"Profiles on file: {count}\n"
        f"Current filters: {current}\n\n"
        "Tip: set one field at a time, then tap Show matches."
    )


def options_keyboard(field_code: str, options: list[tuple[str, int]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for index, (value, count) in enumerate(options):
        label = f"{display_value(value)} ({count})"
        if len(label) > 60:
            label = label[:57] + "..."
        # menu:set:<field>:<index>  — value resolved via user_data map
        button = InlineKeyboardButton(label, callback_data=f"menu:set:{field_code}:{index}")
        row.append(button)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back to menu", callback_data="menu:act:home")])
    return InlineKeyboardMarkup(rows)


def age_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for label, lo, hi in AGE_PRESETS:
        row.append(InlineKeyboardButton(f"Age {label}", callback_data=f"menu:age:{lo}:{hi}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back to menu", callback_data="menu:act:home")])
    return InlineKeyboardMarkup(rows)


def build_field_options(field_code: str) -> list[tuple[str, int]]:
    spec = FIELD_SPECS[field_code]
    return field_value_counts(
        load_profiles(),
        field=spec["profile_field"],
        alias_map=spec["aliases"],
        limit=24,
    )
