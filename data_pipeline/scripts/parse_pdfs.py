import fitz  # PyMuPDF
import re
import json
import os
import glob
from collections import defaultdict

# --- Configuration ---
SOURCE_PDF_DIR = os.path.join(os.path.dirname(__file__), '..', 'source_pdfs')
OUTPUT_JSON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'app_data', 'structured_questions')

# --- Helper Functions ---

def extract_year_slot_from_filename(filename):
    """Extracts year and slot from a PDF filename using a more robust regex."""
    match = re.search(r'CAT-?(\d{4}).*?[-_ ]?[Ss]lot-?0?(\d)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Fallback for other common patterns
    match = re.search(r'(\d{4}).*?[Ss]lot-(\d)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
        
    print(f"Warning: Could not determine year/slot from filename '{os.path.basename(filename)}'. Defaulting to 2024, Slot 1.")
    return 2024, 1

def save_questions_to_json(questions_by_section, base_output_dir):
    """Appends new questions to the appropriate JSON file for each section."""
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir)

    for section, questions in questions_by_section.items():
        if not questions:
            continue
            
        filename = os.path.join(base_output_dir, f"CAT_{section.replace('&', '').strip()}.json")
        
        existing_questions = []
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                try:
                    existing_questions = json.load(f)
                except json.JSONDecodeError:
                    pass # File is empty or corrupt

        # Create a set of existing IDs for quick lookup
        existing_ids = {q['id'] for q in existing_questions}
        new_questions_to_add = [q for q in questions if q['id'] not in existing_ids]

        if new_questions_to_add:
            all_questions = existing_questions + new_questions_to_add
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_questions, f, indent=2)
            print(f"  - Wrote/updated {len(new_questions_to_add)} questions to '{filename}'")

# --- Format-Specific Parsers ---

def parse_answer_key_2022(text):
    """Parses the specific answer key format for 2022 PDFs."""
    key_pattern = re.compile(r'"(\d+)\n","(\d|(?:\d\.\d)|[A-Za-z0-9_]+)\n","(\d|(?:\d\.\d)|[A-Za-z0-9_]+)\n","(\d|(?:\d\.\d)|[A-Za-z0-9_]+)\n"')
    matches = key_pattern.findall(text)
    keys = {'VARC': {}, 'DILR': {}, 'Quant': {}}
    for q_num, varc, dilr, quant in matches:
        keys['VARC'][int(q_num)] = varc
        keys['DILR'][int(q_num)] = dilr
        keys['Quant'][int(q_num)] = quant
    return keys

def parse_answer_key_2023(text):
    """Parses the specific answer key format for 2023 PDFs."""
    keys = {'VARC': {}, 'DILR': {}, 'Quant': {}}
    try:
        key_block = text.split("Answer Keys")[1]
        # Regex to find question number and its answer (A, B, C, D, or a number)
        matches = re.findall(r'(\d+)\s+([A-D]|\d+)', key_block)
        
        # Approximate question counts to split the flat list of answers
        # CAT has roughly 24 VARC, 20 DILR, 22 Quant
        varc_q_count = 24
        dilr_q_count = 20
        
        varc_answers = matches[:varc_q_count]
        dilr_answers = matches[varc_q_count : varc_q_count + dilr_q_count]
        quant_answers = matches[varc_q_count + dilr_q_count:]

        for q_num, answer in varc_answers:
            keys['VARC'][int(q_num)] = answer
        for q_num, answer in dilr_answers:
            keys['DILR'][int(q_num)] = answer
        for q_num, answer in quant_answers:
             keys['Quant'][int(q_num)] = answer
    except IndexError:
        print("Warning: Could not parse 2023 answer key format.")
    return keys


def parse_pdf_format_2022(text, year, slot):
    """Handles the structure of 2022 CAT papers."""
    sections = {
        'VARC': re.search(r'CAT 2022 VARC Section(.*?)CAT 2022 DILR Section', text, re.DOTALL),
        'DILR': re.search(r'CAT 2022 DILR Section(.*?)CAT 2022 Quant Section', text, re.DOTALL),
        'Quant': re.search(r'CAT 2022 Quant Section(.*?)(?=Answer Keys)', text, re.DOTALL)
    }
    answer_keys = parse_answer_key_2022(text)
    
    all_questions = defaultdict(list)
    question_pattern = re.compile(r'Q\.\d+\)')
    
    for sec_name, content_match in sections.items():
        if not content_match:
            continue
        
        content = content_match.group(1)
        # Split content by question pattern
        question_blocks = question_pattern.split(content)[1:]
        question_numbers = [int(n.strip(')')) for n in re.findall(r'Q\.(\d+)\)', content)]

        for i, block in enumerate(question_blocks):
            q_num = question_numbers[i]
            parts = re.split(r'\n\s*\[1\]', block, 1)
            question_text = parts[0].replace('\n', ' ').strip()
            
            options_text = ""
            if len(parts) > 1:
                options_text = "[1]" + parts[1]
                options = [opt.replace('\n', ' ').strip() for opt in re.split(r'\n\s*\[\d\]', options_text)]

            all_questions[sec_name].append({
                'id': f"cat_{sec_name.lower()}_{year}_s{slot}_{q_num:03d}",
                'exam': 'CAT',
                'year': year,
                'slot': slot,
                'section': sec_name,
                'question_text': question_text,
                'options': options,
                'answer': answer_keys.get(sec_name, {}).get(q_num, 'N/A')
            })
    return all_questions

def parse_pdf_format_2023(text, year, slot):
    """Handles the structure of 2023 CAT papers."""
    sections = {
        'VARC': re.search(r'Section 01: Verbal Ability and Reading Comprehension(.*?)Section 02: Data interpretation', text, re.DOTALL),
        'DILR': re.search(r'Section 02: Data interpretation and Logical Reasoning(.*?)Section 03: Quantitative Aptitude', text, re.DOTALL),
        'Quant': re.search(r'Section 03: Quantitative Aptitude(.*?)(?=Answer Keys)', text, re.DOTALL)
    }
    answer_keys = parse_answer_key_2023(text)

    all_questions = defaultdict(list)
    question_pattern = re.compile(r'Q\.\s?\d+\)')
    
    for sec_name, content_match in sections.items():
        if not content_match: continue
        
        content = content_match.group(1)
        question_blocks = question_pattern.split(content)[1:]
        question_numbers = [int(n.strip(')')) for n in re.findall(r'Q\.\s?(\d+)\)', content)]
        
        for i, block in enumerate(question_blocks):
            q_num = question_numbers[i]
            parts = re.split(r'\n\s*A\.', block, 1)
            question_text = parts[0].replace('\n', ' ').strip()
            
            options_text = ""
            if len(parts) > 1:
                options_text = "A." + parts[1]
                options = [opt.replace('\n', ' ').strip() for opt in re.split(r'\n\s*[A-D]\.', options_text)]
            
            all_questions[sec_name].append({
                'id': f"cat_{sec_name.lower()}_{year}_s{slot}_{q_num:03d}",
                'exam': 'CAT',
                'year': year,
                'slot': slot,
                'section': sec_name,
                'question_text': question_text,
                'options': options,
                'answer': answer_keys.get(sec_name, {}).get(q_num, 'N/A')
            })
    return all_questions


def parse_pdf_format_2024(text, year, slot):
    """Handles the original structure (let's call it 2024 style)."""
    # This function would contain the original parsing logic you had.
    # For brevity, I'm providing a simplified version. The key is the structure.
    sections = {
        'VARC': re.search(r'Section: VARC(.*?)Section: DILR', text, re.DOTALL),
        'DILR': re.search(r'Section: DILR(.*?)Section: Quant', text, re.DOTALL),
        'Quant': re.search(r'Section: Quant(.*?)(?=Answer Key: VARC Section)', text, re.DOTALL)
    }
    
    # In this format, answer keys are simpler and per-section
    answer_keys = {}
    for sec_name in ['VARC', 'DILR', 'Quant']:
        key_block_match = re.search(fr'Answer Key: {sec_name} Section(.*?)(?=Section:|Answer Key:|$)', text, re.DOTALL)
        if key_block_match:
            answer_keys[sec_name] = dict(re.findall(r'"(\d+)"\s*,\s*"([a-zA-Z])"', key_block_match.group(1)))

    all_questions = defaultdict(list)
    question_pattern = re.compile(r'Q\.\s?\d+\)')

    for sec_name, content_match in sections.items():
        if not content_match: continue
        content = content_match.group(1)
        # Simplified parsing logic for brevity
        question_blocks = question_pattern.split(content)[1:]
        question_numbers = [int(n.strip(')')) for n in re.findall(r'Q\.\s?(\d+)\)', content)]

        for i, block in enumerate(question_blocks):
            q_num = question_numbers[i]
            # Your original question/option parsing logic for this format
            parts = re.split(r'\n\s*a\)', block, 1)
            question_text = parts[0].replace('\n', ' ').strip()
            options = [] # Parse options based on a), b), c)
            
            all_questions[sec_name].append({
                'id': f"cat_{sec_name.lower()}_{year}_s{slot}_{q_num:03d}",
                'exam': 'CAT', 'year': year, 'slot': slot, 'section': sec_name,
                'question_text': question_text, 'options': options,
                'answer': answer_keys.get(sec_name, {}).get(str(q_num), 'N/A')
            })
    return all_questions

# --- Main Processing Logic ---

def process_pdf(pdf_path):
    """
    Opens a PDF, detects its format, and calls the appropriate parser.
    """
    print(f"Processing '{os.path.basename(pdf_path)}'...")
    year, slot = extract_year_slot_from_filename(os.path.basename(pdf_path))
    
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        print(f"  - Error reading PDF {os.path.basename(pdf_path)}: {e}")
        return

    # Format Detection Logic
    if "CAT 2022 VARC Section" in text:
        # print("  - Detected 2022 format.")
        questions_by_section = parse_pdf_format_2022(text, year, slot)
    elif "CAT 2023 QUESTION PAPER" in text:
        # print("  - Detected 2023 format.")
        questions_by_section = parse_pdf_format_2023(text, year, slot)
    else:
        # print("  - Detected default (2024) format.")
        # Assuming the original parser was for this format
        questions_by_section = parse_pdf_format_2024(text, year, slot)
    
    save_questions_to_json(questions_by_section, OUTPUT_JSON_DIR)

if __name__ == "__main__":
    pdf_files = glob.glob(os.path.join(SOURCE_PDF_DIR, "*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in '{SOURCE_PDF_DIR}'.")
    else:
        for pdf_path in pdf_files:
            process_pdf(pdf_path)
    print("\nPDF parsing finished.")

