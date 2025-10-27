import os
import operator
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define the Tools
@tool
def get_user_profile(username: str):
    """Gets a user's profile. This is a safe, read-only operation."""
    print(f"--- (SAFE) TOOL CALLED: get_user_profile for {username} ---")
    return f"{username}'s profile: LangGraph enthusiast."

@tool
def update_user_profile(username: str, data_to_update: str):
    """Updates a user's profile. This is a DANGEROUS operation and requires approval."""
    print(f"--- (DANGEROUS) TOOL CALLED: Updating {username}'s profile with '{data_to_update}' ---")
    return f"Successfully updated {username}'s profile."


# 2. Create TWO separate tool nodes
safe_tools = [get_user_profile]
dangerous_tools = [update_user_profile]

safe_tool_node = ToolNode(safe_tools)
dangerous_tool_node = ToolNode(dangerous_tools)
# --- END OF CHANGE ---

# 3. Define the State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 4. Define the Nodes
llm = ChatOpenAI(model="gpt-4o-mini")
# We bind *all* tools so the agent knows about them
llm_with_tools = llm.bind_tools(safe_tools + dangerous_tools)

def agent_node(state: AgentState):
    """The primary node that decides the next action."""
    print("--- NODE: agent ---")
    response = llm_with_tools.invoke(state['messages'])
    return {"messages": [response]}

# 5. Define the NEW Dynamic Router 
def dynamic_router(state: AgentState):
    """
    This router inspects the agent's plan and routes
    to the correct tool node (safe or dangerous).
    """
    print("--- ROUTER: dynamic_router ---")
    last_message = state['messages'][-1]

    if isinstance(last_message, HumanMessage): return "agent_node"
    if not last_message.tool_calls: return END
    
    # We only expect one tool call here for this example
    tool_call_name = last_message.tool_calls[0]['name']
    
    if tool_call_name == "get_user_profile":
        print("--- ROUTER: Safe tool detected. Routing to 'safe_tool_node'. ---")
        return "safe_tool_node"
    
    if tool_call_name == "update_user_profile":
        print("--- ROUTER: Dangerous tool detected. Routing to 'dangerous_tool_node'. ---")
        return "dangerous_tool_node"

# 6. Define the Graph 
workflow = StateGraph(AgentState)
workflow.add_node("agent_node", agent_node)
# Add both tool nodes
workflow.add_node("safe_tool_node", safe_tool_node)
workflow.add_node("dangerous_tool_node", dangerous_tool_node)

workflow.add_conditional_edges(
    "agent_node",
    dynamic_router,
    {
        "agent_node": "agent_node",
        "safe_tool_node": "safe_tool_node",
        "dangerous_tool_node": "dangerous_tool_node",
        END: END
    }
)
# Both tool nodes loop back to the agent
workflow.add_edge("safe_tool_node", "agent_node")
workflow.add_edge("dangerous_tool_node", "agent_node")
workflow.add_edge(START, "agent_node")

memory = MemorySaver()
app = workflow.compile(
    checkpointer=memory,
    # We set a *static* interrupt on the *dynamic* target
    interrupt_before=["dangerous_tool_node"]
)

# 7. Run the agent
print("--- Invoking Agent with Dynamic Breakpoint ---")
thread_config = {"configurable": {"thread_id": "dynamic-thread-1"}}

# --- Test 1: Safe Action (Should run automatically) ---
print("\n--- Test 1: Safe Action (get_user_profile) ---")
question1 = "What is my profile, shaurya?"
final_state = app.invoke({"messages": [HumanMessage(content=question1)]}, config=thread_config)
print("--- Test 1 Final Answer ---")
print(final_state['messages'][-1].content)


# --- Test 2: Dangerous Action (Should PAUSE) ---
print("\n\n--- Test 2: Dangerous Action (update_user_profile) ---")
question2 = "Please update my profile, shaurya, to say 'LangGraph expert'."
for event in app.stream({"messages": [HumanMessage(content=question2)]}, config=thread_config):
    print(event)

print("\n--- GRAPH PAUSED (Test 2) ---")
current_state = app.get_state(thread_config)
print(f"Agent wants to run: {current_state.values['messages'][-1].tool_calls[0]['name']}")

# --- Test 3: Human Approves Dangerous Action ---
print("\n--- Test 3: Human Approves and Resumes ---")
for event in app.stream(None, config=thread_config):
    print(event)
    
print("\n--- Test 3 Final Answer ---")
final_state = app.get_state(thread_config)
print(final_state.values['messages'][-1].content)