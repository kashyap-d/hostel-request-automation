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
from classifier import make_llm
from main import CONTEXT_LIMIT, describe_ticket, process_hostel_request, summarize_previous_problems
from supabase_client import fetch_problem_statements, format_history, summaries_from

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Conversation states
ASK_NAME, ASK_REGNO, ASK_PROBLEM = range(3)

# Per-chat details live in context.user_data, which python-telegram-bot keeps
# separately for each user. Database and LLM calls are blocking, so they run in
# a worker thread via asyncio.to_thread to keep the bot responsive for other chats.


# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Hi! I’m your Hostel Helpdesk Bot.\nLet's get started.\n\nPlease enter your full name:"
    )
    return ASK_NAME


# --- Get Name ---
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Thanks! Now enter your registration number:")
    return ASK_REGNO


# --- Get Registration Number ---
async def get_regno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    regno = update.message.text.strip()
    context.user_data["reg_number"] = regno
    name = context.user_data.get("name", "there")

    user_problems = await asyncio.to_thread(fetch_problem_statements, regno, CONTEXT_LIMIT)

    if user_problems:
        await update.message.reply_text(f"👋 Welcome back, {name}! It’s great to see you again.")
        await update.message.reply_text("📜 Your recent issues:\n" + format_history(user_problems))

        # Summarize their past complaints
        llm = context.application.bot_data["llm"]
        summary = await asyncio.to_thread(summarize_previous_problems, summaries_from(user_problems), llm)
        await update.message.reply_text(f"🧾 Summary of your previous problems:\n➡️ {summary}")
        await update.message.reply_text("Let's continue — what would you like help with today?\n")
    else:
        await update.message.reply_text(
            f"👋 Hello {name}! Welcome to the Hostel Helpdesk System.\nIt looks like this is your first time here.\n"
        )

    await update.message.reply_text("Please describe your current problem:")
    return ASK_PROBLEM


# --- Get Problem and Process Request ---
async def get_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    problem_statement = update.message.text.strip()
    name = context.user_data.get("name")
    reg_number = context.user_data.get("reg_number")

    if problem_statement.lower() in ["exit", "quit"]:
        await update.message.reply_text("👋 Goodbye!")
        return ConversationHandler.END

    if not name or not reg_number:
        # The bot restarted mid-conversation and lost this chat's details.
        await update.message.reply_text("Sorry, I lost track of your details. Please type /start to begin again.")
        return ConversationHandler.END

    await update.message.reply_text("🧠 Processing your request... please wait.")

    llm = context.application.bot_data["llm"]
    result = await asyncio.to_thread(process_hostel_request, name, reg_number, problem_statement, llm)

    if result.status == "recorded":
        await update.message.reply_text("✅ Your request was recorded:\n\n" + describe_ticket(result.ticket))
    elif result.status == "rejected":
        await update.message.reply_text(
            "⚠️ This doesn't look like a hostel or admission problem, so it was not recorded."
        )
    else:
        await update.message.reply_text("⚠️ Something went wrong while processing your request. Please try again later.")

    await update.message.reply_text("You can type /start to make another request.")
    return ConversationHandler.END


# --- Cancel Command ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Okay, goodbye!")
    return ConversationHandler.END


# --- Main Setup ---
def main():
    if not TOKEN:
        raise RuntimeError("Set TELEGRAM_TOKEN in .env")

    print("✅ Telegram wrapper running...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.bot_data["llm"] = make_llm()

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
