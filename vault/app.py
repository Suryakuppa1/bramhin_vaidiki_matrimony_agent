"""Desktop Matrimony Vault UI — local full-detail search including phone numbers.

Run from repo root:
  streamlit run vault/app.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from vault.db import clear_all, count_profiles
from vault.ingest import DEFAULT_INBOX, ingest_inbox
from vault.search import search_profiles

st.set_page_config(page_title="Matrimony Vault", page_icon="🗂", layout="wide")
st.title("Matrimony Vault (local desktop)")
st.caption(
    "Private local store. Dump txt / Excel / PDF / images into vault_inbox/, ingest, then search. "
    "Full details including phone numbers are shown here. This DB is separate from the Telegram bot."
)

inbox = DEFAULT_INBOX
inbox.mkdir(parents=True, exist_ok=True)

with st.expander("1) Import from vault_inbox/", expanded=True):
    st.write(f"Drop files into `{inbox}` then ingest. Supported: `.txt`, `.xlsx`, `.pdf`, `.json`, images (OCR if tesseract installed).")
    permission = st.checkbox("I confirm I am allowed to store and search these personal profiles locally (including phone numbers)")
    require_consent = st.checkbox("Only import blocks that contain CONSENT:YES", value=False)
    cols = st.columns(3)
    if cols[0].button("Ingest inbox now", disabled=not permission, type="primary"):
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
    if cols[1].button("Refresh count"):
        st.rerun()
    if cols[2].button("Clear vault DB", type="secondary"):
        n = clear_all()
        st.warning(f"Deleted {n} vault profile(s).")
    st.info(f"Profiles in vault: **{count_profiles()}**")

st.subheader("2) Search")
q = st.text_input("Free-text search (name, phone, place, education, …)", placeholder="Venkatesh OR 93910 OR Vijayawada")
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

st.subheader(f"Results ({len(rows)})")
st.caption("All stored fields are shown — including phone — for local authorized use only.")

if not rows:
    st.write("No matches. Ingest files first or loosen filters.")
else:
    for i, r in enumerate(rows, 1):
        title = r.get("name") or "(unnamed)"
        with st.expander(f"{i}. {title}  |  {r.get('gender') or '—'}  |  phone: {r.get('phone') or 'not provided'}", expanded=i <= 3):
            left, right = st.columns(2)
            with left:
                st.write(
                    {
                        "Name": r.get("name"),
                        "Gender": r.get("gender"),
                        "DOB": r.get("dob"),
                        "Age": r.get("age"),
                        "Father": r.get("father_name"),
                        "Mother": r.get("mother_name"),
                        "Phone": r.get("phone"),
                    }
                )
            with right:
                st.write(
                    {
                        "Nakshatram": r.get("nakshatram"),
                        "Padam": r.get("padam"),
                        "Rashi": r.get("rashi"),
                        "Gotram": r.get("gotram"),
                        "Saka": r.get("saka"),
                        "Birthplace": r.get("birthplace"),
                        "Education": r.get("education"),
                        "Location": r.get("location"),
                        "Source file": r.get("source_file"),
                    }
                )

    preview = [
        {
            "Name": r.get("name"),
            "Gender": r.get("gender"),
            "Age": r.get("age"),
            "Phone": r.get("phone"),
            "Nakshatram": r.get("nakshatram"),
            "Padam": r.get("padam"),
            "Rashi": r.get("rashi"),
            "Birthplace": r.get("birthplace"),
            "Education": r.get("education"),
            "Father": r.get("father_name"),
            "Mother": r.get("mother_name"),
            "Source": r.get("source_file"),
        }
        for r in rows
    ]
    st.dataframe(preview, use_container_width=True, hide_index=True)
