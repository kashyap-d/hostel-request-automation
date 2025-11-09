import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from main import process_hostel_request  # Import your existing core function

load_dotenv()

# Telegram Bot Token
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Conversation states
ASK_NAME, ASK_REGNO, ASK_PROBLEM = range(3)

# Temporary user data storage
user_data = {}

# --- Step 1: Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hi! I’m your Hostel Helpdesk Bot.\nLet's get started.\n\nWhat’s your full name?")
    return ASK_NAME

# --- Step 2: Ask Name ---
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Got it! Please enter your registration number:")
    return ASK_REGNO

# --- Step 3: Ask Registration Number ---
async def get_regno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data["reg_number"] = update.message.text.strip()
    await update.message.reply_text("Thanks! Now please describe your problem:")
    return ASK_PROBLEM

# --- Step 4: Get Problem Statement and Process Request ---
async def get_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    problem_statement = update.message.text.strip()
    name = user_data.get("name", "Unknown")
    reg_number = user_data.get("reg_number", "Unknown")

    await update.message.reply_text("🧠 Processing your request... please wait.")

    # Run your main process in background (to avoid blocking Telegram)
    success = await asyncio.to_thread(
        process_hostel_request,
        name,
        reg_number,
        problem_statement
    )

    if success:
        await update.message.reply_text("✅ Your request was successfully recorded in the system!")
    else:
        await update.message.reply_text("⚠️ Something went wrong while processing your request. Please try again later.")

    await update.message.reply_text("You can type /start to make another request.")
    return ConversationHandler.END


# --- Cancel Handler ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Okay, goodbye!")
    return ConversationHandler.END


# --- Main Telegram Setup ---
def main():
    print("✅ Telegram wrapper running...")

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_REGNO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_regno)],
            ASK_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_problem)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    app.run_polling()


if __name__ == "__main__":
    main()
