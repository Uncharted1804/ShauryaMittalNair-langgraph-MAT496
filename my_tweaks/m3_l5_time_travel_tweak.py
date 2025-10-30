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

# 1. Define the "Dangerous" Tool
@tool
def update_user_profile(username: str, data_to_update: str):
    """Updates a user's profile in the database. Only use if explicitly approved."""
    print(f"--- TOOL CALLED: Updating {username}'s profile with '{data_to_update}' ---")
    return f"Successfully updated {username}'s profile."

tools = [update_user_profile]
tool_node = ToolNode(tools)

# 2. Define the State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 3. Define the Nodes
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState):
    """The primary node that decides the next action."""
    print("--- NODE: agent ---")
    
    messages = state['messages']
    
    cleaned_messages = []
    for i, msg in enumerate(messages):
        cleaned_messages.append(msg)
        if msg.type == "ai":
            if msg.tool_calls:
                if i + 1 < len(messages) and messages[i+1].type == "tool":
                    pass
                else:
                    print("--- AGENT NODE: Pruning dangling tool call ---")
                    cleaned_messages.pop() 

    response = llm_with_tools.invoke(cleaned_messages)
    return {"messages": [response]}

# 4. Define the Router
def should_continue(state: AgentState):
    """A more robust router that handles human feedback."""
    last_message = state['messages'][-1]
    if isinstance(last_message, HumanMessage):
        return "agent_node"
    if not last_message.tool_calls:
        return END
    else:
        return "tool_node"

# 5. Define the Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent_node", agent_node)
workflow.add_node("tool_node", tool_node)
workflow.add_conditional_edges("agent_node", should_continue)
workflow.add_edge("tool_node", "agent_node")
workflow.add_edge(START, "agent_node")

memory = MemorySaver()

app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["tool_node"] 
)

# 6. Run the agent with Time Travel Correction
print("--- Invoking Agent with Time Travel (In-Memory) ---")
thread_config = {"configurable": {"thread_id": "time-travel-thread-1"}}

# --- Turn 1: User Request ---
print("\n--- Turn 1: User Request (Bad Plan) ---")
question = "Please update my profile, shaurya, to say 'LangGraph expert'."
for event in app.stream({"messages": [HumanMessage(content=question)]}, config=thread_config):
    print(event)

print("\n--- GRAPH PAUSED (Turn 1) ---")
current_state = app.get_state