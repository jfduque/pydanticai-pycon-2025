import sqlite3
import os
import datetime
# from openai import OpenAI # No longer directly needed for API call if PydanticAI handles client
from pydantic_ai.llms import OpenAIChain
from pydantic_ai.utils import extract_json
from llm_schemas import AgentResponse # Import the Pydantic model

# --- Configuration ---
DB_NAME = "requests.db"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o" # PydanticAI should pick this up via OpenAIChain

# Updated System Prompt: PydanticAI handles JSON formatting, so focus on task.
# The core instructions about summarization, rejection criteria, and response language should remain.
# PydanticAI uses the Pydantic model's field descriptions to help guide the LLM.
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
    cursor.execute("SELECT * FROM requests WHERE response IS NULL ORDER BY created_at ASC")
    requests = cursor.fetchall()
    return requests

def call_openai_with_pydantic_ai(request_body_text: str) -> AgentResponse | None:
    """
    Calls the OpenAI API using PydanticAI to get the summary and response
    structured as an AgentResponse object.
    """
    if not OPENAI_API_KEY:
        # PydanticAI's OpenAIChain might also check this, but good to have an early exit.
        print("Error: OPENAI_API_KEY environment variable not set.")
        return None

    try:
        # Initialize PydanticAI's OpenAIChain
        # The API key is typically picked up from the environment by the underlying OpenAI client
        # or can be passed explicitly if needed: api_key=OPENAI_API_KEY
        llm_chain = OpenAIChain(
            model=MODEL_NAME,
            # api_key=OPENAI_API_KEY # Usually not needed if OPENAI_API_KEY env var is set
        )

        # Construct the full prompt for PydanticAI, including the system message
        # PydanticAI's `run` method takes the text prompt directly.
        # The system prompt is usually part of the model's configuration or handled by PydanticAI if it supports system prompts directly in a newer version.
        # For now, we prepend it to the user request for clarity, or rely on how OpenAIChain internally handles system context.
        # A common way is to pass system message during chain setup or if the model supports it.
        # Let's assume for now we can provide it as part of the prompt context or that PydanticAI's OpenAIChain handles it.
        # The `llm_chain.run` method expects the main text prompt.
        # We will combine system prompt and user request for the `run` method.

        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Request:\n\"\"\"\n{request_body_text}\n\"\"\""

        # Use PydanticAI to generate the structured response
        # The `run` method will return an instance of the Pydantic model (AgentResponse)
        structured_response: AgentResponse = llm_chain.run(
            text_prompt=full_prompt, # Pass the user's request text
            pydantic_model=AgentResponse
        )
        return structured_response

    except Exception as e:
        # Catching a broad exception, specific PydanticAI errors could be caught if known
        print(f"Error calling OpenAI API with PydanticAI: {e}")
        # Attempt to extract JSON if it's a direct JSON output issue that PydanticAI couldn't parse
        if hasattr(e, 'llm_output'):
            print(f"LLM Output was: {e.llm_output}")
            try:
                # Try to manually parse if the error indicates raw JSON was returned but not parsed
                # This is a fallback, ideally PydanticAI handles this.
                raw_json = extract_json(e.llm_output)
                if raw_json:
                    return AgentResponse(**raw_json)
            except Exception as extract_e:
                print(f"Could not manually extract JSON from LLM output: {extract_e}")
        return None


def update_request(conn, request_id, summary, response_text):
    """Updates the request in the database with the summary and response."""
    cursor = conn.cursor()
    processed_at = datetime.datetime.now()
    try:
        cursor.execute(
            "UPDATE requests SET summary = ?, response = ?, processed_at = ? WHERE id = ?",
            (summary, response_text, processed_at, request_id)
        )
        conn.commit()
        print(f"Request ID {request_id} processed and updated successfully.")
    except sqlite3.Error as e:
        print(f"Database error updating request {request_id}: {e}")
        conn.rollback()


def main():
    """Main function to process requests."""
    print("Starting OpenAI Agent (PydanticAI refactored)...")
    if not os.path.exists(DB_NAME):
        print(f"Database file {DB_NAME} not found. Please run init_db.py first.")
        return

    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable is not set. Please set it before running the agent.")
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

        pydantic_ai_result: AgentResponse | None = call_openai_with_pydantic_ai(req['request_body'])

        if pydantic_ai_result:
            # The result is already an AgentResponse Pydantic model instance
            summary = pydantic_ai_result.summary
            response_text = pydantic_ai_result.response_text
            print(f"Generated Summary (OpenAI via PydanticAI): {summary}")
            print(f"Generated Response (OpenAI via PydanticAI): {response_text}")
            update_request(conn, req['id'], summary, response_text)
        else:
            print(f"Failed to get a valid structured response from OpenAI via PydanticAI for request ID {req['id']}.")

    conn.close()
    print("\nOpenAI Agent (PydanticAI refactored) finished.")

if __name__ == "__main__":
    main()
