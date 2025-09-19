import json
import google.generativeai as genai
from typing import List, Dict, Any
import time
import os

class ExamQuestionSolver:
    """
    A class to solve exam questions using Google Gemini and update JSON data with answers.
    """
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.1):
        """
        Initialize the solver with Gemini API credentials.
        
        Args:
            api_key (str): Google AI API key
            model (str): Gemini model to use (default: gemini-1.5-flash)
            temperature (float): Temperature for response generation (default: 0.1 for consistency)
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.temperature = temperature
        self.rate_limit_delay = 1  # seconds between API calls
        
        # Configure generation settings
        self.generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
            max_output_tokens=1000,
            top_p=0.9,
            top_k=40
        )
    
    def create_solving_prompt(self, question_data: Dict[str, Any]) -> str:
        """
        Create a comprehensive prompt for solving the question.
        
        Args:
            question_data (dict): Single question data from JSON
            
        Returns:
            str: Formatted prompt for the LLM
        """
        prompt = f"""
You are an expert in solving {question_data.get('exam', 'exam')} questions, particularly in the {question_data.get('section', 'section')} section.

Question ID: {question_data.get('id', 'N/A')}
Exam: {question_data.get('exam', 'N/A')} {question_data.get('year', 'N/A')}
Section: {question_data.get('section', 'N/A')}

Question: {question_data.get('question_text', '')}

Options:
"""
        
        # Add options to the prompt
        options = question_data.get('options', [])
        for i, option in enumerate(options):
            prompt += f"{i+1}. {option}\n"
        
        prompt += """
Please solve this question step by step:

1. First, carefully analyze the question and identify what type of problem it is
2. If this is part of a data interpretation set, note that you may need additional context or data that might be missing
3. Apply logical reasoning to eliminate incorrect options
4. Provide your reasoning process
5. Give your final answer as just the option number (1, 2, 3, or 4)

If you cannot solve the question due to missing context or data, respond with "INSUFFICIENT_DATA" and explain what additional information is needed.

Your response should be in this format:
ANALYSIS: [Your step-by-step analysis]
REASONING: [Your logical reasoning process]
ANSWER: [Option number or INSUFFICIENT_DATA]
"""
        return prompt
    
    def solve_single_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solve a single question using Gemini.
        
        Args:
            question_data (dict): Single question data
            
        Returns:
            dict: Updated question data with LLM solution
        """
        try:
            prompt = self.create_solving_prompt(question_data)
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            llm_response = response.text.strip()
            
            # Parse the LLM response to extract the answer
            answer = self.extract_answer_from_response(llm_response)
            
            # Update the question data
            updated_question = question_data.copy()
            updated_question['answer'] = answer
            updated_question['llm_analysis'] = llm_response
            updated_question['solved_by_llm'] = True
            updated_question['solve_timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
            updated_question['model_used'] = "gemini"
            
            return updated_question
            
        except Exception as e:
            # Handle API errors gracefully
            error_question = question_data.copy()
            error_question['answer'] = "ERROR"
            error_question['llm_error'] = str(e)
            error_question['solved_by_llm'] = False
            error_question['model_used'] = "gemini"
            return error_question
    
    def extract_answer_from_response(self, llm_response: str) -> str:
        """
        Extract the final answer from LLM response.
        
        Args:
            llm_response (str): Full response from LLM
            
        Returns:
            str: Extracted answer
        """
        lines = llm_response.split('\n')
        
        for line in lines:
            if line.startswith('ANSWER:'):
                answer = line.replace('ANSWER:', '').strip()
                return answer
        
        # Fallback: look for common answer patterns
        if "INSUFFICIENT_DATA" in llm_response:
            return "INSUFFICIENT_DATA"
        
        # Look for option numbers at the end of response
        for line in reversed(lines):
            line = line.strip()
            if line in ['1', '2', '3', '4']:
                return line
        
        return "UNABLE_TO_EXTRACT"
    
    def solve_questions_batch(self, questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Solve multiple questions in batch with rate limiting.
        
        Args:
            questions_data (list): List of question dictionaries
            
        Returns:
            list: List of updated question dictionaries with solutions
        """
        solved_questions = []
        
        for i, question in enumerate(questions_data):
            print(f"Solving question {i+1}/{len(questions_data)}: {question.get('id', 'Unknown ID')}")
            
            solved_question = self.solve_single_question(question)
            solved_questions.append(solved_question)
            
            # Add delay to respect rate limits
            if i < len(questions_data) - 1:  # Don't delay after the last question
                time.sleep(self.rate_limit_delay)
        
        return solved_questions
    
    def solve_and_save(self, input_file: str, output_file: str) -> None:
        """
        Load questions from JSON file, solve them, and save results.
        
        Args:
            input_file (str): Path to input JSON file
            output_file (str): Path to output JSON file
        """
        # Load questions
        with open(input_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        # Solve questions
        solved_questions = self.solve_questions_batch(questions)
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(solved_questions, f, indent=2, ensure_ascii=False)
        
        print(f"Solved {len(solved_questions)} questions and saved to {output_file}")
    
    def print_solution_summary(self, solved_questions: List[Dict[str, Any]]) -> None:
        """
        Print a summary of the solving results.
        
        Args:
            solved_questions (list): List of solved questions
        """
        total = len(solved_questions)
        solved = sum(1 for q in solved_questions if q.get('answer', 'N/A') not in ['N/A', 'ERROR'])
        na_answers = sum(1 for q in solved_questions if q.get('answer') == 'N/A')
        
        print(f"\n=== SOLUTION SUMMARY ===")
        print(f"Total questions: {total}")
        print(f"Successfully solved: {solved}")
        print(f"Unable to solve: {na_answers}")
        print(f"Success rate: {(solved/total)*100:.1f}%")


# Enhanced version with context management for DILR questions
class AdvancedExamQuestionSolver(ExamQuestionSolver):
    """
    Advanced version that can handle context-dependent DILR questions better.
    """
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.1):
        """
        Initialize with Gemini Flash for better rate limits on free tier.
        """
        super().__init__(api_key, model, temperature)
        self.question_context = {}  # Store context between related questions
        self.rate_limit_delay = 5  # Longer delay for advanced solver
    
    def group_related_questions(self, questions_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group questions that likely share the same context/passage.
        
        Args:
            questions_data (list): List of all questions
            
        Returns:
            dict: Grouped questions by context
        """
        groups = {}
        
        for question in questions_data:
            # Create a context key based on exam, year, slot, section
            context_key = f"{question.get('exam')}_{question.get('year')}_{question.get('slot')}_{question.get('section')}"
            
            if context_key not in groups:
                groups[context_key] = []
            groups[context_key].append(question)
        
        return groups
    
    def create_context_aware_prompt(self, question_data: Dict[str, Any], related_questions: List[Dict[str, Any]]) -> str:
        """
        Create a prompt that includes context from related questions.
        
        Args:
            question_data (dict): Current question
            related_questions (list): Other questions from the same context
            
        Returns:
            str: Enhanced prompt with context
        """
        prompt = self.create_solving_prompt(question_data)
        
        # Add context from related questions
        if len(related_questions) > 1:
            prompt += "\n\nRELATED QUESTIONS IN SAME CONTEXT:\n"
            for i, related_q in enumerate(related_questions):
                if related_q['id'] != question_data['id']:
                    prompt += f"Q{i+1}: {related_q.get('question_text', '')}\n"
            
            prompt += "\nNote: These questions likely share the same data/context. Use this information to better understand the problem domain.\n"
        
        return prompt
    
    def solve_questions_with_context(self, questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Solve questions with enhanced context awareness.
        
        Args:
            questions_data (list): List of question dictionaries
            
        Returns:
            list: List of solved questions
        """
        # Group related questions
        grouped_questions = self.group_related_questions(questions_data)
        solved_questions = []
        
        for context_key, questions_group in grouped_questions.items():
            print(f"\nSolving question group: {context_key} ({len(questions_group)} questions)")
            
            for i, question in enumerate(questions_group):
                print(f"  Solving question {i+1}/{len(questions_group)}: {question.get('id', 'Unknown ID')}")
                
                # Create context-aware prompt
                enhanced_prompt = self.create_context_aware_prompt(question, questions_group)
                
                # Solve with enhanced context
                try:
                    response = self.model.generate_content(
                        enhanced_prompt,
                        generation_config=self.generation_config
                    )
                    
                    llm_response = response.text.strip()
                    answer = self.extract_answer_from_response(llm_response)
                    
                    # Update question data
                    updated_question = question.copy()
                    updated_question['answer'] = answer
                    updated_question['llm_analysis'] = llm_response
                    updated_question['solved_by_llm'] = True
                    updated_question['solve_timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
                    updated_question['model_used'] = "gemini-context-aware"
                    updated_question['context_group'] = context_key
                    
                    solved_questions.append(updated_question)
                    
                except Exception as e:
                    error_question = question.copy()
                    error_question['answer'] = "ERROR"
                    error_question['llm_error'] = str(e)
                    error_question['solved_by_llm'] = False
                    error_question['model_used'] = "gemini-context-aware"
                    solved_questions.append(error_question)
                
                # Rate limiting
                if i < len(questions_group) - 1:
                    time.sleep(self.rate_limit_delay)
        
        return solved_questions


def solve_questions_from_file(input_file_path: str, output_file_path: str = None, api_key: str = None, use_advanced: bool = True):
    """
    Load questions from JSON file, solve them, and save back to file.
    
    Args:
        input_file_path (str): Path to input JSON file containing questions
        output_file_path (str, optional): Path to save solved questions. If None, overwrites input file
        api_key (str, optional): Google AI API key. If None, tries to get from environment
        use_advanced (bool): Whether to use advanced context-aware solver (default: True)
    """
    # Get API key
    if api_key is None:
        api_key = os.getenv('GOOGLE_AI_API_KEY')
        if api_key is None:
            raise ValueError("API key not provided. Set GOOGLE_AI_API_KEY environment variable or pass api_key parameter")
    
    # Set output file path
    if output_file_path is None:
        output_file_path = input_file_path
    
    try:
        # Load questions from file
        print(f"Loading questions from: {input_file_path}")
        with open(input_file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        print(f"Loaded {len(questions)} questions")
        
        # Initialize solver
        if use_advanced:
            print("Using advanced context-aware Gemini solver...")
            solver = AdvancedExamQuestionSolver(api_key)
            solved_questions = solver.solve_questions_with_context(questions)
        else:
            print("Using basic Gemini solver...")
            solver = ExamQuestionSolver(api_key)
            solved_questions = solver.solve_questions_batch(questions)
        
        # Print summary
        solver.print_solution_summary(solved_questions)
        
        # Save results
        print(f"Saving solved questions to: {output_file_path}")
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(solved_questions, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully saved {len(solved_questions)} solved questions!")
        return solved_questions
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file_path}' not found")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{input_file_path}'")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def main():
    """
    Example usage of the ExamQuestionSolver with Gemini using file input/output.
    """
    # Solve questions from file and save to output file
    solve_questions_from_file(
        input_file_path="/Users/vaibhav.yadav/Documents/Course/OELP/app_data/structured_questions/CAT_DILR.json",
        output_file_path="/Users/vaibhav.yadav/Documents/Course/OELP/app_data/structured_questions/CAT_DILR_solved.json",
        api_key=""  # Replace with your API key
    )


if __name__ == "__main__":
    main()