"""Parse labeled biodata for the local Vault (phones kept)."""
from __future__ import annotations

import re
from typing import Any

from core import (
    STAR_ALIASES, RASHI_ALIASES, GOTRAM_ALIASES, SAKA_ALIASES, PLACE_ALIASES,
    canonical, get_age, normalized, parse_dob, normalized_star,
)

VAULT_FIELDS = (
    "name", "gender", "father_name", "mother_name", "dob", "age",
    "nakshatram", "padam", "rashi", "gotram", "saka",
    "birthplace", "birthtime", "education", "location", "phone",
)

GENDER_ALIASES = {
    "male": ["male", "m", "boy", "groom", "man", "పురుషుడు", "మగ"],
    "female": ["female", "f", "girl", "bride", "woman", "స్త్రీ", "ఆడ"],
}

# Extend Magha with common "Maka" spelling used in biodata dumps.
STAR_ALIASES_VAULT = {
    **STAR_ALIASES,
    "magha": list(dict.fromkeys([*STAR_ALIASES.get("magha", []), "maka", "makaa", "మఖా"])),
}

LABELS = {
    "name": ("name", "bride name", "girl name", "groom name", "boy name", "పేరు", "వధువు పేరు", "వరుడు పేరు"),
    "gender": ("gender", "sex", "లింగం"),
    "father_name": ("father name", "father's name", "fathername", "s/o", "so", "తండ్రి పేరు", "తండ్రి"),
    "mother_name": ("mother name", "mother's name", "mothername", "d/o", "do", "మాత పేరు", "తల్లి పేరు", "తల్లి"),
    "dob": ("dob", "date of birth", "birth date", "పుట్టిన తేదీ", "జన్మ తేదీ"),
    "age": ("age", "వయస్సు"),
    "nakshatram": ("nakshatram", "nakshatra", "star", "birth star", "నక్షత్రం"),
    "padam": ("padam", "paadam", "pada", "పాదం", "పదం"),
    "rashi": ("rashi", "raasi", "rasi", "రాశి"),
    "gotram": ("gotram", "gothram", "gotra", "గోత్రం", "గోత్రము"),
    "saka": ("saka", "sakha", "sect", "subsect", "sub sect", "velanadu", "vaidiki",
             "సాఖ", "శాఖ", "వేలనాడు", "వైదికి", "వైదికి వేలనాడు"),
    "birthplace": ("place of birth", "birthplace", "birth place", "born at", "జన్మస్థలం", "పుట్టిన స్థలం"),
    "birthtime": ("time of birth", "birth time", "జన్మ సమయం", "పుట్టిన సమయం"),
    "education": ("education", "qualification", "degree", "విద్య", "చదువు"),
    "location": ("current city", "present location", "current location", "residing at", "నివాసం", "ప్రస్తుత నగరం"),
    "phone": (
        "contact", "contact number", "contactnumber", "phone", "phone number",
        "mobile", "mobile number", "whatsapp", "whatsapp number", "cell",
        "ఫోన్", "మొబైల్", "సంప్రదింపు",
    ),
}

PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-()]{8,}\d)")


def split_star_and_padam(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    text = value.strip()
    match = re.search(r"(?:,|/|-|\s)\s*([1-4])(?:st|nd|rd|th)?\s*padams?\b", text, re.I)
    if match:
        return text[: match.start()].strip(" ,/-") or None, match.group(1)
    only = re.fullmatch(r"\s*([1-4])(?:st|nd|rd|th)?\s*padams?\s*", text, re.I)
    if only:
        return None, only.group(1)
    return text or None, None


def normalize_phones(value: str | None) -> str | None:
    if not value:
        return None
    found = PHONE_RE.findall(value)
    cleaned = []
    for item in found:
        digits = re.sub(r"\D", "", item)
        if len(digits) >= 10:
            cleaned.append(digits[-10:] if len(digits) > 12 else digits)
    # Also keep original labeled text if no regex hit but value looks useful
    if not cleaned and re.search(r"\d{10}", value):
        return re.sub(r"\s+", " ", value).strip()[:160]
    return ", ".join(dict.fromkeys(cleaned)) if cleaned else None


def parse_vault_profile(text: str) -> dict[str, Any] | None:
    """Extract a vault profile including phone numbers from labeled text."""
    extracted: dict[str, Any] = {field: None for field in VAULT_FIELDS}
    for line in text.splitlines():
        m = re.match(r"^\s*([^:：\-–]{2,50})\s*[:：\-–]\s*(.+?)\s*$", line)
        if not m:
            continue
        key, value = normalized(m.group(1)).strip("* _"), m.group(2).strip("* _")
        if not value:
            continue
        for field, possible in LABELS.items():
            if key in possible:
                extracted[field] = value[:200]
                break
    if extracted["dob"]:
        extracted["dob"] = parse_dob(extracted["dob"])
    if extracted["age"]:
        try:
            m_age = re.search(r"\b(1[89]|[2-7]\d)\b", str(extracted["age"]))
            extracted["age"] = int(m_age.group(1)) if m_age else None
        except (ValueError, AttributeError):
            extracted["age"] = None
    extracted["age"] = get_age(extracted["dob"], extracted["age"])
    if extracted["nakshatram"]:
        star_raw, padam_from_star = split_star_and_padam(extracted["nakshatram"])
        if padam_from_star and not extracted.get("padam"):
            extracted["padam"] = padam_from_star
        extracted["nakshatram"] = canonical(star_raw, STAR_ALIASES_VAULT) if star_raw else None
    if extracted.get("padam"):
        padam_match = re.search(r"\b([1-4])\b", str(extracted["padam"]))
        extracted["padam"] = padam_match.group(1) if padam_match else None
    if extracted.get("gender"):
        extracted["gender"] = canonical(extracted["gender"], GENDER_ALIASES) or None
    if extracted["rashi"]:
        extracted["rashi"] = canonical(extracted["rashi"], RASHI_ALIASES)
    if extracted["gotram"]:
        extracted["gotram"] = canonical(extracted["gotram"], GOTRAM_ALIASES)
    if extracted["saka"]:
        extracted["saka"] = canonical(extracted["saka"], SAKA_ALIASES)
    if extracted["birthplace"]:
        place = canonical(extracted["birthplace"], PLACE_ALIASES)
        if place in PLACE_ALIASES:
            extracted["birthplace"] = place
    extracted["phone"] = normalize_phones(extracted.get("phone"))
    if not extracted["phone"]:
        extracted["phone"] = normalize_phones(text)

    present = sum(bool(extracted[x]) for x in (
        "name", "dob", "age", "nakshatram", "phone", "education", "birthplace", "gender"))
    signal = bool(re.search(
        r"\b(bride|groom|matrimony|marriage|biodata|profile|consent)\b|వధువు|వరుడు|వివాహం",
        text, re.I,
    ))
    if present < 2 and not (signal and present >= 1):
        return None
    if not extracted.get("name") and not extracted.get("phone"):
        return None
    return extracted


def build_search_blob(profile: dict) -> str:
    parts = [str(profile.get(f) or "") for f in VAULT_FIELDS]
    return " ".join(p for p in parts if p)
