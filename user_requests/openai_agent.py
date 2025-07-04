import os
import sqlite3
import datetime

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from llm_schemas import AgentResponse

# --- Configuration ---
DB_NAME = os.path.join(os.path.dirname(__file__), "requests.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o"

SYSTEM_PROMPT = """You are an AI assistant. Your task is to process user requests based on the provided text.
1. First, summarize the user's request into concise American English.
2. Then decide if the request can be fulfilled. You MUST REJECT any request that is illegal, dangerous, promotes violence or hate speech, or is otherwise malicious or unethical.
   - For requests you reject, respond with a polite refusal in the original language of the request.
   - For requests you accept, respond with a short affirmation in the original language of the request.
You need to provide two fields in your output: `summary` and `response_text`."""


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_unprocessed_requests(conn):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM requests WHERE response IS NULL ORDER BY created_at ASC"
    )
    return cursor.fetchall()


def call_openai_with_pydantic_ai(
    agent: Agent, request_text: str
) -> AgentResponse | None:
    """
    Runs the agent synchronously on the user's request_text.
    Returns an AgentResponse instance (with .summary and .response_text) or None on error.
    """
    try:
        run_result = agent.run_sync(request_text)
        return run_result.output  # Already validated as AgentResponse
    except Exception as e:
        print(f"Error during agent.run_sync: {e}")
        return None


def update_request(conn, request_id, summary, response_text):
    cursor = conn.cursor()
    processed_at = datetime.datetime.now().isoformat()
    try:
        cursor.execute(
            "UPDATE requests SET summary = ?, response = ?, processed_at = ? WHERE id = ?",
            (summary, response_text, processed_at, request_id),
        )
        conn.commit()
        print(f"✔ Updated request {request_id}")
    except sqlite3.Error as db_err:
        print(f"DB error updating request {request_id}: {db_err}")
        conn.rollback()


def main():
    print("Starting agent")
    if not os.path.exists(DB_NAME):
        print(f"DB not found: {DB_NAME}. Run init_db.py first.")
        return
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set.")
        return

    # Build the provider → model → agent pipeline
    provider = OpenAIProvider(api_key=OPENAI_API_KEY)
    model = OpenAIModel(MODEL_NAME, provider=provider)
    agent = Agent(model, instructions=SYSTEM_PROMPT, output_type=AgentResponse)

    conn = get_db_connection()
    requests = get_unprocessed_requests(conn)
    if not requests:
        print("No new requests to process.")
    else:
        print(f"Found {len(requests)} new requests.")

    for req in requests:
        print(f"\n→ Processing ID {req['id']}")
        result = call_openai_with_pydantic_ai(agent, req["request_body"])
        if result:
            print(f"  • Summary:      {result.summary}")
            print(f"  • Response:     {result.response_text}")
            update_request(conn, req["id"], result.summary, result.response_text)
        else:
            print(f"  ✖ Failed to process ID {req['id']}")

    conn.close()
    print("Agent run complete.")


if __name__ == "__main__":
    main()
