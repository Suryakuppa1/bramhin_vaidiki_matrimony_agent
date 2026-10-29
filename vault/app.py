"""Desktop Matrimony Vault UI — local full-detail search including phone numbers.

Run from repo root:
  streamlit run vault/app.py
"""
from __future__ import annotations

import streamlit as st

from display import format_profile_html
from vault.db import clear_all, count_profiles
from vault.ingest import DEFAULT_INBOX, ingest_inbox
from vault.search import search_profiles

st.set_page_config(page_title="Matrimony Vault", page_icon="🗂", layout="wide")

st.markdown(
    """
    <style>
      .block-container { max-width: 920px; padding-top: 1.5rem; }
      h1 { letter-spacing: -0.02em; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Matrimony Vault")
st.caption(
    "Local desktop reader for dumped biodata (txt / Excel / PDF / images / JSON). "
    "Full details including phone numbers. Separate from the Telegram bot database."
)

inbox = DEFAULT_INBOX
inbox.mkdir(parents=True, exist_ok=True)

with st.expander("Import files from vault_inbox/", expanded=count_profiles() == 0):
    st.write(
        f"Put exports in `{inbox}` then ingest. "
        "Supported: `.txt`, `.xlsx`, `.pdf`, `.json`, images (OCR if tesseract is installed)."
    )
    permission = st.checkbox(
        "I confirm I am allowed to store and search these personal profiles locally (including phone numbers)"
    )
    require_consent = st.checkbox("Only import blocks that contain CONSENT:YES", value=False)
    cols = st.columns(3)
    if cols[0].button("Ingest inbox", disabled=not permission, type="primary"):
        with st.spinner("Ingesting…"):
            try:
                stats = ingest_inbox(
                    inbox,
                    permission_confirmed=True,
                    require_consent_tag=require_consent,
                )
                st.success(
                    f"Files {stats['files']}: imported {stats['accepted']}, "
                    f"skipped {stats['skipped']}, errors {stats['errors']}, unsupported {stats['unsupported']}"
                )
            except Exception as exc:
                st.error(f"{type(exc).__name__}: {exc}")
    if cols[1].button("Refresh"):
        st.rerun()
    if cols[2].button("Clear vault DB"):
        n = clear_all()
        st.warning(f"Deleted {n} vault profile(s).")
    st.write(f"Profiles in vault: **{count_profiles()}**")

st.header("Search")
q = st.text_input("Search any text", placeholder="Venkatesh, 93910, Vijayawada, Maka…")

with st.expander("Filters", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    gender = c1.text_input("Gender", placeholder="Male / Female")
    stars = c2.text_input("Nakshatram", placeholder="Maka / Magha")
    padam = c3.text_input("Padam", placeholder="1-4")
    rashi = c4.text_input("Rashi", placeholder="SIMHA")
    c5, c6, c7, c8 = st.columns(4)
    name = c5.text_input("Name contains", "")
    father = c6.text_input("Father contains", "")
    mother = c7.text_input("Mother contains", "")
    phone = c8.text_input("Phone contains", "")
    c9, c10, c11, c12 = st.columns(4)
    birthplace = c9.text_input("Birthplace", "")
    education = c10.text_input("Education", "")
    gotram = c11.text_input("Gotram", "")
    saka = c12.text_input("Saka", "")
    use_age = st.checkbox("Filter by age", False)
    age_range = st.slider("Age", 18, 60, (22, 35), disabled=not use_age)

rows = search_profiles(
    query=q,
    gender=gender,
    name=name,
    father_name=father,
    mother_name=mother,
    stars=stars,
    padam=padam,
    rashi=rashi,
    gotram=gotram,
    saka=saka,
    birthplace=birthplace,
    education=education,
    phone=phone,
    min_age=age_range[0] if use_age else None,
    max_age=age_range[1] if use_age else None,
    limit=200,
)

st.header(f"{len(rows)} result{'s' if len(rows) != 1 else ''}")
st.caption("Each profile is shown as a readable biodata sheet, including phone when present.")

if not rows:
    st.info("No matches yet. Ingest files from vault_inbox/ or loosen filters.")
else:
    for i, profile in enumerate(rows, 1):
        st.markdown(
            format_profile_html(profile, index=i, include_phone=True),
            unsafe_allow_html=True,
        )
