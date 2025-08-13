import os
import sys
import json
from pathlib import Path
import google.generativeai as genai
from typing import List, Dict, Optional, Any
import argparse
from dotenv import load_dotenv

load_dotenv()

def load_config():
    """Load configuration from environment and defaults"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: Please set GOOGLE_API_KEY environment variable")
        print("   Example: export GOOGLE_API_KEY='your-api-key-here'")
        print("   Or create a .env file with: GOOGLE_API_KEY=your-api-key-here")
        return None
    
    config = {
        "google_api_key": api_key,
        "model_name": os.getenv("MODEL_NAME", "gemini-1.5-flash"),
        "max_tokens": int(os.getenv("MAX_TOKENS", "2000")),
        "temperature": float(os.getenv("TEMPERATURE", "0.1"))
    }
    
    return config

def setup_api(config):
    """Setup Google AI API with config"""
    genai.configure(api_key=config["google_api_key"])
    return True

def generate_persona_prompt(description, config, model):
    meta_prompt = (
        f"You are  a helfpul AI assistant skilled in prompt engineering\n"
        f"Given this persona description, generate a step by step code review prompt template."
        f"Persona description: {description}\n\n"
        f"Make sure to include sections like focus areas, methodology, output format, and examples."
    )

    try:
        response = model.generate_content(
            meta_prompt, 
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=config["max_tokens"],
                temperature=config["temperature"],
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating persona prompt: {e}")
        return ""
    
class CodeReviewPersona:
    def __init__(self, name: str, config, focus: str, prompt_template= None, description=None):
        self.name = name
        self.focus = focus
        self.config = config
        self.model = genai.GenerativeModel(config['model_name'])

        if prompt_template:
            self.prompt_template = prompt_template
        elif description:
            print(f"Generating a prompt template for {self.name} using meta-prompting")
            self.prompt_template = generate_persona_prompt(description, self.config, self.model)
        else:
            raise ValueError(f"Either prompt template or description must be provided.")
        
    def review_code(self, code_diff: str) -> Dict:
        """Review code from this persona's perspective"""
        full_prompt = self.prompt_template.format(code_diff=code_diff)
        
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.config["max_tokens"],
                    temperature=self.config["temperature"],
                )
            )
            return {
                "persona": self.name,
                "focus": self.focus,
                "review": response.text,
                "status": "success"
            }
        except Exception as e:
            return {
                "persona": self.name,
                "focus": self.focus,
                "review": f"Error during review: {str(e)}",
                "status": "error"
            }

class CodeReviewEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.personas = self._initialize_personas()
    
    def _initialize_personas(self) -> List[CodeReviewPersona]:
        """Define review personas with advanced prompting methodologies"""
        personas = [
            CodeReviewPersona(
                name="Code Quality Specialist",
                focus="Code maintainability and best practices",
                prompt_template="""You are a Senior Software Engineer specializing in code quality assessment with extensive experience in enterprise software development. Your responsibility is to conduct thorough maintainability and best practices analysis.

**Analysis Methodology:**
Execute your review using the following systematic approach:
1. Structural Assessment: Evaluate function complexity, nesting depth, and code organization
2. Naming Convention Analysis: Assess variable, function, and class naming clarity
3. Best Practices Compliance: Verify adherence to language-specific standards and patterns
4. Maintainability Impact Assessment: Determine long-term implications of current implementation

Code Under Review:
{code_diff}

**Required Output Format:**
For each identified issue, provide:
1. SEVERITY CLASSIFICATION (🔴 Critical, 🟡 Warning, ℹ️ Info) with CONFIDENCE LEVEL (0-100%)
2. Detailed technical explanation of the maintainability concern
3. Business impact assessment and recommended remediation steps
4. Complete code example demonstrating the proposed solution
5. Knowledge validation question related to the underlying software engineering principle

Maintain professional technical standards and provide actionable recommendations.""",
                config=self.config
            ),
            
            CodeReviewPersona(
                name="Bug Hunter",
                focus="Potential bugs and edge cases",
                prompt_template="""You are a Senior Quality Assurance Engineer and Security Specialist with expertise in identifying software defects and vulnerability patterns. Your mandate is to conduct comprehensive defect analysis and risk assessment.

**Systematic Defect Analysis Process:**
Apply the following structured methodology:
1. Input Validation Assessment: Analyze handling of null, empty, and malformed inputs
2. Exception Handling Evaluation: Verify comprehensive error management and recovery
3. Resource Management Review: Assess memory usage, connection handling, and cleanup procedures
4. Logic Correctness Verification: Identify algorithmic errors and boundary condition failures
5. Concurrency Safety Analysis: Evaluate thread safety and race condition susceptibility

Code Under Review:
{code_diff}

**Required Output Format:**
For each identified defect, provide:
1. SEVERITY CLASSIFICATION (🔴 Critical, 🟡 Warning, ℹ️ Info) with CONFIDENCE ASSESSMENT (0-100%)
2. Defect category and specific failure conditions
3. Security implications and potential exploitation vectors
4. Detailed reproduction steps for verification
5. Complete remediation implementation with defensive programming practices
6. Quality assurance testing recommendations

Execute thorough analysis maintaining enterprise-grade quality standards.""",
                config=self.config
            )
        ]
        return personas
    
    def review_code(self, code_diff: str, selected_personas: List[str] = None, file_path: str = None) -> List[Dict]:
        """Run code through selected personas and collect reviews"""
        reviews = []
        
        
        if selected_personas is None:
            personas_to_run = self.personas
        else:
            personas_to_run = [p for p in self.personas if p.name.lower() in [s.lower() for s in selected_personas]]
            
            if not personas_to_run:
                print(f"Warning: No matching personas found for {selected_personas}")
                return reviews
        
        print(f"🔍 Starting review with {len(personas_to_run)} persona(s)...")
        
        for persona in personas_to_run:
            print(f"⚡ Running {persona.name} review...")
            review = persona.review_code(code_diff)
            reviews.append(review)
        
        return reviews
    
    def list_available_personas(self) -> None:
        """List all available personas"""
        print("📋 Available personas:")
        for i, persona in enumerate(self.personas, 1):
            print(f"  {i}. {persona.name} - {persona.focus}")
        print()
        print("Usage examples:")
        print("  --personas 'code quality'")
        print("  --personas 'bug hunter'")
        print("  --personas 'code quality' 'bug hunter'  # Run both")
    
    def format_reviews(self, reviews: List[Dict]) -> str:
        """Format all reviews into a readable report with summary stats"""
        report = "# 🔍 Multi-Persona Code Review Report\n\n"
        
        # Summary stats
        total_reviews = len([r for r in reviews if r["status"] == "success"])
        error_count = len([r for r in reviews if r["status"] == "error"])
        
        report += f"📊 **Review Summary:**\n"
        report += f"- ✅ Successful reviews: {total_reviews}\n"
        report += f"- ❌ Failed reviews: {error_count}\n\n"
        report += "---\n\n"
        
        for review in reviews:
            if review["status"] == "success":
                report += f"## 🤖 {review['persona']} - {review['focus']}\n\n"
                report += f"{review['review']}\n\n"
                report += "---\n\n"
            else:
                report += f"## ❌ {review['persona']} - ERROR\n\n"
                report += f"{review['review']}\n\n"
                report += "---\n\n"
        
        return report

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='🔍 AI-powered code review tool')
    parser.add_argument('--personas', nargs='*', 
                       help='Select specific personas to run (e.g., "code quality" "bug hunter")')
    parser.add_argument('--list-personas', action='store_true',
                       help='List all available personas')
    parser.add_argument('--file', type=str,
                       help='Review a specific file')
    parser.add_argument('--quiet', action='store_true',
                       help='Minimal output, just show the report')
    parser.add_argument('--description', type=str,
                        help='Natural language description for a dynamic persona')
    parser.add_argument('--name', type=str, default='Custom Persona',
                        help='Name for the dynamic persona (only if using --description)')
    parser.add_argument('--focus', type=str, default='Custom review focus',
                        help='Short focus area for the dynamic persona')
    
    return parser.parse_args()

def read_file_content(file_path: str) -> str:
    """Read content from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found")
        return None
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None

def main():
    args = parse_arguments()
    
    # Load configuration
    config = load_config()
    if config is None:
        return
    
    # Setup API
    setup_api(config)
    
    # Initialize the review engine
    engine = CodeReviewEngine(config)
    
    if args.description:
        engine.personas.append(CodeReviewPersona(name=args.name,
                focus=args.focus,
                description=args.description, 
                config=config))
    
    # Handle list personas command
    if args.list_personas:
        engine.list_available_personas()
        return
    
    # Determine code input and file path
    code_content = None
    file_path = None
    
    if args.file:
        if not args.quiet:
            print(f"📄 Reading file: {args.file}")
        code_content = read_file_content(args.file)
        file_path = args.file
        if code_content is None:
            return
    else:
        # Use sample code if no input specified
        code_content = """
def process_user_input(user_input):
    # New function to process user data
    result = eval(user_input)  # Potential security issue
    return result

def calculate_total(items):
    total = 0
    for i in range(len(items)):  # Performance issue - inefficient loop
        total += items[i]
    return total

class DataProcessor:
    def process_data_with_long_function_name_that_does_too_many_things(self, data1, data2, data3, data4, data5, data6):
        # This function has too many parameters
        if data1:
            if data2:
                if data3:
                    if data4:
                        if data5:
                            # Deep nesting issue
                            return data1 + data2 + data3 + data4 + data5
        return 0
        """
        file_path = "sample.py"
        if not args.quiet:
            print("📝 No input file specified, using sample code...")
    
    # Run the review with selected personas
    reviews = engine.review_code(code_content, args.personas, file_path)
    
    if not reviews:
        print("❌ No reviews generated.")
        return
    
    # Format and display results
    formatted_report = engine.format_reviews(reviews)
    print(formatted_report)
    
    # Save to file
    output_filename = "review_report.txt"
    with open(output_filename, "w") as f:
        f.write(formatted_report)
    
    if not args.quiet:
        print(f"💾 Review report saved to {output_filename}")

if __name__ == "__main__":
    main()