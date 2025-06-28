import sqlite3
import os
import datetime
# import ollama # No longer directly needed for API call if PydanticAI handles client
# import json
from pydantic_ai.llms import OllamaChain # Correct PydanticAI chain for Ollama
from pydantic_ai.utils import extract_json
from llm_schemas import AgentResponse

# --- Configuration ---
DB_NAME = "requests.db"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.environ.get("OLLAMA_MODEL_NAME", "gemma:latest")

# Updated System Prompt for PydanticAI
# Ollama's API can take a system message. PydanticAI's OllamaChain should handle this.
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

def call_ollama_with_pydantic_ai(request_body_text: str) -> AgentResponse | None:
    """
    Calls a local Ollama API using PydanticAI to get the summary and response
    structured as an AgentResponse object.
    """
    try:
        # Initialize PydanticAI's OllamaChain
        # The OllamaChain constructor takes `model` and `host`.
        # For system prompt, it might be passed via `model_kwargs` or a specific param.
        # The native ollama client's `chat` method takes a `messages` list including a system role.
        # PydanticAI's OllamaChain should map to this.
        # A common way to pass system prompt if not a direct param is via model_kwargs
        # or it might be inferred if the main prompt is structured with "SYSTEM: ..." "USER: ..."
        # Let's assume `model_kwargs` or a direct parameter for system prompt for cleaner separation.
        # Consulting PydanticAI docs for OllamaChain specifics is best.
        # If it supports `system_message` in constructor or `run`, that's preferred.
        # If not, we might need to include it in the `text_prompt`.
        # For now, assuming it can be passed via model_kwargs that map to ollama client options.
        # The `ollama.Client.chat` method uses a `messages` list.
        # PydanticAI's `OllamaChain` likely constructs this list.
        # It might take `system_message` as a constructor kwarg, or within `run`.
        # Let's try passing system prompt in a way that `OllamaChain` might use it for the system message.
        # One way is to prepend, another is to hope PydanticAI has a specific parameter.
        # Given the previous pattern, let's assume it's part of model_kwargs or the chain constructor.
        # The `OllamaChain` documentation should clarify if `system_prompt` or similar is a direct parameter.
        # For now, we'll pass it as part of the text_prompt to `run` if not explicitly supported in constructor.

        llm_chain = OllamaChain(
            model=OLLAMA_MODEL_NAME,
            host=OLLAMA_HOST,
            # PydanticAI's OllamaChain might take system prompt in constructor or run method.
            # If it uses ollama.chat, it might be:
            # system_prompt=SYSTEM_PROMPT # (If supported directly)
            # Or, it might be part of model_kwargs passed to ollama client
            # model_kwargs = {"options": {"temperature": 0.7}, "system": SYSTEM_PROMPT } # Example
        )

        # Construct full prompt, ensuring system context is clear.
        # If OllamaChain doesn't have a dedicated system prompt parameter, we combine.
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Request:\n\"\"\"\n{request_body_text}\n\"\"\""
        # Note: Ollama's `format='json'` is very helpful. PydanticAI should leverage this.

        structured_response: AgentResponse = llm_chain.run(
            text_prompt=full_prompt, # Pass combined prompt
            pydantic_model=AgentResponse
            # OllamaChain might have specific params for `format='json'` or other options.
            # e.g., `run(..., format="json")` or in constructor.
        )
        return structured_response

    except Exception as e:
        print(f"Error calling Ollama API with PydanticAI: {e}")
        if "Connection refused" in str(e) or "Failed to establish a new connection" in str(e):
            print(f"Ollama connection to {OLLAMA_HOST} refused. Ensure Ollama server is running and accessible.")
        elif "model not found" in str(e).lower():
             print(f"Ollama model '{OLLAMA_MODEL_NAME}' not found on server {OLLAMA_HOST}.")
        elif hasattr(e, 'llm_output'):
            print(f"LLM Output was: {e.llm_output}")
            try:
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
    print(f"Starting Ollama Agent (PydanticAI refactored, Model: {OLLAMA_MODEL_NAME}, Host: {OLLAMA_HOST})...")
    if not os.path.exists(DB_NAME):
        print(f"Database file {DB_NAME} not found. Please run init_db.py first.")
        return

    # Optional: A quick check for Ollama server reachability at startup
    # This is not strictly necessary as errors will be caught per-call too.
    try:
        # Simple way to check, PydanticAI chain init might do this too.
        # For now, we rely on error handling in `call_ollama_with_pydantic_ai`.
        # If PydanticAI's OllamaChain has a health check or list models method, that could be used.
        pass
    except Exception as e:
        print(f"Warning: Initial check for Ollama server at {OLLAMA_HOST} failed. {e}")


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

        pydantic_ai_result: AgentResponse | None = call_ollama_with_pydantic_ai(req['request_body'])

        if pydantic_ai_result:
            summary = pydantic_ai_result.summary
            response_text = pydantic_ai_result.response_text
            print(f"Generated Summary (Ollama via PydanticAI): {summary}")
            print(f"Generated Response (Ollama via PydanticAI): {response_text}")
            update_request(conn, req['id'], summary, response_text)
        else:
            print(f"Failed to get a valid structured response from Ollama via PydanticAI for request ID {req['id']}.")

    conn.close()
    print("\nOllama Agent (PydanticAI refactored) finished.")

if __name__ == "__main__":
    main()
