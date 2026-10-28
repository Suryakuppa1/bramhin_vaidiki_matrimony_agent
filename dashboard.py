"""Private local Streamlit dashboard. Do not expose directly on a public IP."""
from datetime import date
import streamlit as st
from core import load_profiles, import_export_json, is_match, delete_profile
from reports import to_xlsx, to_docx, to_pdf

st.set_page_config(page_title="Marriage Profile Filters", page_icon="🔎", layout="wide")
st.title("Marriage Profile Filter Dashboard")
st.caption("Private local app • Telegram old exports + new opt-in bot submissions • Telugu / English labels")

with st.expander("Import old Telegram JSON history", expanded=False):
    st.info("Only posts explicitly marked CONSENT:YES are imported. Group permission and the individual's informed consent are both required. Bot credentials are never requested here.")
    files = st.file_uploader("Upload one or more Telegram Desktop JSON exports", type="json", accept_multiple_files=True)
    permission = st.checkbox("I confirm group authorization and the relevant individuals' explicit consent to this profile processing")
    if st.button("Import history", disabled=not (files and permission)):
        n = 0
        for file in files:
            try:
                imported, _ = import_export_json(file.getvalue(), filename=file.name, permission_confirmed=permission)
                n += imported
            except (ValueError, KeyError, UnicodeError) as exc:
                st.error(f"{file.name}: {exc}")
        st.success(f"Processed {n} profile messages. Repeated imports update by source/message ID.")

all_rows = load_profiles()
st.sidebar.header("Bride requirements")
use_age = st.sidebar.checkbox("Filter by age", True)
minage, maxage = st.sidebar.slider("Age range", 18, 60, (22, 29), disabled=not use_age)
stars = st.sidebar.text_input("Nakshatram (comma-separated)", placeholder="Rohini, Swathi")
city = st.sidebar.text_input("Place of birth", placeholder="Hyderabad")
rashi = st.sidebar.text_input("Rashi", placeholder="Vrishabha")
education = st.sidebar.text_input("Education contains", placeholder="B.Tech, MBA")
use_dob = st.sidebar.checkbox("Filter by date of birth", False)
dob_values = st.sidebar.date_input("DOB from/to", value=(date(1995, 1, 1), date(2005, 12, 31)), disabled=not use_dob)
show_incomplete = st.sidebar.checkbox("Include profiles with missing fields (Needs review)", True)
show_nonmatches = st.sidebar.checkbox("Show non-matches", False)
include_duplicates = st.sidebar.checkbox("Include possible duplicates", False)

criteria = dict(min_age=minage if use_age else None, max_age=maxage if use_age else None,
                stars=stars, birthplace=city, rashi=rashi, education=education)
if use_dob and isinstance(dob_values, (tuple, list)) and len(dob_values) == 2:
    criteria.update(dob_start=dob_values[0], dob_end=dob_values[1])
filters_summary = f"Age: {minage}-{maxage}" if use_age else "Any age"
for label, val in (("Nakshatram", stars), ("Birthplace", city), ("Rashi", rashi), ("Education", education)):
    if val.strip():
        filters_summary += f" | {label}: {val.strip()}"
if use_dob and len(dob_values) == 2:
    filters_summary += f" | DOB: {dob_values[0]} to {dob_values[1]}"

rows = []
for row in all_rows:
    if row.get("duplicate_of") and not include_duplicates:
        continue
    row = dict(row)
    row["status"] = is_match(row, **criteria)
    if row["status"] == "No match" and not show_nonmatches:
        continue
    if row["status"] == "Needs review" and not show_incomplete:
        continue
    rows.append(row)
rows.sort(key=lambda r: (0 if r["status"] == "Match" else 1 if r["status"] == "Needs review" else 2,
                         r.get("name") or ""))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total profiles", len(all_rows))
c2.metric("Matched", sum(r["status"] == "Match" for r in rows))
c3.metric("Needs review", sum(r["status"] == "Needs review" for r in rows))
c4.metric("Displayed", len(rows))
st.caption("The match filter is strict: missing requested fields are flagged for review, not assumed to match. Profile ages are calculated from DOB when present.")
preview = []
for r in rows:
    preview.append({"Bride Name":r.get("name"), "Age":r.get("age"), "DOB":r.get("dob"),
        "Nakshatram":r.get("nakshatram"), "Rashi":r.get("rashi"), "Place of Birth":r.get("birthplace"),
        "Education":r.get("education"), "Group":r.get("source_name"), "Message ID":r.get("source_ref"),
        "Status":r.get("status"), "Duplicate?":bool(r.get("duplicate_of"))})
st.dataframe(preview, use_container_width=True, hide_index=True)

st.subheader("Download reports")
col1, col2, col3 = st.columns(3)
with col1:
    st.download_button("Download Excel (.xlsx)", data=to_xlsx(rows, filters_summary),
                       file_name="matched_bride_profiles.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with col2:
    st.download_button("Download Word (.docx)", data=to_docx(rows, filters_summary),
                       file_name="matched_bride_profiles.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
with col3:
    if st.button("Prepare PDF"):
        try:
            st.session_state["pdf_report"] = to_pdf(rows, filters_summary)
        except (RuntimeError, OSError) as e:
            st.error(str(e))
    if "pdf_report" in st.session_state:
        st.download_button("Download PDF (.pdf)", data=st.session_state["pdf_report"],
                           file_name="matched_bride_profiles.pdf", mime="application/pdf")

with st.expander("Delete a stored profile", expanded=False):
    st.warning("Deletion is permanent. Confirm the source name and person before deleting.")
    names = {f"{r.get('name') or 'Unknown'} | {r.get('source_name')} | {r['id'][:8]}": r['id'] for r in all_rows}
    selected = st.selectbox("Choose profile", options=["Select..."] + list(names))
    delete_confirmation = st.checkbox("I confirm permanent deletion")
    if st.button("Delete selected profile", disabled=(selected == "Select..." or not delete_confirmation)):
        delete_profile(names[selected])
        st.success("Deleted. Reload dashboard to refresh results.")
