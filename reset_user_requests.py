import sqlite3
import datetime
import random
import ollama
import os
import json

DB_NAME = "requests.db"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.environ.get("OLLAMA_MODEL_FOR_RESET", "gemma:latest") # Use a specific model for generation if needed

# Prompts for Ollama to generate diverse requests
# We'll try to get a mix of languages (EN, ES, PT) and types (safe, problematic)
REQUEST_GENERATION_PROMPTS = [
    # English - Safe
    {"lang": "English", "topic_type": "safe", "prompt": "Generate a short, common, safe user request in English. Output ONLY the user request text itself, nothing else. Example of desired output: 'What is the capital of France?'"},
    {"lang": "English", "topic_type": "safe", "prompt": "Create a brief, harmless user query in English asking for simple information. Your response should be JUST the query. Example of desired output: 'How tall is Mount Everest?'"},
    {"lang": "English", "topic_type": "safe", "prompt": "Formulate an innocuous user request in English for a daily task. Provide ONLY the request text. Example of desired output: 'Remind me to buy milk.'"},
    # English - Ambiguous/Complex
    {"lang": "English", "topic_type": "ambiguous", "prompt": "Generate a short user request in English that is vague or poorly defined, requiring clarification. Output ONLY the request text. Example of desired output: 'Tell me about that thing we talked about for the project.'"},

    # Spanish - Safe
    {"lang": "Spanish", "topic_type": "safe", "prompt": "Genera una solicitud de usuario corta, común y segura en español. Tu respuesta debe ser SOLO el texto de la solicitud, nada más. Ejemplo de salida deseada: '¿Cuál es la capital de Argentina?'"},
    {"lang": "Spanish", "topic_type": "safe", "prompt": "Crea una consulta de usuario breve e inofensiva en español que solicite información simple. Responde ÚNICAMENTE con la consulta. Ejemplo de salida deseada: '¿Qué altura tiene el Aconcagua?'"},
    {"lang": "Spanish", "topic_type": "safe", "prompt": "Formula una solicitud de usuario inocua en español para una tarea cotidiana. Entrega SOLAMENTE el texto de la solicitud. Ejemplo de salida deseada: 'Recuérdame llamar a mi madre.'"},
    # Spanish - Ambiguous/Complex
    {"lang": "Spanish", "topic_type": "ambiguous", "prompt": "Genera una solicitud de usuario breve en español que sea vaga o esté mal definida, necesitando clarificación. Tu respuesta debe ser SOLO el texto de la solicitud. Ejemplo de salida deseada: 'Háblame de eso que comentamos para el proyecto.'"},

    # Portuguese - Safe
    {"lang": "Portuguese", "topic_type": "safe", "prompt": "Gere uma solicitação de usuário curta, comum e segura em português. Forneça APENAS o texto da solicitação do usuário, mais nada. Exemplo de saída desejada: 'Qual é a capital do Brasil?'"},
    {"lang": "Portuguese", "topic_type": "safe", "prompt": "Crie uma consulta de usuário breve e inócua em português pedindo informações simples. Sua resposta deve ser SÓ a consulta. Exemplo de saída desejada: 'Qual a altura do Monte Roraima?'"},
    {"lang": "Portuguese", "topic_type": "safe", "prompt": "Formule um pedido de usuário inócuo em português para uma tarefa diária. Entregue SOMENTE o texto do pedido. Exemplo de saída desejada: 'Lembre-me de comprar pão.'"},
    # Portuguese - Ambiguous/Complex
    {"lang": "Portuguese", "topic_type": "ambiguous", "prompt": "Gere um pedido de usuário breve em português que seja vago ou mal definido, necessitando de clarificação. Forneça APENAS o texto do pedido. Exemplo de saída desejada: 'Fale-me sobre aquela coisa que discutimos para o projeto.'"}
]

TOTAL_REQUESTS_TO_GENERATE = 10 # Aim for this many, might be less if generation fails

def generate_request_from_ollama(client, generation_instruction):
    """Generates a single request body using Ollama based on the instruction."""
    try:
        response = client.generate(
            model=OLLAMA_MODEL_NAME,
            prompt=generation_instruction,
            stream=False, # We want the full response at once
            options={'temperature': 0.8, 'num_predict': 50} # Higher temp for variety, limit length
        )
        # The actual generated text is in response['response']
        generated_text = response.get('response', '').strip()
        # Sometimes models add quotes around the generated text, try to remove them
        if len(generated_text) > 1 and generated_text.startswith('"') and generated_text.endswith('"'):
            generated_text = generated_text[1:-1]
        if generated_text:
            return generated_text
        else:
            print(f"Warning: Ollama returned an empty response for prompt: \"{generation_instruction[:50]}...\"")
            return None
    except ollama.ResponseError as e:
        print(f"Ollama API error while generating request with prompt \"{generation_instruction[:50]}...\": {e}")
        if "model not found" in str(e).lower():
            print(f"Ensure model '{OLLAMA_MODEL_NAME}' is pulled and available on Ollama server '{OLLAMA_HOST}'.")
        return None
    except Exception as e:
        print(f"Unexpected error calling Ollama for request generation: {e}")
        return None

def reset_and_populate_requests_with_ollama():
    """Clears the requests table and populates it with 10 new requests generated by Ollama."""
    conn = None
    generated_count = 0
    try:
        print(f"Connecting to Ollama server at {OLLAMA_HOST} using model {OLLAMA_MODEL_NAME} for request generation.")
        ollama_client = ollama.Client(host=OLLAMA_HOST)
        # Test connection / model availability
        try:
            ollama_client.show(OLLAMA_MODEL_NAME)
            print(f"Successfully connected to Ollama and model '{OLLAMA_MODEL_NAME}' is available.")
        except Exception as e:
            print(f"Error: Could not verify Ollama model '{OLLAMA_MODEL_NAME}' on server '{OLLAMA_HOST}'. {e}")
            print("Please ensure Ollama is running, the model is pulled, and OLLAMA_HOST/OLLAMA_MODEL_FOR_RESET env vars are correct.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM requests")
        print("Cleared all existing requests from the 'requests' table.")

        print(f"\nAttempting to generate {TOTAL_REQUESTS_TO_GENERATE} new sample requests using Ollama:")

        # Shuffle prompts to get variety
        shuffled_prompts = random.sample(REQUEST_GENERATION_PROMPTS, len(REQUEST_GENERATION_PROMPTS))

        for gen_prompt_info in shuffled_prompts:
            if generated_count >= TOTAL_REQUESTS_TO_GENERATE:
                break # Stop if we have enough requests

            print(f"  Attempting generation for: Lang={gen_prompt_info['lang']}, Type={gen_prompt_info['topic_type']}...")
            request_body = generate_request_from_ollama(ollama_client, gen_prompt_info["prompt"])

            if request_body:
                created_at = datetime.datetime.now() - datetime.timedelta(seconds=random.randint(1, 3600))
                cursor.execute(
                    "INSERT INTO requests (request_body, summary, response, processed_at, created_at) VALUES (?, NULL, NULL, NULL, ?)",
                    (request_body, created_at)
                )
                request_id = cursor.lastrowid
                generated_count += 1
                print(f"    {generated_count}/{TOTAL_REQUESTS_TO_GENERATE}: Added ID {request_id}: \"{request_body[:70].replace('\n', ' ')}...\"")
            else:
                print(f"    Failed to generate request for this attempt. Trying next prompt if available.")

        if generated_count < TOTAL_REQUESTS_TO_GENERATE:
            print(f"\nWarning: Only generated {generated_count}/{TOTAL_REQUESTS_TO_GENERATE} requests due to potential issues with Ollama generation.")

        conn.commit()
        print(f"\nDatabase reset and populated with {generated_count} new requests generated by Ollama.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_NAME):
        print(f"Database file '{DB_NAME}' not found. Please run 'init_db.py' first to create the database and table.")
    else:
        reset_and_populate_requests_with_ollama()
