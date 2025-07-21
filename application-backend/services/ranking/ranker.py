from typing import List, Dict, Any, Optional, Tuple, NamedTuple
import numpy as np
from models.job import Job
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
import math
import heapq
from sklearn.metrics.pairwise import cosine_similarity
from collections import namedtuple
import spacy # Added for skill extraction from prompt
from spacy.matcher import PhraseMatcher # Added for skill extraction from prompt

from services.pdf_processing.parse_resume import parse_job_description, parse_resume # Ensured parse_resume is imported
from dependencies.embedding_model import get_embedding_model
from services.ranking.location import get_location_coordinates, compute_proximity_score
from models.user import User

def load_skill_keywords() -> List[str]:
    """Loads a list of skill keywords from the extracted_skills_improved.txt file."""
    import os
    file_path = os.path.join(os.path.dirname(__file__), 'extracted_skills_improved.txt')
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Warning: Skill keywords file not found at {file_path}. Skill extraction may be limited.")
        return []

try:
    nlp_for_skills = spacy.load("en_core_web_sm")
    skill_keywords_list = load_skill_keywords()
    matcher_for_skills = PhraseMatcher(nlp_for_skills.vocab)
    patterns_for_skills = [nlp_for_skills.make_doc(text) for text in skill_keywords_list]
    matcher_for_skills.add("SkillList", patterns_for_skills)
except Exception as e:
    print(f"Error loading SpaCy model or skill keywords for extraction: {e}")
    nlp_for_skills = None
    matcher_for_skills = None

def extract_skills_from_text(text: str) -> List[str]:
    """
    Extracts skills from a given text using SpaCy's PhraseMatcher and a predefined keyword list.
    """
    if nlp_for_skills and matcher_for_skills:
        doc = nlp_for_skills(text)
        matches = matcher_for_skills(doc)
        extracted_skills = [doc[start:end].text for match_id, start, end in matches]
        return list(set(extracted_skills)) # Return unique skills
    else:
        return []


JobScore = namedtuple('JobScore', ['job', 'score', 'resume_similarity', 'prompt_similarity', 
                                 'skill_overlap', 'experience_match'])


EXPERIENCE_LEVELS = {
    "internship": 0, 
    "entry_level": 1,
    "mid-level": 2,
    "senior": 3,
    "lead": 4,
    "not specified": -1
}

MAX_EXPERIENCE_DIFF = 4

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score between the two embeddings
    """
    if not embedding1 or not embedding2:
        return 0.0
        
    # Convert to numpy arrays if they're not already
    emb1 = np.array(embedding1).reshape(1, -1)
    emb2 = np.array(embedding2).reshape(1, -1)
    
    return cosine_similarity(emb1, emb2)[0][0]


async def rank_and_filter_jobs(
    jobs: List[Job], 
    resume_text: str, 
    search_prompt: str, 
    model: Any, # This is your embedding model (e.g., from get_embedding_model)
    filter_params: Optional[Dict[str, Any]] = None
) -> List[Job]:
    """
    Ranks and filters jobs based on resume text and search prompt.
    
    Args:
        jobs: List of Job objects to be ranked and filtered
        resume_text: The text content of the user's resume
        search_prompt: The search prompt to match against job titles and descriptions
        model: The embedding model for encoding (e.g., SentenceTransformer model)
        filter_params: Dictionary of filter parameters
        
    Returns:
        List of Job objects sorted by relevance score
    """
    if not jobs:
        return []

    # Default filter parameters if not provided
    if filter_params is None:
        filter_params = {
            'max_distance_km': 50,
            'remote_ok': True,
            'min_salary': 0,
            'max_salary': float('inf'),
            'job_type': 'any',
            'experience_level': 'any',
            'location_preference': 'any',
            'preferred_locations': [],
            'prompt_boost_threshold': 0.5,
            'prompt_boost_factor': 1.2,
            'role_relevance_threshold': 0.3,
            'role_relevance_boost_factor': 0.5,
            'min_overall_score': 0.0,
            'weights': {
                'resume_match': 0.4,
                'prompt_match': 0.3,
                'skill_overlap': 0.2,
                'experience_match': 0.1,
                'job_description_match': 0.4,
                'proximity_score': 0.3
            }
        }
    else:
        if 'weights' not in filter_params:
            filter_params['weights'] = {
                'resume_match': 0.4,
                'prompt_match': 0.3,
                'skill_overlap': 0.2,
                'experience_match': 0.1,
                'job_description_match': 0.4,
                'proximity_score': 0.3
            }
    
    # Parse the resume to get skills and experience level
    parsed_resume, resume_embedding = parse_resume(resume_text)
    
    # Generate embedding for the resume if not already available
    if not resume_embedding:
        resume_embedding = model.encode(resume_text).tolist()
    
    # Encode the search prompt if provided
    prompt_embedding = None
    if search_prompt:
        try:
            prompt_embedding = model.encode(search_prompt).tolist()
        except Exception as e:
            print(f"Error encoding search prompt: {e}")
            prompt_embedding = None

    # Parse job descriptions and calculate similarities using a min-heap for top 100 jobs
    top_k_heap = []
    k = 100
    
    # Extract required skills semantically from the search prompt
    # This replaces the need for 'required_skills' in filter_params for skill matching
    required_skills_from_prompt = extract_skills_from_text(search_prompt)


    for job in jobs:
        if not hasattr(job, 'description') or not job.description:
            continue

        parsed_job = parse_job_description(job.description)
        
        if not hasattr(job, 'description_embedding') or not job.description_embedding:
            job.description_embedding = model.encode(job.description).tolist()
        
        resume_similarity = calculate_similarity(resume_embedding, job.description_embedding)
        

        prompt_similarity = 0.0
        if prompt_embedding:
            if not hasattr(job, 'title_embedding') or not job.title_embedding:
                job.title_embedding = model.encode(job.title).tolist()
            prompt_similarity = calculate_similarity(prompt_embedding, job.title_embedding)
        
        # Semantic skill overlap
        skill_overlap_score = 0.0
        if required_skills_from_prompt and job.description_embedding:
            required_skills_text_combined = ", ".join(required_skills_from_prompt)
            if required_skills_text_combined:
                required_skills_embedding = model.encode(required_skills_text_combined).tolist()
                skill_overlap_score = calculate_similarity(required_skills_embedding, job.description_embedding)
        
        resume_exp = parsed_resume.get('experience_level', 'not specified')
        job_exp = parsed_job.get('experience_level', 'not specified')
        

        if resume_exp == 'not specified' and job_exp == 'not specified':
            experience_match = 1.0
        elif resume_exp == 'not specified' or job_exp == 'not specified':
            experience_match = 0.5
        else:
            resume_experience_level = EXPERIENCE_LEVELS.get(resume_exp, -1)
            job_experience_level = EXPERIENCE_LEVELS.get(job_exp, -1)
            
            # Add a sigmoid decay to penalize large differences in experience levels
            experience_diff = abs(resume_experience_level - job_experience_level)
            experience_match = 1 - math.log2(1 + experience_diff) / math.log2(1 + MAX_EXPERIENCE_DIFF)
            
        # Calculate the job description match score
        job_description_match = resume_similarity
        
        # Default proximity score
        proximity_score = 0.3

        try:
            if hasattr(job, 'location') and job.location:
                user_coordinates = await get_location_coordinates(parsed_resume.get('location', ''))
                job_coordinates = await get_location_coordinates(job.location)
                if user_coordinates and job_coordinates:
                    proximity_score = compute_proximity_score(user_coordinates, job_coordinates)
        except Exception as e:
            print(f"Error calculating proximity score: {e}")
        
        try:
            role_relevance = 1.0
            
            if prompt_embedding is not None and hasattr(job, 'title_embedding') and job.title_embedding is not None:
                title_prompt_similarity = calculate_similarity(prompt_embedding, job.title_embedding)
                if title_prompt_similarity < filter_params['role_relevance_threshold']:
                    role_relevance -= (1.0 - title_prompt_similarity) * filter_params['role_relevance_boost_factor']
                    role_relevance = max(role_relevance, 0.0)
            
            if hasattr(job, 'title_embedding') and job.title_embedding is not None and resume_embedding is not None:
                title_resume_similarity = calculate_similarity(resume_embedding, job.title_embedding)
                if title_resume_similarity < filter_params['role_relevance_threshold']:
                    role_relevance -= (1.0 - title_resume_similarity) * filter_params['role_relevance_boost_factor']
                    role_relevance = max(role_relevance, 0.0)
            
            weights = filter_params.get('weights', {})
            overall_score = (
                weights.get('resume_match', 0.4) * resume_similarity + 
                weights.get('prompt_match', 0.3) * prompt_similarity +
                weights.get('skill_overlap', 0.2) * skill_overlap_score +
                weights.get('experience_match', 0.1) * experience_match + 
                weights.get('job_description_match', 0.4) * job_description_match + 
                weights.get('proximity_score', 0.3) * proximity_score
            )
            
            # Apply the role relevance penalty
            score = overall_score * role_relevance
            score = float(score)
            
            # Apply the minimum overall score filter
            if score < filter_params.get('min_overall_score', 0.0):
                continue
                
            # Create a JobScore object to store the job and its scores
            job_score = JobScore(
                job=job,
                score=score, # Use the final calculated score
                resume_similarity=resume_similarity,
                prompt_similarity=prompt_similarity,
                skill_overlap=skill_overlap_score,
                experience_match=experience_match
            )
            
            # Use a min-heap to efficiently keep track of top k jobs
            if len(top_k_heap) < k:
                heapq.heappush(top_k_heap, (score, job_score))
            else:
                # If current job is better than the worst in heap, replace it
                if score > top_k_heap[0][0]:
                    heapq.heappop(top_k_heap)
                    heapq.heappush(top_k_heap, (score, job_score))

        except Exception as e:
            print(f"Error calculating job score for job {getattr(job, 'id', 'N/A')}: {e}")
            # If there's an error in score calculation, skip this job
            continue

    # Convert the heap to a sorted list in descending order
    sorted_job_scores = []
    while top_k_heap:
        score, job_score_obj = heapq.heappop(top_k_heap)
        sorted_job_scores.append((job_score_obj, score))
    
    # Sort by score in descending order (already effectively sorted by heap popping, but explicit for clarity)
    sorted_job_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Extract just the jobs in order of their scores
    return [job_score_obj.job for job_score_obj, _ in sorted_job_scores]