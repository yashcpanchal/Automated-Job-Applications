import spacy
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from spacy.matcher import PhraseMatcher
from dependencies.embedding_model import get_embedding_model
from services.util.text_processing import preprocess_text

# Initialize spaCy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading en_core_web_sm model.")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Initialize matcher
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

# Load skills from file
MODULE_DIR = Path(__file__).parent.parent / "ranking"
SKILLS_FILE_PATH = MODULE_DIR / "extracted_skills_improved.txt"

skill_phrases = []
try:
    with open(SKILLS_FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            skill = line.strip().strip('"').lower()
            if skill:
                skill_phrases.append(skill)
    print(f"Loaded {len(skill_phrases)} skills from {SKILLS_FILE_PATH}")
except FileNotFoundError:
    print(f"Error: The skills file '{SKILLS_FILE_PATH}' was not found.")
    skill_phrases = ["python", "machine learning", "data science"]
    print(f"Using default skills: {', '.join(skill_phrases)}")

# Add skill patterns to matcher
patterns = [nlp.make_doc(phrase) for phrase in skill_phrases]
matcher.add("SKILLS", patterns)

def parse_resume(resume_text: str) -> Tuple[Dict[str, Any], List[float]]:
    """
    Parse resume text to extract skills, experience level, and generate embedding.
    
    Args:
        resume_text: The text content of the resume
        
    Returns:
        Tuple containing:
        - Dictionary with parsed resume data (skills, experience_level, raw_text)
        - List of floats representing the resume embedding
    """
    # Preprocess the text first
    preprocessed_text = preprocess_text(resume_text)
    doc = nlp(preprocessed_text)
    
    # Extract skills
    skills = []
    for match_id, start, end in matcher(doc):
        span = doc[start:end]
        skills.append(span.text)
    skills = list(set(skills))  # Remove duplicates
    
    # Detect experience level
    experience_level = "not specified"
    if any(term in doc.text for term in ["intern", "internship", "collegiate", "student"]):
        experience_level = "internship"
    elif any(term in doc.text for term in ["entry-level", "junior", "new grad"]):
        experience_level = "entry_level"
    elif any(term in doc.text for term in ["mid-level", "3+ years"]):
        experience_level = "mid-level"
    elif any(term in doc.text for term in ["senior", "5+ years", "sr."]):
        experience_level = "senior"
    elif any(term in doc.text for term in ["lead", "staff", "principal"]):
        experience_level = "lead"
    
    # Generate embedding using the preprocessed text
    try:
        model = get_embedding_model()
        embedding = model.encode(preprocessed_text).tolist()
    except Exception as e:
        print(f"Error generating resume embedding: {e}")
        raise
    
    # Prepare parsed data
    parsed_data = {
        "skills": skills,
        "experience_level": experience_level,
        "raw_text": resume_text,
        "preprocessed_text": preprocessed_text
    }
    
    return parsed_data, embedding

def parse_job_description(job_description: str) -> Dict[str, Any]:
    """
    Parse job description text to extract skills and other relevant information.
    
    Args:
        job_description: The text content of the job description
        
    Returns:
        Dictionary with parsed job description data
    """
    preprocessed_text = preprocess_text(job_description)
    doc = nlp(preprocessed_text)
    
    # Extract skills
    skills = []
    for match_id, start, end in matcher(doc):
        span = doc[start:end]
        skills.append(span.text)
    skills = list(set(skills))  # Remove duplicates
    
    # Detect experience level
    experience_level = "not specified"
    if any(term in doc.text for term in ["intern", "internship"]):
        experience_level = "internship"
    elif any(term in doc.text for term in ["entry-level", "junior", "new grad"]):
        experience_level = "entry_level"
    elif any(term in doc.text for term in ["mid-level", "3+ years"]):
        experience_level = "mid-level"
    elif any(term in doc.text for term in ["senior", "5+ years", "sr."]):
        experience_level = "senior"
    elif any(term in doc.text for term in ["lead", "staff", "principal"]):
        experience_level = "lead"
    
    return {
        "skills": skills,
        "experience_level": experience_level,
        "raw_text": job_description,
        "preprocessed_text": preprocessed_text
    }

def update_user_with_resume(user, resume_text: str) -> None:
    """
    Update user object with parsed resume data and embedding.
    
    Args:
        user: The user object to update
        resume_text: The text content of the resume
    """
    try:
        parsed_data, embedding = parse_resume(resume_text)
        
        # Update user attributes
        user.resume_embedding = embedding
        # Add any other parsed data to user if needed
        # user.skills = parsed_data["skills"]
        # user.experience_level = parsed_data["experience_level"]
        
    except Exception as e:
        print(f"Error updating user with resume: {e}")
        raise