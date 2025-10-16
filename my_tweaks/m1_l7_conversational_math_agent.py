import os
import operator
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
# This is the new import for adding memory
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define the Tool
@tool
def simple_adder(a: int, b: int) -> int:
    """Adds two integers together. Use this for any addition questions."""
    print(f"--- TOOL CALLED: simple_adder with a={a} and b={b} ---")
    return a + b

tools = [simple_adder]
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
    """Determines whether to continue the loop or end."""
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

# The key change: add a checkpointer
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 6. Run the agent conversationally
print("--- Invoking Conversational Math Agent ---")

# Define a unique ID for this conversation
thread_config = {"configurable": {"thread_id": "math-thread-1"}}

# First turn of the conversation
print("\n--- Turn 1 ---")
question1 = "What is 15 + 7?"
for event in app.stream({"messages": [HumanMessage(content=question1)]}, config=thread_config):
    for value in event.values():
        if isinstance(value["messages"][-1], BaseMessage):
            print("Agent:", value["messages"][-1].content)

# Second turn of the conversation
print("\n--- Turn 2 ---")
question2 = "Okay, now add 10 to that number."
for event in app.stream({"messages": [HumanMessage(content=question2)]}, config=thread_config):
    for value in event.values():
        if isinstance(value["messages"][-1], BaseMessage):
            print("Agent:", value["messages"][-1].content)