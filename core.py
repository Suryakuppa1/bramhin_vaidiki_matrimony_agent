"""Local profile extraction, deduplication and filtering.
Never sends profile text to external AI services.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "data" / "profiles.sqlite3"
FIELDS = (
    "name", "dob", "age", "nakshatram", "rashi", "gotram", "saka",
    "birthplace", "birthtime", "education", "location",
)
LABELS = {
    "name": ("name", "bride name", "girl name", "పేరు", "వధువు పేరు"),
    "dob": ("dob", "date of birth", "birth date", "పుట్టిన తేదీ", "జన్మ తేదీ"),
    "age": ("age", "వయస్సు"),
    "nakshatram": ("nakshatram", "nakshatra", "star", "birth star", "నక్షత్రం"),
    "rashi": ("rashi", "raasi", "rasi", "రాశి"),
    "gotram": ("gotram", "gothram", "gotra", "గోత్రం", "గోత్రము"),
    "saka": ("saka", "sakha", "sect", "subsect", "sub sect", "velanadu", "vaidiki",
             "సాఖ", "శాఖ", "వేలనాడు", "వైదికి", "వైదికి వేలనాడు"),
    "birthplace": ("place of birth", "birthplace", "birth place", "born at", "జన్మస్థలం", "పుట్టిన స్థలం"),
    "birthtime": ("time of birth", "birth time", "జన్మ సమయం", "పుట్టిన సమయం"),
    "education": ("education", "qualification", "degree", "విద్య", "చదువు"),
    "location": ("current city", "present location", "current location", "residing at", "నివాసం", "ప్రస్తుత నగరం"),
}
# Telugu + English spellings normalize to one key so either language matches in search.
STAR_ALIASES = {
    "rohini": ["rohini", "రోహిణి"], "swati": ["swati", "swathi", "స్వాతి"],
    "ashwini": ["ashwini", "aswini", "అశ్విని"], "bharani": ["bharani", "భరణి"],
    "krithika": ["krithika", "krittika", "kritika", "కృత్తిక"],
    "mrigashira": ["mrigashira", "mrigasira", "మృగశిర"],
    "ardra": ["ardra", "arudra", "ఆర్ద్ర"], "punarvasu": ["punarvasu", "పునర్వసు"],
    "pushyami": ["pushyami", "pushya", "పుష్యమి"], "aslesha": ["aslesha", "ashlesha", "ఆశ్లేష"],
    "magha": ["magha", "makha", "మఖ"], "pubba": ["pubba", "purva phalguni", "పుబ్బ"],
    "uttara": ["uttara", "uttara phalguni", "ఉత్తర"], "hasta": ["hasta", "హస్త"],
    "chitta": ["chitta", "chitra", "చిత్త"], "visakha": ["visakha", "vishakha", "విశాఖ"],
    "anuradha": ["anuradha", "అనూరాధ"], "jyestha": ["jyestha", "jyeshta", "జ్యేష్ఠ"],
    "moola": ["moola", "mula", "మూల"], "purvashada": ["purvashada", "poorvashada", "పూర్వాషాఢ"],
    "uttarashada": ["uttarashada", "uttara ashadha", "ఉత్తరాషాఢ"],
    "sravana": ["sravana", "shravana", "శ్రవణం"], "dhanishta": ["dhanishta", "ధనిష్ఠ"],
    "satabhisham": ["satabhisham", "shatabhisha", "శతభిషం"],
    "purvabhadra": ["purvabhadra", "poorvabhadra", "పూర్వాభాద్ర"],
    "uttarabhadra": ["uttarabhadra", "ఉత్తరాభాద్ర"], "revati": ["revati", "రేవతి"],
}
RASHI_ALIASES = {
    "mesha": ["mesha", "aries", "మేష"],
    "vrishabha": ["vrishabha", "vrishaba", "rishabha", "taurus", "వృషభ"],
    "mithuna": ["mithuna", "gemini", "మిథున"],
    "karka": ["karka", "kataka", "cancer", "కర్కాటక", "కర్క"],
    "simha": ["simha", "leo", "సింహ"],
    "kanya": ["kanya", "virgo", "కన్య"],
    "tula": ["tula", "thula", "libra", "తుల"],
    "vrischika": ["vrischika", "vrishchika", "scorpio", "వృశ్చిక"],
    "dhanu": ["dhanu", "dhanus", "sagittarius", "ధనుస్సు", "ధనుస్"],
    "makara": ["makara", "capricorn", "మకర"],
    "kumbha": ["kumbha", "aquarius", "కుంభ"],
    "meena": ["meena", "pisces", "మీన"],
}
GOTRAM_ALIASES = {
    "bharadwaja": ["bharadwaja", "bharadwaj", "bharadvaja", "భరద్వాజ", "భరద్వాజస"],
    "kashyapa": ["kashyapa", "kasyapa", "కశ్యప"],
    "atri": ["atri", "అత్రి"],
    "vasishtha": ["vasishtha", "vashishta", "vasista", "వసిష్ఠ"],
    "gautama": ["gautama", "gauthama", "గౌతమ"],
    "jamadagni": ["jamadagni", "జమదగ్ని"],
    "vishwamitra": ["vishwamitra", "viswamitra", "విశ్వామిత్ర"],
    "kaundinya": ["kaundinya", "kowndinya", "కౌండిన్య"],
    "srivatsa": ["srivatsa", "shrivatsa", "శ్రీవత్స"],
    "harita": ["harita", "haarita", "హారీత", "హరిత"],
    "kaushika": ["kaushika", "koushika", "కౌశిక"],
    "moudgalya": ["moudgalya", "maudgalya", "మౌద్గల్య"],
    "shandilya": ["shandilya", "sandilya", "శాండిల్య"],
    "agastya": ["agastya", "అగస్త్య"],
}
SAKA_ALIASES = {
    "vaidiki_velanadu": [
        "vaidiki velanadu", "vaidiki velanadu brahmin", "velanadu", "velanati",
        "vaidiki", "వైదికి వేలనాడు", "వేలనాడు", "వేలనాటి", "వైదికి",
    ],
    "vaidiki_venginadu": ["vaidiki venginadu", "venginadu", "వైదికి వేంగినాడు", "వేంగినాడు"],
    "vaidiki_kosalanadu": ["vaidiki kosalanadu", "kosalanadu", "వైదికి కోసలనాడు", "కోసలనాడు"],
    "niyogi": ["niyogi", "నియోగి"],
    "dravida": ["dravida", "ద్రావిడ"],
}
PLACE_ALIASES = {
    "hyderabad": ["hyderabad", "hyd", "హైదరాబాద్", "హైదరాబాదు"],
    "vijayawada": ["vijayawada", "bezawada", "విజయవాడ"],
    "visakhapatnam": ["visakhapatnam", "vizag", "విశాఖపట్నం"],
    "tirupati": ["tirupati", "tirupathi", "తిరుపతి"],
    "guntur": ["guntur", "గుంటూరు"],
    "nellore": ["nellore", "నెల్లూరు"],
    "kakinada": ["kakinada", "కాకినాడ"],
    "rajahmundry": ["rajahmundry", "rajahmundry", "రాజమండ్రి"],
    "warangal": ["warangal", "వరంగల్"],
    "chennai": ["chennai", "madras", "చెన్నై"],
    "bangalore": ["bangalore", "bengaluru", "బెంగళూరు", "బెంగళూర్"],
}
# Back-compat for older imports/tests.
ALIASES = STAR_ALIASES


def normalized(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().casefold())


def canonical(value: str | None, alias_map: dict[str, list[str]]) -> str:
    """Map Telugu/English variants onto one search key."""
    s = normalized(value)
    if not s:
        return ""
    for key, variants in alias_map.items():
        if s == key or s in variants:
            return key
    return s


def normalized_star(value: str | None) -> str:
    return canonical(value, STAR_ALIASES)


def field_value_counts(
    profiles: list[dict],
    *,
    field: str,
    alias_map: dict[str, list[str]] | None = None,
    limit: int = 24,
) -> list[tuple[str, int]]:
    """Count canonical values for a profile field among adult non-duplicate rows."""
    counts: dict[str, int] = {}
    for profile in profiles:
        if profile.get("duplicate_of"):
            continue
        age = get_age(profile.get("dob"), profile.get("age"))
        if age is not None and age < 18:
            continue
        raw = profile.get(field)
        if not raw:
            continue
        key = canonical(str(raw), alias_map) if alias_map else normalized(str(raw))
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]


def field_choices_match(filter_value: str, profile_value: str | None, *,
                        alias_map: dict[str, list[str]] | None = None,
                        mode: str = "exact") -> bool | None:
    """OR across comma-separated filter choices. None => profile field missing."""
    choices = [v.strip() for v in (filter_value or "").split(",") if v.strip()]
    if not choices:
        return True
    raw = normalized(profile_value)
    if not raw:
        return None
    profile_key = canonical(profile_value, alias_map) if alias_map else raw
    for choice in choices:
        choice_key = canonical(choice, alias_map) if alias_map else normalized(choice)
        if mode == "exact":
            if choice_key and choice_key == profile_key:
                return True
        else:
            if choice_key and (choice_key in profile_key or profile_key in choice_key or choice_key == profile_key):
                return True
            if normalized(choice) and normalized(choice) in raw:
                return True
    return False


def parse_dob(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%d %b %Y", "%d %B %Y"):
        try:
            result = datetime.strptime(value, fmt).date()
            if date(1900, 1, 1) <= result <= date.today():
                return result.isoformat()
        except ValueError:
            continue
    return None


def get_age(dob: str | None, fallback: int | None = None, today: date | None = None) -> int | None:
    if dob:
        try:
            d = date.fromisoformat(dob)
            now = today or date.today()
            return now.year - d.year - ((now.month, now.day) < (d.month, d.day))
        except (ValueError, TypeError):
            pass
    return fallback


def parse_profile(text: str) -> dict | None:
    """Conservative extractor for labeled Telugu/English matrimonial messages.
    Unlabeled content and images are intentionally queued for manual review externally.
    """
    extracted: dict[str, Any] = {field: None for field in FIELDS}
    for line in text.splitlines():
        # Keep DOB strings with dashes; only recognize a labeled key/value pair.
        m = re.match(r"^\s*([^:：\-–]{2,50})\s*[:：\-–]\s*(.+?)\s*$", line)
        if not m:
            continue
        key, value = normalized(m.group(1)).strip("* _"), m.group(2).strip("* _")
        if not value:
            continue
        for field, possible in LABELS.items():
            if key in possible:
                extracted[field] = value[:160]
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
        extracted["nakshatram"] = normalized_star(extracted["nakshatram"])
    if extracted["rashi"]:
        extracted["rashi"] = canonical(extracted["rashi"], RASHI_ALIASES)
    if extracted["gotram"]:
        extracted["gotram"] = canonical(extracted["gotram"], GOTRAM_ALIASES)
    if extracted["saka"]:
        extracted["saka"] = canonical(extracted["saka"], SAKA_ALIASES)
    if extracted["birthplace"]:
        place = canonical(extracted["birthplace"], PLACE_ALIASES)
        # Keep original city text when unknown; only replace known bilingual aliases.
        if place in PLACE_ALIASES:
            extracted["birthplace"] = place
    # Avoid collecting unrelated group chat accidentally.
    present = sum(bool(extracted[x]) for x in (
        "name", "dob", "age", "nakshatram", "gotram", "saka", "birthplace", "education"))
    signal = bool(re.search(r"\b(bride|matrimony|marriage|biodata|profile)\b|వధువు|వివాహం|#marriageprofile", text, re.I))
    if present < 2 and not (signal and present >= 1):
        return None
    return extracted


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS profiles (
       id TEXT PRIMARY KEY, name TEXT, dob TEXT, age INTEGER, nakshatram TEXT,
       rashi TEXT, gotram TEXT, saka TEXT, birthplace TEXT, birthtime TEXT,
       education TEXT, location TEXT,
       source_name TEXT NOT NULL, source_ref TEXT NOT NULL,
       source_kind TEXT NOT NULL, submitted_by TEXT, message_date TEXT,
       fingerprint TEXT, duplicate_of TEXT, inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    existing = {row[1] for row in con.execute("PRAGMA table_info(profiles)")}
    for column in ("gotram", "saka"):
        if column not in existing:
            con.execute(f"ALTER TABLE profiles ADD COLUMN {column} TEXT")
    con.execute("CREATE INDEX IF NOT EXISTS idx_profile_name ON profiles(name)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_profile_star ON profiles(nakshatram)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_profile_gotram ON profiles(gotram)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_profile_saka ON profiles(saka)")
    con.commit()
    return con


def _duplicate_of_for(con: sqlite3.Connection, uid: str, fingerprint: str | None) -> str | None:
    """Point new same-name+DOB rows at an existing canonical peer; never demote that canonical row."""
    if not fingerprint:
        return None
    canonical = con.execute(
        "SELECT id FROM profiles WHERE fingerprint=? AND id<>? AND duplicate_of IS NULL "
        "ORDER BY inserted_at ASC, id ASC LIMIT 1",
        (fingerprint, uid),
    ).fetchone()
    if canonical:
        return canonical["id"]
    peer = con.execute(
        "SELECT id FROM profiles WHERE fingerprint=? AND id<>? ORDER BY inserted_at ASC, id ASC LIMIT 1",
        (fingerprint, uid),
    ).fetchone()
    if not peer:
        return None
    me = con.execute("SELECT id FROM profiles WHERE id=?", (uid,)).fetchone()
    # Brand-new source message → mark as duplicate. Existing row with no canonical peer stays visible.
    return peer["id"] if me is None else None


def repair_duplicate_flags(con: sqlite3.Connection | None = None) -> int:
    """Heal mutual duplicate_of links so each fingerprint keeps one visible canonical row."""
    own = con is None
    if own:
        con = connect()
    try:
        fixed = 0
        fingerprints = [
            row["fingerprint"]
            for row in con.execute(
                "SELECT fingerprint FROM profiles WHERE fingerprint IS NOT NULL GROUP BY fingerprint"
            )
        ]
        for fingerprint in fingerprints:
            preferred = con.execute(
                "SELECT id FROM profiles WHERE fingerprint=? AND duplicate_of IS NULL "
                "ORDER BY inserted_at ASC, id ASC LIMIT 1",
                (fingerprint,),
            ).fetchone()
            rows = con.execute(
                "SELECT id FROM profiles WHERE fingerprint=? ORDER BY inserted_at ASC, id ASC",
                (fingerprint,),
            ).fetchall()
            if not rows:
                continue
            canonical = preferred["id"] if preferred else rows[0]["id"]
            cur = con.execute(
                "UPDATE profiles SET duplicate_of=NULL WHERE id=? AND duplicate_of IS NOT NULL",
                (canonical,),
            )
            fixed += cur.rowcount
            for row in rows:
                if row["id"] == canonical:
                    continue
                cur = con.execute(
                    "UPDATE profiles SET duplicate_of=? WHERE id=? AND IFNULL(duplicate_of, '') != ?",
                    (canonical, row["id"], canonical),
                )
                fixed += cur.rowcount
        if own:
            con.commit()
        return fixed
    finally:
        if own:
            con.close()


def store_profile(profile: dict, *, source_name: str, source_ref: str,
                  source_kind: str, submitted_by: str | None = None,
                  message_date: str | None = None) -> bool:
    """Upsert by unique source message. Does not persist complete message text."""
    uid = hashlib.sha256(f"{source_kind}:{source_name}:{source_ref}".encode()).hexdigest()[:24]
    name, dob = normalized(profile.get("name")), profile.get("dob")
    fingerprint = hashlib.sha256(f"{name}|{dob}".encode()).hexdigest()[:20] if name and dob else None
    con = connect()
    try:
        original = _duplicate_of_for(con, uid, fingerprint)
        values = [uid] + [profile.get(f) for f in FIELDS] + [source_name, source_ref, source_kind,
                     submitted_by, message_date, fingerprint, original]
        # SQL parameterized; upsert is idempotent after reimport.
        cols = ["id", *FIELDS, "source_name", "source_ref", "source_kind", "submitted_by", "message_date", "fingerprint", "duplicate_of"]
        update = ",".join(f"{field}=excluded.{field}" for field in cols if field != "id")
        con.execute(f"INSERT INTO profiles({','.join(cols)}) VALUES({','.join(['?']*len(cols))}) ON CONFLICT(id) DO UPDATE SET {update}", values)
        repair_duplicate_flags(con)
        con.commit()
        return True
    finally:
        con.close()


def load_profiles() -> list[dict]:
    con = connect()
    try:
        # Self-heal DBs corrupted by older mutual duplicate_of tagging on reimport.
        if repair_duplicate_flags(con):
            con.commit()
        return [dict(row) for row in con.execute("SELECT * FROM profiles ORDER BY inserted_at DESC, id DESC")]
    finally:
        con.close()


def delete_profile(profile_id: str) -> int:
    con = connect()
    try:
        cur = con.execute("DELETE FROM profiles WHERE id=?", (profile_id,))
        con.commit()
        return cur.rowcount
    finally:
        con.close()


def delete_by_submitter(submitter_id: str) -> int:
    con = connect()
    try:
        cur = con.execute("DELETE FROM profiles WHERE submitted_by=?", (submitter_id,))
        con.commit()
        return cur.rowcount
    finally:
        con.close()


def is_match(profile: dict, *, min_age: int | None = None, max_age: int | None = None,
             stars: str = "", birthplace: str = "", education: str = "",
             rashi: str = "", gotram: str = "", saka: str = "", name: str = "",
             dob_start: date | None = None, dob_end: date | None = None) -> str:
    """Returns Match / Needs review / No match. Missing fields never match silently.

    Telugu and English aliases for star/rashi/gotram/saka/place compare as the same value.
    """
    missing = False
    age = get_age(profile.get("dob"), profile.get("age"))
    if min_age is not None or max_age is not None:
        if age is None:
            missing = True
        elif (min_age is not None and age < min_age) or (max_age is not None and age > max_age):
            return "No match"
    checks = [
        ("name", name, None, "contains"),
        ("nakshatram", stars, STAR_ALIASES, "exact"),
        ("rashi", rashi, RASHI_ALIASES, "exact"),
        ("gotram", gotram, GOTRAM_ALIASES, "exact"),
        ("saka", saka, SAKA_ALIASES, "exact"),
        ("birthplace", birthplace, PLACE_ALIASES, "contains"),
        ("education", education, None, "contains"),
    ]
    for field, filter_value, alias_map, mode in checks:
        result = field_choices_match(filter_value, profile.get(field), alias_map=alias_map, mode=mode)
        if result is None:
            missing = True
        elif result is False:
            return "No match"
    if dob_start or dob_end:
        if not profile.get("dob"):
            missing = True
        else:
            d = date.fromisoformat(profile["dob"])
            if (dob_start and d < dob_start) or (dob_end and d > dob_end):
                return "No match"
    return "Needs review" if missing else "Match"


_CONSENT_RE = re.compile(
    r"(?:^|\n)\s*(?:/submit(?:@\w+)?\s+)?CONSENT\s*:\s*YES\b", re.I
)
# WhatsApp / some Telegram copy exports prefix each line with a timestamp + sender.
_CHAT_PREFIX_RE = re.compile(
    r"^(?:"
    r"\[\d{1,2}[./-]\d{1,2}[./-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?\]\s*[^:\n]{1,80}:\s*"
    r"|"
    r"\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?:\s*[APap][Mm])?\s*-\s*[^:\n]{1,80}:\s*"
    r")"
)
_TEXT_SUFFIXES = {".txt", ".text"}
_JSON_SUFFIXES = {".json"}
_SKIP_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".mp4", ".opus", ".ogg", ".wav", ".m4a", ".aac",
    ".zip", ".rar", ".7z", ".gz",
}


def strip_chat_prefixes(text: str) -> str:
    """Remove WhatsApp/Telegram timestamp+sender prefixes so labeled fields remain."""
    return "\n".join(_CHAT_PREFIX_RE.sub("", line) for line in text.splitlines())


def split_profile_blocks(text: str) -> list[str]:
    """Split an export into candidate biodata blocks."""
    cleaned = strip_chat_prefixes(text)
    if _CONSENT_RE.search(cleaned):
        parts = re.split(
            r"(?=(?:^|\n)\s*(?:/submit(?:@\w+)?\s+)?CONSENT\s*:\s*YES\b)",
            cleaned,
            flags=re.I,
        )
        return [part.strip() for part in parts if part.strip()]
    return [block.strip() for block in re.split(r"\n\s*\n+", cleaned) if block.strip()]


def import_export_json(payload: bytes, *, filename: str, permission_confirmed: bool) -> tuple[int, int]:
    if not permission_confirmed:
        raise ValueError("Import requires confirmed permission to process these profiles.")
    obj = json.loads(payload.decode("utf-8-sig"))
    messages = obj.get("messages", [])
    if not isinstance(messages, list):
        raise ValueError("Telegram JSON expected: messages[]")
    source_name = str(obj.get("name") or filename)[:150]
    accepted = reviewed = 0
    for message in messages:
        if not isinstance(message, dict) or message.get("type") not in (None, "message"):
            continue
        parts = message.get("text", "")
        if isinstance(parts, list):
            raw = "".join(part if isinstance(part, str) else str(part.get("text", "")) for part in parts)
        else:
            raw = str(parts)
        if not raw.strip():
            continue
        # In historical exports, do not silently index posts with no explicit
        # documented opt-in. Group access alone is not subject consent.
        if not _CONSENT_RE.search(raw):
            reviewed += 1
            continue
        profile = parse_profile(raw)
        if profile is None:
            reviewed += 1
            continue
        store_profile(profile, source_name=source_name,
                      source_ref=str(message.get("id") or hashlib.sha256(raw.encode()).hexdigest()[:16]),
                      source_kind="telegram_export", message_date=str(message.get("date") or ""))
        accepted += 1
    return accepted, reviewed


def import_text_export(
    text: str,
    *,
    filename: str,
    permission_confirmed: bool,
    require_consent_tag: bool = True,
) -> tuple[int, int]:
    """Import labeled profiles from a plain-text / WhatsApp chat export."""
    if not permission_confirmed:
        raise ValueError("Import requires confirmed permission to process these profiles.")
    source_name = Path(filename).stem.replace("_", " ")[:150] or filename[:150]
    accepted = skipped = 0
    for index, block in enumerate(split_profile_blocks(text), 1):
        if require_consent_tag and not _CONSENT_RE.search(block):
            skipped += 1
            continue
        profile = parse_profile(block)
        if profile is None or not profile.get("name") or not get_age(profile.get("dob"), profile.get("age")):
            skipped += 1
            continue
        age = get_age(profile.get("dob"), profile.get("age"))
        if age is not None and age < 18:
            skipped += 1
            continue
        ref = hashlib.sha256(f"{filename}:{index}:{profile.get('name')}|{profile.get('dob')}".encode()).hexdigest()[:16]
        store_profile(
            profile,
            source_name=source_name,
            source_ref=ref,
            source_kind="resources_text",
            message_date="",
        )
        accepted += 1
    return accepted, skipped


def import_resources_dir(
    directory: Path,
    *,
    permission_confirmed: bool,
    require_consent_tag: bool = True,
) -> dict[str, int]:
    """Scan resources/ for text + JSON exports. Skips images and other binaries."""
    if not permission_confirmed:
        raise ValueError("Import requires confirmed permission to process these profiles.")
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Resources folder not found: {directory}")
    stats = {"accepted": 0, "skipped": 0, "files": 0, "ignored_media": 0}
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.name.upper().startswith("PUT_EXPORTS_HERE"):
            continue
        suffix = path.suffix.casefold()
        if suffix in _SKIP_SUFFIXES:
            stats["ignored_media"] += 1
            continue
        if suffix in _JSON_SUFFIXES:
            yes, other = import_export_json(
                path.read_bytes(), filename=path.name, permission_confirmed=True
            )
            stats["accepted"] += yes
            stats["skipped"] += other
            stats["files"] += 1
            continue
        if suffix in _TEXT_SUFFIXES or suffix == "":
            # Allow extensionless text dumps people sometimes save.
            if suffix == "" and path.stat().st_size > 2_000_000:
                stats["ignored_media"] += 1
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            yes, other = import_text_export(
                text,
                filename=str(path.relative_to(directory)),
                permission_confirmed=True,
                require_consent_tag=require_consent_tag,
            )
            stats["accepted"] += yes
            stats["skipped"] += other
            stats["files"] += 1
            continue
        stats["ignored_media"] += 1
    return stats
