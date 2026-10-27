from dataclasses import dataclass
from typing import Literal, Optional

from dotenv import load_dotenv

from classifier import Ticket, classify_complaint, make_llm
from supabase_client import fetch_problem_statements, format_history, insert_request, summaries_from

load_dotenv()

CONTEXT_LIMIT = 5


@dataclass
class RequestResult:
    status: Literal["recorded", "rejected", "error"]
    ticket: Optional[Ticket] = None


# --- Helper function: summarize previous problems ---
def summarize_previous_problems(previous_summaries, llm) -> str:
    """Summarize one student's previous problem statements."""
    from langchain_core.messages import HumanMessage, SystemMessage

    if not previous_summaries:
        return "No previous problems found."

    joined = "\n".join(f"- {s}" for s in previous_summaries)
    summary_prompt = f"""
    Summarize the key issues and recurring themes in the following list of student complaints.
    Keep the summary short (max 3 lines).
    Complaints:
    {joined}
    """
    response = llm.invoke([
        SystemMessage(content="You are a concise summarizer."),
        HumanMessage(content=summary_prompt)
    ])
    return response.content.strip()


# --- Core Function ---
def process_hostel_request(name: str, reg_number: str, problem_statement: str, llm=None) -> RequestResult:
    """Classify a complaint and store it if it is hostel-related."""
    llm = llm or make_llm()
    previous = summaries_from(fetch_problem_statements(reg_number, limit=CONTEXT_LIMIT))

    ticket = classify_complaint(problem_statement, previous, llm)
    if ticket is None:
        return RequestResult("error")
    if not ticket.is_hostel_related:
        return RequestResult("rejected", ticket)

    try:
        insert_request(name, reg_number, ticket)
    except Exception as e:
        print(f"[Error] Failed to store request: {type(e).__name__}")
        return RequestResult("error", ticket)
    return RequestResult("recorded", ticket)


def describe_ticket(ticket: Ticket) -> str:
    """Human-readable confirmation of what was stored."""
    lines = [
        f"Problem:  {ticket.summary}",
        f"Category: {ticket.category}",
        f"Urgency:  {ticket.urgency}",
        f"Location: {ticket.location or 'not given'}",
    ]
    if ticket.is_repeat:
        lines.append("Note:     you have reported this before")
    return "\n".join(lines)


def main():
    print("\n" + "="*60)
    print(" Hostel Request Automation System")
    print("="*60)
    print("Enter 'quit' anytime to exit.\n")

    llm = make_llm()

    name = input("Enter your name: ").strip()
    reg_number = input("Enter your registration number: ").strip()

    user_problems = fetch_problem_statements(reg_number, limit=CONTEXT_LIMIT)

    if user_problems:
        print(f"\n👋 Welcome back, {name}! It’s great to see you again.")
        print("\n📜 Your recent issues:")
        print("-" * 60)
        print(format_history(user_problems))
        print("-" * 60)

        summary = summarize_previous_problems(summaries_from(user_problems), llm)
        print(f"\n🧾 Summary of your previous problems:\n➡️ {summary}\n")
        print("Let's continue — what would you like help with today?\n")
    else:
        print(f"\n👋 Hello {name}! Welcome to the Hostel Helpdesk System.")
        print("It looks like this is your first time here.\n")

    while True:
        user_problem = input("Please describe your current problem:\n> ")

        if user_problem.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!\n")
            break

        if not user_problem.strip():
            print("Please enter some details.\n")
            continue

        print("\nProcessing request...")
        result = process_hostel_request(name, reg_number, user_problem, llm)

        if result.status == "recorded":
            print("\n✅ Request recorded:")
            print(describe_ticket(result.ticket))
        elif result.status == "rejected":
            print("\n⚠️  This doesn't look like a hostel or admission problem, so it was not recorded.")
        else:
            print("\n❌ Something went wrong. Please try again.")
        print("\n")


if __name__ == "__main__":
    main()
