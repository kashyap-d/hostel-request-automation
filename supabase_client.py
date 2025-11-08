from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

url: str = "https://ecnyhehyimblbopayjys.supabase.co"  # your Supabase URL
key: str = os.getenv("SUPABASE_SERVICE_KEY")  # or "SUPABASE_ANON_KEY" depending on which you want to use

supabase: Client = create_client(url, key)

def parse_llm_output(text):
    lines = text.strip().split('\n')
    data = {}
    for line in lines:
        key, value = line.split(':', 1)
        data[key.strip().lower().replace(" ", "_")] = value.strip()
    return data

def fetch_problem_statements(limit: int = 10, reg_number: str = None):
    """
    Fetch problem statements from the request table to use as context.
    
    Args:
        limit: Number of recent problem statements to fetch (default: 10)
        reg_number: Optional registration number to filter by specific student
    
    Returns:
        List of dictionaries containing problem_statement, reg_number, student_name, and created_at
    """
    try:
        query = supabase.table("request").select("problem_statement, reg_number, student_name, created_at")
        
        # Filter by registration number if provided
        if reg_number:
            query = query.eq("reg_number", reg_number)
        
        # Order by created_at descending (most recent first) and limit results
        response = query.order("created_at", desc=True).limit(limit).execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"[Error] Failed to fetch problem statements: {e}")
        return []

def insert_request(data):
    # Insert into StudentInfo if not exists
    supabase.table("studentinfo").upsert({
        "reg_number": data["registration_number"],
        "name": data["name"],
        "hostel_block": None  # set this if available
    }).execute()

    # Insert into Request table
    supabase.table("request").insert({
        "reg_number": data["registration_number"],
        "student_name": data["name"],
        "problem_statement": data["problem_statement"],
    }).execute()

if __name__ == "__main__":
    llm_response = """
    Name: xyz
    Registration Number: 123
    Problem Statement: my ac is not working
    """
    parsed_data = parse_llm_output(llm_response)
    insert_request(parsed_data)