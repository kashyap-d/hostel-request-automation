import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import TypedDict, List
from supabase_client import parse_llm_output, insert_request

load_dotenv()

class State(TypedDict):
    problem_statement: str
    generated_response: List[AIMessage]

def process_hostel_request(problem_statement: str):
    """Process a hostel request from problem statement to database insertion"""
    
    # Initialize LLM
    llm = ChatGroq(model="llama-3.1-8b-instant")
    
    # Create prompt for extracting details
    prompt = f"""
    Problem Statement:
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
    response = llm.invoke([
        SystemMessage(content="You are an excellent details retriever."),
        HumanMessage(content=prompt)
    ])

    generated_response = response.content
    print(f"[LLM] Generated response:\n{generated_response}\n")

    # Parse the response
    try:
        parsed_data = parse_llm_output(generated_response)
        print(f"[Parser] Parsed data: {parsed_data}")
        
        # Validate required fields
        if parsed_data.get("name") == "NULL" or parsed_data.get("registration_number") == "NULL":
            print("[Error] Missing required fields (name or registration number)")
            return False
            
        if parsed_data.get("problem_statement") == "NULL":
            print("[Warning] Problem statement is not hostel-related")
            return False
        
        # Insert into database
        insert_request(parsed_data)
        print("[Success] Request processed and stored in database")
        return True
        
    except Exception as e:
        print(f"[Error] Failed to process request: {e}")
        return False

def main():
    """Main application loop"""
    print("=== Hostel Request Automation System ===")
    print("Enter 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("Enter complaint and user details:\n")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            if not user_input.strip():
                print("Please enter some details.")
                continue
                
            success = process_hostel_request(user_input)
            
            if success:
                print("Request processed successfully!\n")
            else:
                print("Failed to process request. Please try again.\n")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Unexpected error: {e}\n")

if __name__ == "__main__":
    main()
