import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.messages import AIMessage
from typing import TypedDict, Annotated, List

load_dotenv()
llm = ChatGroq(model="llama-3.1-8b-instant")

class State(TypedDict):
    problem_statement: str
    generated_response: List[AIMessage]

def model(state: State):
    problem_statement = state["problem_statement"]

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

    response = llm.invoke([
        SystemMessage(content="You are an excellent details retriever."),
        HumanMessage(content=prompt)
    ])

    generated_response = response.content
    print(f"[model_node] Generated response:\n{generated_response}\n")

    return {
        "generated_response": [AIMessage(content=generated_response)],
    }


if __name__ == "__main__":
    user_prompt = input("Enter complaint and user details:\n")
    state = {"problem_statement": user_prompt}
    output = model(state)