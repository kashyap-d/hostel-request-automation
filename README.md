# Hostel Request Automation

A Telegram and command-line helpdesk bot that turns students' free-text hostel complaints into structured, validated tickets stored in Supabase Postgres.

A message like *"bhai room 210 ka fan kaam nahi kar raha"* should become a ticket like:

```text
Problem:  The fan in room 210 is not working.
Category: electrical
Urgency:  medium
Location: room 210
```

Off-topic messages ("When is the DBMS assignment due?") are rejected and not stored.

## How it works

```text
student message (Telegram or CLI)
  -> fetch this student's own recent requests        (supabase_client.py)
  -> LLM fills the Ticket schema via tool calling      (classifier.py)
  -> Pydantic validates the answer; one retry on failure
  -> rejected  -> tell the student, store nothing
     recorded  -> insert into Postgres, show the student what was saved
     error     -> tell the student to try again
```

Design choices:

- **Structured output instead of text parsing.** The model must call a `Ticket` tool whose fields are typed (`category` and `urgency` are fixed enums). Pydantic validates the result, and a hostel ticket without a category, urgency or summary is rejected. The database has matching `CHECK` constraints.
- **The model never writes to the database.** It only proposes a ticket; application code decides whether to store it.
- **Only the student's own history is used as context.** Other students' names, registration numbers and complaints are never sent to the model or shown to a user.
- **Complaint text is treated as data.** It is wrapped in `<complaint>` tags, and the prompt tells the model to ignore any instructions inside it. The eval set includes prompt-injection attempts to check this.
- **Locations are never guessed.** If the student doesn't state a room or block, `location` stays empty. The evals measure this as "no invented location".
- **Rejection and failure are different outcomes.** The student is told whether their message was off-topic or whether something broke.

## Evaluation

`evals/complaints.jsonl` holds 55 hand-labelled messages: complaints in every category, admission queries, off-topic messages, prompt-injection attempts, Hinglish, and repeat complaints with history. Where a label is reasonably debatable (is a broken geyser plumbing or electrical?), the case lists every acceptable answer.

```bash
python -m evals.run_eval                                   # default model
python -m evals.run_eval --model llama-3.3-70b-versatile   # compare another Groq model
```

The runner reports accept/reject accuracy, precision and recall, category, urgency and location accuracy, the invented-location rate, prompt-injection resistance, repeat detection, and p50/p95 latency. It lists every failing case and saves a markdown report in `evals/results/`.

The labels are synthetic. Before relying on the numbers, add real (anonymised) complaints.

## Setup

1. Install dependencies (Python 3.10+):

   ```bash
   pip install -r requirements-dev.txt
   ```

2. Copy `.env.example` to `.env` and fill in `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` and `TELEGRAM_TOKEN`.

3. Run `migrations/001_structured_tickets.sql` in the Supabase SQL editor. It creates the tables if they don't exist and adds the ticket columns to existing ones, so it's safe to run more than once.

4. Create a Telegram bot with [@BotFather](https://t.me/BotFather) (`/newbot`) and put its token in `.env`.

## Usage

```bash
python telegram_wrapper.py   # Telegram bot (polling)
python main.py               # command-line version
pytest -q                    # unit tests; no API keys needed
```

## Project layout

```text
classifier.py         Ticket schema, prompt, LLM call with validation and retry
main.py               request processing and the command-line interface
telegram_wrapper.py   Telegram conversation flow
supabase_client.py    database access, always scoped to one student
migrations/           database schema
evals/                labelled cases and the eval runner
tests/                unit tests with a fake LLM
```

## Contributors

Built by [kashyap-d](https://github.com/kashyap-d), [akshat652256](https://github.com/akshat652256) and [edwinsajith](https://github.com/edwinsajith).
