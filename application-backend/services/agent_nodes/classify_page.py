# Langchain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Import pydantic model
from models.agent_models.page_classification import PageClassification, ExtractedPageClassification
# Import API key
from core.config import GOOGLE_API_KEY

async def classify_page_node(state: dict) -> dict:
    """
    Classifies the text content of a single webpage.

    Args:
        state (dict): The current agent state, must contain `current_page_text`.

    Returns:
        dict: A dictionary with the `current_page_classification`.
    """
    # print("--- NODE: CLASSIFYING PAGE ---")
    page_text = state.get("current_page_text", "")

    if not page_text:
        print("  -> Skipping classification: No page text found.")
        return {"current_page_classification": "IRRELEVANT"}

    # Setup a fast and cheap LLM for classification
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=GOOGLE_API_KEY, temperature=0)
    # llm = ChatGoogleGenerativeAI(model="gemma-3-12b-it", google_api_key=GOOGLE_API_KEY, temperature=0)

    if state.get("is_on_extracted_jb_urls", False):
        # If we are on extracted jb urls then we can ONLY categorize
        # this as either a job application or irrelevant
        structured_llm = llm.with_structured_output(ExtractedPageClassification)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at identifying job application pages on the web. Your task is to classify a given web page as either a JOB_DESCRIPTION or IRRELEVANT.

            - A JOB_DESCRIPTION is a page that is likely advertising a specific job opening. These pages often include elements such as the job title, company name, responsibilities, qualifications, benefits, or an apply button or link. While not all of these elements must be present, you should only label a page as JOB_DESCRIPTION if you are confident it is describing a specific role.

            - IRRELEVANT includes all other types of pages, such as job boards listing multiple roles, blog posts, news articles, PDFs, company homepages, or error pages.

            Your classification should be based solely on the likelihood that the page content refers to a specific job opportunity. Be conservative: if you are unsure or if the page does not clearly resemble a job description, classify it as IRRELEVANT.
            """),
            ("user", "Please classify the following page content:\n\n<content>\n{page_text}\n</content>")
        ])
    else:
        structured_llm = llm.with_structured_output(PageClassification)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at classifying web page content. Your goal is to determine if a page is a single job description, a list of jobs (a job board), or irrelevant.
            - A JOB_DESCRIPTION contains details like 'Responsibilities', 'Qualifications', 'About the Role' for one specific job.
            - A JOB_BOARD contains a list of multiple job titles, often with links to view details.
            - IRRELEVANT is anything else, like a company's main page, a blog article, or an error page."""),
            ("user", "Please classify the following page content:\n\n<content>\n{page_text}\n</content>")
        ])

    chain = prompt | structured_llm

    try:
        result = await chain.ainvoke({"page_text": page_text[:10000]}) # Use first ~10k chars for speed
        classification = result.classification
        # print(f"Classification result: {classification}")
        return {"current_page_classification": classification}
    except Exception as e:
        print(f"Error during classification: {e}")
        return {"current_page_classification": "IRRELEVANT"}
