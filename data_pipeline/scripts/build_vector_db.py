import chromadb
from sentence_transformers import SentenceTransformer
import json
import os
import glob

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2' # A good starting model

def get_paths(exam_type):
    """Get data and vector DB paths for a specific exam type"""
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    data_dir = os.path.join(base_path, 'app_data', 'structured_questions', exam_type.upper())
    vector_db_path = os.path.join(base_path, 'app_data', 'vector_db', exam_type.upper())
    return data_dir, vector_db_path

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

def build_vector_database_for_exam(exam_type):
    """
    Reads structured JSON data, creates text embeddings, and stores them in
    separate ChromaDB collections for each section of a specific exam type.
    """
    print(f"\n=== Building Vector Database for {exam_type} ===")
    data_dir, vector_db_path = get_paths(exam_type)
    
    print(f"Loading sentence transformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    print(f"Initializing persistent vector database at: {vector_db_path}")
    os.makedirs(vector_db_path, exist_ok=True)
    client = chromadb.PersistentClient(path=vector_db_path)
    
    json_files = glob.glob(os.path.join(data_dir, "*.json"))
    
    if not json_files:
        print(f"No JSON files found in {data_dir}. Run the PDF parser first for {exam_type}.")
        return

    for json_file in json_files:
        filename = os.path.basename(json_file)
        
        # Extract collection name from filename
        if exam_type == "CAT":
            # e.g., "CAT_VARC_all_years_combined.json" -> "cat_varc_all_years_combined"
            section_name = filename.replace('CAT_', '').replace('.json', '').lower()
            collection_name = f"cat_{section_name}"
        else:  # GATE
            # Handle both general files (GATE_GA_...) and stream-specific files (GATE_CS_TECH_...)
            parts = filename.replace('GATE_', '').replace('.json', '').split('_')
            if len(parts) >= 3 and parts[1] in ['GA', 'TECH']:
                # Stream-specific file: GATE_CS_TECH_all_years_combined.json
                stream, section = parts[0], parts[1]
                collection_name = f"gate_{stream.lower()}_{section.lower()}_all_years_combined"
            else:
                # General file: GATE_GA_all_years_combined.json
                section = parts[0]
                collection_name = f"gate_{section.lower()}_all_years_combined"

        print(f"\n--- Processing: {filename} -> {collection_name} ---")

        # Get or create a dedicated collection for the section
        collection = client.get_or_create_collection(name=collection_name)
        
        with open(json_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        if not questions:
            print(f"No questions found in {filename}. Skipping.")
            continue

        print(f"Preparing {len(questions)} documents for embedding...")
        documents = [_construct_document_from_question(q) for q in questions]
        
        # Create metadata including available fields
        metadatas = []
        for q in questions:
            metadata = {"year": q.get('year', 0), "slot": q.get('slot', 0)}
            if 'stream' in q:
                metadata['stream'] = q['stream']
            metadatas.append(metadata)
        
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

    print(f"\nVector database build complete for {exam_type}.")
    print(f"Database files are stored in: {os.path.abspath(vector_db_path)}")

def build_all_vector_databases():
    """Build vector databases for both CAT and GATE exams"""
    for exam_type in ["CAT", "GATE"]:
        build_vector_database_for_exam(exam_type)
    print("\n=== All vector databases built successfully ===")


if __name__ == "__main__":
    build_all_vector_databases()

