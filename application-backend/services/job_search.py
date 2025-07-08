from typing import List
import json

# Langgraph imports
from langgraph.graph import StateGraph, END

# Models imports
from models.job import Job
from models.agent_state import AgentState

# Nodes from the agent_nodes subfolder
from services.agent_nodes.craft_query import craft_query_node
from services.agent_nodes.retrieve_parse import retrieve_and_parse_node
from services.agent_nodes.process_match import process_and_match_node

class JobSearchService:
    def __init__(self):
        workflow = StateGraph(AgentState)

        # Add the nodes to the graph
        workflow.add_node("craft_query", craft_query_node)
        workflow.add_node("retrieve_and_parse", retrieve_and_parse_node)
        workflow.add_node("process_and_match", process_and_match_node)

        # Set the entry and finish points of the graph
        workflow.set_entry_point("craft_query")
        workflow.add_edge("craft_query", "retrieve_and_parse")
        workflow.add_edge("retrieve_and_parse", "process_and_match")
        workflow.add_edge("process_and_match", END)

        # Compile the graph into a runnable application
        self.app = workflow.compile()

    async def search_and_process_jobs(self, resume_text: str, search_prompt: str) -> List[Job]:
        """
        The main method to run the job search agent.
        """
        print(" --- STARTING AGENTIC JOB SEARCH --- ")
        inputs = {"resume_text": resume_text, "search_prompt": search_prompt}
        final_state = await self.app.ainvoke(inputs)
        print(" --- AGENTIC JOB SEARCH COMPLETE --- \n")
        final_jobs = final_state.get('final_jobs', [])
        if final_jobs:
            final_jobs_as_dicts = [job.model_dump() for job in final_jobs]
            print(F"FINAL RESULTS:\n {json.dumps(final_jobs_as_dicts, indent=2)}")
        else:
            print("No jobs were found or extracted successfully unfortunately :(")

        return final_state.get('final_jobs', [])
