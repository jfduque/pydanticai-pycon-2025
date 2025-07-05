import sqlite3
import os
import datetime
from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider
from llm_schemas import AgentResponse

# --- Configuration ---
DB_NAME = os.path.join(os.path.dirname(__file__), "requests.db")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"

# System Prompt to be injected into the user message
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
    requests = cursor.fetchall()
    return requests


def call_bedrock_with_pydantic_ai(request_body_text: str) -> AgentResponse | None:
    """
    Calls AWS Bedrock using PydanticAI by explicitly creating the message list
    to satisfy the Bedrock Converse API requirements.
    """
    try:
        provider = BedrockProvider(
            region_name=AWS_REGION,
        )

        model = BedrockConverseModel(model_name=BEDROCK_MODEL_ID, provider=provider)

        agent = Agent(
            model=model,
            output_type=AgentResponse,
            system_prompt=SYSTEM_PROMPT,
        )

        result = agent.run_sync(request_body_text)

        structured_response = result.output
        return structured_response

    except Exception as e:
        print(f"Error calling AWS Bedrock with PydanticAI: {e}")
        if "NoCredentialsError" in str(e) or "Unable to locate credentials" in str(e):
            print(
                "AWS Credentials not found or not configured correctly for Boto3 / PydanticAI."
            )
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


def main():
    """Main function to process requests."""
    print(
        f"Starting AWS Bedrock Agent (PydanticAI, Model: {BEDROCK_MODEL_ID}, Region: {AWS_REGION})..."
    )
    if not os.path.exists(DB_NAME):
        print(f"Database file {DB_NAME} not found. Please run init_db.py first.")
        return

    if not (
        os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")
    ):
        print(
            "Warning: Ensure AWS credentials are configured (e.g., `aws configure`, IAM Role)."
        )

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

        pydantic_ai_result: AgentResponse | None = call_bedrock_with_pydantic_ai(
            req["request_body"]
        )

        if pydantic_ai_result:
            summary = pydantic_ai_result.summary
            response_text = pydantic_ai_result.response_text
            print(f"Generated Summary (AWS Bedrock via PydanticAI): {summary}")
            print(f"Generated Response (AWS Bedrock via PydanticAI): {response_text}")
            update_request(conn, req["id"], summary, response_text)
        else:
            print(
                f"Failed to get a valid structured response from AWS Bedrock via PydanticAI for request ID {req['id']}."
            )

    conn.close()
    print("\nAWS Bedrock Agent (PydanticAI) finished.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript interrupted by user (Ctrl+C). Exiting...")
