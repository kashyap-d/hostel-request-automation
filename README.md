# Hostel Request Automation System

An automated system for processing hostel-related complaints using AI and storing them in Supabase.

## Features

- AI-powered extraction of student details and problem statements
- Automatic validation of hostel-related complaints
- Database storage using Supabase
- Interactive command-line interface
- Telegram Bot integration for user-friendly complaint submission

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Environment variables:

   - Copy `env.example` to `.env`:
     ```bash
     copy env.example .env
     ```
   - Edit `.env` and set the required keys:

     ```
     GROQ_API_KEY=your_groq_api_key_here
     SUPABASE_URL=your_supabase_url_here
     SUPABASE_SERVICE_KEY=your_supabase_service_key_here
     TELEGRAM_TOKEN=your_telegram_bot_token_here
     ```

3. Database setup:

   - Ensure your Supabase database has the required tables:
     - `studentinfo` table with columns: `reg_number`, `name`, `hostel_block`
     - `request` table with columns: `reg_number`, `student_name`, `problem_statement`

## Telegram — Step-by-step setup

1. Create a Telegram Bot
   - Open Telegram.
   - Search for @BotFather.
   - Send the command:
     ```
     /newbot
     ```
   - Follow the prompts to choose a name and username.
   - BotFather will return a Bot Token like:
     ```
     123456789:ABCdefGhIJKlmNoPQrsTUVwxYZ
     ```
   - Add that token to your `.env` as `TELEGRAM_TOKEN`.

2. Run the bot locally
   - Make sure `.env` is populated and dependencies installed.
   - Start the Telegram wrapper:
     ```bash
     python telegram_wrapper.py
     ```
   - The bot will run in polling mode and accept user complaints.

## Usage

Run the main application:

```bash
python main.py
```

Or run the Telegram bot:

```bash
python telegram_wrapper.py
```

Enter student complaints in the format:

```
Name: John Doe
Registration Number: 2024001
Problem: My AC is not working in room 101
```

The system will extract the details, validate it's hostel-related, and store it in the database.

## Files

- `main.py` - Main application combining LLM processing and database operations
- `supabase_client.py` - Database operations and data parsing
- `telegram_wrapper.py` - Telegram bot interface
- `prototype.py` - Original LLM processing prototype
- `requirements.txt` - Python dependencies
- `env.example` - Environment variables template

## Example Input

```
Name: Alice Smith
Registration Number: 2024002
Problem: The WiFi is very slow in my hostel room
```
