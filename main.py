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

def process_hostel_request(problem_statement: str, context_limit: int = 10, use_context: bool = True):
    """Process a hostel request from problem statement to database insertion"""
    
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
    
    # Create prompt for extracting details
    prompt = f"""
    {context_text}
    Current Problem Statement:
    {problem_statement}

    Extract the following details ONLY in the order given below.
    Do NOT REARRANGE OR INTERCHANGE THE ORDER OF THE FIELDS.

    1. Name: <name value or NULL if not provided>
    2. Registration Number: <registration number value or NULL if not provided>
    3. Problem Statement: <only the complaint or problem related to HOSTEL or ADMISSION issues; if none, output NULL>

    DISREGARD ANY ADDITIONAL INFORMATION or user metadata in the Problem Statement field.
    If the complaint is NOT related to hostel, please output NULL for Problem Statement.

    If any field is missing, output NULL as its value.

    DO NOT output anything else.
    """

    # Get LLM response
    print("\n" + "="*60)
    print("Processing request...")
    print("="*60)
    
    response = llm.invoke([
        SystemMessage(content="You are an excellent details retriever."),
        HumanMessage(content=prompt)
    ])

    generated_response = response.content

    # Parse the response
    try:
        parsed_data = parse_llm_output(generated_response)
        
        # Display parsed data in a clean format
        print("\n📋 Extracted Information:")
        print("-" * 60)
        print(f"  Name:                {parsed_data.get('name', 'N/A')}")
        print(f"  Registration Number: {parsed_data.get('registration_number', 'N/A')}")
        print(f"  Problem Statement:   {parsed_data.get('problem_statement', 'N/A')}")
        print("-" * 60)
        
        # Validate required fields
        if parsed_data.get("name") == "NULL" or parsed_data.get("registration_number") == "NULL":
            print("\n❌ Error: Missing required fields (name or registration number)")
            return False
            
        if parsed_data.get("problem_statement") == "NULL":
            print("\n⚠️  Warning: Problem statement is not hostel-related")
            return False
        
        # Insert into database
        insert_request(parsed_data)
        print("\n✅ Success: Request processed and stored in database")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: Failed to process request: {e}")
        print("="*60)
        return False

def main():
    """Main application loop"""
    print("\n" + "="*60)
    print("  🏠 Hostel Request Automation System")
    print("="*60)
    print("  Enter 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("📝 Enter complaint and user details:\n> ")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!\n")
                break
                
            if not user_input.strip():
                print("⚠️  Please enter some details.\n")
                continue
                
            success = process_hostel_request(user_input)
            
            if success:
                print("\n")
            else:
                print("\n")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}\n")

if __name__ == "__main__":
    main()
