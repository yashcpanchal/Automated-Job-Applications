from typing import List, Dict, Any, Optional, Tuple, NamedTuple
import numpy as np
from models.job import Job
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
import math
import heapq
from sklearn.metrics.pairwise import cosine_similarity
from collections import namedtuple

from services.pdf_processing.parse_resume import parse_job_description
from dependencies.embedding_model import get_embedding_model
from services.ranking.location import get_location_coordinates, compute_proximity_score
from models.user import User

# Define a named tuple to store job scores
JobScore = namedtuple('JobScore', ['job', 'score', 'resume_similarity', 'prompt_similarity', 
                                 'skill_overlap', 'experience_match'])


# Experience level constants
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
    model: Any,
    filter_params: Optional[Dict[str, Any]] = None
) -> List[Job]:
    """
    Ranks and filters jobs based on resume text and search prompt.
    
    Args:
        jobs: List of Job objects to be ranked and filtered
        resume_text: The text content of the user's resume
        search_prompt: The search prompt to match against job titles and descriptions
        model: The embedding model for encoding
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
        # Ensure weights are defined in filter_params
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
    from services.pdf_processing.parse_resume import parse_resume
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
    
    for job in jobs:
        # Skip if job doesn't meet basic criteria
        if not hasattr(job, 'description') or not job.description:
            continue
            
        # Parse the job description
        parsed_job = parse_job_description(job.description)
        
        # If job doesn't have an embedding, generate one
        if not hasattr(job, 'description_embedding') or not job.description_embedding:
            job.description_embedding = model.encode(job.description).tolist()
        
        # Calculate similarity between resume and job description
        resume_similarity = calculate_similarity(resume_embedding, job.description_embedding)
        
        # Calculate prompt similarity if search prompt was provided
        prompt_similarity = 0.0
        if prompt_embedding:
            if not hasattr(job, 'title_embedding') or not job.title_embedding:
                job.title_embedding = model.encode(job.title).tolist()
            prompt_similarity = calculate_similarity(prompt_embedding, job.title_embedding)
        
        # Calculate skill overlap
        resume_skills = set(parsed_resume.get('skills', []))
        job_skills = set(parsed_job.get('skills', []))
        skill_overlap = len(resume_skills.intersection(job_skills)) / max(len(job_skills), 1)
        
        # Calculate experience level match
        resume_exp = parsed_resume.get('experience_level', 'not specified')
        job_exp = parsed_job.get('experience_level', 'not specified')
        exp_match = 1.0 if resume_exp == job_exp else 0.0
        
        # Calculate overall score with weights
        weights = {
            'resume_similarity': 0.5,
            'prompt_similarity': 0.2,
            'skill_overlap': 0.2,
            'experience_match': 0.1
        }
        
        overall_score = (
            resume_similarity * weights['resume_similarity'] +
            prompt_similarity * weights['prompt_similarity'] +
            skill_overlap * weights['skill_overlap'] +
            exp_match * weights['experience_match']
        )
        
        # Skip jobs that don't meet the minimum score threshold
        if overall_score < filter_params.get('role_relevance_threshold', 0.0):
            continue
            
        # Create a JobScore object to store the job and its scores
        job_score = JobScore(
            job=job,
            score=overall_score,
            resume_similarity=resume_similarity,
            prompt_similarity=prompt_similarity,
            skill_overlap=skill_overlap,
            experience_match=exp_match
        )
        
        # Apply salary filters if salary is available
        if hasattr(job, 'salary') and job.salary is not None:
            if job.salary < filter_params.get('min_salary', 0):
                continue
            if job.salary > filter_params.get('max_salary', float('inf')):
                continue
        
        # Use a min-heap to efficiently keep track of top k jobs
        # We store negative scores since Python's heapq is a min-heap
        if len(top_k_heap) < k:
            heapq.heappush(top_k_heap, (overall_score, job_score))
        else:
            # If current job is better than the worst in heap, replace it
            if overall_score > top_k_heap[0][0]:
                heapq.heappop(top_k_heap)
                heapq.heappush(top_k_heap, (overall_score, job_score))

        # Non-linear boost for prompt similarity if it exceeds the threshold
        if prompt_embedding is not None and prompt_similarity > filter_params['prompt_boost_threshold']:
            prompt_similarity *= filter_params['prompt_boost_factor']
            prompt_similarity = min(prompt_similarity, 1.0)

        # Calculate skill overlap as the Jaccard similarity between the skills in the resume and job description
        resume_skills_set = set(parsed_resume['skills'])
        job_skills_set = set(parsed_job['skills'])
        skill_overlap = len(resume_skills_set.intersection(job_skills_set)) / max(len(resume_skills_set), len(job_skills_set), 1)

        resume_experience_level = EXPERIENCE_LEVELS.get(parsed_resume['experience_level'], -1)
        job_experience_level = EXPERIENCE_LEVELS.get(parsed_job['experience_level'], -1)

        # Ensure experience levels are comparable
        if resume_experience_level == -1 and job_experience_level == -1:
            experience_match = 1.0  # Both 'not specified', considered a perfect match in this context
        elif resume_experience_level == -1 or job_experience_level == -1:
            experience_match = 0.5  # One is 'not specified', the other is a defined level
        else:
            # Add a sigmoid decay to penalize large differences in experience levels
            experience_diff = abs(resume_experience_level - job_experience_level)
            experience_match = 1 - math.log2(1 + experience_diff) / math.log2(1 + MAX_EXPERIENCE_DIFF)

        # Calculate the job description match score (same as resume similarity)
        job_description_match = resume_similarity
        
        # Default proximity score (will be overridden if location is available)
        proximity_score = 0.3
        
        # Try to get location-based proximity score if location is available
        try:
            if hasattr(job, 'location') and job.location:
                user_coordinates = await get_location_coordinates(parsed_resume.get('location', ''))
                job_coordinates = await get_location_coordinates(job.location)
                if user_coordinates and job_coordinates:
                    proximity_score = compute_proximity_score(user_coordinates, job_coordinates)
        except Exception as e:
            print(f"Error calculating proximity score: {e}")
        
        # Calculate the final score using the weights from filter_params
        try:
            # Role relevance penalty: comparing job title to resume and the search prompt
            role_relevance = 1.0
            
            # Check title-prompt similarity if possible
            if prompt_embedding is not None and hasattr(job, 'title_embedding') and job.title_embedding is not None:
                title_prompt_similarity = calculate_similarity(prompt_embedding, job.title_embedding)
                if title_prompt_similarity < filter_params['role_relevance_threshold']:
                    role_relevance -= (1.0 - title_prompt_similarity) * filter_params['role_relevance_boost_factor']
                    role_relevance = max(role_relevance, 0.0)  # Ensure it doesn't go negative
            
            # Check title-resume similarity if possible
            if hasattr(job, 'title_embedding') and job.title_embedding is not None and resume_embedding is not None:
                title_resume_similarity = calculate_similarity(resume_embedding, job.title_embedding)
                if title_resume_similarity < filter_params['role_relevance_threshold']:
                    role_relevance -= (1.0 - title_resume_similarity) * filter_params['role_relevance_boost_factor']
                    role_relevance = max(role_relevance, 0.0)  # Ensure it doesn't go negative
            
            # Calculate the base score using the weights from filter_params
            weights = filter_params.get('weights', {})
            base_score = (
                weights.get('resume_match', 0.4) * resume_similarity + 
                weights.get('prompt_match', 0.3) * prompt_similarity +
                weights.get('skill_overlap', 0.2) * skill_overlap +
                weights.get('experience_match', 0.1) * experience_match + 
                weights.get('job_description_match', 0.4) * job_description_match + 
                weights.get('proximity_score', 0.3) * proximity_score
            )
            
            # Apply the role relevance penalty
            score = base_score * role_relevance
            score = float(score)
            
            # Apply the minimum overall score filter
            if score < filter_params.get('min_overall_score', 0.0):
                continue
                
        except Exception as e:
            print(f"Error calculating job score: {e}")
            # If there's an error in score calculation, skip this job
            continue

    # Convert the heap to a sorted list in descending order
    sorted_job_scores = []
    while top_k_heap:
        score, job_score = heapq.heappop(top_k_heap)
        sorted_job_scores.append((job_score, score))
    
    # Sort by score in descending order
    sorted_job_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Extract just the jobs in order of their scores
    return [job_score.job for job_score, _ in sorted_job_scores]
