import os
import sqlite3
import datetime
from pydantic_ai import Agent
from llm_schemas import AgentResponse

# --- Configuration ---
DB_NAME = "requests.db"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY environment variable is not set.")

MODEL_NAME = "gemini-2.5-flash"
SYSTEM_PROMPT = """You are an AI assistant. Your task is to process user requests based on the provided text.
1.  First, summarize the user's request into concise American English. This summary should capture the core essence of what the user is asking for.
2.  Second, decide if the request can be fulfilled. You MUST REJECT any request that is illegal, dangerous, promotes violence or hate speech, or is otherwise malicious or unethical.
    -   For requests you reject, the response text should be a polite refusal in the original language of the request, briefly stating that the request cannot be fulfilled due to its nature.
    -   For requests you accept, the response text should be a short affirmation in the original language of the request, like "Okay, I can help with that." or "Understood, I will proceed with that request."
You need to provide a summary and a response_text.
"""

# Initialize the PydanticAI Agent
agent = Agent(
    f"google-gla:{MODEL_NAME}",
    system_prompt=SYSTEM_PROMPT,
    output_type=AgentResponse,
)


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


def update_request(conn, request_id, summary, response_text):
    cursor = conn.cursor()
    processed_at = datetime.datetime.now().isoformat()
    cursor.execute(
        "UPDATE requests SET summary = ?, response = ?, processed_at = ? WHERE id = ?",
        (summary, response_text, processed_at, request_id),
    )
    conn.commit()


def main():
    if not os.path.exists(DB_NAME):
        print(
            f"Database file {DB_NAME} not found. Please initialize the database first."
        )
        return

    conn = get_db_connection()
    requests = get_unprocessed_requests(conn)
    if not requests:
        print("No new requests to process.")
        return

    print(f"Processing {len(requests)} requests using Google model {MODEL_NAME} ...")
    for req in requests:
        request_id = req["id"]
        body = req["request_body"]
        try:
            result = agent.run_sync(body)
            summary = result.output.summary
            response_text = result.output.response_text
            update_request(conn, request_id, summary, response_text)
            print(f"Request {request_id} processed.")
        except Exception as e:
            print(f"Error processing request {request_id}: {e}")

    conn.close()


if __name__ == "__main__":
    main()
