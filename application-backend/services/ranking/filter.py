from services.util.text_processing import preprocess_text
from services.ranking.location import get_location_coordinates, compute_proximity_score
from models.job import Job
from typing import Dict, Any, Optional

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
            return None  # Fails job type filter

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
            return None  # Fails prompt keyword filter

    # If all filters pass, return the parsed job data
    return parsed_job