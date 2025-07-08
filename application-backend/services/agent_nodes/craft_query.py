# Langchain and Langgraph imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Models imports
from models.search_queries import SearchQueries
from models.agent_state import AgentState

# Config import
from core.config import GOOGLE_API_KEY


async def craft_query_node(state: AgentState):
    """
    Node 1: Crafts targeted search queries based on the user's resume and prompt.
    """
    resume = state['resume_text']
    prompt = state['search_prompt']

    # Generate the search query here

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY, temperature=0.2)
    # Ensuring that the llm sticks to the desired output schema
    structured_llm = llm.with_structured_output(SearchQueries)

    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a world-class career assistant and expert at crafting search engine queries.
        Your goal is to help a user find relevant job postings based on their resume and a specific prompt.
        
        Generate a diverse list of 3 to 5 search queries that are likely to yield direct job application links
        on company career pages. The queries should be
        creative and varied to cover different angles of the job search."""),
        ("user", """Here is my resume:
        <resume>
        {resume_text}
        </resume>
        \n\n
        Here is my current search prompt:
        <prompt>
        {search_prompt}
        </prompt>
        \n\n
        Please generate the search queries.""")
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
