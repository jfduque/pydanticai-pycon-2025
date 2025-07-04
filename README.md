# pydanticai-pycon-2025

## Setup (Required for All Demonstrations)

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

### 3. Configure API Keys (All Demonstrations)

Each demonstration requires API keys for the LLM providers. Set these as environment variables:

**For OpenAI Agent:**
```bash
export OPENAI_API_KEY="your_openai_api_key"
```

**For Anthropic Agent:**
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

**For Google Agent:**
```bash
export GOOGLE_API_KEY="your_google_api_key"
```

**For AWS Bedrock Agent:**
```bash
export AWS_ACCESS_KEY_ID="your_aws_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
```

**For Ollama Agent:**
-   **Install Ollama:** Follow the instructions at [https://ollama.com/](https://ollama.com/) to download and install Ollama on your system.
-   **Pull Llama 3.1 model:**
    ```bash
    ollama pull llama3.1:latest
    ```
    Ensure the Ollama application is running (it usually runs as a background server).

---

## Demonstrations

### 1. user_requests

This demonstration processes user requests stored in a database using various LLM agents.

#### Usage

1. **Initialize the Database:**
    - Run the following script to create an empty database:
    ```bash
    uv run user_requests/init_db.py
    ```

2. **Populate with Sample Requests:**
    - Use the utility script to populate the `requests` table with sample entries:
    ```bash
    uv run user_requests/reset_user_requests.py
    ```

3. **Process Requests with an Agent:**
    - Run one of the agent scripts to process the requests in the database. The agent will look for unprocessed requests, and then it will process them using its configured LLM, and update the `summary` and `response` fields in the database.

    **OpenAI Agent:**
    ```bash
    uv run user_requests/openai_agent.py
    ```
    **Anthropic Agent:**
    ```bash
    uv run user_requests/anthropic_agent.py
    ```
    **Google Agent:**
    ```bash
    uv run user_requests/google_agent.py
    ```
    **AWS Bedrock Agent:**
    ```bash
    uv run user_requests/aws_bedrock_agent.py
    ```
    **Ollama Agent:**
    ```bash
    uv run user_requests/ollama_agent.py
    ```

    Each agent will print processing information to the console, including the generated summary and response for each request.

4. **View Current Requests:**
    - To view the current requests and their status, run:
    ```bash
    uv run user_requests/show_requests.py
    ```

---

### 2. complaint_data_extraction

This demonstration extracts structured data from complaint texts using LLM agents.

#### Usage

- Run the appropriate agent script for your LLM provider to process complaint data and extract structured information.

    **Formal complaint example:**
    ```bash
    uv run complaint_data_extraction/extract_data_complaint.py complaint_data_extraction/demo_complaint.txt
    ```
    **Call transcript complaint example:**
    ```bash
    uv run complaint_data_extraction/extract_data_complaint.py --mode transcript complaint_data_extraction/complaint_patricia_telmex.txt
    ```

- The script will process complaint entries and output the extracted data.

---

### 3. multi_agent

This demonstration showcases coordination between multiple agents to solve a task.

#### Usage

1. **Prepare the Credit Applications Database:**
    - Create and populate the database with mock credit applications:
    ```bash
    uv run multi_agent/database_setup.py
    ```

2. **View Current Applications:**
    - To view the current credit applications:
    ```bash
    uv run multi_agent/show_applications.py
    ```

3. **Process Credit Applications:**

    **Process a random credit application:**
    ```bash
    uv run multi_agent/process_applications.py
    ```
    **Process given credit application:**
    ```bash
    uv run multi_agent/process_applications.py --app-id 4
    ```

- The script will coordinate multiple LLM agents to process the task and display the results.

---
