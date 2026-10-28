# Brahmin Vaidiki Matrimony Agent

Telegram bride-profile matching starter project. It accepts explicitly consented profile submissions via `/submit CONSENT:YES` in administrator-approved Telegram groups and lets the authorized user filter matches in private chat. It also includes a Streamlit dashboard, historical JSON import where consent permits, and Excel/Word/PDF report exports.

## Setup

The source bundle is being prepared for this repository. The Telegram bot must be configured locally with a private `.env` file copied from `.env.example`; **never commit tokens, account credentials, Telegram sessions, actual matrimonial records, or exported group histories**.

Requirements: Python 3.11+, a Telegram bot created via [BotFather](https://t.me/BotFather), and an explicitly authorized group to use the bot. Use only profiles provided with appropriate informed consent.

This starter does not bulk scrape group history or automatically index every group conversation.
