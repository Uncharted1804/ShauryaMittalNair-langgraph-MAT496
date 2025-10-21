import os
import operator
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
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
    """The primary node that decides the next action AND trims history."""
    print("--- NODE: agent ---")

    # --- THIS IS THE TWEAK ---
    # Get all messages from the state
    messages = state['messages']

    # Define the max number of messages to keep (e.D., 6 messages = 3 turns)
    MAX_MESSAGES = 6 

    if len(messages) > MAX_MESSAGES:
        print(f"History too long ({len(messages)}). Trimming to last {MAX_MESSAGES} messages.")
        # This slices the list, keeping only the last 6 items
        messages_to_send = messages[-MAX_MESSAGES:]
    else:
        print(f"History length ({len(messages)}) is within limit.")
        messages_to_send = messages
    # --- END OF TWEAK ---

    # The agent invokes the LLM with the (potentially trimmed) message history
    response = llm_with_tools.invoke(messages_to_send)
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

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 6. Run the agent conversationally to test the trimming
print("--- Invoking Conversational Agent (with Trimming) ---")
thread_config = {"configurable": {"thread_id": "math-trim-thread-1"}}

# We will run 3 turns. Each turn adds 3 messages (H, AI-tool-call, Tool).
# By the 3rd turn (9 messages), the trimming should activate.

print("\n--- Turn 1 ---")
question1 = "What is 10 + 5?"
app.invoke({"messages": [HumanMessage(content=question1)]}, config=thread_config)

print("\n--- Turn 2 ---")
question2 = "What is 2 + 1?"
app.invoke({"messages": [HumanMessage(content=question2)]}, config=thread_config)

print("\n--- Turn 3 (Trimming should activate here) ---")
question3 = "What is 3 + 3?"
app.invoke({"messages": [HumanMessage(content=question3)]}, config=thread_config)