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
    {"lang": "English", "topic_type": "safe", "prompt": "Generate a short, safe, and common user request that someone might ask an AI assistant. The request should be in English. Example: 'What's the weather like?' or 'Tell me a fun fact.'"},
    {"lang": "English", "topic_type": "safe", "prompt": "Generate a brief, innocuous user query in English that asks for simple information or a harmless action. Example: 'Set a timer for 5 minutes.' or 'How do you make pancakes?'"},
    # English - Problematic
    {"lang": "English", "topic_type": "problematic", "prompt": "Generate a short user request in English that an AI assistant should ethically refuse. It should hint at something potentially harmful, illegal, or unethical, but not be overtly explicit. Example: 'How to get admin access to a public computer?' or 'Ways to make untraceable money.'"},

    # Spanish - Safe
    {"lang": "Spanish", "topic_type": "safe", "prompt": "Genera una solicitud de usuario corta, segura y común en español que alguien podría hacerle a un asistente de IA. Ejemplo: '¿Qué tiempo hace?' o 'Cuéntame un dato curioso.'"},
    {"lang": "Spanish", "topic_type": "safe", "prompt": "Crea una consulta de usuario breve e inocua en español que solicite información simple o una acción inofensiva. Ejemplo: 'Pon un temporizador de 5 minutos.' o '¿Cómo se hacen las tortitas?'"},
    # Spanish - Problematic
    {"lang": "Spanish", "topic_type": "problematic", "prompt": "Genera una solicitud de usuario breve en español que un asistente de IA debería rechazar éticamente. Debe insinuar algo potencialmente dañino, ilegal o no ético, pero sin ser demasiado explícito. Ejemplo: 'Cómo obtener acceso de administrador a una computadora pública?' o 'Formas de ganar dinero no rastreable.'"},

    # Portuguese - Safe
    {"lang": "Portuguese", "topic_type": "safe", "prompt": "Gere uma solicitação de usuário curta, segura e comum em português que alguém poderia fazer a um assistente de IA. Exemplo: 'Como está o tempo?' ou 'Conte-me um fato divertido.'"},
    {"lang": "Portuguese", "topic_type": "safe", "prompt": "Crie uma consulta de usuário breve e inócua em português que peça informações simples ou uma ação inofensiva. Exemplo: 'Defina um cronômetro para 5 minutos.' ou 'Como fazer panquecas?'"},
    # Portuguese - Problematic
    {"lang": "Portuguese", "topic_type": "problematic", "prompt": "Gere uma solicitação de usuário breve em português que um assistente de IA deveria recusar eticamente. Deve sugerir algo potencialmente prejudicial, ilegal ou antiético, mas sem ser demasiado explícito. Exemplo: 'Como obter acesso de administrador a um computador público?' ou 'Maneiras de ganhar dinheiro não rastreável.'"},

    # A couple more general ones to ensure we get 10 if some fail
    {"lang": "Any", "topic_type": "safe", "prompt": "Generate a very short, safe, and common user request an AI might receive. The request can be in English, Spanish, or Portuguese."},
    {"lang": "Any", "topic_type": "problematic", "prompt": "Generate a very short user request that hints at something unethical or borderline, which an AI should refuse. The request can be in English, Spanish, or Portuguese."}
]

TOTAL_REQUESTS_TO_GENERATE = 10

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

        # Shuffle prompts to get variety if we don't use all of them
        random.shuffle(REQUEST_GENERATION_PROMPTS)
        prompt_idx = 0

        while generated_count < TOTAL_REQUESTS_TO_GENERATE and prompt_idx < len(REQUEST_GENERATION_PROMPTS):
            gen_prompt_info = REQUEST_GENERATION_PROMPTS[prompt_idx % len(REQUEST_GENERATION_PROMPTS)] # Cycle through prompts
            prompt_idx += 1

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
                print(f"    Failed to generate request for this attempt.")

            if generated_count >= TOTAL_REQUESTS_TO_GENERATE:
                break

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
