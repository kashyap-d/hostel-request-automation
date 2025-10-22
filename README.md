# Hostel Request Automation System

An automated system for processing hostel-related complaints using AI and storing them in Supabase.

## Features

- AI-powered extraction of student details and problem statements
- Automatic validation of hostel-related complaints
- Database storage using Supabase
- Interactive command-line interface

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables:**

   - Copy `env.example` to `.env`
   - Fill in your API keys:
     - `GROQ_API_KEY`: Get from [Groq Console](https://console.groq.com/)
     - `SUPABASE_SERVICE_KEY`: Get from your Supabase project settings

3. **Database setup:**
   - Ensure your Supabase database has the required tables:
     - `studentinfo` table with columns: `reg_number`, `name`, `hostel_block`
     - `request` table with columns: `reg_number`, `student_name`, `problem_statement`

## Usage

Run the main application:

```bash
python main.py
```

Enter student complaints in the format:

```
Name: John Doe
Registration Number: 2024001
Problem: My AC is not working in room 101
```

## Files

- `main.py` - Main application combining LLM processing and database operations
- `supabase_client.py` - Database operations and data parsing
- `prototype.py` - Original LLM processing prototype
- `requirements.txt` - Python dependencies
- `env.example` - Environment variables template

## Example Input

```
Name: Alice Smith
Registration Number: 2024002
Problem: The WiFi is very slow in my hostel room
```

The system will extract the details, validate it's hostel-related, and store it in the database.
