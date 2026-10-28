"""First-run helper: securely replies to /myid only; no profiles stored."""
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
load_dotenv()
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(f'Telegram user ID: {update.effective_user.id}\nChat ID: {update.effective_chat.id}')
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await myid(update, context)
if __name__ == '__main__':
    token = os.getenv('BOT_TOKEN', '')
    if not token:
        raise SystemExit('Set BOT_TOKEN in .env first.')
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('myid', myid))
    app.add_handler(CommandHandler('start', start))
    print('Send /myid to your bot in Telegram; stop with Ctrl+C after copying your user ID.')
    app.run_polling()
