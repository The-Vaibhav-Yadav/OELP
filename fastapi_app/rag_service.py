import chromadb
from sentence_transformers import SentenceTransformer
import json
import os
import random
import asyncio
import aiohttp
from datetime import datetime

# --- Configuration ---
VECTOR_DB_PATH = os.path.join('/Users/vaibhav.yadav/Documents/Course/OELP/app_data', 'vector_db', 'CAT')
STRUCTURED_QUESTIONS_DIR = os.path.join('/Users/vaibhav.yadav/Documents/Course/OELP/app_data', 'structured_questions', 'CAT')
GENERATED_EXAMS_DIR = os.path.join('/Users/vaibhav.yadav/Documents/Course/OELP/app_data', 'generated_questions', 'CAT')
MODEL_NAME = 'all-MiniLM-L6-v2'

# Structure of the CAT exam to be generated
SUPPORTED_EXAMS = {
    "CAT": {
        "varc": {"mcq": 21, "tita": 3},
        "dilr": {"mcq": 12, "tita": 10},
        "quant": {"mcq": 14, "tita": 8}
    }
    # Future exams like GATE can be added here
}

# Mapping for section names to filename abbreviations
SECTION_FILENAME_MAP = {
    "varc": "VARC",
    "dilr": "DILR",
    "quant": "QA"
}

class RAGService:
    def __init__(self):
        print("Initializing RAG Service...")
        print(f"Loading vector database from: {VECTOR_DB_PATH}")
        self.client = chromadb.PersistentClient(path=VECTOR_DB_PATH)

        # Diagnostic check for existing collections
        print("\n--- Vector DB Collection Summary ---")
        try:
            collections = self.client.list_collections()
            if collections:
                print(f"Found {len(collections)} collections: {[c.name for c in collections]}")
            else:
                print("No collections found. Please run 'build_vector_db.py' to create them.")
        except Exception as e:
            print(f"Could not connect to or list collections in ChromaDB: {e}")
            print("Please ensure the vector database has been built correctly.")
        print("------------------------------------\n")

        print(f"Loading sentence transformer model: {MODEL_NAME}")
        self.model = SentenceTransformer(MODEL_NAME)

        self.source_questions = self._load_source_questions()

        # Diagnostic summary to check loaded data
        print("\n--- Source Data Summary ---")
        for section, questions in self.source_questions.items():
            if not questions:
                print(f"Section {section.upper()}: 0 questions loaded. Please check the source JSON file.")
                continue
            mcq_count = sum(1 for q in questions if 'option1' in q)
            tita_count = sum(1 for q in questions if 'option1' not in q)
            print(f"Section {section.upper()}: Loaded {len(questions)} total questions ({mcq_count} MCQ, {tita_count} TITA).")
        print("---------------------------\n")

        print("RAG Service initialized successfully.")

    def _load_source_questions(self):
        """
        Loads all questions from the JSON files into memory for quick lookups.
        Handles specific filenames like 'CAT_QA_all_years_combined.json'.
        """
        source_data = {}
        for section in SUPPORTED_EXAMS["CAT"].keys():
            file_abbr = SECTION_FILENAME_MAP.get(section, section.upper())
            file_name = f"CAT_{file_abbr}_all_years_combined.json"
            file_path = os.path.join(STRUCTURED_QUESTIONS_DIR, file_name)
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        source_data[section] = data if isinstance(data, list) else []
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON from {file_path}.")
                    source_data[section] = []
            else:
                source_data[section] = []
                print(f"Warning: Source JSON file not found at '{file_path}'")
        return source_data

    def _find_seed_question(self, section, q_type, exam_name, stream, year):
        """Finds a random question that matches the specified filters to seed the search."""
        candidates = self.source_questions.get(section, [])
        
        # Filter by exam, stream, year if provided
        if exam_name:
            candidates = [q for q in candidates if q.get('exam', '').lower() == exam_name.lower()]
        if stream:
            candidates = [q for q in candidates if q.get('stream', '').lower() == stream.lower()]
        if year:
            candidates = [q for q in candidates if q.get('year') == year]

        if q_type == 'mcq':
            filtered = [q for q in candidates if 'option1' in q]
        else: # TITA
            filtered = [q for q in candidates if 'option1' not in q]

        return random.choice(filtered) if filtered else None

    async def _generate_single_question(self, session, section, q_type, exam_name, stream, year):
        """Generates one new question using the RAG pipeline with Groq API."""
        seed_question = self._find_seed_question(section, q_type, exam_name, stream, year)
        if not seed_question:
            return {"error": f"No seed questions found for {exam_name} {stream or ''} {year or ''} - {section} {q_type}"}

        collection_abbr = 'qa' if section == 'quant' else section
        collection_name = f"cat_{collection_abbr}_all_years_combined"

        try:
            collection = self.client.get_collection(name=collection_name)
            retrieved_results = collection.query(
                query_texts=[seed_question['question_text']],
                n_results=3 
            )
            
            context_questions = retrieved_results['documents'][0]
            prompt = self._create_llm_prompt(section, q_type, context_questions)
            
            GROQ_API_KEY = os.environ.get("GROQ_API_KEY") 
            if not GROQ_API_KEY:
                return {"error": "Groq API Key not found. Please set the GROQ_API_KEY environment variable."}

            api_url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "model": "llama-3.1-8b-instant",
                "temperature": 0.7,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"}
            }
            
            async with session.post(api_url, json=payload, headers=headers, timeout=120) as response:
                if response.status == 200:
                    result = await response.json()
                    llm_text = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    
                    try:
                        generated_q = json.loads(llm_text)
                        generated_q['section'] = SECTION_FILENAME_MAP.get(section, section.upper())
                        generated_q['type'] = q_type.upper()
                        return generated_q
                    except json.JSONDecodeError:
                        return {"error": "Failed to parse LLM JSON response", "raw_response": llm_text}
                else:
                    error_text = await response.text()
                    return {"error": f"LLM API Error: {response.status}", "details": error_text[:200]}

        except ValueError as e:
            if "does not exist" in str(e):
                return {"error": f"Vector DB collection '{collection_name}' not found. Please run the build script."}
            return {"error": f"An exception occurred: {str(e)}"}
        except Exception as e:
            return {"error": f"An unexpected exception occurred: {str(e)}"}

    def _create_llm_prompt(self, section, q_type, context_questions):
        """Constructs the prompt with instructions and context."""
        question_type_instruction = (
            "an MCQ (Multiple Choice Question) with 4 options labeled 'option1' to 'option4'" if q_type == 'mcq'
            else "a TITA (Type In The Answer) question where the answer is a numerical value or short text"
        )
        
        context_str = "\n---\n".join(context_questions)

        prompt = f"""
        You are an expert question setter for the CAT (Common Admission Test) exam.
        Your task is to generate a new, original question for the '{SECTION_FILENAME_MAP.get(section, section.upper())}' section.
        The question must be of type: {question_type_instruction}.
        It should be of a similar style, topic, and difficulty level to the following examples:
        ---
        {context_str}
        ---
        Your entire response MUST be a single, valid JSON object. Do not include any other text, markdown, or explanation.
        The JSON object must have the following structure:
        - For MCQ: {{"question_text": "...", "option1": "...", "option2": "...", "option3": "...", "option4": "...", "answer": "The correct option text", "explanation": "A brief explanation."}}
        - For TITA: {{"question_text": "...", "answer": "The numerical or short text answer", "explanation": "A brief explanation."}}
        """
        return prompt

    async def generate_full_exam(self, exam_name: str, stream: str | None = None, year: int | None = None):
        """
        Orchestrates the generation of a full mock exam section by section
        to respect API rate limits.
        """
        if exam_name.upper() == "CAT":
            exam_key = f"{exam_name.upper()}"
        else:
            exam_key = f"{exam_name.upper()}_{stream.upper()}" if stream else exam_name.upper()
        exam_structure = SUPPORTED_EXAMS.get(exam_key)

        if not exam_structure:
            return {"error": f"Exam structure for '{exam_key}' is not supported."}

        print(f"Generating {exam_key} mock exam...")
        full_exam = {
            "exam_details": {"name": exam_name, "stream": stream, "year": year},
            "VARC": [], "DILR": [], "QA": [], "errors": []
        }

        async with aiohttp.ClientSession() as session:
            sections_to_process = list(exam_structure.keys())

            for i, section in enumerate(sections_to_process):
                print(f"\n--- Generating section: {section.upper()} ---")
                
                tasks = []
                structure = exam_structure[section]
                
                for q_type, count in structure.items():
                    for _ in range(count):
                        tasks.append(self._generate_single_question(session, section, q_type, exam_name, stream, year))
                
                generated_questions = await asyncio.gather(*tasks)

                for q in generated_questions:
                    section_key = q.get('section')
                    if section_key and section_key in full_exam:
                        full_exam[section_key].append(q)
                    elif "error" in q:
                        full_exam["errors"].append(q)
                    else:
                        full_exam["errors"].append({"error": "Generated question has unknown section", "details": q})

                print(f"--- Section {section.upper()} generation complete. ---")

                if i < len(sections_to_process) - 1:
                    print(f"Waiting for 60 seconds to avoid rate limiting...")
                    await asyncio.sleep(60)
        
        print("\nFull exam generation complete.")
        self._save_exam(full_exam)
        return full_exam

    def _save_exam(self, exam_data):
        """Saves the generated exam to a timestamped JSON file."""
        try:
            os.makedirs(GENERATED_EXAMS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"exam_{timestamp}.json"
            save_path = os.path.join(GENERATED_EXAMS_DIR, file_name)

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(exam_data, f, indent=2)
            
            print(f"Successfully saved generated exam to: {save_path}")
        except Exception as e:
            print(f"Error saving the generated exam: {e}")

async def main_test():
    """For standalone testing of the RAG service."""
    rag_service = RAGService()
    # Test generating a standard CAT exam
    await rag_service.generate_full_exam(exam_name="CAT")

if __name__ == '__main__':
    # This allows you to test the service by running 'python rag_service.py'
    asyncio.run(main_test())

