import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import TypedDict, List
from supabase_client import parse_llm_output, insert_request, fetch_problem_statements

load_dotenv()

class State(TypedDict):
    problem_statement: str
    generated_response: List[AIMessage]

# --- Helper function: summarize previous problems ---
def summarize_previous_problems(reg_number: str, llm, context_limit: int = 10) -> str:
    """Fetch and summarize a user's previous problem statements."""
    previous_problems = fetch_problem_statements(reg_number=reg_number, limit=context_limit)
    if not previous_problems:
        return "No previous problems found."

    joined = "\n".join([f"- {p.get('problem_statement', '')}" for p in previous_problems if p.get('problem_statement')])
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
def process_hostel_request(name: str, reg_number: str, problem_statement: str, context_limit: int = 10, use_context: bool = True):
    """Process a hostel request given user details and a problem statement"""

    # Initialize LLM
    llm = ChatGroq(model="llama-3.1-8b-instant")

    # Fetch previous problem statements as context
    context_text = ""
    if use_context:
        previous_problems = fetch_problem_statements(limit=context_limit)
        if previous_problems:
            context_text = "\n\nPrevious Problem Statements (for context):\n"
            for idx, problem in enumerate(previous_problems, 1):
                context_text += f"{idx}. Student: {problem.get('student_name', 'N/A')} (Reg: {problem.get('reg_number', 'N/A')})\n"
                context_text += f"   Problem: {problem.get('problem_statement', 'N/A')}\n"
                context_text += f"   Date: {problem.get('created_at', 'N/A')}\n\n"

    # Create simplified prompt (no name/reg number extraction)
    prompt = f"""
    {context_text}
    Current Problem Description:
    {problem_statement}

    Task:
    Determine if this complaint is related to HOSTEL or ADMISSION.
    If it is, return the problem statement cleaned up (grammar corrected, remove unnecessary phrases).
    If not, output "NULL".

    Output format:
    Problem Statement: <cleaned problem statement or NULL>
    """

    print("\n" + "="*60)
    print("Processing request...")
    print("="*60)

    response = llm.invoke([
        SystemMessage(content="You are an excellent problem classifier and cleaner."),
        HumanMessage(content=prompt)
    ])

    generated_response = response.content

    if os.getenv("DEBUG", "False").lower() == "true":
        print(f"\n[DEBUG] Raw LLM Response:\n{generated_response}\n")

    try:
        parsed_data = parse_llm_output(generated_response)

        problem = parsed_data.get("problem_statement", "").strip()

        print("\n Extracted Information:")
        print("-" * 60)
        print(f"  Name:                {name}")
        print(f"  Registration Number: {reg_number}")
        print(f"  Problem Statement:   {problem}")
        print("-" * 60)

        if not problem or problem.upper() == "NULL":
            print("\n⚠️  Warning: Problem statement is not hostel-related or is missing.")
            return False

        # Insert into database
        insert_request({
            "name": name,
            "registration_number": reg_number,
            "problem_statement": problem
        })

        print("\n✅ Success: Request processed and stored in database.")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ Error: Failed to process request: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False


def main():
    print("\n" + "="*60)
    print(" Hostel Request Automation System")
    print("="*60)
    print("Enter 'quit' anytime to exit.\n")

    name = input("Enter your name: ").strip()
    reg_number = input("Enter your registration number: ").strip()

    # Check if user exists
    previous_problems = fetch_problem_statements()
    existing_user = any(p.get("reg_number") == reg_number for p in previous_problems)

    if existing_user:
        print(f"\n👋 Welcome back, {name}! It’s great to see you again.")
        print("I’ve reviewed your previous requests — let's continue.\n")
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

        success = process_hostel_request(name, reg_number, user_problem)

        print("\n")



if __name__ == "__main__":
    main()
