from typing import List
import json
import asyncio

from langgraph.graph import StateGraph, END
from playwright.async_api import Browser

from models.job import Job
from models.agent_models.agent_state import AgentState

from services.agent_nodes.craft_query import craft_query_node
from services.agent_nodes.web_search import find_urls_node
from services.agent_nodes.page_processing import fetch_page_text_node, extract_job_details_node
from services.agent_nodes.classify_page import classify_page_node
from services.agent_nodes.process_match import process_and_match_node
from services.utils.playwright_manager import PlaywrightManager

def should_process_urls_router(state: AgentState) -> str:
    if state.get("urls_to_process"):
        return "process_urls"
    return "finish_processing"

async def process_urls_in_parallel(state: AgentState) -> dict:
    urls_to_process = state['urls_to_process']
    browser = state.get('browser')
    if not browser:
        raise ValueError("Playwright browser object not found in state.")

    print(f"--- NODE: PROCESSING {len(urls_to_process)} URLs IN PARALLEL ---")
    
    semaphore = asyncio.Semaphore(10)

    async def process_url(url: str, browser: Browser):
        print(f"🚀 Processing URL: {url}")
        async with semaphore:
            context = None
            try:
                context = await browser.new_context()
                page = await context.new_page()
                
                page_text = await fetch_page_text_node(page, url)
                
                if not page_text:
                    await context.close()
                    return None, "IRRELEVANT"
                
                classification = await classify_page_node(page_text)
                await context.close() 
                return page_text, classification

            # Key Change: Made the exception logging more robust.
            except Exception as e:
                # This will now safely print any exception that might occur.
                print(f"  -> Critical error processing {url}: {e!r}")
                if context:
                    await context.close()
                return None, "IRRELEVANT"

    tasks = [process_url(url, browser) for url in urls_to_process]
    results = await asyncio.gather(*tasks)

    job_description_pages = []
    job_board_pages = []

    for i, (page_text, classification) in enumerate(results):
        if classification == "JOB_DESCRIPTION" and page_text:
            job_description_pages.append({"url": urls_to_process[i], "text": page_text})
        elif classification == "JOB_BOARD":
            job_board_pages.append(urls_to_process[i])

    extracted_jobs = []
    if job_description_pages:
        print(f"\n--- EXTRACTING DETAILS FROM {len(job_description_pages)} JOB DESCRIPTIONS ---")
        job_detail_tasks = [extract_job_details_node(page["text"], page["url"]) for page in job_description_pages]
        extracted_jobs = await asyncio.gather(*job_detail_tasks)
        extracted_jobs = [job for job in extracted_jobs if job] 

    if job_board_pages:
        print(f"\nINFO: Found {len(job_board_pages)} job boards, but skipping recursive extraction for now.")

    return {
        "extracted_jobs": extracted_jobs,
        "urls_to_process": [] 
    }

class JobSearchService:
    def __init__(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("craft_query", craft_query_node)
        workflow.add_node("find_urls", find_urls_node)
        workflow.add_node("process_urls_in_parallel", process_urls_in_parallel)
        workflow.add_node("process_and_match", process_and_match_node)

        workflow.set_entry_point("craft_query")
        workflow.add_edge("craft_query", "find_urls")
        workflow.add_conditional_edges(
            "find_urls",
            should_process_urls_router,
            {"process_urls": "process_urls_in_parallel", "finish_processing": "process_and_match"}
        )
        workflow.add_edge("process_urls_in_parallel", "process_and_match")
        workflow.add_edge("process_and_match", END)
        self.app = workflow.compile()
    
    async def search_and_process_jobs(self, resume_text: str, search_prompt: str) -> List[Job]:
        print("\n🚀 --- STARTING AGENTIC JOB SEARCH --- 🚀")

        async with PlaywrightManager() as browser:
            initial_state = {
                "resume_text": resume_text,
                "search_prompt": search_prompt,
                "browser": browser,
                "extracted_jobs": [],
            }
        
            final_state = await self.app.ainvoke(initial_state, config={"recursion_limit": 100})
            final_jobs = final_state.get('final_jobs', [])

        print("✅ --- AGENTIC JOB SEARCH COMPLETE --- ✅\n")
        if final_jobs:
            print(f"--- Found {len(final_jobs)} Relevant Jobs! ---")
        else:
            print("No jobs were found or extracted successfully.")
        
        return final_jobs