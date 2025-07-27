from bs4 import BeautifulSoup
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
# Import TimeoutError and Error for specific exception handling
from playwright.async_api import Page, Error, TimeoutError

from models.job import Job
from core.config import GOOGLE_API_KEY

async def fetch_page_text_node(page: Page, url: str) -> str:
    """
    Fetches the text content of a URL, with robust error handling for timeouts.
    """
    print(f"  -> Navigating to: {url}")
    try:
        # We continue to use 'networkidle' for reliability.
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        html_content = await page.content()
        soup = BeautifulSoup(html_content, "html.parser")
        page_text = soup.get_text(separator=' ', strip=True)
                
        print(f"  ✅ Successfully fetched content from: {url}")
        return page_text
    
    # Key Change: Catch TimeoutError specifically.
    except TimeoutError:
        print(f"  -> Skipping {url}: Navigation timed out after 30 seconds.")
        return ""
    # Catch other Playwright-specific errors.
    except Error as e:
        print(f"  -> Skipping {url}: Playwright error during navigation - {e.msg}")
        return ""
    # A general catch-all for any other unexpected issues.
    except Exception as e:
        print(f"  -> Skipping {url}: An unexpected error occurred - {e}")
        return ""

async def extract_job_details_node(page_text: str, url: str) -> Job | None:
    """
    Extracts structured job information from the page text using an LLM.
    """
    if not page_text:
        print(f"  -> Skipping extraction for {url}: No page text provided.")
        return None
    
    print(f"  -> Extracting job details from: {url}")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", google_api_key=GOOGLE_API_KEY, temperature=0)
    structured_llm = llm.with_structured_output(Job, include_raw=False)
    
    schema_str = json.dumps(Job.model_json_schema()).replace("{", "{{").replace("}", "}}")
    extraction_prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an expert data extraction agent... schema: {schema_str}..."),
        ("user", "Page Text:\n\n{page_text}")
    ])
    
    extraction_chain = extraction_prompt | structured_llm

    try:
        extracted_data = await extraction_chain.ainvoke({"page_text": page_text})
        if extracted_data:
            extracted_data.source_url = url
            print(f"  ✅ SUCCESS: Extracted '{extracted_data.title}' from {extracted_data.company}")
            return extracted_data
    except Exception as e:
        print(f"  -> Extraction failed for {url}: {e}")
    
    return None