"""Desktop Wedding Vault — import files, pick fields from menus, submit for biodata.

Run from repo root:
  python run_vault.py
  python -m streamlit run vault/app.py
"""
from __future__ import annotations

import streamlit as st

from display import format_profile_html, format_vault_report, vault_hero_html, vault_stylesheet
from vault.db import clear_all, count_profiles, load_all
from vault.export import to_docx, to_xlsx
from vault.ingest import DEFAULT_INBOX, ingest_inbox, ingest_uploaded
from vault.menus import (
    ANY,
    FIELD_MENUS,
    MENU_SECTIONS,
    age_labels,
    describe_selection,
    menu_options,
    search_kwargs,
)
from vault.search import search_profiles

st.set_page_config(page_title="Wedding Vault", page_icon="💍", layout="wide")
st.markdown(vault_stylesheet(), unsafe_allow_html=True)

inbox = DEFAULT_INBOX
inbox.mkdir(parents=True, exist_ok=True)

if st.session_state.pop("vault_clear_pending", False):
    for spec in FIELD_MENUS:
        st.session_state[f"vault_menu_{spec['key']}"] = ANY
    st.session_state["vault_menu_age"] = ANY
    st.session_state["vault_ready"] = False
    st.session_state.pop("vault_rows", None)
    st.session_state.pop("vault_summary", None)


def _format_stats(stats: dict) -> str:
    accepted = stats["accepted"]
    files = stats["files"]
    parts = [
        f"Imported {accepted} profile{'' if accepted == 1 else 's'} "
        f"from {files} file{'' if files == 1 else 's'}."
    ]
    if stats["skipped"]:
        parts.append(f"Skipped {stats['skipped']}.")
    if stats["errors"]:
        parts.append(f"Could not read {stats['errors']}.")
    if stats["unsupported"]:
        parts.append(
            f"Left out {stats['unsupported']} unsupported file{'' if stats['unsupported'] == 1 else 's'}."
        )
    notes = stats.get("notes") or []
    if notes and (stats["skipped"] or stats["errors"] or stats["unsupported"]):
        parts.append(" ".join(notes))
    return " ".join(parts)


def _remember_import(stats: dict) -> None:
    st.session_state["import_note"] = _format_stats(stats)
    st.session_state["import_error"] = ""


st.markdown(vault_hero_html(count_profiles()), unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="mv-panel-title">Bring in a file</div>', unsafe_allow_html=True)
    st.caption(
        "Choose biodata from this computer. Text, Excel, Word, PDF, JSON, and photos are read. "
        "Other file types are counted and left out."
    )
    permission = st.checkbox(
        "I confirm I am allowed to store and search these personal profiles on this computer, including phone numbers",
        key="vault_permission",
    )
    require_consent = st.checkbox(
        "Only import blocks that contain CONSENT:YES",
        value=False,
        key="vault_require_consent",
    )
    uploads = st.file_uploader(
        "Files from this computer",
        accept_multiple_files=True,
        key="vault_uploads",
        label_visibility="visible",
    )
    import_col, folder_col = st.columns(2)
    import_clicked = import_col.button(
        "Import files",
        type="primary",
        disabled=not (permission and uploads),
        use_container_width=True,
    )
    folder_clicked = folder_col.button(
        "Read inbox folder",
        disabled=not permission,
        use_container_width=True,
    )
    if import_clicked and uploads:
        with st.spinner("Reading files…"):
            try:
                stats = ingest_uploaded(
                    [(item.name, item.getvalue()) for item in uploads],
                    permission_confirmed=True,
                    require_consent_tag=require_consent,
                )
                _remember_import(stats)
            except Exception as exc:
                st.session_state["import_note"] = ""
                st.session_state["import_error"] = f"{type(exc).__name__}: {exc}"
        st.rerun()
    if folder_clicked:
        with st.spinner("Reading vault_inbox…"):
            try:
                stats = ingest_inbox(
                    inbox,
                    permission_confirmed=True,
                    require_consent_tag=require_consent,
                )
                _remember_import(stats)
            except Exception as exc:
                st.session_state["import_note"] = ""
                st.session_state["import_error"] = f"{type(exc).__name__}: {exc}"
        st.rerun()
    if st.session_state.get("import_error"):
        st.error(st.session_state["import_error"])
    elif st.session_state.get("import_note"):
        st.success(st.session_state["import_note"])

profiles = load_all()
by_key = {spec["key"]: spec for spec in FIELD_MENUS}
age_options = age_labels()

st.markdown('<div class="mv-panel-title">Required fields</div>', unsafe_allow_html=True)
st.caption("Open a menu and pick a value. Leave Any on fields you do not need. Nothing to type.")

with st.form("vault_filters"):
    if "vault_menu_age" in st.session_state and st.session_state["vault_menu_age"] not in age_options:
        st.session_state["vault_menu_age"] = ANY
    age_label = st.selectbox("Age", age_options, key="vault_menu_age")
    chosen: dict[str, str] = {}
    for title, keys in MENU_SECTIONS:
        st.markdown(f"**{title}**")
        columns = st.columns(len(keys))
        for column, key in zip(columns, keys):
            spec = by_key[key]
            widget_key = f"vault_menu_{key}"
            options = menu_options(profiles, spec)
            if widget_key in st.session_state and st.session_state[widget_key] not in options:
                st.session_state[widget_key] = ANY
            with column:
                chosen[key] = st.selectbox(spec["label"], options, key=widget_key)
    submit_col, clear_col, _rest = st.columns([1, 1, 2])
    submitted = submit_col.form_submit_button("Submit", type="primary", use_container_width=True)
    cleared = clear_col.form_submit_button("Clear", use_container_width=True)

if cleared:
    st.session_state["vault_clear_pending"] = True
    st.rerun()
elif submitted:
    summary = describe_selection(chosen, age_label)
    st.session_state["vault_rows"] = search_profiles(**search_kwargs(chosen, age_label), limit=200)
    st.session_state["vault_summary"] = summary
    st.session_state["vault_ready"] = True

if not st.session_state.get("vault_ready"):
    st.markdown(
        '<div class="mv-waiting">Press Submit to bring the profiles back as biodata sheets.</div>',
        unsafe_allow_html=True,
    )
else:
    rows = st.session_state.get("vault_rows") or []
    summary = st.session_state.get("vault_summary") or "All stored profiles"
    st.markdown('<div class="mv-panel-title">Profiles</div>', unsafe_allow_html=True)
    st.caption(summary)
    if count_profiles() == 0:
        st.info("Nothing is stored yet. Import a file, then press Submit.")
    elif not rows:
        st.info("No profile matched these fields. Set a menu back to Any and press Submit again.")
    else:
        word_col, excel_col, text_col = st.columns(3)
        word_col.download_button(
            "Download Word",
            data=to_docx(rows, summary),
            file_name="vault_profiles.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        excel_col.download_button(
            "Download Excel",
            data=to_xlsx(rows, summary),
            file_name="vault_profiles.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        text_col.download_button(
            "Download text",
            data=format_vault_report(rows, summary=summary),
            file_name="vault_profiles.txt",
            mime="text/plain",
            use_container_width=True,
        )
        for index, profile in enumerate(rows, 1):
            st.markdown(
                format_profile_html(profile, index=index, include_phone=True),
                unsafe_allow_html=True,
            )

with st.expander("Remove everything stored here", expanded=False):
    st.caption(f"{count_profiles()} profile(s) in the local vault. This does not touch the Telegram bot.")
    confirmed = st.checkbox("I confirm these stored profiles should be deleted", key="vault_delete_confirm")
    if st.button("Delete stored profiles", disabled=not confirmed):
        removed = clear_all()
        st.session_state["vault_ready"] = False
        st.session_state.pop("vault_rows", None)
        st.session_state.pop("vault_summary", None)
        st.session_state["import_error"] = ""
        st.session_state["import_note"] = f"Removed {removed} stored profile(s)."
        st.rerun()
