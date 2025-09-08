import fitz  # PyMuPDF
import re
import json
import os
import glob

# --- Configuration ---
# Use relative paths to make the script portable within the project structure
SOURCE_PDF_DIR = os.path.join(os.path.dirname(__file__), '..', 'source_pdfs')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '2_app_data', 'structured_questions')

def parse_answer_keys(full_text):
    """Parses answer key tables from the PDF's full text."""
    answers = {'VARC': {}, 'DILR': {}, 'Quant': {}}
    key_sections = re.findall(r"Answer Key: (VARC|DILR|Quant) Section\s*([\s\S]*?)(?=\nAnswer Key:|\Z)", full_text)
    
    for section_name, key_block in key_sections:
        section_key = section_name.strip()
        answer_pairs = re.findall(r'"(\d+)\s*","\s*([a-zA-Z0-9\.]+)\s*"', key_block)
        if not answer_pairs:
             answer_pairs = re.findall(r'(\d+)\s*,\s*([a-zA-Z0-9\.]+)', key_block)

        for q_num, answer in answer_pairs:
            try:
                answers[section_key][int(q_num)] = answer.strip()
            except ValueError:
                continue # Skip if q_num is not a valid integer
            
    return answers

def process_cat_pdf(pdf_path, year, slot):
    """Processes a single CAT PDF to extract questions."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return None

    full_text = "".join(page.get_text("text") for page in doc)
    answers = parse_answer_keys(full_text)
    
    structured_data = {"VARC": [], "DILR": [], "Quant": []}
    
    # Split the document by sections
    sections = re.split(r"Section: (VARC|DILR|Quant)", full_text)
    
    for i in range(1, len(sections), 2):
        section_name = sections[i].strip()
        section_content = sections[i+1]
        
        # Split content into individual questions
        questions_raw = re.split(r'(?=Q\.\s*\d+\))', section_content)
        
        passage_context = ""
        for block in questions_raw:
            block = block.strip()
            if not block or not block.startswith("Q."):
                if block.startswith("The passage below") or block.startswith("The chart below"):
                    passage_context = block
                continue
            
            question_match = re.match(r'Q\.\s*(\d+)\)', block)
            if not question_match:
                continue
            
            q_num_local = int(question_match.group(1))
            
            # Separate question text from options
            parts = re.split(r'\n\s*a\)', block, 1)
            question_text = parts[0].replace(f'Q. {q_num_local})', '').strip()
            
            options_part = "a)" + parts[1] if len(parts) > 1 else ""
            options = re.findall(r'([a-d]\))\s*(.*?)(?=\n\s*[a-d]\)|$)', options_part, re.DOTALL)
            options_list = [f"{opt[0]} {opt[1].strip().replace('\n', ' ')}" for opt in options]

            question_obj = {
                "id": f"cat_{year}_s{slot}_{section_name.lower()}_{q_num_local:03d}",
                "exam": "CAT",
                "year": year,
                "slot": slot,
                "section": section_name,
                "question_text": question_text,
                "options": options_list,
                "answer": answers.get(section_name, {}).get(q_num_local, "N/A"),
                "explanation": "",
                "passage_context": passage_context if section_name == "VARC" else "",
            }
            structured_data[section_name].append(question_obj)

    doc.close()
    return structured_data

if __name__ == "__main__":
    print("Starting PDF parsing process...")
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    pdf_files = glob.glob(os.path.join(SOURCE_PDF_DIR, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {SOURCE_PDF_DIR}. Please add your source PDFs.")
    else:
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            print(f"Processing '{filename}'...")
            
            # Simple way to get year and slot from filename, can be improved
            match = re.search(r'(\d{4}).*Slot-(\d{1,2})', filename)
            if match:
                year, slot = int(match.group(1)), int(match.group(2))
            else:
                print(f"Warning: Could not determine year/slot from filename '{filename}'. Defaulting to 2024, Slot 1.")
                year, slot = 2024, 1

            extracted_data = process_cat_pdf(pdf_path, year, slot)
            
            if extracted_data:
                for section, questions in extracted_data.items():
                    if questions:
                        output_filename = os.path.join(OUTPUT_DIR, f"CAT_{section}.json")
                        
                        # Append to existing file or create a new one
                        existing_data = []
                        if os.path.exists(output_filename):
                            with open(output_filename, 'r', encoding='utf-8') as f:
                                existing_data = json.load(f)
                        
                        # Avoid duplicates
                        existing_ids = {q['id'] for q in existing_data}
                        new_questions = [q for q in questions if q['id'] not in existing_ids]
                        
                        with open(output_filename, 'w', encoding='utf-8') as f:
                            json.dump(existing_data + new_questions, f, indent=2, ensure_ascii=False)
                        
                        print(f"  - Wrote/updated {len(new_questions)} questions to '{output_filename}'")
    
    print("\nPDF parsing finished.")
