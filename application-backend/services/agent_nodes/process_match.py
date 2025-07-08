from models.agent_state import AgentState

async def process_and_match_node(state: AgentState):
    """
    Node 3: Filters the extracted jobs for relevance against the user's resume.
    """
    print("--- NODE: PROCESSING AND MATCHING JOBS ---")
    
    # TODO: Implement the final filtering logic.
    # This is where we could use semantic search (vector similarity) to compare
    # each job description to the user's resume text.
    print("INFO: Filtering jobs for relevance (mock implementation)...")
    
    # For now, we'll just assume all extracted jobs are relevant.
    return {"final_jobs": state['extracted_jobs']}
