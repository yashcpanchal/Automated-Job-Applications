import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Optional
from models.job import Job
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
import uuid
from spacy.matcher import PhraseMatcher
from dependencies.embedding_model import get_embedding_model
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import math

# Initialize the geolocator for reverse geocoding
geolocator = Nominatim(user_agent="job_search_agent")
# Cache for locations to avoid repeated geocoding
location_cache = {}

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading en_core_web_sm model.")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

SKILLS_FILE_PATH = "extracted_skills_improved.txt"
skill_phrases = []
try:
    with open(SKILLS_FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            # Clean each line: strip leading/trailing whitespace, remove quotes if present, and convert to lowercase
            skill = line.strip().strip('",').lower()
            if skill: # Only add if the cleaned line is not empty
                skill_phrases.append(skill)
except FileNotFoundError:
    print(f"Error: The skills file '{SKILLS_FILE_PATH}' was not found.")
# Create a PhraseMatcher to match skill phrases and make doc objects for each phrase
patterns = [nlp.make_doc(phrase) for phrase in skill_phrases]
matcher.add("SKILLS", patterns)

EXPERIENCE_LEVELS = {
    "internship": 0, 
    "entry-level": 1,
    "mid-level": 2,
    "senior": 3,
    "lead": 4,
    "not specified": -1
}

MAX_EXPERIENCE_DIFF = 4

def get_location_coordinates(location_name: str) -> Optional[tuple[float, float]]:
    """
    Retrieves latitude and longitude for specified location

    Args:
        location_name (str): The name of the location to geocode.

    Returns:
        Optional[tuple[float, float]]: A tuple containing latitude and longitude if found,
                                       otherwise None.
    """
    if not location_name:
        return None
    if location_name.lower() in location_cache:
        # Check if already cached
        return location_cache[location_name.lower()]
    try:
        # Use geopy to get the coordinates
        location = geolocator.geocode(location_name)
        if location:
            coords = (location.latitude, location.longitude)
            location_cache[location_name.lower()] = coords
            return coords
        else:
            return None
    except Exception as e:
        print(f"Error geocoding location '{location_name}': {e}")
        return None

def compute_proximity_score(user_coordinates, job_coordinates, decay_factor=0.2):
    """
    Computes a proximity score based on the distance between user and job coordinates.
    Args:
        user_coordinates (tuple): A tuple containing the user's latitude and longitude.
        job_coordinates (tuple): A tuple containing the job's latitude and longitude.
        decay_factor (float): The factor by which the score decays with distance.
    Returns:
        float: A proximity score between 0 and 1, where 1 means the job is at the user's location.
    """
    if not user_coordinates or not job_coordinates:
        return 0.3
    distance = geodesic(user_coordinates, job_coordinates).kilometers
    # Closer the job, higher the score; decays exponentially with distance
    score = math.exp(-decay_factor * distance)
    return max(0.0, min(score, 1.0))

def parse_resume(resume_text: str) -> Dict[str, Any]:
    """
    Parses resume text to extract skills 
    Returns a dictionary with skills and other relevant information.
    """

    doc = nlp(resume_text.lower())
    skills = []
    for match_id, start, end in matcher(doc):
        span = doc[start:end]
        skills.append(span.text)
    
    # Remove duplicates by converting to a set and back to a list
    skills = list(set(skills))
    
    experience_level = "not specified"
    # Prioritize internship detection
    if any(term in doc.text for term in ["intern", "internship", "collegiate", "student"]):
        experience_level = "internship"
    # Then check for general entry-level terms if not already classified as internship
    elif any(term in doc.text for term in ["entry-level", "junior", "new grad"]):
        experience_level = "entry_level" # Corrected from "entry-level" to "entry_level" for consistency
    elif any(term in doc.text for term in ["mid-level", "3+ years"]):
        experience_level = "mid-level"
    elif any(term in doc.text for term in ["senior", "5+ years", "sr."]): # 'lead', 'staff', 'principal' could imply lead tier
        experience_level = "senior"
    elif any(term in doc.text for term in ["lead", "staff", "principal"]): # Explicitly capture lead tier
        experience_level = "lead"
    
    return {
        "raw_text": resume_text,
        "skills": skills,
        "experience_level": experience_level,
    }

def parse_job_description(job_description: str):
    """
    Parses job description text to extract skills 
    Returns a dictionary with skills and other relevant information.
    """

    doc = nlp(job_description.lower())
    skills = []
    for match_id, start, end in matcher(doc):
        span = doc[start:end]
        skills.append(span.text)
    
    # Remove duplicates by converting to a set and back to a list
    skills = list(set(skills))
    
    experience_level = "not specified"
    # Prioritize internship detection
    if any(term in doc.text for term in ["intern", "internship", "collegiate", "student"]):
        experience_level = "internship"
    # Then check for general entry-level terms if not already classified as internship
    elif any(term in doc.text for term in ["entry level", "junior", "new grad"]): # Note: "entry level" with space for job descriptions
        experience_level = "entry_level" # Corrected from "entry-level" to "entry_level" for consistency
    elif any(term in doc.text for term in ["mid-level", "3+ years"]):
        experience_level = "mid-level"
    elif any(term in doc.text for term in ["senior", "5+ years", "sr."]): # 'lead', 'staff', 'principal' could imply lead tier
        experience_level = "senior"
    elif any(term in doc.text for term in ["lead", "staff", "principal"]): # Explicitly capture lead tier
        experience_level = "lead"

    job_type = "not specified"
    if "internship" in doc.text or "intern " in doc.text:
        job_type = "internship"
    elif "full-time" in doc.text or "entry-level" in doc.text or "junior" in doc.text:
        job_type = "entry_level"
    
    return {
        "raw_text": job_description.lower(),
        "skills": skills,
        "experience_level": experience_level,
        "job_type": job_type
    }

def preprocess_text(text: str) -> str:
    """
    Preprocesses text by removing extra spaces and converting to lowercase.
    """
    return text.lower().strip()

def filter_job(
    job: Job,
    parsed_resume: Dict[str, Any],
    search_prompt: str,
    filter_criteria: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Applies various filters to a single job.

    Args:
        job (Job): The job object to filter.
        parsed_resume (Dict[str, Any]): Parsed resume data.
        search_prompt (str): The original search prompt.
        filter_criteria (Dict[str, Any]): Dictionary containing filtering rules.

    Returns:
        Optional[Dict[str, Any]]: The parsed job data if it passes all filters,
                                   otherwise None.
    """
    parsed_job = parse_job_description(job.description)

    # 1. Experience level filtering
    if filter_criteria['strict_experience_match']:
        resume_exp = parsed_resume['experience_level']
        job_exp = parsed_job['experience_level']

        is_resume_junior_or_intern = (resume_exp in ["internship", "entry_level"])
        is_job_senior_or_lead = (job_exp in ["senior", "lead"])

        if (is_resume_junior_or_intern and is_job_senior_or_lead) or \
           (resume_exp in ["senior", "lead"] and (job_exp in ["internship", "entry_level"])):
            return None

    # 2. Job type preference filtering
    if filter_criteria['job_type_preference']:
        if parsed_job['job_type'] not in filter_criteria['job_type_preference'] and parsed_job['job_type'] != "not specified":
            return None # Fails job type filter

    # 3. Location based filtering
    if filter_criteria.get('location_preference') == 'remote_only':
        if job.location is None or "remote" not in job.location.lower():
            # return None # Uncomment to re-enable hard filter
            pass
    elif filter_criteria.get('location_preference') == 'local_only':
        # This is a basic string check. For strict radius filter,
        # one would check get_coordinates and geodesic distance here.
        if job.location is None or "remote" in job.location.lower():
            # return None # Uncomment to re-enable hard filter
            pass

    if filter_criteria.get('preferred_locations'):
        if job.location is None or not any(loc.lower() in job.location.lower() for loc in filter_criteria['preferred_locations']):
            # return None # Uncomment to re-enable hard filter
            pass

    # 4. Prompt-based keyword filtering
    if filter_criteria['require_prompt_keywords'] and search_prompt:
        doc_prompt = nlp(search_prompt.lower())
        prompt_keywords = {token.lemma_ for token in doc_prompt if not token.is_stop and not token.is_punct}
        doc_job_desc = nlp(job.description.lower())
        job_desc_tokens = {token.lemma_ for token in doc_job_desc if not token.is_stop and not token.is_punct}
        if not any(keyword in job_desc_tokens for keyword in prompt_keywords):
            return None # Fails prompt keyword filter

    # If all filters pass, return the parsed job data
    return parsed_job


def rank_and_filter_jobs(jobs: List[Job], resume_text: str, search_prompt: str, model: Any) -> List[Job]:
    """
    Ranks and filters jobs based on resume and search prompt.
    
    Args:
        jobs (List[Job]): List of Job objects to be ranked and filtered.
        resume_text (str): The text of the resume to match against job descriptions.
        search_prompt (str): The search prompt to match against job titles and descriptions.
        model (ModelDependency): The embedding model dependency for vectorization.
    
    Returns:
        List[Job]: A list of Job objects sorted by their relevance score, filtered based on the criteria.
    """

    weights = {
        'resume_match': 0.4,
        'prompt_match': 0.2,
        'skill_overlap': 0.15,
        'experience_match': 0.1,
        'job_description_match': 0.1,
        'proximity_score': 0.05
    }
    filter = {
        'min_overall_score': 0.1,
        'min_skill_match_percentage': 0.0,
        'strict_experience_match': True,
        'require_prompt_keywords': False,
        'job_type_preference': [],
        'location_preference': 'any',
        'preferred_locations': [],
        'prompt_boost_threshold': 0.5,
        'prompt_boost_factor': 1.2,
        'role_relevance_threshold': 0.3,
        'role_relevance_boost_factor': 0.5
    }
    
    # Parse and preprocess the resume and search prompt
    parsed_resume = parse_resume(resume_text)
    preprocessed_resume = preprocess_text(parsed_resume['raw_text'])
    preprocessed_prompt = preprocess_text(search_prompt)

    resume_encoded = model.encode(preprocessed_resume)
    prompt_encoded = model.encode(preprocessed_prompt) if preprocessed_prompt else None

    ranked_jobs_list: List[Job] = []

    # Iterate through each job and calculate its score based on the resume and search prompt
    for job in jobs:
        # parsed_job = filter_job(job, parsed_resume, search_prompt, filter)
        # if parsed_job is None:
        #     continue
        parsed_job = parse_job_description(job.description)
        if parsed_job is None:
            continue
        preprocessed_job_desc = preprocess_text(parsed_job['raw_text'])
        # First filter out jobs based on a variety of criteria
        preprocessed_job_title = preprocess_text(job.title)
            
        job_desc_encoded = model.encode(preprocessed_job_desc)
        job_title_encoded = model.encode(preprocessed_job_title)

        resume_similarity = cosine_similarity(resume_encoded.reshape(1, -1), job_desc_encoded.reshape(1, -1))[0][0]
        prompt_similarity = cosine_similarity(prompt_encoded.reshape(1, -1), job_desc_encoded.reshape(1, -1))[0][0]

        # Non-linear boost for prompt similarity if it exceeds the threshold
        if prompt_encoded is not None and prompt_similarity > filter['prompt_boost_threshold']:
            prompt_similarity *= filter['prompt_boost_factor']
            prompt_similarity = min(prompt_similarity, 1.0)
        



        # Calculate skill overlap as the Jaccard similarity between the skills in the resume and job description
        resume_skills_set = set(parsed_resume['skills'])
        job_skills_set = set(parsed_job['skills'])
        skill_overlap = len(resume_skills_set.intersection(job_skills_set)) / max(len(resume_skills_set), len(job_skills_set), 1)

        resume_experience_level = EXPERIENCE_LEVELS.get(parsed_resume['experience_level'], -1)
        job_experience_level = EXPERIENCE_LEVELS.get(parsed_job['experience_level'], -1)

        # Ensure experience levels are comparable
        if resume_experience_level == -1 and job_experience_level == -1:
            experience_match = 1.0 # Both 'not specified', considered a perfect match in this context
        elif resume_experience_level == -1 or job_experience_level == -1:
            experience_match = 0.5 # One is 'not specified', the other is a defined level
        else:
            # Add an sigmoid decay to penalize large differences in experience levels
            experience_diff = abs(resume_experience_level - job_experience_level)
            experience_match = 1 - math.log2(1 + experience_diff) / math.log2(1 + MAX_EXPERIENCE_DIFF)

        # Calculate the job description match score
        job_description_match = resume_similarity
    
        # Role relevance penalty: comparing job title to resume and the search prompt
        role_relevance = 1.0
        if prompt_encoded is not None:
            title_prompt_similarity = cosine_similarity(prompt_encoded.reshape(1, -1), job_title_encoded.reshape(1, -1))[0][0]
            if (title_prompt_similarity < filter['role_relevance_threshold']):
                role_relevance -= (1.0 - title_prompt_similarity) * filter['role_relevance_boost_factor']
                role_relevance = max(role_relevance, 0.0) # Ensure it doesn't go negative
        
        # Do the same thing above for resume
        title_resume_similarity = cosine_similarity(resume_encoded.reshape(1, -1), job_title_encoded.reshape(1, -1))[0][0]
        if (title_resume_similarity < filter['role_relevance_threshold']):
            role_relevance -= (1.0 - title_resume_similarity) * filter['role_relevance_boost_factor']
            role_relevance = max(role_relevance, 0.0) # Ensure it doesn't go negative

        # Calculate the proximity score if location is provided
        user_coordinates = get_location_coordinates(parsed_resume.get('location', ''))
        job_coordinates = get_location_coordinates(job.location) if job.location else None
        proximity_score = compute_proximity_score(user_coordinates, job_coordinates) if user_coordinates and job_coordinates else 0.3

        score = (
            weights['resume_match'] * resume_similarity + 
            weights['prompt_match'] * prompt_similarity +
            weights['skill_overlap'] * skill_overlap +
            weights['experience_match'] * experience_match + 
            weights['job_description_match'] * job_description_match + 
            weights['proximity_score'] * proximity_score
        )

        # Apply the role relevance penalty
        score *= role_relevance

        # Apply the minimum overall score filter
        if score < filter['min_overall_score']:
            continue

        job_with_score = job.model_copy(update={'score': score})
        ranked_jobs_list.append(job_with_score)

    # Sorts the jobs in a decreasing order of score
    ranked_jobs_list.sort(key=lambda x: x.score, reverse=True)
    return ranked_jobs_list
