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
from main import process_hostel_request, summarize_previous_problems
from supabase_client import fetch_problem_statements

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Conversation states
ASK_NAME, ASK_REGNO, ASK_PROBLEM = range(3)

# Store user data per Telegram chat (not global)
user_sessions = {}

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_sessions[user_id] = {}
    await update.message.reply_text(
        "👋 Hi! I’m your Hostel Helpdesk Bot.\nLet's get started.\n\nPlease enter your full name:"
    )
    return ASK_NAME


# --- Get Name ---
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_sessions[user_id]["name"] = update.message.text.strip()
    await update.message.reply_text("Thanks! Now enter your registration number:")
    return ASK_REGNO


# --- Get Registration Number ---
async def get_regno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    regno = update.message.text.strip()
    user_sessions[user_id]["reg_number"] = regno

    name = user_sessions[user_id]["name"]

    # Check if user exists in DB
    previous_problems_all = fetch_problem_statements()
    existing_user = any(p.get("reg_number") == regno for p in previous_problems_all)

    if existing_user:
        await update.message.reply_text(f"👋 Welcome back, {name}! It’s great to see you again.")

        # Fetch previous problems
        user_problems = fetch_problem_statements(reg_number=regno, limit=5)

        if user_problems:
            msg = "\n📜 Your recent issues:\n" + "-" * 60 + "\n"
            for idx, p in enumerate(user_problems, 1):
                msg += f"{idx}. {p.get('problem_statement', 'N/A')}  ({p.get('created_at', 'Unknown date')})\n"
            msg += "-" * 60
            await update.message.reply_text(msg)

            # Summarize their past complaints
            from langchain_groq import ChatGroq
            llm = ChatGroq(model="llama-3.1-8b-instant")
            summary = summarize_previous_problems(regno, llm)
            await update.message.reply_text(f"🧾 Summary of your previous problems:\n➡️ {summary}")
        else:
            await update.message.reply_text("It seems we couldn’t find your past records.")
        
        await update.message.reply_text("Let's continue — what would you like help with today?\n")
    else:
        await update.message.reply_text(
            f"👋 Hello {name}! Welcome to the Hostel Helpdesk System.\nIt looks like this is your first time here.\n"
        )

    await update.message.reply_text("Please describe your current problem:")
    return ASK_PROBLEM


# --- Get Problem and Process Request ---
async def get_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    problem_statement = update.message.text.strip()

    name = user_sessions[user_id].get("name", "Unknown")
    reg_number = user_sessions[user_id].get("reg_number", "Unknown")

    if problem_statement.lower() in ["exit", "quit"]:
        await update.message.reply_text("👋 Goodbye!")
        return ConversationHandler.END

    await update.message.reply_text("🧠 Processing your request... please wait.")

    # Run blocking AI + DB call safely
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


# --- Cancel Command ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Okay, goodbye!")
    return ConversationHandler.END


# --- Main Setup ---
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
