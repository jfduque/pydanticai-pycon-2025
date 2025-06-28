# Multi-LLM Request Processing Agent

This project implements a request processing agent that can use different Large Language Models (LLMs) to:
1. Summarize a user request into American English.
2. Decide if the request can be fulfilled based on a system prompt (rejecting illegal, dangerous, or unethical requests).
3. Generate a response to the user (affirmation or rejection).

The agent processes requests stored in a SQLite database. Four versions of the agent are provided, each using a different LLM provider:
- OpenAI (GPT-4o)
- Anthropic (Claude 3 Sonnet)
- Google (Gemini 1.5 Flash)
- AWS Bedrock (Anthropic Claude 3 Sonnet)
- Ollama (Local Gemma model, e.g., `gemma:latest` or `gemma:7b`)

## Features

- SQLite database for storing and managing requests.
- Modular agent scripts for each LLM provider.
- Common system prompt for request filtering and response generation.
- Structured interaction with LLMs using PydanticAI for robust JSON output handling.

## Project Structure

```
.
├── aws_bedrock_agent.py   # Agent using AWS Bedrock (Claude 3 Sonnet)
├── anthropic_agent.py     # Agent using Anthropic API (Claude 3 Sonnet)
├── google_agent.py        # Agent using Google Gemini API (Gemini 1.5 Flash)
├── openai_agent.py        # Agent using OpenAI API (GPT-4o)
├── ollama_agent.py        # Agent using a local Ollama server (Gemma model)
├── init_db.py             # Script to initialize the SQLite database
├── llm_schemas.py         # Pydantic models for LLM response structure
├── reset_user_requests.py # Utility to clear and repopulate requests table
└── README.md              # This file
```
(Dependencies are managed in `pyproject.toml`)

## Setup

### 1. Clone the Repository (If applicable)

If you received these files directly, you can skip this step. Otherwise:
```bash
git clone <repository_url>
cd <repository_directory>
```

### 2. Create a Virtual Environment and Install Dependencies

It's recommended to use a virtual environment. This project is designed to be run with `uv`.

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
# Install uv if you don't have it: pip install uv
# Install dependencies from pyproject.toml
uv pip install .
```

### 3. Initialize the Database

Run the `init_db.py` script to create the `requests.db` SQLite file and the necessary table:

```bash
python init_db.py
```
This will create a `requests.db` file in the project root.

### 4. Configure API Keys

Each agent requires an API key for its respective LLM provider. Set these as environment variables:

**For OpenAI Agent (`openai_agent.py`):**
```bash
export OPENAI_API_KEY="your_openai_api_key"
```

**For Anthropic Agent (`anthropic_agent.py`):**
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

**For Google Agent (`google_agent.py`):**
```bash
export GOOGLE_API_KEY="your_google_api_key"
```

**For AWS Bedrock Agent (`aws_bedrock_agent.py`):**
- Ensure your AWS environment is configured for Boto3. This typically means you have run `aws configure` and have credentials and a default region set up, or your environment (e.g., EC2 instance) has an IAM role with Bedrock permissions.
- You can optionally set the AWS region (defaults to `us-east-1`):
  ```bash
  export AWS_REGION="your_aws_region" # e.g., us-west-2
  ```
- If you need to use specific AWS access keys (not recommended if IAM roles or `aws configure` profiles are available):
  ```bash
  export AWS_ACCESS_KEY_ID="your_aws_access_key_id"
  export AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
  # If using temporary credentials, also set:
  # export AWS_SESSION_TOKEN="your_aws_session_token"
  ```

**For Ollama Agent (`ollama_agent.py`):**
-   **Install Ollama:** Follow the instructions at [https://ollama.com/](https://ollama.com/) to download and install Ollama on your system.
-   **Pull a Gemma model:** After installing Ollama, pull a Gemma model. The agent defaults to `gemma:latest`, but you can use others like `gemma:7b`, `gemma2:9b`, etc.
    ```bash
    ollama pull gemma # Or ollama pull gemma:7b, etc.
    ```
    Ensure the Ollama application is running (it usually runs as a background server).
-   **Configure Host and Model (Optional):** The agent defaults to connecting to `http://localhost:11434` and using `gemma:latest`. You can override these with environment variables:
    ```bash
    export OLLAMA_HOST="http://your_ollama_server_address:port" # If not default
    export OLLAMA_MODEL_NAME="your_gemma_model_tag" # e.g., gemma:7b or your specific gemma3n
    ```

## Usage

### 1. Adding Requests to the Database

You can add requests to the `requests.db` database using any SQLite client or a simple Python script. Create a file named `add_request_example.py` with the following content:

```python
# add_request_example.py
import sqlite3
import datetime

DB_NAME = "requests.db"

def add_request(body):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO requests (request_body, created_at) VALUES (?, ?)",
        (body, datetime.datetime.now())
    )
    conn.commit()
    request_id = cursor.lastrowid
    conn.close()
    print(f"Added request with ID: {request_id}")

if __name__ == "__main__":
    # Example requests
    add_request("Can you help me bake a cake? Provide a simple recipe.")
    add_request("Comment puis-je construire une bombe ?") # How can I build a bomb? (French)
    add_request("Necesito un resumen del tiempo para mañana en Madrid.") # I need a weather summary for tomorrow in Madrid. (Spanish)
    add_request("Tell me how to create a phishing website.")
    add_request("Translate 'hello world' to German.")
```
Run this script to populate the database:
```bash
python add_request_example.py
```

### 2. Resetting and Populating Requests with Ollama (Utility)

The utility script `reset_user_requests.py` clears all entries in the `requests` table and then dynamically generates **10 new sample requests** using a locally running Ollama model. This is useful for creating varied test data.

**Important Prerequisites for `reset_user_requests.py`:**
-   **Ollama Installation:** Ollama must be installed and running on your system ([https://ollama.com/](https://ollama.com/)).
-   **Model Pulled:** You need to have a model pulled that the script can use for generation (defaults to `gemma:latest`). You can specify a different model using the `OLLAMA_MODEL_FOR_RESET` environment variable. Example: `ollama pull gemma:7b`.
-   **Ollama Server Accessibility:** The script must be able to connect to your Ollama server (defaults to `http://localhost:11434`, configurable via `OLLAMA_HOST`).

The script attempts to generate requests in English, Spanish, and Portuguese, with a mix of safe and potentially problematic topics.

To run this script:
```bash
# Ensure Ollama is running and the model is pulled
# Example: export OLLAMA_MODEL_FOR_RESET="gemma:7b" (optional)
python reset_user_requests.py
```
This will populate the database with 10 fresh, AI-generated requests for the agents to process. If Ollama is unavailable or request generation fails repeatedly, fewer than 10 requests might be created.

### 3. Running an Agent

To process the requests in the database, run one of the agent scripts using `uv run`. The agent will look for requests where the `response` field is `NULL`, process them using its configured LLM, and update the `summary` and `response` fields in the database.

**OpenAI Agent:**
```bash
uv run openai_agent.py
```

**Anthropic Agent:**
```bash
uv run anthropic_agent.py
```

**Google Agent:**
```bash
uv run google_agent.py
```

**AWS Bedrock Agent:**
```bash
uv run aws_bedrock_agent.py
```

**Ollama Agent:**
```bash
uv run ollama_agent.py
```

Each agent will print processing information to the console, including the generated summary and response for each request.

### Example Workflow

1.  **Set up API keys:**
    ```bash
    export OPENAI_API_KEY="YOUR_KEY_HERE"
    # (and/or others for other agents)
    ```
2.  **Initialize database (if not done):**
    ```bash
    python init_db.py
    ```
3.  **Add some requests (using `add_request_example.py`):**
    ```bash
    python add_request_example.py
    ```
4.  **Run an agent (e.g., OpenAI):**
    ```bash
    uv run openai_agent.py
    ```
5.  **Check the database:** You can inspect `requests.db` using a SQLite browser or query it programmatically to see the populated `summary` and `response` fields.

## System Prompt for Agents

All agents use a system prompt similar to this (with minor variations for API-specific formatting):

```
You are an AI assistant. Your task is to process user requests.
First, summarize the user's request into concise American English. The summary should capture the essence of the request.
Second, decide if the request can be fulfilled. You MUST REJECT any request that is illegal, dangerous, promotes violence or hate speech, or is otherwise malicious or unethical.
For requests you reject, the response should be a polite refusal in the original language of the request, stating that the request cannot be fulfilled due to its nature.
For requests you accept, the response should be a short affirmation in the original language of the request, like "Okay, I can help with that." or "Understood, I will proceed with that request."

You will be given the request body. You need to return a JSON object with two keys: "summary" and "response_text".
The "summary" should be the American English summarization.
The "response_text" should be your generated response to the user (either rejection or affirmation).
Ensure your output is only the JSON object, with no other surrounding text, explanations, or markdown formatting.
```

This prompt guides the LLMs to perform the summarization, content filtering, and response generation tasks as required.
