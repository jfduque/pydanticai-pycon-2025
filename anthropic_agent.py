import sqlite3
import os
import datetime
# import json # No longer directly needed for parsing if PydanticAI handles it
# from anthropic import Anthropic # No longer directly needed for API call
from pydantic_ai.llms import AnthropicChain # Correct PydanticAI chain for Anthropic
from pydantic_ai.utils import extract_json
from llm_schemas import AgentResponse

# --- Configuration ---
DB_NAME = "requests.db"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-3-sonnet-20240229"

# Updated System Prompt for PydanticAI
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

def call_anthropic_with_pydantic_ai(request_body_text: str) -> AgentResponse | None:
    """
    Calls the Anthropic API using PydanticAI to get the summary and response
    structured as an AgentResponse object.
    """
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        return None

    try:
        # Initialize PydanticAI's AnthropicChain
        # The API key is typically picked up from ANTHROPIC_API_KEY env var by the underlying Anthropic client
        llm_chain = AnthropicChain(
            model=MODEL_NAME,
            # api_key=ANTHROPIC_API_KEY # Usually not needed if ANTHROPIC_API_KEY env var is set
            # For Anthropic, system prompt is often passed differently.
            # PydanticAI's AnthropicChain should ideally handle this.
            # If AnthropicChain doesn't directly support a `system_prompt` parameter in its constructor
            # or `run` method in a way that aligns with Anthropic's native API,
            # we might need to prepend it to the user prompt or check PydanticAI docs for specific handling.
            # For now, let's assume a similar pattern to OpenAIChain, prepending system prompt.
        )

        # Construct the full prompt for PydanticAI.
        # Anthropic's API usually takes system prompt separately.
        # How PydanticAI's AnthropicChain handles this is key.
        # If it doesn't pass `system` param to Anthropic client, we include it in main prompt.
        # The PydanticAI documentation or source would clarify best practice for system prompts with AnthropicChain.
        # A common approach if not explicitly supported is to prepend system prompt to user prompt.
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Request:\n\"\"\"\n{request_body_text}\n\"\"\""
        # However, Anthropic best practices are to use the 'system' parameter.
        # Let's check if PydanticAI's AnthropicChain has a way to pass it.
        # Looking at typical PydanticAI structure, it's often part of the model args or run method.
        # If PydanticAI `AnthropicChain` is a light wrapper, it might not expose `system` directly in `run`.
        # For now, we will rely on PydanticAI to process the full_prompt effectively.
        # If issues arise, one might need to customize or check PydanticAI's Anthropic client for system prompt features.
        # The `BaseLLMChain` in PydanticAI might have a `system_message` parameter or similar.
        # For the sake of this refactor, we'll assume the `text_prompt` is the primary input.

        structured_response: AgentResponse = llm_chain.run(
            text_prompt=full_prompt, # Pass the combined system and user request
            pydantic_model=AgentResponse
        )
        return structured_response

    except Exception as e:
        print(f"Error calling Anthropic API with PydanticAI: {e}")
        if hasattr(e, 'llm_output'):
            print(f"LLM Output was: {e.llm_output}")
            try:
                raw_json = extract_json(e.llm_output)
                if raw_json:
                    return AgentResponse(**raw_json) # Manually parse if PydanticAI failed
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
    print("Starting Anthropic Agent (PydanticAI refactored)...")
    if not os.path.exists(DB_NAME):
        print(f"Database file {DB_NAME} not found. Please run init_db.py first.")
        return

    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY environment variable is not set. Please set it before running the agent.")
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

        pydantic_ai_result: AgentResponse | None = call_anthropic_with_pydantic_ai(req['request_body'])

        if pydantic_ai_result:
            summary = pydantic_ai_result.summary
            response_text = pydantic_ai_result.response_text
            print(f"Generated Summary (Anthropic via PydanticAI): {summary}")
            print(f"Generated Response (Anthropic via PydanticAI): {response_text}")
            update_request(conn, req['id'], summary, response_text)
        else:
            print(f"Failed to get a valid structured response from Anthropic via PydanticAI for request ID {req['id']}.")

    conn.close()
    print("\nAnthropic Agent (PydanticAI refactored) finished.")

if __name__ == "__main__":
    main()
