from typing import Optional
import asyncio
import httpx
from bs4 import BeautifulSoup
import json

# Langchain and Langgraph imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import BraveSearch

# Models imports
from models.job import Job
from models.agent_state import AgentState

# API key imports
from core.config import GOOGLE_API_KEY, BRAVE_SEARCH_API_KEY


async def _fetch_and_extract_job_data(url: str, llm_chain, semaphore: asyncio.Semaphore) -> Optional[Job]:
    """
    Fetches content from a URL, cleans it, and uses an LLM to actually extract the job data.
    Fetching and cleaning is done through bs4, the rest is done thru the llm chain. LLM chain will append
    all of the relevant data into the job model when it is invoked with the page_text passed in.
    """
    # Will only enter the function if the semaphore allows it
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    async with semaphore:
        print(f"Analyzing URL: {url}")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status() # Will raise an http error for bad status codes
            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text(separator=' ', strip=True)[:60000]
            
            if not page_text:
                print("Skipping {url}: No text content found")
                return None
            
            # Feeds into llm chain
            extracted_data = await llm_chain.ainvoke({"page_text": page_text})

            if extracted_data:
                extracted_data.source_url = url
                print(f"Extracted {extracted_data.title} from URL")
                return extracted_data
        
        except httpx.RequestError as e:
            print(f"Skipping {url}: Network error - {e}")
        except Exception as e:
            print(f"Skipping {url}: Error during processing - {e}")
        return None


async def retrieve_and_parse_node(state: AgentState):
    """
    Node 2: Uses a search tool to find job URLs and then parses each URL to extract job data.
    """
    queries = state['search_queries']
    search_tool = BraveSearch(api_key=BRAVE_SEARCH_API_KEY, return_direct=True, search_kwargs={"count": 20, "offset": 0}) # other params: freshness, result_filter 
    all_urls = set() # ensures no duplicates

    # Each entry in search_tasks is a call to brave search api with query
    # ainvoke creates an awaitable object which needs to be ran with asyncio
    for query in queries:
        results = await search_tool.ainvoke(query)
        results_list = json.loads(results)
        try:
            for result in results_list:
                if isinstance(result, dict) and 'link' in result:
                    all_urls.add(result['link'])
                else:
                    print("ALERT THERE IS AN ERROR HERE RESULT IS NOT A DICT")
                    breakpoint()
        except json.JSONDecodeError:
            print(f"Could not decode JSON from search results for query: {query}")
        
        await asyncio.sleep(1) # Wait 1 sec bc of Brave's 1 req/sec limit

    found_urls = list(all_urls)
    print(f"INFO: Found {len(found_urls)} unique URLs.")
    print(found_urls)

    # Another agent to parse through the search results retrieved by the search api and format them properly
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", google_api_key=GOOGLE_API_KEY)
    structured_llm = llm.with_structured_output(Job, include_raw=False)

    schema_str = json.dumps(Job.model_json_schema()).replace("{", "{{").replace("}", "}}")

    extraction_prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are an expert data extraction agent. Your task is to extract job posting information
        from the provided text content of a web page.
        
        You must extract the information into the following JSON schema:
        {schema_str}
        
        Pay close attention to finding the direct application URL. If a field is not present, use null.
        Do not invent any information."""),
        ("user", "Page Text:\n\n{page_text}")
    ])
    # Creating the llm chain using lcel
    extraction_chain = extraction_prompt | structured_llm
    # Create the semaphore
    semaphore = asyncio.Semaphore(5)
    # Creating a list of awaitable objects (bc function is async).
    extraction_tasks = [_fetch_and_extract_job_data(url, extraction_chain, semaphore) for url in found_urls]
    # Runs the awaitable objects in extraction_tasks using asyncio
    extracted_job_results = await asyncio.gather(*extraction_tasks)
    # Filters out emptyy jobs in extracted_job_results
    extracted_jobs = [job for job in extracted_job_results if job is not None]

    print(f"Successfully retrieved {len(extracted_jobs)} jobs.")

    return {"retrieved_urls": found_urls, "extracted_jobs": extracted_jobs}
