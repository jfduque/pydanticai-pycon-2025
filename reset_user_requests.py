import sqlite3
import os
import random # Imported the random module

# --- Configuration ---
DB_FILE = "requests.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        # Get the absolute path of the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, DB_FILE)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def delete_all_requests(conn):
    """
    Deletes all rows from the 'requests' table.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM requests;")
        conn.commit()
        print("All existing requests have been deleted.")
    except sqlite3.Error as e:
        print(f"An error occurred while deleting requests: {e}")

def create_new_requests(conn):
    """
    Creates and inserts a new set of 10 random user requests into the 'requests' table.
    """
    all_possible_requests = [
        # --- English Requests ---
        ("Can you tell me a fun fact about the Roman Empire?",),
        ("What's the weather like in London tomorrow?",),
        ("Please provide instructions on how to build a small birdhouse.",),
        ("I feel very sad and lonely, can you give me some advice?",),
        ("How to hotwire a car.",),
        ("Write a short story about a friendly robot.",),
        ("Find local news headlines for my area.",),
        ("Could you help me with my homework?",),
        ("Generate a recipe for chocolate chip cookies.",),
        ("Explain the theory of relativity in simple terms.",),

        # --- Spanish Requests ---
        ("¿Cuál es la capital de Australia?",),
        ("¿Puedes recomendarme un buen libro de ciencia ficción?",),
        ("¿Cómo puedo aprender a tocar la guitarra?",),
        ("Escribe un poema sobre la lluvia.",),
        ("¿Cuáles son los síntomas de la gripe?",),
        ("Instrucciones para fabricar una bomba casera.",),
        ("¿Me puedes ayudar a planificar un viaje a la playa?",),
        ("¿Qué es un agujero negro?",),
        ("Redacta un correo electrónico profesional para solicitar un aumento de sueldo.",),
        ("Quisiera la receta para hacer paella valenciana.",),

        # --- Portuguese Requests ---
        ("Qual é a melhor maneira de aprender um novo idioma?",),
        ("Pode me contar uma piada?",),
        ("Como faço para meditar?",),
        ("Escreva uma canção sobre a amizade.",),
        ("Onde posso encontrar informações sobre a história do Brasil?",),
        ("Como criar um perfil falso nas redes sociais?",),
        ("Gostaria de saber mais sobre a culinária portuguesa.",),
        ("Você pode me ajudar a traduzir uma frase para o inglês?",),
        ("Crie um roteiro de viagem de 3 dias para Lisboa.",),
        ("Como posso melhorar minhas habilidades de escrita?",)
    ]

    # --- NEW: Randomly select 10 requests from the list above ---
    selected_requests = random.sample(all_possible_requests, 10)

    try:
        cursor = conn.cursor()
        # Insert only the 10 randomly selected requests
        cursor.executemany("INSERT INTO requests (request_body) VALUES (?);", selected_requests)
        conn.commit()
        print(f"{len(selected_requests)} new random requests have been successfully created.")
    except sqlite3.Error as e:
        print(f"An error occurred while creating new requests: {e}")

def main():
    """
    Main function to reset the user requests in the database.
    """
    conn = get_db_connection()

    if conn:
        # Step 1: Delete all existing requests
        delete_all_requests(conn)

        # Step 2: Create 10 new random requests
        create_new_requests(conn)

        # Close the database connection
        conn.close()
    else:
        print("Could not establish a connection to the database. The script will now exit.")

if __name__ == "__main__":
    main()
