import asyncio
import json
from langchain_community.tools import BraveSearch
from core.config import BRAVE_SEARCH_API_KEY

async def find_urls_node(state: dict) -> dict:
    """
    Node that uses the Brave Search API to find relevant URLs based on the generated queries.
    """
    print("--- NODE: FINDING URLs ---")
    queries = state['search_queries']
    search_tool = BraveSearch(api_key=BRAVE_SEARCH_API_KEY, search_kwargs={"count": 20, "offset": 0}, return_direct=True)  # other params: freshness, result_filter
    all_urls = set() # ensures no duplicates

    # Each entry in search_tasks is a call to brave search api with query
    # ainvoke creates an awaitable object which needs to be ran with asyncio
    print(f"INFO: Executing {len(queries)} searches...")
    for query in queries:
        results_str = await search_tool.ainvoke(query)
        try:
            results_list = json.loads(results_str)
            for result in results_list:
                if isinstance(result, dict) and 'link' in result:
                    all_urls.add(result['link'])
        except json.JSONDecodeError:
            print(f"  -> Could not decode JSON from search results for query: {query}")
        await asyncio.sleep(1) # Wait 1 sec bc of Brave's 1 req/sec limit

    print(f"INFO: Found {len(all_urls)} unique URLs.")
    return {
        "urls_to_process": list(all_urls),
        "url_index": 0,
    }