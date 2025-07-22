from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from models.agent_models.url_classification import FilteredUrls
from core.config import GOOGLE_API_KEY
from typing import List

async def filter_urls_node(state: dict) -> dict:
    """
    Filters a list of URLs to identify which ones are likely to be job postings.

    Args:
        state (dict): The current agent state, must contain `urls_to_process`.

    Returns:
        dict: A dictionary with the `urls_to_process` updated with the filtered list.
    """
    print("--- NODE: FILTERING URLS ---")
    urls_to_process = state.get("urls_to_process", [])

    if not urls_to_process:
        print("  -> Skipping filtering: No URLs to process.")
        return {"urls_to_process": []}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)
    structured_llm = llm.with_structured_output(FilteredUrls)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at identifying URLs that point to job postings.
        Your goal is to filter a list of URLs and return only those that are likely to be direct links to job descriptions.
        Analyze the URL structure and path. Look for keywords like 'job', 'careers', 'posting', 'apply', 'gh_jid'.
        Exclude general career pages, blog posts, and company homepages.
        Return a list of URLs that you are confident are job postings."""),
        ("user", "Please filter the following URLs:\n\n<urls>\n{url_list}\n</urls>")
    ])

    chain = prompt | structured_llm

    try:
        # Join the list of URLs into a single string for the prompt
        url_list_str = "\n".join(urls_to_process)
        result = await chain.ainvoke({"url_list": url_list_str})
        filtered_urls = result.job_urls
        print(f"  -> Original URLs: {len(urls_to_process)}, Filtered URLs: {len(filtered_urls)}")
        return {"urls_to_process": filtered_urls}
    except Exception as e:
        print(f"  -> Error during URL filtering: {e}")
        # In case of an error, return the original list to avoid breaking the flow
        return {"urls_to_process": urls_to_process}