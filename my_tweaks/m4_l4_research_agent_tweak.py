import os
import operator
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence, List
import requests
from bs4 import BeautifulSoup
# ToolMessage is needed
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
import json # <-- This import is required

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"
# Note: A TAVILY_API_KEY is also required in your .env file

# --- 1. Define Tools ---
tavily_tool = TavilySearch(max_results=4)

# Scraper Tool
@tool
def scrape_webpages(urls: List[str]) -> str:
    """
    Use requests and BeautifulSoup to scrape the content of a list of webpages.
    """
    print(f"--- TOOL: Scraping {len(urls)} webpages ---")
    all_content = ""
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.body.get_text(" ", strip=True)
            cleaned_content = " ".join(text_content.split())[:3000]
            all_content += f"--- Content from {url} ---\n{cleaned_content}\n\n"
        except Exception as e:
            all_content += f"--- Failed to scrape {url}: {e} ---\n\n"
    return all_content

# --- 2. Define State ---
class ResearchAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    urls: List[str]
    scraped_content: str
    report: str

# --- 3. Define Graph Nodes ---
llm = ChatOpenAI(model="gpt-4o-mini")

def search_agent_node(state: ResearchAgentState):
    print("--- NODE: search_agent ---")
    llm_with_tools = llm.bind_tools([tavily_tool])
    response = llm_with_tools.invoke(state['messages'])
    tool_call = response.tool_calls[0]

    # Invoke Tavily tool
    tool_output = tavily_tool.invoke(tool_call['args'])

    # Handle both string or dict outputs safely
    if isinstance(tool_output, str):
        try:
            tool_output_list = json.loads(tool_output)
        except json.JSONDecodeError:
            print("Warning: Tavily output not JSON decodable.")
            tool_output_list = []
    elif isinstance(tool_output, dict):
        # Tavily returns a dict like {"results": [{"url": ...}, ...]}
        tool_output_list = tool_output.get("results", [])
    elif isinstance(tool_output, list):
        tool_output_list = tool_output
    else:
        tool_output_list = []

    urls = [result['url'] for result in tool_output_list if 'url' in result]

    tool_message = ToolMessage(
        content=json.dumps(tool_output_list, indent=2),
        tool_call_id=tool_call['id']
    )

    return {
        "messages": [response, tool_message],
        "urls": urls
    }


def web_scraper_node(state: ResearchAgentState):
    """
    The 'map' node. It runs the scraper tool on all URLs in parallel.
    """
    print("--- NODE: web_scraper ---")
    
    # This call is correct
    content = scrape_webpages.invoke({"urls": state['urls']})
    
    return {"scraped_content": content}

def generate_report_node(state: ResearchAgentState):
    """
    The 'reduce' node. It synthesizes all scraped content
    into a final research report.
    """
    print("--- NODE: generate_report ---")
    
    query = state['messages'][0].content
    
    prompt = f"""
    Based on the following user query and scraped web content,
    please write a concise, one-page research report.

    User Query: {query}

    Scraped Content:
    {state['scraped_content']}
    """
    
    response = llm.invoke(prompt)
    return {
        "messages": [response],
        "report": response.content
    }

# --- 4. Define Graph ---
workflow = StateGraph(ResearchAgentState)

workflow.add_node("search_agent", search_agent_node)
workflow.add_node("web_scraper", web_scraper_node)
workflow.add_node("generate_report", generate_report_node)

workflow.add_edge(START, "search_agent")
workflow.add_edge("search_agent", "web_scraper")
workflow.add_edge("web_scraper", "generate_report")
workflow.add_edge("generate_report", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- 5. Run the Graph ---
print("--- Invoking Capstone Research Agent ---")

query = "What's the latest in AI-powered code generation?"
thread = {"configurable": {"thread_id": "research-thread-1"}}

final_state = app.invoke({"messages": [HumanMessage(content=query)]}, config=thread)

print("\n" + "="*50)
print("--- FINAL RESEARCH REPORT ---")
print(final_state['report'])
print("="*50)