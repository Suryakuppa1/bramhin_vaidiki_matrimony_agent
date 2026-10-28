# Telegram Bride Names Matcher — private opt-in bot

**What this upgrade adds:** The previous dashboard still works. Now the Telegram bot lets an authorized person save matching requirements in a private bot chat and receive bride names, new-match alerts, and Excel/Word/PDF reports without opening the dashboard.

### Set up on Windows

1. Extract the ZIP. Install Python 3.11+ and, if PDF output is needed, LibreOffice.
2. Open PowerShell in `marriage-profile-filter`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

3. Open Telegram, message `@BotFather`, run `/newbot`, and copy the bot token **into your local `.env`** (`BOT_TOKEN=...`). Do not paste the token into chat or share it.
4. Run `python get_my_id.py` first, DM your bot `/myid`, copy your Telegram **user ID**, and stop the helper with Ctrl+C. The upgraded main bot intentionally does not start until `AUTHORIZED_USER_IDS` is configured; add `AUTHORIZED_USER_IDS=123456789` to `.env` using your real ID.
5. For approved groups only: temporarily set `ALLOWED_GROUP_IDS=` empty until you've obtained group IDs. The easiest way: add bot to the group, then in the group issue `/myid` to see its numeric chat ID, and insert it into `ALLOWED_GROUP_IDS=-100...`. Restart bot.
6. Run:

```powershell
python bot.py
```

Keep the machine online while you want new submissions processed. Group admins must approve the use of the bot, explain it to members, and ensure subjects have explicitly consented to submitting profiles to this private matcher.

### DM commands

```text
/setage 23 28
/setstar Rohini, Swathi
/setbirthplace Hyderabad
/setgroup Approved Group Name
/filters
/matches
/review
/export excel
/export word
/export pdf
/clearfilters
```

For an approved group, consenting adult subjects or expressly authorized representatives send:

```text
/submit CONSENT:YES
Name: Example Person
DOB: 14-07-1999
Nakshatram: Rohini
Rashi: Vrishabha
Place of Birth: Hyderabad
Education: B.Tech
```

Bot responds to `/matches` in your **private DM** with the matching bride names. When matching profiles are submitted, it can privately send an alert if `ENABLE_MATCH_ALERTS=true` and you have already started its private chat.

### What this does not do

- **No bulk scraping of existing group messages.** Telegram's Bot API does not provide bulk historical chat retrieval, and Telegram's terms restrict harvesting or indexing group content. A group name alone never authorizes access to its members' personal data.
- **Does not ingest every group chat message.** The bot reads directly submitted, explicitly consented `/submit` profiles, not the group's ordinary conversations. Telegram privacy mode can remain enabled.
- Existing JSON imports should only be used where both group access and the relevant individuals' informed consent permit processing. Do not process unrelated private messages.
- It does not verify claims of consent; production use needs group rules, verifiable subject permission, access auditing, data retention and removal policies.
- It uses a SQLite database on the machine running the bot. The private dashboard is not login-protected: do **not** publish it to the internet directly.
- No image-biodata OCR. Labeled English/Telugu text fields are supported by the current parser.
- This is a tested local starter, not a deployed hosted 24/7 service.

**Privacy:** Use only necessary fields, no phone numbers, contacts, or street addresses; share exports only with authorized recipients. To withdraw a submission, sender uses `/delete_my_profiles`; downloaded copies must be deleted separately. SQLite should be protected with filesystem permissions, encryption-at-rest/backup controls added for real deployment.

**Telegram docs:** https://core.telegram.org/bots/faq ; https://telegram.org/tos/bot-developers
