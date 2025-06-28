import sqlite3
import os
import datetime
# import boto3 # No longer directly needed for API call if PydanticAI handles client
# import json
from pydantic_ai.llms import BedrockClaudeChain # Correct PydanticAI chain for Bedrock (Claude)
from pydantic_ai.utils import extract_json
from llm_schemas import AgentResponse

# --- Configuration ---
DB_NAME = "requests.db"
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
# PydanticAI's BedrockClaudeChain should pick up AWS credentials from the environment (IAM role, aws configure, env vars)

# Bedrock model ID for Claude 3 Sonnet
BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0" # Used by BedrockClaudeChain

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

def call_bedrock_with_pydantic_ai(request_body_text: str) -> AgentResponse | None:
    """
    Calls AWS Bedrock (Claude) using PydanticAI to get the summary and response
    structured as an AgentResponse object.
    """
    try:
        # Initialize PydanticAI's BedrockClaudeChain
        # It should use the Boto3 session configured in the environment.
        # AWS Region and credentials should be picked up automatically by boto3.
        llm_chain = BedrockClaudeChain(
            model=BEDROCK_MODEL_ID, # Pass the specific Bedrock model ID
            aws_region=AWS_REGION, # Explicitly pass region if needed, though often picked up
            # For Bedrock Claude, the system prompt is passed via `model_kwargs`
            # or a specific parameter if the chain supports it, similar to Anthropic's direct API.
            # The native Bedrock invoke_model for Claude takes 'system' in the payload.
            # PydanticAI's BedrockClaudeChain should map to this.
            # Assuming `model_kwargs` can be used to pass provider-specific parameters.
            # The structure for Bedrock Claude's `system` parameter is typically just a string.
            model_kwargs={"system": SYSTEM_PROMPT} # Tentative, verify with PydanticAI docs for BedrockClaude
        )

        # With Bedrock Claude, the system prompt is handled by the 'system' parameter.
        # The `text_prompt` for `run` should then just be the user's request.
        structured_response: AgentResponse = llm_chain.run(
            text_prompt=request_body_text, # User request body
            pydantic_model=AgentResponse
        )
        return structured_response

    except Exception as e:
        print(f"Error calling AWS Bedrock with PydanticAI: {e}")
        if "NoCredentialsError" in str(e) or "Unable to locate credentials" in str(e):
            print("AWS Credentials not found or not configured correctly for Boto3 / PydanticAI.")
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
    print(f"Starting AWS Bedrock Agent (PydanticAI refactored, Model: {BEDROCK_MODEL_ID}, Region: {AWS_REGION})...")
    if not os.path.exists(DB_NAME):
        print(f"Database file {DB_NAME} not found. Please run init_db.py first.")
        return

    # Basic check for AWS config hint, actual errors caught by boto3/PydanticAI
    if not (os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")) and \
       not os.environ.get("AWS_PROFILE") and not os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"):
        print("Warning: Specific AWS Key/Profile environment variables not detected. Ensure AWS credentials are configured (e.g., `aws configure`, IAM Role).")

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

        pydantic_ai_result: AgentResponse | None = call_bedrock_with_pydantic_ai(req['request_body'])

        if pydantic_ai_result:
            summary = pydantic_ai_result.summary
            response_text = pydantic_ai_result.response_text
            print(f"Generated Summary (AWS Bedrock via PydanticAI): {summary}")
            print(f"Generated Response (AWS Bedrock via PydanticAI): {response_text}")
            update_request(conn, req['id'], summary, response_text)
        else:
            print(f"Failed to get a valid structured response from AWS Bedrock via PydanticAI for request ID {req['id']}.")

    conn.close()
    print("\nAWS Bedrock Agent (PydanticAI refactored) finished.")

if __name__ == "__main__":
    main()
