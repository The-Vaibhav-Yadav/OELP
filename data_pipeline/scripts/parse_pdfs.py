import fitz  # PyMuPDF
import re
import json
import os
import glob
from collections import defaultdict

# --- Helper Functions ---
def parse_metadata_from_filename(filename):
    """
    Extracts exam, year, and slot information from the PDF filename.
    Handles variations in naming conventions for both CAT and GATE.
    """
    # Regex for CAT filenames like 'CAT-2022-Slot-2...' or 'CAT-2024-Slot-01...'
    cat_match = re.search(r'CAT-(\d{4}).*slot-0?(\d+)', filename, re.IGNORECASE)
    if cat_match:
        year = int(cat_match.group(1))
        slot = int(cat_match.group(2))
        return "CAT", year, slot
    
    # Regex for GATE filenames like 'GATE-2023-CS-Session-1...' or 'GATE-2024-EE...'
    gate_match = re.search(r'GATE-(\d{4})-([A-Z]{2,3}).*(?:session|slot)?-?0?(\d+)?', filename, re.IGNORECASE)
    if gate_match:
        year = int(gate_match.group(1))
        stream = gate_match.group(2).upper()
        session = int(gate_match.group(3)) if gate_match.group(3) else 1
        return "GATE", year, session, stream
        
    return "Unknown", 0, 0, None

def get_section_and_abbreviation(text, exam_type="CAT"):
    """
    Determines the exam section based on keywords in the text for both CAT and GATE.
    """
    text_lower = text.lower()
    
    if exam_type == "CAT":
        if "verbal ability" in text_lower or "varc" in text_lower:
            return "Verbal Ability and Reading Comprehension", "VARC"
        elif "data interpretation" in text_lower or "dilr" in text_lower:
            return "Data Interpretation and Logical Reasoning", "DILR"
        elif "quantitative aptitude" in text_lower or "quant" in text_lower:
            return "Quantitative Aptitude", "QA"
    elif exam_type == "GATE":
        if "general aptitude" in text_lower or "ga" in text_lower:
            return "General Aptitude", "GA"
        elif any(term in text_lower for term in ["technical", "engineering", "mathematics", "subject"]):
            return "Technical", "TECH"
            
    return "Unknown", "Unknown"


def convert_questions_to_json(pdf_filepath):
    """
    Extracts text from a PDF and converts questions into a list of JSON objects.

    Args:
        pdf_filepath (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, where each dictionary represents a question.
              Returns an empty list if the PDF cannot be read.
    """
    filename = os.path.basename(pdf_filepath)
    metadata = parse_metadata_from_filename(filename)
    if len(metadata) == 4:  # GATE
        exam, year, slot, stream = metadata
    else:  # CAT
        exam, year, slot = metadata
        stream = None
    
    pdf_text = ""
    try:
        with fitz.open(pdf_filepath) as doc:
            for page in doc:
                page_text = page.get_text()
                if page_text.strip():  # Only add non-empty pages
                    pdf_text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF file {pdf_filepath}: {e}")
        return []

    # Split the text by common question markers
    # For CAT: Q. 1), Q. 2) format
    # For GATE: Q.1, Q.2 format (without parentheses)
    if exam == "CAT":
        question_blocks = re.split(r'(?=Q\.\s?\d+\))', pdf_text)
    else:  # GATE format
        question_blocks = re.split(r'(?=Q\.\s?\d+(?:\s|$))', pdf_text)
    
    json_output = []
    question_counter = 0

    # Determine the section once from the start of the text
    full_section_name, section_abbr = get_section_and_abbreviation(question_blocks[0] or "", exam)
    
    for i, block in enumerate(question_blocks):
        if not block.strip():
            continue
        
        # Check if block starts with question marker
        if exam == "CAT" and not block.strip().startswith('Q.'):
            continue
        elif exam == "GATE":
            if not re.match(r'Q\.\s?\d+', block.strip()):
                continue
            # For GATE, skip header blocks that don't have options (like "Q.1 – Q.5 Carry ONE mark Each")
            if '(' not in block or not re.search(r'\([A-D]\)', block):
                continue

        question_counter += 1
        
        # Define regex patterns to find options based on exam type
        if exam == "CAT":
            # CAT formats: A. text, [1] text, a) text, 1. text
            option_pattern = re.compile(
                r'(\n(?:[A-D]\)|[A-D]\.|\[[1-4]\]|[a-d]\))\s)(.*?)(?=\n(?:[A-D]\)|[A-D]\.|\[[1-4]\]|[a-d]\))|\Z)', 
                re.DOTALL
            )
        else:  # GATE
            # GATE formats: (A) text, (B) text, (C) text, (D) text
            option_pattern = re.compile(
                r'(\n?\s*\(([A-D])\)\s*)(.*?)(?=\s*\([A-D]\)|\Z)', 
                re.DOTALL
            )
        
        options = option_pattern.findall(block)
        
        # The question text is everything before the first option starts
        first_option_pos = -1
        if options:
            if exam == "CAT":
                first_option_full_match = options[0][0] + options[0][1]
            else:  # GATE
                first_option_full_match = options[0][0]
            first_option_pos = block.find(first_option_full_match)

        if first_option_pos != -1:
            question_text_raw = block[:first_option_pos]
        else:
            question_text_raw = block

        # Clean question text based on format
        if exam == "CAT":
            question_text_cleaned = re.sub(r'^Q\.\s?\d+\)\s*', '', question_text_raw).strip()
        else:  # GATE
            question_text_cleaned = re.sub(r'^Q\.\s?\d+\s*', '', question_text_raw).strip()
        
        # If the block contains a new section header, update it
        current_section_name, current_section_abbr = get_section_and_abbreviation(block, exam)
        if current_section_abbr != "Unknown":
            section_abbr = current_section_abbr

        # Structure the final JSON object for this question
        question_id_parts = [exam.lower(), section_abbr.lower(), str(year), f"s{slot}", f"{question_counter:03d}"]
        if stream:  # Add stream for GATE
            question_id_parts.insert(2, stream.lower())
        
        question_data = {
            "id": "_".join(question_id_parts),
            "exam": exam,
            "year": year,
            "slot": slot,
            "section": section_abbr,
            "question_text": question_text_cleaned.replace('\n', ' ').strip()
        }
        
        # Add stream for GATE questions
        if stream:
            question_data["stream"] = stream
        
        # Populate options into the desired format (option1, option2...)
        for idx, opt in enumerate(options[:4]):
            if exam == "CAT":
                option_text = opt[1].replace('\n', ' ').strip()
            else:  # GATE - opt[2] contains the text, opt[1] contains the letter
                option_text = opt[2].replace('\n', ' ').strip()
            question_data[f"option{idx+1}"] = option_text

        json_output.append(question_data)
        
    return json_output

# Define Source and Output Directories
# Assumes the script is in a 'scripts' folder, 'source_pdfs' is a sibling to 'scripts',
# and 'app_data' is in the parent of the parent directory.
def get_directories(exam_type):
    """Get source and output directories for a specific exam type"""
    source_dir = os.path.join(os.path.dirname(__file__), '..', 'source_pdfs', exam_type.upper())
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'app_data', 'structured_questions', exam_type.upper())
    return source_dir, output_dir

def process_pdf(pdf_path, output_dir):
    """Processes a single PDF, parses questions, and saves to JSON."""
    print(f"Processing {os.path.basename(pdf_path)}...")
    parsed_questions = convert_questions_to_json(pdf_path)

    if parsed_questions:
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create an output JSON filename based on the input PDF name
        base_filename = os.path.basename(pdf_path)
        output_filename = os.path.splitext(base_filename)[0] + '.json'
        output_filepath = os.path.join(output_dir, output_filename)
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(parsed_questions, f, indent=2, ensure_ascii=False)
        print(f"-> Success: Parsed {len(parsed_questions)} questions. Output saved to {output_filepath}")
    else:
        print(f"-> Warning: No questions parsed from {os.path.basename(pdf_path)}.")

def process_exam_type(exam_type):
    """Process all PDFs for a specific exam type"""
    print(f"\n=== Processing {exam_type} Exam PDFs ===")
    source_dir, output_dir = get_directories(exam_type)
    
    pdf_files = glob.glob(os.path.join(source_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in '{source_dir}'. Skipping {exam_type}.")
        return
    
    all_questions = []
    
    # Step 1: Parse all PDFs and collect all questions into one list
    for pdf_path in pdf_files:
        print(f"Processing {os.path.basename(pdf_path)}...")
        parsed_questions = convert_questions_to_json(pdf_path)
        if parsed_questions:
            all_questions.extend(parsed_questions)
            print(f"-> Found {len(parsed_questions)} questions.")
        else:
            print(f"-> Warning: No questions parsed from {os.path.basename(pdf_path)}.")

    if not all_questions:
        print(f"No questions found for {exam_type}.")
        return

    # Step 2: Group the collected questions by section
    if exam_type == "CAT":
        sections_map = {"VARC": [], "DILR": [], "QA": []}
    else:  # GATE
        sections_map = {"GA": [], "TECH": []}
        # For GATE, also group by stream
        streams_map = defaultdict(lambda: {"GA": [], "TECH": []})

    for question in all_questions:
        section = question.get("section")
        if exam_type == "CAT":
            if section in sections_map:
                sections_map[section].append(question)
        else:  # GATE
            stream = question.get("stream")
            if section in ["GA", "TECH"]:
                sections_map[section].append(question)
                if stream:
                    streams_map[stream][section].append(question)

    # Step 3: Write the grouped questions into section-specific JSON files
    os.makedirs(output_dir, exist_ok=True)

    # For CAT: Create section files
    # For GATE: Create both general section files and stream-specific files
    for section, questions in sections_map.items():
        if questions:
            output_filename = f"{exam_type}_{section}_all_years_combined.json"
            output_filepath = os.path.join(output_dir, output_filename)
            
            # Sort questions by year, then slot, then ID for consistency
            questions.sort(key=lambda q: (q.get('year', 0), q.get('slot', 0), q.get('id', '')))

            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(questions, f, indent=2, ensure_ascii=False)
            
            print(f"-> Success: Saved {len(questions)} {section} questions to {output_filepath}")

    # For GATE: Also create stream-specific files
    if exam_type == "GATE":
        for stream, stream_sections in streams_map.items():
            for section, questions in stream_sections.items():
                if questions:
                    output_filename = f"GATE_{stream}_{section}_all_years_combined.json"
                    output_filepath = os.path.join(output_dir, output_filename)
                    
                    questions.sort(key=lambda q: (q.get('year', 0), q.get('slot', 0), q.get('id', '')))

                    with open(output_filepath, 'w', encoding='utf-8') as f:
                        json.dump(questions, f, indent=2, ensure_ascii=False)
                    
                    print(f"-> Success: Saved {len(questions)} {stream}-{section} questions to {output_filepath}")

if __name__ == "__main__":
    print("Starting PDF parsing for CAT and GATE exams...")
    
    # Process both exam types
    for exam_type in ["CAT", "GATE"]:
        process_exam_type(exam_type)
    
    print("\nPDF parsing and grouping finished for all exam types.")