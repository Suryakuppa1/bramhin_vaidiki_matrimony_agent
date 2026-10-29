"""Consent-based Telegram marriage profiles with private self-service matching.

Commands in allowlisted groups: /submit CONSENT:YES ...
Commands in private chat: /menu (tap filters), /setage, /setstar, /setrashi,
/setgotram, /setsaka, /setname, /setbirthplace, /seteducation, /setgroup, /setdob,
/filters, /matches, /review, /export, /clearfilters.
Telugu or English filter values both work.

This bot does NOT scrape group history or index ordinary messages.
"""
from __future__ import annotations

import io
import logging
import os
import re
from datetime import date
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
from core import parse_profile, store_profile, delete_by_submitter, load_profiles, is_match, get_age
from preferences import (EMPTY, read_filters, save_filters, clear_filters,
                         configured, describe_filters, criteria, matching_rows,
                         empty_matches_reason)
from menu import (
    FIELD_SPECS, home_keyboard, home_text, options_keyboard,
    age_keyboard, build_field_options, display_value,
)
from reports import to_xlsx, to_docx, to_pdf

load_dotenv()
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)
TOKEN = os.getenv('BOT_TOKEN', '').strip()
ALLOWED_GROUP_IDS = {int(s.strip()) for s in os.getenv('ALLOWED_GROUP_IDS', '').split(',') if s.strip()}
AUTHORIZED_USER_IDS = {int(s.strip()) for s in os.getenv('AUTHORIZED_USER_IDS', '').split(',') if s.strip()}
ENABLE_MATCH_ALERTS = os.getenv('ENABLE_MATCH_ALERTS', 'true').lower() in ('1', 'true', 'yes')

TEMPLATE = (
    'New profile submission (subject consent required):\n'
    '/submit CONSENT:YES\n'
    'Name: Example Name\n'
    'DOB: 14-07-1999\n'
    'Nakshatram: Rohini\n'
    'Rashi: Vrishabha\n'
    'Gotram: Bharadwaja\n'
    'Saka: Vaidiki Velanadu\n'
    'Place of Birth: Hyderabad\n'
    'Education: B.Tech\n\n'
    'Telugu labels also work (పేరు, నక్షత్రం, రాశి, గోత్రం, వైదికి వేలనాడు, …). '
    'Only submit your own profile or one you are explicitly authorized to submit. '
    'By submitting you authorize private matchmaking storage/results; use /delete_my_profiles to revoke. '
    'Do not include phone numbers, addresses or government IDs.'
)
HELP = (
    'Private search commands (authorized users only).\n'
    'Easiest: /menu — tap Nakshatram, Rashi, Gotram, Saka, place, age, then Show matches.\n'
    'Options come from profiles already imported into your local database.\n\n'
    'Or set manually (Telugu or English):\n'
    '/setage 23 28\n'
    '/setstar Rohini   (or /setstar రోహిణి)\n'
    '/setrashi Vrishabha\n'
    '/setgotram Bharadwaja\n'
    '/setsaka Vaidiki Velanadu\n'
    '/setname Ananya\n'
    '/setbirthplace Hyderabad\n'
    '/seteducation B.Tech\n'
    '/setgroup Marriage Group Name\n'
    '/setdob 1997-01-01 2003-12-31\n'
    '/filters – show requirements\n'
    '/matches – matching profiles for those filters only\n'
    '/review – include incomplete profiles\n'
    '/export excel | word | pdf – private report\n'
    '/clearfilters – reset requirements\n'
    '/myid – show your Telegram ID\n'
    '/delete_my_profiles – revoke submissions from your account\n\n'
    'In approved groups use /submit CONSENT:YES followed by labeled fields.\n'
    'Old history is not accessible through the Bot API; authorized, consent-tagged JSON profiles can be imported in the local dashboard.'
)


def is_authorized(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id in AUTHORIZED_USER_IDS)


async def require_private_owner(update: Update) -> bool:
    if update.effective_chat.type != 'private':
        await update.effective_message.reply_text('Private details are available only in a DM with this bot. Open the bot chat and try there.')
        return False
    if not is_authorized(update):
        await update.effective_message.reply_text('Private matching is restricted. Send /myid to your bot administrator for access approval.')
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text('Marriage Profile Filter bot (consent-based).\n\n' + HELP + '\n' + TEMPLATE)


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(f'Your Telegram user ID: {update.effective_user.id}\nThis chat ID: {update.effective_chat.id}')


async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    sender = update.effective_user
    if chat.type != 'private' and chat.id not in ALLOWED_GROUP_IDS:
        await msg.reply_text('This group is not authorized for submissions. Contact the group admin or DM the bot.')
        return
    m = re.match(r'^/submit(?:@\w+)?\s+CONSENT\s*:\s*YES\b(.*)$', msg.text or '', re.I | re.S)
    if not m:
        await msg.reply_text(TEMPLATE)
        return
    profile = parse_profile(m.group(1).strip())
    if not profile or not profile.get('name') or not get_age(profile.get('dob'), profile.get('age')):
        await msg.reply_text('Name and DOB or age are required, along with labeled profile details. Nothing was stored.')
        return
    age = get_age(profile.get('dob'), profile.get('age'))
    if age < 18:
        await msg.reply_text('Only adult (18+) profiles are accepted; nothing was stored.')
        return
    store_profile(profile, source_name=chat.title or 'Private opt-in submission',
                  source_ref=f'{chat.id}:{msg.message_id}', source_kind='opt_in_bot',
                  submitted_by=str(sender.id), message_date=msg.date.isoformat() if msg.date else '')
    await msg.reply_text('Profile saved for private matching. /delete_my_profiles withdraws submissions made from your account.')
    if ENABLE_MATCH_ALERTS:
        # Notifications only to expressly configured private recipients who have saved requirements.
        for uid in AUTHORIZED_USER_IDS:
            f = read_filters(uid)
            if not configured(f) or is_match(profile, **criteria(f)) != 'Match':
                continue
            try:
                await context.bot.send_message(chat_id=uid,
                    text=f'New consenting profile matched your filters: {profile["name"]}, age {age}, '
                         f'nakshatram {profile.get("nakshatram") or "not provided"}. '
                         f'Send /matches to view private matching results.')
            except Exception as exc:
                logging.warning('Match alert failed for authorized user %s: %s', uid, exc)


async def _set_filter(update: Update, key: str, value: str):
    if not await require_private_owner(update):
        return
    f = read_filters(update.effective_user.id)
    f[key] = value.strip()
    save_filters(update.effective_user.id, f)
    await update.effective_message.reply_text(f'Filter saved. {describe_filters(f)}\nUse /matches to get bride names.')


async def setage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_private_owner(update):
        return
    args = context.args
    if len(args) != 2 or not all(a.isdigit() for a in args):
        await update.effective_message.reply_text('Usage: /setage 23 28')
        return
    lo, hi = map(int, args)
    if not (18 <= lo <= hi <= 80):
        await update.effective_message.reply_text('Age range must be between 18 and 80, with minimum <= maximum.')
        return
    f = read_filters(update.effective_user.id)
    f.update(min_age=lo, max_age=hi)
    save_filters(update.effective_user.id, f)
    await update.effective_message.reply_text(f'Age set to {lo}–{hi}. Use /matches.')


async def setstar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text('Usage: /setstar Rohini, Swathi')
        return
    await _set_filter(update, 'stars', ' '.join(context.args))


async def setbirthplace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text('Usage: /setbirthplace Hyderabad')
        return
    await _set_filter(update, 'birthplace', ' '.join(context.args))


async def setrashi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text('Usage: /setrashi Vrishabha   (or Telugu రాశి name)')
        return
    await _set_filter(update, 'rashi', ' '.join(context.args))


async def setgotram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text('Usage: /setgotram Bharadwaja   (or Telugu భరద్వాజ)')
        return
    await _set_filter(update, 'gotram', ' '.join(context.args))


async def setsaka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text('Usage: /setsaka Vaidiki Velanadu   (or వైదికి వేలనాడు)')
        return
    await _set_filter(update, 'saka', ' '.join(context.args))


async def setname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text('Usage: /setname Ananya')
        return
    await _set_filter(update, 'name', ' '.join(context.args))


async def seteducation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text('Usage: /seteducation B.Tech')
        return
    await _set_filter(update, 'education', ' '.join(context.args))


async def setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text('Usage: /setgroup Approved Group Name')
        return
    await _set_filter(update, 'group', ' '.join(context.args))


async def setdob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_private_owner(update):
        return
    if len(context.args) != 2:
        await update.effective_message.reply_text('Usage: /setdob 1997-01-01 2003-12-31')
        return
    try:
        lo, hi = [date.fromisoformat(v) for v in context.args]
        if lo > hi:
            raise ValueError('Invalid date range')
    except ValueError:
        await update.effective_message.reply_text('Dates must be YYYY-MM-DD and start <= end.')
        return
    f = read_filters(update.effective_user.id)
    f.update(dob_start=lo.isoformat(), dob_end=hi.isoformat())
    save_filters(update.effective_user.id, f)
    await update.effective_message.reply_text(f'Date of birth set: {lo} through {hi}. Use /matches.')


async def filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_private_owner(update):
        return
    await update.effective_message.reply_text(describe_filters(read_filters(update.effective_user.id)))


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_private_owner(update):
        return
    clear_filters(update.effective_user.id)
    await update.effective_message.reply_text('Your requirements are cleared. Set at least one filter before /matches.')


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_private_owner(update):
        return
    await update.effective_message.reply_text(
        home_text(update.effective_user.id),
        reply_markup=home_keyboard(),
    )


async def _reply_matches_text(update: Update, user_id: int) -> str:
    prefs = read_filters(user_id)
    if not configured(prefs):
        return 'Please set a requirement first from /menu (or /setage, /setstar, …).'
    rows = matching_rows(load_profiles(), prefs, limit=100)
    if not rows:
        return empty_matches_reason(load_profiles(), prefs)
    lines = [
        f'Found {len(rows)} matching profiles (up to 100). Your requirements: {describe_filters(prefs)}',
        '',
    ]
    for i, p in enumerate(rows[:20], 1):
        lines.append(
            f'{i}. {p.get("name") or "Name unavailable"} | Age {p.get("age") or "?"} | '
            f'{p.get("nakshatram") or "Star unknown"} | {p.get("gotram") or "Gotram n/a"} | '
            f'{p.get("saka") or "Saka n/a"} | {p.get("source_name") or "Opt-in"}'
        )
    if len(rows) > 20:
        lines.append(f'... plus {len(rows)-20} more. Use /export excel to view the complete filtered list.')
    return '\n'.join(lines)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    if update.effective_chat.type != 'private':
        await query.edit_message_text('Open a private DM with this bot and use /menu there.')
        return
    if not is_authorized(update):
        await query.edit_message_text('Private matching is restricted. Send /myid to your bot administrator.')
        return
    user_id = update.effective_user.id
    data = query.data
    parts = data.split(':')
    if len(parts) < 3 or parts[0] != 'menu':
        return
    action = parts[1]

    if action == 'act' and parts[2] == 'home':
        await query.edit_message_text(home_text(user_id), reply_markup=home_keyboard())
        return
    if action == 'act' and parts[2] == 'filters':
        await query.edit_message_text(
            f'Current filters: {describe_filters(read_filters(user_id))}',
            reply_markup=home_keyboard(),
        )
        return
    if action == 'act' and parts[2] == 'clear':
        clear_filters(user_id)
        await query.edit_message_text(
            'Filters cleared.\n\n' + home_text(user_id),
            reply_markup=home_keyboard(),
        )
        return
    if action == 'act' and parts[2] == 'matches':
        text = await _reply_matches_text(update, user_id)
        await query.edit_message_text(text[:4000], reply_markup=home_keyboard())
        return

    if action == 'list' and parts[2] == 'age':
        await query.edit_message_text(
            'Pick an age range preset:',
            reply_markup=age_keyboard(),
        )
        return

    if action == 'list' and parts[2] in FIELD_SPECS:
        field_code = parts[2]
        options = build_field_options(field_code)
        context.user_data[f'menu_opts_{field_code}'] = [value for value, _ in options]
        label = FIELD_SPECS[field_code]['label']
        if not options:
            await query.edit_message_text(
                f'No {label} values found in imported profiles yet. Import resources or wait for /submit, then /menu again.',
                reply_markup=home_keyboard(),
            )
            return
        await query.edit_message_text(
            f'Pick {label} (counts from your local DB):',
            reply_markup=options_keyboard(field_code, options),
        )
        return

    if action == 'age' and len(parts) == 4:
        lo, hi = int(parts[2]), int(parts[3])
        prefs = read_filters(user_id)
        prefs.update(min_age=lo, max_age=hi)
        save_filters(user_id, prefs)
        await query.edit_message_text(
            f'Age set to {lo}–{hi}.\n\n' + home_text(user_id),
            reply_markup=home_keyboard(),
        )
        return

    if action == 'set' and len(parts) == 4 and parts[2] in FIELD_SPECS:
        field_code = parts[2]
        try:
            index = int(parts[3])
        except ValueError:
            return
        options = context.user_data.get(f'menu_opts_{field_code}') or [v for v, _ in build_field_options(field_code)]
        if index < 0 or index >= len(options):
            await query.edit_message_text('That option expired. Open /menu again.', reply_markup=home_keyboard())
            return
        value = options[index]
        spec = FIELD_SPECS[field_code]
        prefs = read_filters(user_id)
        prefs[spec['filter_key']] = value
        save_filters(user_id, prefs)
        await query.edit_message_text(
            f"Saved {spec['label']}: {display_value(value)}.\n\n" + home_text(user_id),
            reply_markup=home_keyboard(),
        )
        return


async def _get_rows(update: Update, *, review: bool = False, limit: int = 100):
    if not await require_private_owner(update):
        return None
    prefs = read_filters(update.effective_user.id)
    if not configured(prefs):
        await update.effective_message.reply_text('Please set a requirement first, e.g. /setage 23 28 or /setstar Rohini.')
        return None
    return matching_rows(load_profiles(), prefs, include_review=review, limit=limit)


async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = await _get_rows(update, limit=100)
    if rows is None:
        return
    if not rows:
        prefs = read_filters(update.effective_user.id)
        await update.effective_message.reply_text(empty_matches_reason(load_profiles(), prefs))
        return
    lines = [f'Found {len(rows)} matching profiles (up to 100). Your requirements: {describe_filters(read_filters(update.effective_user.id))}', '']
    for i, p in enumerate(rows[:20], 1):
        lines.append(
            f'{i}. {p.get("name") or "Name unavailable"} | Age {p.get("age") or "?"} | '
            f'{p.get("nakshatram") or "Star unknown"} | {p.get("gotram") or "Gotram n/a"} | '
            f'{p.get("saka") or "Saka n/a"} | {p.get("source_name") or "Opt-in"}'
        )
    if len(rows) > 20:
        lines.append(f'... plus {len(rows)-20} more. Use /export excel to view the complete filtered list.')
    await update.effective_message.reply_text('\n'.join(lines))


async def review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = await _get_rows(update, review=True)
    if rows is None:
        return
    pending = [r for r in rows if r['status'] == 'Needs review']
    if not pending:
        await update.effective_message.reply_text('No incomplete profiles require review for your requirements.')
        return
    lines = [f'{len(pending)} profiles with missing requirements (not confirmed matches):']
    for i, r in enumerate(pending[:20], 1):
        lines.append(f'{i}. {r.get("name") or "Unnamed"} | {r.get("source_name") or "Opt-in"}')
    await update.effective_message.reply_text('\n'.join(lines))


async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = await _get_rows(update, limit=100)
    if rows is None:
        return
    if not rows:
        await update.effective_message.reply_text('No matches to export yet.')
        return
    fmt = (context.args[0] if context.args else '').strip().lower()
    if fmt not in ('excel', 'word', 'pdf'):
        await update.effective_message.reply_text('Usage: /export excel  (or word, pdf)')
        return
    try:
        label = describe_filters(read_filters(update.effective_user.id))
        if fmt == 'excel':
            data, filename = to_xlsx(rows, label), 'matched_bride_profiles.xlsx'
        elif fmt == 'word':
            data, filename = to_docx(rows, label), 'matched_bride_profiles.docx'
        else:
            data, filename = to_pdf(rows, label), 'matched_bride_profiles.pdf'
        await update.effective_message.reply_document(document=io.BytesIO(data), filename=filename,
               caption='Private consenting match report. Do not forward without authorization.')
    except Exception as exc:
        logging.exception('Export failed')
        await update.effective_message.reply_text(f'Could not prepare that report: {type(exc).__name__}. '
              'PDF requires LibreOffice installed on the host. Try /export excel or word.')


async def delete_mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        await update.effective_message.reply_text('For privacy, send /delete_my_profiles in a DM with this bot.')
        return
    count = delete_by_submitter(str(update.effective_user.id))
    await update.effective_message.reply_text(f'Deleted {count} submitted profile entries. Locally exported copies cannot be revoked automatically.')


def main():
    if not TOKEN:
        raise SystemExit('BOT_TOKEN missing. Obtain it from @BotFather and set it in .env.')
    if not AUTHORIZED_USER_IDS:
        raise SystemExit('AUTHORIZED_USER_IDS missing. Use the bot /myid to get your ID; set it in .env before enabling private search.')
    app = ApplicationBuilder().token(TOKEN).build()
    for cmd, fn in [('start', start), ('help', start), ('myid', myid), ('submit', submit),
                    ('setage', setage), ('setstar', setstar), ('setbirthplace', setbirthplace),
                    ('setrashi', setrashi), ('setgotram', setgotram), ('setsaka', setsaka),
                    ('setname', setname), ('seteducation', seteducation), ('setgroup', setgroup),
                    ('setdob', setdob), ('filters', filters), ('clearfilters', clear),
                    ('menu', menu), ('options', menu),
                    ('matches', matches), ('review', review), ('export', export),
                    ('delete_my_profiles', delete_mine)]:
        app.add_handler(CommandHandler(cmd, fn))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r'^menu:'))
    logging.info('Opt-in matcher bot running; /matches and exports available only to authorized private users')
    app.run_polling(allowed_updates=['message', 'callback_query'])

if __name__ == '__main__':
    main()
