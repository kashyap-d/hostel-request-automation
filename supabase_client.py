from supabase import create_client, Client
from dotenv import load_dotenv
import os
import re

load_dotenv()

url: str = "https://ecnyhehyimblbopayjys.supabase.co"  # your Supabase URL
key: str = os.getenv("SUPABASE_SERVICE_KEY")  # or "SUPABASE_ANON_KEY" depending on which you want to use

supabase: Client = create_client(url, key)

def parse_llm_output(text):
    """
    Parse LLM output to extract name, registration number, and problem statement.
    Handles various formats including numbered lists and different key variations.
    """
    
    lines = text.strip().split('\n')
    data = {}
    
    # Key mapping for variations (normalized to standard keys)
    key_mappings = {
        'name': 'name',
        'registration_number': 'registration_number',
        'registration_no': 'registration_number',
        'reg_number': 'registration_number',
        'reg_no': 'registration_number',
        'problem_statement': 'problem_statement',
        'problem': 'problem_statement',
    }
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Remove numbered list prefixes (e.g., "1. ", "2. ", etc.)
        line = re.sub(r'^\d+\.\s*', '', line.strip())
        
        # Skip lines that don't contain a colon
        if ':' not in line:
            continue
        
        try:
            # Split on first colon only
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
                
            key_raw = parts[0].strip()
            value = parts[1].strip()
            
            # Normalize key: lowercase, remove special chars, replace spaces with underscores
            key_normalized = re.sub(r'[^\w\s]', '', key_raw.lower())
            key_normalized = re.sub(r'\s+', '_', key_normalized)
            
            # Remove trailing underscores and numbers (from numbered lists)
            key_normalized = key_normalized.strip('_0123456789')
            
            # Map to standard key names
            if key_normalized in key_mappings:
                standard_key = key_mappings[key_normalized]
            else:
                # Try partial matching for variations
                if 'name' in key_normalized and 'registration' not in key_normalized:
                    standard_key = 'name'
                elif 'registration' in key_normalized or ('reg' in key_normalized and 'number' in key_normalized):
                    standard_key = 'registration_number'
                elif 'problem' in key_normalized or 'statement' in key_normalized:
                    standard_key = 'problem_statement'
                else:
                    # Use normalized key as fallback
                    standard_key = key_normalized
            
            data[standard_key] = value
            
        except Exception as e:
            # Skip lines that cause errors
            continue
    
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
    # Test various formats
    test_cases = [
        # Standard format
        """
        Name: xyz
        Registration Number: 123
        Problem Statement: my ac is not working
        """,
        # Numbered list format
        """
        1. Name: John Doe
        2. Registration Number: 2024001
        3. Problem Statement: AC not working
        """,
        # With variations in key names
        """
        Name: Alice Smith
        Reg Number: 2024002
        Problem Statement: WiFi is slow
        """,
        # With extra whitespace
        """
        Name:   Bob Johnson   
        Registration Number:   2024003
        Problem Statement:   Water leak in room
        """,
        # Missing colon space
        """
        Name:Charlie Brown
        Registration Number:2024004
        Problem Statement:Broken window
        """
    ]
    
    print("Testing parse_llm_output with various formats:\n")
    for i, llm_response in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        print("-" * 60)
        parsed_data = parse_llm_output(llm_response)
        print(f"Parsed data: {parsed_data}")
        print(f"Name: {parsed_data.get('name', 'MISSING')}")
        print(f"Registration Number: {parsed_data.get('registration_number', 'MISSING')}")
        print(f"Problem Statement: {parsed_data.get('problem_statement', 'MISSING')}")
        print()
    
    # Test with actual insert (commented out to avoid database writes during testing)
    # llm_response = """
    #     Name: xyz
    #     Registration Number: 123
    #     Problem Statement: my ac is not working
    # """
    # parsed_data = parse_llm_output(llm_response)
    # insert_request(parsed_data)