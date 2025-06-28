# pydanticai-pycon-2025

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
# Install dependencies from pyproject.toml
uv sync
```

### 3. Initialize the Database

Run the `init_db.py` script to create the `requests.db` SQLite file and the necessary table:

```bash
uv run init_db.py
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
  ```bash
  export AWS_ACCESS_KEY_ID="your_aws_access_key_id"
  export AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
  # If using temporary credentials, also set:
  # export AWS_SESSION_TOKEN="your_aws_session_token"
  ```

**For Ollama Agent (`ollama_agent.py`):**
-   **Install Ollama:** Follow the instructions at [https://ollama.com/](https://ollama.com/) to download and install Ollama on your system.
-   **Pull Gemma3n model:** 
    ```bash
    ollama pull gemma3n:e2b
    ```
    Ensure the Ollama application is running (it usually runs as a background server).

## Usage

### 1. Resetting and Populating Requests with Ollama (Utility)

The utility script `reset_user_requests.py` clears all entries in the `requests` table.

### 2. Running an Agent

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
