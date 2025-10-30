import os
import operator
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define the Tool
@tool
def get_current_weather(location: str):
    """Get the current weather for a specific location."""
    print(f"--- SUBGRAPH: TOOL CALLED: get_current_weather for {location} ---")
    return f"The weather in {location} is currently 80°F and clear."

tools = [get_current_weather]

# 2. Define the State (Used by both graphs)
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 3. Build the "Tool-Using Subgraph"
tool_workflow = StateGraph(AgentState)
tool_workflow.add_node("tool_node", ToolNode(tools))
tool_workflow.add_edge(START, "tool_node")
tool_workflow.add_edge("tool_node", END)

tool_graph = tool_workflow.compile()
print("--- Subgraph compiled ---")

# 4. Build the "Main Agent Graph"
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools)

# --- THIS IS THE CORRECTED FUNCTION ---
def agent_node(state: AgentState):
    """The 'thinker' node that decides what to do."""
    print("--- MAIN GRAPH: agent_node ---")
    
    messages = state['messages']
    
    # --- ADD CLEANUP LOGIC ---
    # This prevents crashes if we load a state
    # that was interrupted after a tool call.
    cleaned_messages = []
    for i, msg in enumerate(messages):
        cleaned_messages.append(msg)
        if msg.type == "ai":
            if msg.tool_calls:
                if i + 1 < len(messages) and messages[i+1].type == "tool":
                    pass # This is a valid pair
                else:
                    print("--- AGENT NODE: Pruning dangling tool call ---")
                    cleaned_messages.pop() # Remove the dangling tool call
    # --- END OF CLEANUP LOGIC ---
    
    response = llm_with_tools.invoke(cleaned_messages)
    return {"messages": [response]}

def router(state: AgentState):
    """Router that decides whether to end or call the subgraph."""
    print("--- MAIN GRAPH: router ---")
    if not state['messages'][-1].tool_calls:
        return END
    else:
        print("--- MAIN GRAPH: Routing to subgraph ---")
        return "call_tool_subgraph"

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("call_tool_subgraph", tool_graph)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent", 
    router,
    {
        "call_tool_subgraph": "call_tool_subgraph",
        END: END
    }
)
workflow.add_edge("call_tool_subgraph", "agent")

# Compile the main graph
# NOTE: This is stateless. If you *are* using a checkpointer,
# you may want to use a new 'thread_id' to start fresh.
app = workflow.compile()
print("--- Main graph compiled ---")

# 5. Run the graph
print("\n--- Invoking Main Weather Agent ---")
question = "What's the weather in San Francisco?"
final_state = app.invoke({"messages": [HumanMessage(content=question)]})

print("\n--- Final Answer ---")
print(final_state['messages'][-1].content)