from typing import List
import json

# Langgraph imports
from langgraph.graph import StateGraph, END

# Models imports
from models.job import Job
from models.agent_models.agent_state import AgentState

# Nodes from the agent_nodes subfolder
from services.agent_nodes.craft_query import craft_query_node
from services.agent_nodes.web_search import find_urls_node
from services.agent_nodes.page_processing import fetch_page_text_node, extract_job_details_node
from services.agent_nodes.classify_page import classify_page_node
from services.agent_nodes.process_match import process_and_match_node

# --- Router Functions ---

def should_continue_router(state: AgentState) -> str:
    """Router that decides if there are more URLs to process."""
    print("--- ROUTER: SHOULD CONTINUE? ---")
    urls = state.get("urls_to_process", [])
    index = state.get("url_index", 0)
    
    if index >= len(urls):
        print("  -> Decision: NO, processed all URLs. Finishing.")
        return "finish_processing"
    else:
        print(f"  -> Decision: YES, processing URL {index + 1} of {len(urls)}.")
        return "continue_processing"

def should_extract_router(state: AgentState) -> str:
    """The 'gatekeeper' router."""
    print("--- ROUTER: SHOULD EXTRACT? ---")
    classification = state.get("current_page_classification", "IRRELEVANT")
    
    if classification == "JOB_DESCRIPTION":
        print("  -> Decision: YES, page is a job description.")
        return "extract_details"
    else:
        print("  -> Decision: NO, page is a job board or irrelevant.")
        return "skip_extraction"

# --- Node Functions ---

def increment_index_node(state: AgentState) -> dict:
    """Increments the URL index and appends any newly extracted job to the list."""
    index = state.get("url_index", 0)
    return {
        "url_index": index + 1
    }

class JobSearchService:
    def __init__(self):
        workflow = StateGraph(AgentState)

        # Add all nodes to the graph
        workflow.add_node("craft_query", craft_query_node)
        workflow.add_node("find_urls", find_urls_node)
        workflow.add_node("fetch_page_text", fetch_page_text_node)
        workflow.add_node("classify_page", classify_page_node)
        workflow.add_node("extract_job_details", extract_job_details_node)
        workflow.add_node("increment_index", increment_index_node)
        workflow.add_node("process_and_match", process_and_match_node)

        # Define the graph's execution flow
        workflow.set_entry_point("craft_query")
        workflow.add_edge("craft_query", "find_urls")

        # After finding URLs, go directly to the decision router.
        workflow.add_conditional_edges(
            "find_urls",
            should_continue_router,
            {"continue_processing": "fetch_page_text", "finish_processing": "process_and_match"}
        )
        
        # The processing flow for a single URL
        workflow.add_edge("fetch_page_text", "classify_page")

        # The "gatekeeper" router after classification
        workflow.add_conditional_edges(
            "classify_page",
            should_extract_router,
            {"extract_details": "extract_job_details", "skip_extraction": "increment_index"}
        )

        # After extraction, we increment the index
        workflow.add_edge("extract_job_details", "increment_index")
        
        # After incrementing the index, loop back to the main decision router
        workflow.add_conditional_edges(
            "increment_index",
            should_continue_router,
            {"continue_processing": "fetch_page_text", "finish_processing": "process_and_match"}
        )

        # The final step after the loop is complete
        workflow.add_edge("process_and_match", END)

        # Compile the graph
        self.app = workflow.compile()
    
    async def search_and_process_jobs(self, resume_text: str, search_prompt: str) -> List[Job]:
        print("\n🚀 --- STARTING AGENTIC JOB SEARCH --- 🚀")
        initial_state = {"resume_text": resume_text, "search_prompt": search_prompt}
        
        final_state = await self.app.ainvoke(initial_state, config={"recursion_limit": 500})
        
        # Retrieve the list from the 'final_jobs' key, which is set by the last node in the graph.
        final_jobs = final_state.get('final_jobs', [])

        print("✅ --- AGENTIC JOB SEARCH COMPLETE --- ✅\n")
        if final_jobs:
            final_jobs_as_dicts = [job.model_dump() for job in final_jobs]
            print(f"FINAL RESULTS:\n {json.dumps(final_jobs_as_dicts, indent=2)}")
        else:
            print("No jobs were found or extracted successfully.")
        
        return final_jobs
