# Langchain and Langgraph imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Models imports
from models.agent_models.search_queries import SearchQueries
from models.agent_models.agent_state import AgentState

# Config import
from core.config import GOOGLE_API_KEY


async def craft_query_node(state: AgentState):
    """
    Node 1: Crafts targeted search queries based on the user's resume and prompt.
    """
    
    # Generate the search query here
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.2)
    # Ensuring that the llm sticks to the desired output schema
    structured_llm = llm.with_structured_output(SearchQueries)

    # Define the prompt template
    # prompt = ChatPromptTemplate.from_messages([
    #     ("system", """You are a world-class career assistant and an expert at crafting search engine queries for the Brave Search engine.
    #     Your goal is to generate 3-5 search queries to help a user find relevant job postings.

    #     **Strategy: Vague to Specific**
    #     1. Start with broad, simple queries.
    #     2. Create slightly more specific queries using keywords from the user's resume and prompt.
    #     3. Use Brave Search operators to refine the search.

    #     **Key Brave Search Operators to Use:**
    #     - `""`: Use double quotes for exact phrases, like `"software engineer"`. This is very important.
    #     - `-`: Use a minus sign to exclude terms. For example, `-internship` or `-entry-level` if the resume seems senior.
    #     - `OR`: Use the OR operator (in uppercase) to search for alternatives, like `(Django OR FastAPI)`.

    #     **Example of GOOD Queries:**
    #     - "backend developer" remote
    #     - "python developer" (FastAPI OR Django)
    #     - "senior software engineer" cloud -"entry-level"

    #     **Example of a BAD Query (Too Specific):**
    #     - "remote senior software engineer with 5 years of python fastapi and sql experience"

    #     Now, based on the user's resume and prompt below, generate the queries."""),
    #     ("user", """Here is my resume:
    #     <resume>
    #     {resume_text}
    #     </resume>
        
    #     Here is my current search prompt:
    #     <prompt>
    #     {search_prompt}
    #     </prompt>
        
    #     Please generate the search query.""")
    # ])


    # TESTING PROMPT GENERATES ONLY 1 QUERY
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a world-class career assistant and an expert at crafting search engine queries for the Brave Search engine.
        Your goal is to generate 1 search query to help a user find relevant job postings.

        Now, based on the user's resume and prompt below, generate the query. Keep it vague but relevant to the users' industry
        a good example is 'software engineering internships'."""),
        ("user", """Here is my resume:
        <resume>
        {resume_text}
        </resume>
        
        Here is my current search prompt:
        <prompt>
        {search_prompt}
        </prompt>
        
        Please generate the search query.""")
    ])

    
    chain = prompt | structured_llm

    result_model = await chain.ainvoke({
        "resume_text": state['resume_text'],
        "search_prompt": state['search_prompt']
    })

    # queries is defined by the output schema in the SearchQueries class
    print(f"GENERATED QUERIES: {result_model.queries}")
    # breakpoint()
    return {"search_queries": result_model.queries}
