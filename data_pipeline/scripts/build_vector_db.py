import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import json
import os
import glob
import numpy as np

# --- Configuration ---
# Database connection details (consider using environment variables for production)
DB_NAME = os.environ.get("DB_NAME", "mock_test_db")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "password")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

# --- Project Paths and Model Config ---
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'app_data', 'structured_questions')
MODEL_NAME = 'all-MiniLM-L6-v2' # A good starting model
TABLE_NAME = "questions"

def build_vector_database():
    """
    Reads structured JSON data, creates text embeddings, and stores them in a PostgreSQL database with pgvector.
    """
    print(f"Loading sentence transformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    embedding_dim = model.get_sentence_embedding_dimension()
    
    conn = None
    try:
        print("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        with conn.cursor() as cur:
            # --- Setup Database ---
            print("Setting up database extensions and tables...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            register_vector(conn) # Register the vector type with psycopg2
            
            # Create the table to store questions and embeddings
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id VARCHAR(255) PRIMARY KEY,
                    document TEXT,
                    metadata JSONB,
                    embedding VECTOR({embedding_dim})
                );
            """)
            
            # Clear the table for a fresh build
            print(f"Clearing existing data from table '{TABLE_NAME}'...")
            cur.execute(f"TRUNCATE TABLE {TABLE_NAME};")

        # --- Read and Process JSON data ---
        json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
        if not json_files:
            print(f"No JSON files found in {DATA_DIR}. Run the PDF parser first.")
            return

        all_documents = []
        all_metadatas = []
        all_ids = []
        print("Reading and processing JSON files...")
        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                questions = json.load(f)
                for q in questions:
                    text_to_embed = f"Section: {q['section']}. Question: {q['question_text']}"
                    if q.get('passage_context'):
                        text_to_embed = f"Passage: {q['passage_context']}. " + text_to_embed

                    all_documents.append(text_to_embed)
                    all_metadatas.append({
                        "year": q['year'],
                        "section": q['section'],
                        "source_id": q['id']
                    })
                    all_ids.append(q['id'])
        
        if not all_documents:
            print("No documents to process. Exiting.")
            return

        # --- Generate Embeddings ---
        print(f"Generating embeddings for {len(all_documents)} questions... (This may take a moment)")
        embeddings = model.encode(all_documents, show_progress_bar=True)

        # --- Insert Data into PostgreSQL ---
        print("Inserting data into the database...")
        with conn.cursor() as cur:
            # Use execute_values for efficient batch insertion
            data_to_insert = [
                (all_ids[i], all_documents[i], json.dumps(all_metadatas[i]), np.array(embeddings[i]))
                for i in range(len(all_ids))
            ]
            psycopg2.extras.execute_values(
                cur,
                f"INSERT INTO {TABLE_NAME} (id, document, metadata, embedding) VALUES %s",
                data_to_insert
            )
        
        # --- Create an Index for Fast Searching ---
        print("Creating an IVFFlat index for efficient similarity search...")
        with conn.cursor() as cur:
            num_rows = len(all_ids)
            # The number of lists is a tuning parameter, sqrt(num_rows) is a common suggestion
            num_lists = int(np.sqrt(num_rows))
            cur.execute(f"CREATE INDEX ON {TABLE_NAME} USING ivfflat (embedding vector_l2_ops) WITH (lists = {num_lists});")

        conn.commit()
        
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
            count = cur.fetchone()[0]
            print(f"\nVector database build complete. Table '{TABLE_NAME}' now contains {count} items.")
            
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    build_vector_database()

