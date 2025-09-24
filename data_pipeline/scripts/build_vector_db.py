import chromadb
from sentence_transformers import SentenceTransformer
import json
import os
import glob

# --- Configuration ---
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'app_data', 'structured_questions', 'CAT')
VECTOR_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'app_data', 'vector_db', 'CAT')
MODEL_NAME = 'all-MiniLM-L6-v2' # A good starting model

def _construct_document_from_question(question_data):
    """
    Constructs a single string from a question object for embedding,
    handling the 'option1', 'option2', etc., format.
    """
    # Start with the core question text and section
    text_parts = [
        f"Section: {question_data.get('section', '')}",
        f"Question: {question_data.get('question_text', '')}"
    ]

    # Append options if they exist
    for i in range(1, 5):
        option_key = f"option{i}"
        if option_key in question_data:
            text_parts.append(f"Option {i}: {question_data[option_key]}")

    return " ".join(text_parts)

def build_vector_database():
    """
    Reads structured JSON data, creates text embeddings, and stores them in
    separate ChromaDB collections for each section.
    """
    print(f"Loading sentence transformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    print(f"Initializing persistent vector database at: {VECTOR_DB_PATH}")
    # This creates a client that saves all DB data to the specified folder
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    
    if not json_files:
        print(f"No JSON files found in {DATA_DIR}. Run the PDF parser first.")
        return

    for json_file in json_files:
        section_name = os.path.basename(json_file).replace('CAT_', '').replace('.json', '').lower()
        collection_name = f"cat_{section_name}"

        print(f"\n--- Processing section: {section_name.upper()} ---")

        # Get or create a dedicated collection for the section
        collection = client.get_or_create_collection(name=collection_name)
        
        with open(json_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        if not questions:
            print(f"No questions found in {os.path.basename(json_file)}. Skipping.")
            continue

        print(f"Preparing {len(questions)} documents for embedding...")
        documents = [_construct_document_from_question(q) for q in questions]
        metadatas = [{"year": q['year'], "slot": q['slot']} for q in questions]
        ids = [q['id'] for q in questions]

        print(f"Generating embeddings for {len(documents)} documents... (This may take a moment)")
        embeddings = model.encode(documents, show_progress_bar=True)
        
        print(f"Upserting {len(ids)} documents into the '{collection_name}' collection...")
        # Use upsert to add new documents or update existing ones based on ID
        collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            documents=documents
        )
        
        count = collection.count()
        print(f"Collection '{collection_name}' now contains {count} items.")

    print("\nVector database build complete.")
    print(f"Database files are stored in: {os.path.abspath(VECTOR_DB_PATH)}")


if __name__ == "__main__":
    build_vector_database()

