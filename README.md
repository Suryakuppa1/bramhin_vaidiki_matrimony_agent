> **Updated Telegram chat-bot:** Read [README_BOT_UPGRADE.md](README_BOT_UPGRADE.md) first. The main bot now supports private `/matches`, `/setage`, `/setstar`, `/setbirthplace`, `/export` and automated consenting-profile notifications. Old `ADMIN_CHAT_ID` and `ALERT_...` settings below have been replaced by `AUTHORIZED_USER_IDS` and private saved filters. Older import files are now limited to explicitly consent-tagged messages.

# Marriage Profile Filter — Private, consent-based local starter

**What works**

- Import older Telegram Desktop **JSON** chat history containing explicit `CONSENT:YES` tags for profiles you have permission to process.
- Extract labeled Telugu/English profile details (name, DOB, age, nakshatram, rashi, birthplace, birth time, education, current location).
- Receive future profiles that users explicitly send using a Telegram bot: `/submit CONSENT:YES ...`.
- Filter by age, nakshatram, rashi, DOB, birth location, and education.
- Display `Match`, `Needs review` (if requested fields are missing), and `No match`.
- Identify possible repeated profiles by normalized name + date of birth (review, do not auto-merge).
- Download XLSX, DOCX, and PDF reports; PDFs require LibreOffice + font support.
- Private SQLite database (original full messages/contact numbers are **not** stored).
- Withdraw bot submissions via `/delete_my_profiles`; manually remove imported records via the dashboard.

**Limits**

- This is a **running starter app**, not a production service. It has no user login, encrypted database, backups, audit logs, role-based access, or hard deletion propagation across prior downloaded reports.
- It does **not** silently read all messages in arbitrary groups. Telegram terms restrict scraping and personal data aggregation. Only use old files containing explicitly consent-tagged posts that you are authorized to process; future profiles require explicit opt-in submissions and group permission.
- Telegram bots cannot bulk-import historical group messages; use Telegram Desktop exports for older messages. Group bot use requires approval and `ALLOWED_GROUP_IDS`.
- Image/photo/PDF biodata OCR is **not included**. Unlabeled, complex free-form messages and spelling variations may need manual review. No LLM API is used and profile text is never sent to one.
- This code assumes the sender's `CONSENT:YES` statement is truthful; independent subject consent and disclosure mechanisms are needed in a real deployment, especially for third-party-submitted biodata.
- Source message ID and group name are preserved, but links to private Telegram groups are not fabricated.
- Email/phone numbers are not extracted. Do not share reports without authorization; downloaded copies must be deleted separately on revocation.

## 1) Install

Prerequisites: Python 3.11+; on Windows install Python from python.org. Install **LibreOffice** to enable PDF export. For Telugu PDF/DOCX display, install a Telugu-compatible font such as **Noto Sans Telugu**.

Windows PowerShell:

```powershell
cd marriage-profile-filter
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
streamlit run dashboard.py
```

macOS/Linux:

```bash
cd marriage-profile-filter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run dashboard.py
```

Open the local URL shown in the terminal (typically `http://localhost:8501`). Never make this unauthenticated dashboard publicly accessible.

## 2) Old Telegram messages

1. Install/open Telegram Desktop on PC and sign in.
2. Open the relevant group you may legitimately process; menu `…` -> `Export chat history` -> choose **Machine-readable JSON**.
3. In the dashboard, expand `Import old Telegram JSON history`, upload one or more `.json` files, confirm you have permission, then select `Import history`.
4. Or via command line:

```bash
python import_history.py samples/telegram_export_sample.json --i-have-permission
```

The sample file is **fictional test data**. Old exports do not continuously update; subsequent authorized exports can be reimported without duplicating identical `group + message ID` entries. For best stability, keep the group name unchanged.

## 3) Future opt-in Telegram submissions and private matching

See **README_BOT_UPGRADE.md** for the current, complete bot instructions and commands, including the separate `get_my_id.py` first-run helper.

## 4) Filtering and reports

In the Streamlit sidebar, enter your required age range, nakshatram (comma-separated, includes Telugu aliases for common stars), DOB range, place of birth, rashi, and education. Missing requested fields are always `Needs review` rather than invented or treated as a full match. Enable or disable review, duplicates and nonmatching profiles as needed.

- **Excel**: overview tab + filterable profiles table, with source group/message id, status, duplicate flag.
- **Word**: readable profile cards with missing fields marked.
- **PDF**: converted from DOCX by a local LibreOffice installation (Telugu font support must be present).

The system is designed to work first on your own PC. For true 24x7 intake, the bot process and database must run on an **always-on, private host**. Keep the Streamlit UI behind authentication/VPN if accessed from mobile, use encrypted disks and secure backups, and establish permission/retention/deletion workflows. Do not port-forward the Streamlit dev server onto the open Internet.

## 5) Local desktop Vault (full details including phone)

The Telegram bot intentionally does **not** store phone numbers. For a local full-detail search over dumped files (txt / Excel / PDF / images / JSON), use the Vault:

```bash
# put exports in vault_inbox/
streamlit run vault/app.py
# or: python run_vault.py
```

In the UI: confirm permission → **Ingest inbox** → search by name / star / padam / phone / etc. Results show **all stored fields including ContactNumber**. Data lives in `data/vault.sqlite3` only (gitignored), separate from the bot DB.

## 6) Test

```bash
python -m unittest discover -s tests -v
python import_history.py samples/telegram_export_sample.json --i-have-permission
streamlit run dashboard.py
streamlit run vault/app.py
```

The fictional JSON file includes two profiles and one unrelated chat message. Once imported, adjust the sidebar criteria and use all export buttons.

## 7) Suggested next iteration

- Verified consent and privacy disclosures for people whose biodata is shared by relatives.
- Editable review screen for unknown/inconsistent data, permissions and deletion requests.
- Optional OCR for image-based biodata, only for authorized submissions; local models instead of third-party AI services.
- Per-user authorization, encryption at rest, data retention periods and protected mobile access.
- Field normalizations for all 27 Telugu nakshatras and place-name transliterations.

## References

- Telegram Desktop JSON exports: https://telegram.org/blog/export-and-more
- Telegram Bot privacy mode: https://core.telegram.org/bots/features
- Telegram Bot developer terms: https://telegram.org/tos/bot-developers
- Telegram content licensing: https://telegram.org/tos/content-licensing
