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
def process_hostel_request(problem_statement: str, reg_number: str, name: str, context_limit: int = 10, use_context: bool = True):
    """Process a hostel request with personalized context awareness."""

    llm = ChatGroq(model="llama-3.1-8b-instant")

    # Fetch previous problem statements for this specific user
    context_text = ""
    if use_context:
        previous_problems = fetch_problem_statements(reg_number=reg_number, limit=context_limit)
        if previous_problems:
            summary = summarize_previous_problems(reg_number, llm, context_limit)
            context_text = f"Student: {name} ({reg_number})\nPrevious issues summary:\n{summary}\n"

    # Construct the extraction prompt
    prompt = f"""
    {context_text}

    Current Problem Statement:
    {problem_statement}

    Extract the following details ONLY in the exact format below:

    Name: <name value or NULL if not provided>
    Registration Number: <registration number value or NULL if not provided>
    Problem Statement: <only the complaint or problem related to HOSTEL or ADMISSION issues; if none, output NULL>

    IMPORTANT:
    - Use exactly these field names.
    - Each field on a new line.
    - If not hostel-related, Problem Statement should be NULL.
    """

    print("\n" + "="*60)
    print("Processing request...")
    print("="*60)

    response = llm.invoke([
        SystemMessage(content="You are an excellent details retriever."),
        HumanMessage(content=prompt)
    ])

    generated_response = response.content

    parsed_data = None
    try:
        parsed_data = parse_llm_output(generated_response)
        if not parsed_data:
            print("\n❌ Error: Failed to parse LLM output.")
            return False

        # Display parsed data
        print("\nExtracted Information:")
        print("-" * 60)
        print(f"  Name:                {parsed_data.get('name', 'N/A')}")
        print(f"  Registration Number: {parsed_data.get('registration_number', 'N/A')}")
        print(f"  Problem Statement:   {parsed_data.get('problem_statement', 'N/A')}")
        print("-" * 60)

        # Validate essential fields
        name = parsed_data.get("name", "").strip()
        reg_number = parsed_data.get("registration_number", "").strip()
        problem = parsed_data.get("problem_statement", "").strip()

        if not name or name.upper() == "NULL":
            print("\n⚠️ Missing name field.")
            return False
        if not reg_number or reg_number.upper() == "NULL":
            print("\n⚠️ Missing registration number.")
            return False
        if not problem or problem.upper() == "NULL":
            print("\n⚠️ Problem statement not hostel-related or missing.")
            return False

        # Store in database
        insert_request(parsed_data)
        print("\n✅ Success: Request stored in database.")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n❌ Error processing request: {e}")
        return False


# --- Main interactive loop ---
def main():
    print("\n" + "="*60)
    print(" Hostel Request Automation System")
    print("="*60)
    print("Enter 'quit' anytime to exit.\n")

    llm = ChatGroq(model="llama-3.1-8b-instant")

    while True:
        try:
            # Step 1: Ask for user name and registration number
            name = input("Enter your name: ").strip()
            if name.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!\n")
                break

            reg_number = input("Enter your registration number: ").strip()
            if reg_number.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!\n")
                break

            # Step 2: Check if user exists in DB
            previous_problems = fetch_problem_statements(reg_number=reg_number, limit=5)
            if not previous_problems:
                # New user greeting
                print(f"\n👋 Hello {name}! Welcome to the Hostel Helpdesk System.")
                print("It looks like this is your first time here.\n")
            else:
                # Returning user greeting
                print(f"\n👋 Welcome back, {name}!")
                summary = summarize_previous_problems(reg_number, llm, context_limit=5)
                print("Here's a quick summary of your previous complaints:")
                print(f"📝 {summary}\n")

            # Step 3: Ask for problem statement
            problem_statement = input("Please describe your current problem:\n> ").strip()
            if not problem_statement:
                print("⚠️ Please enter a valid problem statement.\n")
                continue

            # Step 4: Process and store
            success = process_hostel_request(problem_statement, reg_number, name)
            if success:
                print(f"\n✅ Thank you, {name}. Your issue has been recorded.\n")
            else:
                print(f"\n⚠️ Sorry {name}, there was an issue processing your request.\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\nUnexpected error: {e}\n")


if __name__ == "__main__":
    main()
