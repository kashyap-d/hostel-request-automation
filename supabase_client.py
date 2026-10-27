import os
from typing import List

from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client():
    """Create the Supabase client on first use, so importing this module needs no credentials."""
    global _client
    if _client is None:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        _client = create_client(url, key)
    return _client


def fetch_problem_statements(reg_number: str, limit: int = 10) -> List[dict]:
    """
    Fetch one student's most recent requests, newest first.

    Always scoped to a single registration number: other students' complaints
    are never shown to a user or sent to the LLM.
    """
    try:
        response = (
            get_client()
            .table("request")
            .select("problem_statement, category, urgency, created_at")
            .eq("reg_number", reg_number)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[Error] Failed to fetch problem statements: {type(e).__name__}")
        return []


def insert_request(name: str, reg_number: str, ticket) -> None:
    """Store a validated ticket. Raises if the database rejects the write."""
    client = get_client()

    # Insert into StudentInfo if not exists. hostel_block is deliberately omitted
    # so an upsert never wipes a block that was already recorded.
    client.table("studentinfo").upsert({
        "reg_number": reg_number,
        "name": name,
    }).execute()

    client.table("request").insert({
        "reg_number": reg_number,
        "student_name": name,
        "problem_statement": ticket.summary,
        "category": ticket.category,
        "urgency": ticket.urgency,
        "location": ticket.location,
        "is_repeat": ticket.is_repeat,
    }).execute()


def summaries_from(rows: List[dict]) -> List[str]:
    """Extract non-empty problem statements from request rows."""
    return [r["problem_statement"] for r in rows if r.get("problem_statement")]


def format_history(rows: List[dict]) -> str:
    """Render a student's past requests as a numbered list."""
    lines = []
    for idx, r in enumerate(rows, 1):
        label = f"[{r['category']}] " if r.get("category") else ""
        lines.append(f"{idx}. {label}{r.get('problem_statement', 'N/A')}  ({r.get('created_at', 'Unknown date')})")
    return "\n".join(lines)
