from typing import Optional
from urllib.parse import urlparse, urljoin
from playwright.async_api import Page
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from models.agent_models.url_classification import FilteredUrls
from core.config import GOOGLE_API_KEY
from typing import List


async def extract_clean_text(page: Page) -> str:
    """
    Helper method to extract abbreviated text to (usually) feed into llm
    """
    content_selectors = ['div[class*="job-description"]', '.job-details', '#jobDescription', 'main[role="main"]', 'article']
    focused_text = ""
    for selector in content_selectors:
        if await page.locator(selector).count() > 0:
            focused_text = await page.locator(selector).first.inner_text()
            print(f"  -> Found focused content with selector: '{selector}'")
            break
    if not focused_text:
        focused_text = await page.locator('body').inner_text()
    cleaned_text = re.sub(r'\s+', ' ', focused_text).strip()[:15000]
    return cleaned_text


def resolve_url(base_url: str, relative_url: str) -> Optional[str]:
    """Resolves a relative URL to an absolute URL. Returns None if input is invalid."""
    if not relative_url or not isinstance(relative_url, str):
        return None
    try:
        return urljoin(base_url, relative_url)
    except (ValueError, TypeError):
        return None

async def extract_urls_node(state: dict) -> dict:
    """
    Extracts individual job posting URLs from a job board page using a more
    robust, multi-layered heuristic approach that includes smart scrolling
    and positive/negative keyword filtering.
    """
    page = state.get("page", None)
    if not page:
        raise ValueError("Playwright page object not found in state.")
    
    base_url = page.url
    job_links = set()

    # Common job link url patterns
    url_structure_pattern = re.compile(
        r'/jobs?/|/careers?/|/openings?/|viewjob|job_id=|gh_jid|posting', 
        re.IGNORECASE
    )

    # List of keywords that are often found in job links
    positive_keywords_url = [
        'careers', 'jobs', 'career', 'job', 'intern', 'summer', 'apply', 
        'position', 'opportunities', 'recruit', 'opening', 'analyst', 'software', 
        'engineer', 'quant', 'trading', 'technology', 'developer', 'associate', 'roles'
    ]

    # List of domain names that typically lead to job applications
    positive_root_keywords = [
        'greenhouse', 'careers', 'jobs', 'simplify', 'glassdoor', 'lever'
    ]
    
    # Negative keywords to filter out common non-job pages
    negative_keywords_url = [
        'blog', 'advice', 'salaries', 
    ]

    # List of domain names to not touch
    negative_root_keywords = [
        'github', 'indeed', 'linkedin', 'intern-list'
    ]

    all_links_locators = await page.locator('a[href]').all()
    
    count = 0
    for link_locator in all_links_locators:
        href = await link_locator.get_attribute('href')
        
        absolute_url = resolve_url(base_url, href)

        parsed = urlparse(absolute_url)
        stripped_url = parsed.path or "/"

        if not absolute_url:
            continue

        if not stripped_url:
            continue

        count+=1
        lower_absolute_url = absolute_url.lower()
        lower_url = stripped_url.lower()

        # --- Basic Filtering Logic ---
        has_positive_keyword = any(keyword in lower_url for keyword in positive_keywords_url)
        has_positive_root = any(keyword in lower_absolute_url for keyword in positive_root_keywords)
        has_negative_keyword = any(keyword in lower_url for keyword in negative_keywords_url)
        has_negative_root = any(keyword in lower_absolute_url for keyword in negative_root_keywords)
        has_job_pattern = bool(url_structure_pattern.search(href))

        if (has_positive_root or has_positive_keyword or has_job_pattern) and not (has_negative_keyword or has_negative_root):
            job_links.add(absolute_url)

    root = urlparse(base_url)
    if "github" not in root:
        filtered_links = await filter_urls(list(job_links))
    else:
        filtered_links = list(job_links)

    # --- Step 4: Filter and Return Results ---
    print(f"--- EXTRACTED {len(all_links_locators)} LINKS from: {page.url} and added {len(filtered_links)} JOBS ---")
    # print(f"ADDED JOBS:")
    # for i in range(len(filtered_links)):
    #     print(f"--> {i}. {filtered_links[i]}")  
    current_urls = set(state.get("urls_to_process", []))
    current_extracted_job_board_urls = set(state.get("urls_extracted_job_boards", []))
    visited_urls_set = current_urls | current_extracted_job_board_urls
    final_links = [link for link in filtered_links if link not in visited_urls_set]
    return {"urls_extracted_job_boards": final_links}

async def filter_urls(urls_to_filter: List[str]) -> List[str]:
    """
    Uses a Gemini model to filter a list of URLs, returning only those
    that are likely to be direct job postings.
    """
    print("--- NODE: FILTERING URLS ---")

    if not urls_to_filter:
        # print("  -> Skipping filtering: No URLs to process.")
        return {"urls_to_process": []}

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0)
    structured_llm = llm.with_structured_output(FilteredUrls)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a highly specialized AI assistant for parsing web URLs to identify and extract direct links to individual job postings. Your execution must be flawless.
        Your primary objective is to analyze a provided list of URLs and extract ONLY the ones that lead directly to a page for a SINGLE job description.

        **CRITICAL RULES:**

        1.  **THE 50 URL LIMIT:** You MUST NOT return more than 50 URLs. If you identify more than 50 valid URLs, return only the first 50.
        2.  **THE "ONE JOB" RULE:** The most important rule is that a valid URL must point to a page describing a *single* job, not a list of multiple jobs.
        3.  **STRICTLY EXCLUDE:** You must discard any URL that is a general careers page, a list of jobs, a search results page, a company homepage, a blog post, or a login page.

        **ANALYSIS PROCESS:**

        * **Positive Indicators (Look for these):**
            * Keywords like `job`, `posting`, `vacancy`, `opening`, `apply`.
            * Recruiting platform domains like `greenhouse.io`, `lever.co`, `workday.com`.
            * URL paths that contain specific job identifiers (e.g., numerical IDs, UUIDs, or job titles), such as `/jobs/123456` or `?gh_jid=4815162342`.

        * **Negative Indicators (Immediately discard these):**
            * Generic paths like `/careers`, `/jobs`, `/opportunities`. These are almost always lists.
            * Search query parameters like `?q=engineer` or `/search`.
            * URLs that end in the plain company domain (e.g., `https://company.com/`).

        **EXAMPLES:**

        * **GOOD (Include):** `https://boards.greenhouse.io/stripe/jobs/4169621`
            * *Reason: Contains a platform domain, `/jobs/`, and a specific ID.*
        * **GOOD (Include):** `https://www.notion.so/careers/product-designer-48a68b8a83444158bb9150644235c43c`
            * *Reason: Contains `/careers/` followed by a specific job title and a unique ID.*
        * **BAD (Exclude):** `https://stripe.com/jobs`
            * *Reason: This is a general list of jobs, not a specific posting.*
        * **BAD (Exclude):** `https://www.google.com/careers/search?q=software`
            * *Reason: This is a search results page.*
        * **BAD (Exclude):** `https://www.apple.com/careers/us/`
            * *Reason: This is a regional careers portal, not a specific job.*

        **Final Output:**
        Return ONLY a plain list of the valid URLs. Do not add any commentary, explanations, or numbering. If no URLs meet the criteria, return nothing."""),
        ("user", "Please filter the following URLs:\n\n<urls>\n{url_list}\n</urls>")
    ])

    chain = prompt | structured_llm

    try:
        # Join the list of URLs into a single string for the prompt
        url_list_str = "\n".join(urls_to_filter)
        print("Starting Filter")
        result = await chain.ainvoke({"url_list": url_list_str})
        print("Ending Filter")
        filtered_urls = list(result.job_urls)
        # print(f"  -> Original URLs: {len(urls_to_filter)}, Filtered URLs: {len(filtered_urls)}")
        return filtered_urls
    except Exception as e:
        print("ERROR")
        print(f"  -> Error during URL filtering: {e}")
        # In case of an error, return the original list to avoid breaking the flow
        return []