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
def parse_metadata_from_filename(filename):
    """
    Extracts exam, year, and slot information from the PDF filename.
    Handles variations in naming conventions.
    """
    # Regex to find year and slot from filenames like 'CAT-2022-Slot-2...' or 'CAT-2024-Slot-01...'
    match = re.search(r'CAT-(\d{4}).*slot-0?(\d+)', filename, re.IGNORECASE)
    if match:
        year = int(match.group(1))
        slot = int(match.group(2))
        return "CAT", year, slot
        
    return "Unknown", 0, 0

def get_section_and_abbreviation(text):
    """
    Determines the exam section based on keywords in the text.
    """
    text_lower = text.lower()
    if "verbal ability" in text_lower or "varc" in text_lower:
        return "Verbal Ability and Reading Comprehension", "VARC"
    elif "data interpretation" in text_lower or "dilr" in text_lower:
        return "Data Interpretation and Logical Reasoning", "DILR"
    elif "quantitative aptitude" in text_lower or "quant" in text_lower:
        return "Quantitative Aptitude", "QA"
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
    exam, year, slot = parse_metadata_from_filename(filename)
    
    pdf_text = ""
    try:
        with fitz.open(pdf_filepath) as doc:
            for page in doc:
                pdf_text += page.get_text()
    except Exception as e:
        print(f"Error reading PDF file {pdf_filepath}: {e}")
        return []

    # Split the text by common question markers (e.g., Q. 1), Q. 2))
    # We use a lookahead `(?=...)` to split the text while keeping the delimiter.
    question_blocks = re.split(r'(?=Q\.\s?\d+\))', pdf_text)
    
    json_output = []
    question_counter = 0

    # Determine the section once from the start of the text
    full_section_name, section_abbr = get_section_and_abbreviation(question_blocks[0] or "")
    
    for i, block in enumerate(question_blocks):
        if not block.strip() or not block.strip().startswith('Q.'):
            continue

        question_counter += 1
        
        # Define regex patterns to find options. This handles formats like:
        # A. text, [1] text, a) text, 1. text
        option_pattern = re.compile(
            r'(\n(?:[A-D]\)|[A-D]\.|\[[1-4]\]|[a-d]\))\s)(.*?)(?=\n(?:[A-D]\)|[A-D]\.|\[[1-4]\]|[a-d]\))|\Z)', 
            re.DOTALL
        )
        
        options = option_pattern.findall(block)
        
        # The question text is everything before the first option starts
        first_option_pos = -1
        if options:
            first_option_full_match = options[0][0] + options[0][1]
            first_option_pos = block.find(first_option_full_match)

        if first_option_pos != -1:
            question_text_raw = block[:first_option_pos]
        else:
            question_text_raw = block

        question_text_cleaned = re.sub(r'^Q\.\s?\d+\)\s*', '', question_text_raw).strip()
        
        # If the block contains a new section header, update it
        current_section_name, current_section_abbr = get_section_and_abbreviation(block)
        if current_section_abbr != "Unknown":
            section_abbr = current_section_abbr

        # Structure the final JSON object for this question
        question_data = {
            "id": f"{exam.lower()}_{section_abbr.lower()}_{year}_s{slot}_{question_counter:03d}",
            "exam": exam,
            "year": year,
            "slot": slot,
            "section": section_abbr,
            "question_text": question_text_cleaned.replace('\n', ' ').strip()
        }
        
        # Populate options into the desired format (option1, option2...)
        for idx, opt in enumerate(options[:4]):
            option_text = opt[1].replace('\n', ' ').strip()
            question_data[f"option{idx+1}"] = option_text

        question_data["answer"] = "N/A"
        json_output.append(question_data)
        
    return json_output

# Define Source and Output Directories
# Assumes the script is in a 'scripts' folder, 'source_pdfs' is a sibling to 'scripts',
# and 'app_data' is in the parent of the parent directory.
# Adjust the pathing ('..') as needed for your project structure.
SOURCE_PDF_DIR = os.path.join(os.path.dirname(__file__), '..', 'source_pdfs')
OUTPUT_JSON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'app_data', 'structured_questions')

def process_pdf(pdf_path):
    """Processes a single PDF, parses questions, and saves to JSON."""
    print(f"Processing {os.path.basename(pdf_path)}...")
    parsed_questions = convert_questions_to_json(pdf_path)

    if parsed_questions:
        # Ensure the output directory exists
        os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
        
        # Create an output JSON filename based on the input PDF name
        base_filename = os.path.basename(pdf_path)
        output_filename = os.path.splitext(base_filename)[0] + '.json'
        output_filepath = os.path.join(OUTPUT_JSON_DIR, output_filename)
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(parsed_questions, f, indent=2, ensure_ascii=False)
        print(f"-> Success: Parsed {len(parsed_questions)} questions. Output saved to {output_filepath}")
    else:
        print(f"-> Warning: No questions parsed from {os.path.basename(pdf_path)}.")

if __name__ == "__main__":
    all_questions = []
    pdf_files = glob.glob(os.path.join(SOURCE_PDF_DIR, "*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in '{SOURCE_PDF_DIR}'. Please check the path and file locations.")
    else:
        # Step 1: Parse all PDFs and collect all questions into one list
        for pdf_path in pdf_files:
            print(f"Processing {os.path.basename(pdf_path)}...")
            parsed_questions = convert_questions_to_json(pdf_path)
            if parsed_questions:
                all_questions.extend(parsed_questions)
                print(f"-> Found {len(parsed_questions)} questions.")
            else:
                print(f"-> Warning: No questions parsed from {os.path.basename(pdf_path)}.")

        # Step 2: Group the collected questions by section
        questions_by_section = {
            "VARC": [],
            "DILR": [],
            "QA": []
        }

        for question in all_questions:
            section = question.get("section")
            if section in questions_by_section:
                questions_by_section[section].append(question)

        # Step 3: Write the grouped questions into section-specific JSON files
        os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

        for section, questions in questions_by_section.items():
            if questions:
                output_filename = f"CAT_{section}_all_years_combined.json"
                output_filepath = os.path.join(OUTPUT_JSON_DIR, output_filename)
                
                # Sort questions by year, then slot, then ID for consistency
                questions.sort(key=lambda q: (q.get('year', 0), q.get('slot', 0), q.get('id', '')))

                with open(output_filepath, 'w', encoding='utf-8') as f:
                    json.dump(questions, f, indent=2, ensure_ascii=False)
                
                print(f"\n-> Success: Saved {len(questions)} {section} questions to {output_filepath}")

    print("\nPDF parsing and grouping finished.")