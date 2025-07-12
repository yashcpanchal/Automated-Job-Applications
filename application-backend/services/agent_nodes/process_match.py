from models.agent_models.agent_state import AgentState
from services.rank_and_filter_jobs import rank_and_filter_jobs
from models.job import Job
from dependencies.embedding_model import get_embedding_model


async def process_and_match_node(state: AgentState) -> dict:
    """
    Node 3: Filters the extracted jobs for relevance against the user's resume.
    """
    print("--- NODE: PROCESSING AND MATCHING JOBS ---")

    extracted_jobs = state['extracted_jobs']
    if not extracted_jobs:
        print("INFO: No jobs extracted to process.")
        return {"final_jobs": []}
    
    resume_text = state['resume_text']
    if not resume_text:
        print("ERROR: No resume text provided for matching.")
        return {"final_jobs": []}
    
    search_prompt = state['search_prompt']
    if not search_prompt:
        print("ERROR: No search prompt provided for matching.")
        return {"final_jobs": []}
    
    # TODO: Implement the final filtering logic.
    # This is where we could use semantic search (vector similarity) to compare
    # each job description to the user's resume text.
    print(f"INFO: Processing {len(extracted_jobs)} extracted jobs...")

    # Initialize the embedding model
    embedding_model = get_embedding_model()

    # Rank and filter jobs based on the resume and search prompt
    ranked_and_filtered_jobs = rank_and_filter_jobs(
        jobs=extracted_jobs,
        resume_text=resume_text,
        search_prompt=search_prompt,
        model=embedding_model
    )

    print(f"INFO: Finished processing. Found {len(ranked_and_filtered_jobs)} relevant jobs.")

    # Update the state with the final jobs
    state['extracted_jobs'] = ranked_and_filtered_jobs



    # For now, we'll just assume all extracted jobs are relevant.
    return {"final_jobs": state['extracted_jobs']}
