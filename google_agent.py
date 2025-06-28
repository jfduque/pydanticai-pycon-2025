import sqlite3
import os
import datetime
# import google.generativeai as genai # No longer directly needed for API call
from pydantic_ai.llms import GoogleGeminiChain # Correct PydanticAI chain for Google Gemini
from pydantic_ai.utils import extract_json
from llm_schemas import AgentResponse

# --- Configuration ---
DB_NAME = "requests.db"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL_NAME = "gemini-1.5-flash" # Or other compatible Gemini model

# Updated System Prompt for PydanticAI
# Google's Gemini API handles system instructions well. PydanticAI's GoogleGeminiChain
# should ideally pass this through or have a mechanism for it.
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

def call_google_with_pydantic_ai(request_body_text: str) -> AgentResponse | None:
    """
    Calls the Google Gemini API using PydanticAI to get the summary and response
    structured as an AgentResponse object.
    """
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        return None

    try:
        # Initialize PydanticAI's GoogleGeminiChain
        # The API key is typically picked up from GOOGLE_API_KEY env var
        llm_chain = GoogleGeminiChain(
            model=MODEL_NAME,
            # api_key=GOOGLE_API_KEY, # Usually not needed if GOOGLE_API_KEY env var is set
            # For Gemini, system_instruction is important.
            # We need to see how PydanticAI's GoogleGeminiChain handles this.
            # It might take it as a constructor argument, or within `run` method options.
            # Assuming it might be part of `model_kwargs` or a specific parameter.
            # If not directly supported, prepending to the user prompt is a fallback.
            # Let's assume it might be passed via model_kwargs if available, or prepended.
            # The native genai.GenerativeModel takes `system_instruction`.
            # PydanticAI might expose this via `model_kwargs={"system_instruction": SYSTEM_PROMPT}`
            # or a dedicated parameter. If not, combining with `text_prompt` is an alternative.
            model_kwargs={"system_instruction": SYSTEM_PROMPT} # Tentative: check PydanticAI docs
        )

        # With Gemini, the system prompt is typically handled by `system_instruction`.
        # The `text_prompt` for `run` should then just be the user's request.
        structured_response: AgentResponse = llm_chain.run(
            text_prompt=request_body_text, # User request body
            pydantic_model=AgentResponse
        )
        return structured_response

    except Exception as e:
        print(f"Error calling Google Gemini API with PydanticAI: {e}")
        if hasattr(e, 'llm_output'): # PydanticAI often stores the raw output here on error
            print(f"LLM Output was: {e.llm_output}")
            try:
                raw_json = extract_json(e.llm_output) # pydantic_ai.utils
                if raw_json:
                    return AgentResponse(**raw_json)
            except Exception as extract_e:
                print(f"Could not manually extract JSON from LLM output: {extract_e}")
        # Check for specific Google API feedback if available in the exception
        # (This might be more complex if PydanticAI wraps the original exception heavily)
        # Example: if "Prompt feedback:" in str(e): print(str(e))
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
    print("Starting Google Gemini Agent (PydanticAI refactored)...")
    if not os.path.exists(DB_NAME):
        print(f"Database file {DB_NAME} not found. Please run init_db.py first.")
        return

    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY environment variable is not set. Please set it before running the agent.")
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

        pydantic_ai_result: AgentResponse | None = call_google_with_pydantic_ai(req['request_body'])

        if pydantic_ai_result:
            summary = pydantic_ai_result.summary
            response_text = pydantic_ai_result.response_text
            print(f"Generated Summary (Google Gemini via PydanticAI): {summary}")
            print(f"Generated Response (Google Gemini via PydanticAI): {response_text}")
            update_request(conn, req['id'], summary, response_text)
        else:
            print(f"Failed to get a valid structured response from Google Gemini via PydanticAI for request ID {req['id']}.")

    conn.close()
    print("\nGoogle Gemini Agent (PydanticAI refactored) finished.")

if __name__ == "__main__":
    main()
