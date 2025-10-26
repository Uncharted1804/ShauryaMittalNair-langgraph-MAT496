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
    response = llm_with_tools.invoke(state['messages'])
    return {"messages": [response]}

# 4. Define the Router
def should_continue(state: AgentState):
    if not state['messages'][-1].tool_calls:
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

# We compile the graph with a checkpointer AND an interrupt
memory = MemorySaver()
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["tool_node"]
)

# 6. Run the agent
print("--- Invoking Agent with Breakpoint ---")
thread_config = {"configurable": {"thread_id": "breakpoint-thread-1"}}

# First turn - The agent will decide to use the tool and then pause
print("\n--- Turn 1: User Request ---")
question = "Please update my profile, shaurya, to say 'LangGraph expert'."
for event in app.stream({"messages": [HumanMessage(content=question)]}, config=thread_config):
    print(event)

print("\n--- GRAPH PAUSED ---")
current_state = app.get_state(thread_config)
last_message = current_state.values['messages'][-1]
print(f"Agent wants to run tool: {last_message.tool_calls[0]['name']}")

# Simulate human approval by resuming the graph
print("\n--- Turn 2: Human Approves and Resumes Graph ---")
for event in app.stream(None, config=thread_config):
    print(event)
    
print("\n--- FINAL STATE ---")
final_state = app.get_state(thread_config)


print(final_state.values['messages'][-1].content)
