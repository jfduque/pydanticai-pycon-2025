import sqlite3
import os
import datetime
import asyncio
from pydantic_ai import Agent
from llm_schemas import AgentResponse

# --- Configuration ---
DB_NAME = os.path.join(os.path.dirname(__file__), "requests.db")
# ANTHROPIC_API_KEY is read from environment variables by default
MODEL_NAME = "anthropic:claude-sonnet-4-0"

# System Prompt for the Agent
SYSTEM_PROMPT = """You are an AI assistant. Your task is to process user requests based on the provided text.
1.  First, summarize the user's request into concise American English. This summary should capture the core essence of what the user is asking for.
2.  Second, decide if the request can be fulfilled. You MUST REJECT any request that is illegal, dangerous, promotes violence or hate speech, or is otherwise malicious or unethical.
    -   For requests you reject, the response text should be a polite refusal in the original language of the request, briefly stating that the request cannot be fulfilled due to its nature.
    -   For requests you accept, the response text should be a short affirmation in the original language of the request, like "Okay, I can help with that." or "Understood, I will proceed with that request."
You need to provide a summary and a response_text.
"""


def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_unprocessed_requests(conn):
    """Fetches all requests that have not yet been processed (response is NULL)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM requests WHERE response IS NULL ORDER BY created_at ASC"
    )
    return cursor.fetchall()


async def call_anthropic_with_pydantic_ai(
    request_body_text: str,
) -> AgentResponse | None:
    """
    Calls the Anthropic API using the PydanticAI Agent to get a structured response.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        return None

    try:
        # Initialize the PydanticAI Agent
        agent = Agent(
            MODEL_NAME, system_prompt=SYSTEM_PROMPT, result_type=AgentResponse
        )

        result = await agent.run(request_body_text)

        return result.data

    except Exception as e:
        print(f"Error calling Anthropic API with PydanticAI: {e}")
        return None


def update_request(conn, request_id, summary, response_text):
    """Updates the request in the database with the summary and response."""
    cursor = conn.cursor()
    processed_at = datetime.datetime.now().isoformat()
    try:
        cursor.execute(
            "UPDATE requests SET summary = ?, response = ?, processed_at = ? WHERE id = ?",
            (summary, response_text, processed_at, request_id),
        )
        conn.commit()
        print(f"Request ID {request_id} processed and updated successfully.")
    except sqlite3.Error as e:
        print(f"Database error updating request {request_id}: {e}")
        conn.rollback()


async def main():
    """Main function to process requests."""
    print("Starting Anthropic Agent (PydanticAI)...")
    if not os.path.exists(DB_NAME):
        print(f"Database file {DB_NAME} not found. Please run init_db.py first.")
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        exit(1)

    conn = get_db_connection()
    if not conn:
        return

    unprocessed_requests = get_unprocessed_requests(conn)

    if not unprocessed_requests:
        print("No new requests to process.")
    else:
        print(f"Found {len(unprocessed_requests)} new requests.")

    for req in unprocessed_requests:
        print(f"\nProcessing request ID: {req['id']}")
        print(f"Request body: {req['request_body'][:200]}...")

        pydantic_ai_result = await call_anthropic_with_pydantic_ai(req["request_body"])

        if pydantic_ai_result:
            print(
                f"Generated Summary (Anthropic via PydanticAI): {pydantic_ai_result.summary}"
            )
            print(
                f"Generated Response (Anthropic via PydanticAI): {pydantic_ai_result.response_text}"
            )
            update_request(
                conn,
                req["id"],
                pydantic_ai_result.summary,
                pydantic_ai_result.response_text,
            )
        else:
            print(
                f"Failed to get a valid structured response for request ID {req['id']}."
            )

    conn.close()
    print("\nAnthropic Agent (PydanticAI) finished.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user (Ctrl+C). Exiting...")
