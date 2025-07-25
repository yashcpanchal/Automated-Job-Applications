import httpx
from bs4 import BeautifulSoup
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from models.job import Job
from core.config import GOOGLE_API_KEY

async def fetch_page_text_node(state: dict) -> dict:
    """
    Fetches the text content of the current URL being processed.
    """
    print("--- NODE: FETCHING PAGE TEXT ---")
    urls = state.get("urls_to_process", [])
    index = state.get("url_index", 0)

    # Get the current URL using the index
    if index >= len(urls):
        print("  -> ERROR: Index out of bounds. Cannot fetch page.")
        return {"current_page_text": "", "current_url": ""}

    url = urls[index]
    print(f"  -> Fetching: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        async with httpx.AsyncClient(headers=headers, verify=False, timeout=15.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(separator=' ', strip=True)
        return {"current_page_text": page_text, "current_url": url}
    except Exception as e:
        print(f"  -> Skipping {url}: Error fetching page - {e}")
        return {"current_page_text": "", "current_url": url}


async def extract_job_details_node(state: dict) -> dict:
    """
    Extracts structured job information from the page text using an LLM. State inputted should
    contain the scraped page text.
    """
    print("--- NODE: EXTRACTING JOB DETAILS ---")
    page_text = state.get("current_page_text", "")
    url = state.get("current_url", "")

    if not page_text:
        print("  -> Skipping extraction: No page text.")
        return {}
    
    # Another agent to parse through the search results retrieved by the search api and format them properly
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", google_api_key=GOOGLE_API_KEY)
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