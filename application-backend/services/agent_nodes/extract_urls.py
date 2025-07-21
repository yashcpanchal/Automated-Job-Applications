from typing import Optional
from urllib.parse import urlparse, urljoin
from playwright.async_api import Page
import re

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
    
    print(f"--- EXTRACTED {len(all_links_locators)} LINKS from: {page.url} ---")


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

        # --- Filtering Logic ---
        has_positive_keyword = any(keyword in lower_url for keyword in positive_keywords_url)
        has_positive_root = any(keyword in lower_absolute_url for keyword in positive_root_keywords)
        has_negative_keyword = any(keyword in lower_url for keyword in negative_keywords_url)
        has_negative_root = any(keyword in lower_absolute_url for keyword in negative_root_keywords)
        has_job_pattern = bool(url_structure_pattern.search(href))

        if (has_positive_root or has_positive_keyword or has_job_pattern) and not (has_negative_keyword or has_negative_root):
            job_links.add(absolute_url)

    # --- Step 4: Filter and Return Results ---
    final_links = list(job_links)

    print(f"ADDED JOBS:")
    for i in range(len(final_links)):
        print(f"--> {i}. {final_links[i]}")    
    return {"urls_to_process": final_links}


