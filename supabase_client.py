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