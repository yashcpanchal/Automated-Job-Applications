from bs4 import BeautifulSoup

import json
import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from services.agent_nodes.extract_urls import extract_clean_text
from models.job import Job
from core.config import GOOGLE_API_KEY

async def fetch_page_text_node(state: dict) -> dict:
    """
    Fetches the text content of the current URL being processed.
    """
    print("--- NODE: FETCHING PAGE TEXT ---")

    start_time = time.time()
    urls = state.get("urls_to_process", [])
    index = state.get("url_index", 0)

    # Get the current URL using the index
    if index >= len(urls):
        print("  -> ERROR: Index out of bounds. Cannot fetch page.")
        return {"current_page_text": "", "current_url": "", "loop_start_time": start_time}

    url = urls[index]
    print(f"  -> Fetching: {url}")

    page = state.get('page')
    if not page:
        raise ValueError("Playwright page object not found in state.")
    
    try:
        # Use the single, persistent page to navigate to the new URL
        await page.goto(url, wait_until="domcontentloaded", timeout=10000)
        
        # Get the page's content after JavaScript has potentially run
        html_content = await page.content()
        
        # Use BeautifulSoup on the final HTML to extract clean text
        
        soup = BeautifulSoup(html_content, "html.parser")
        page_text = soup.get_text(separator=' ', strip=True)
                
        # page_text = await extract_clean_text(page)

        return {"current_page_text": page_text, "current_url": url, "loop_start_time": start_time}
    
    except Exception as e:
        print(f"  -> Skipping {url}: Error during Playwright navigation - {e}")
        return {"current_page_text": "", "current_url": url, "loop_start_time": start_time}

async def extract_job_details_node(state: dict) -> dict:
    """
    Extracts structured job information from the page text using an LLM. State inputted should
    contain the scraped page text.
    """
    print("--- NODE: EXTRACTING JOB DETAILS ---")
    # page_text = state.get("current_page_text", "")
    page = state.get("page", None)
    page_text = await extract_clean_text(page)
    url = state.get("current_url", "")

    if not page_text:
        print("  -> Skipping extraction: No page text.")
        return {}
    
    # Another agent to parse through the search results retrieved by the search api and format them properly
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", google_api_key=GOOGLE_API_KEY)
    # llm = ChatGoogleGenerativeAI(model="gemma-3-12b-it", google_api_key=GOOGLE_API_KEY)
    structured_llm = llm.with_structured_output(Job, include_raw=False)
    
    schema_str = json.dumps(Job.model_json_schema()).replace("{", "{{").replace("}", "}}")
    extraction_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an expert data extraction agent... schema: {schema_str}..."),
        ("user", "Page Text:\n\n{page_text}")
    ])
    
    # Creating the llm chain using lcel
    extraction_chain = extraction_prompt | structured_llm

    try:
        extracted_data = await extraction_chain.ainvoke({"page_text": page_text})
        if extracted_data:
            extracted_data.source_url = url
            print(f"  -> SUCCESS: Extracted '{extracted_data.title}'")
            # Return a list containing the new job to be appended to the main list
            return {"extracted_jobs": [extracted_data]}
    except Exception as e:
        print(f"  -> Error during extraction: {e}")
    
    return {}