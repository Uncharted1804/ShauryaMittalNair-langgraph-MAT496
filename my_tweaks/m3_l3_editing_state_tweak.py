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

# 1. Define the "Dangerous" Tool (Unchanged)
@tool
def update_user_profile(username: str, data_to_update: str):
    """Updates a user's profile in the database. Only use if explicitly approved."""
    print(f"--- TOOL CALLED: Updating {username}'s profile with '{data_to_update}' ---")
    return f"Successfully updated {username}'s profile."

tools = [update_user_profile]
tool_node = ToolNode(tools)

# 2. Define the State (Unchanged)
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 3. Define the Nodes (THIS IS THE CORRECTED PART)
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState):
    """The primary node that decides the next action."""
    print("--- NODE: agent ---")
    
    messages = state['messages']
    
    # --- NEW CLEANUP LOGIC ---
    cleaned_messages = []
    for i, msg in enumerate(messages):
        cleaned_messages.append(msg)
        
        # --- THIS IS THE FIX ---
        # We must check if the message is an AI message *before*
        # trying to access its .tool_calls attribute.
        if msg.type == "ai":
        # --- END OF FIX ---
        
            # Check if the message has tool calls
            if msg.tool_calls:
                # Check if the next message is a tool response
                if i + 1 < len(messages) and messages[i+1].type == "tool":
                    # The tool call was executed, so we're good
                    pass
                else:
                    # The tool call was NOT executed (e.g., human interrupted)
                    # We need to remove this dangling tool call to avoid an API error
                    print("--- AGENT NODE: Pruning dangling tool call ---")
                    cleaned_messages.pop() 
    # --- END OF CLEANUP LOGIC ---

    # Invoke the LLM with the cleaned message history
    response = llm_with_tools.invoke(cleaned_messages)
    return {"messages": [response]}

# 4. Define the Router (Unchanged)
def should_continue(state: AgentState):
    """A more robust router that handles human feedback."""
    last_message = state['messages'][-1]

    if isinstance(last_message, HumanMessage):
        return "agent_node"
    if not last_message.tool_calls:
        return END
    else:
        return "tool_node"

# 5. Define the Graph (Unchanged)
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

# 6. Run the agent (Unchanged)
print("--- Invoking Agent with HITL Correction ---")
thread_config = {"configurable": {"thread_id": "correction-thread-1"}}

print("\n--- Turn 1: User Request ---")
question = "Please update my profile, shaurya, to say 'LangGraph expert'."
for event in app.stream({"messages": [HumanMessage(content=question)]}, config=thread_config):
    print(event)

print("\n--- GRAPH PAUSED ---")
current_state = app.get_state(thread_config)
last_message = current_state.values['messages'][-1]
print(f"Agent wants to run tool: {last_message.tool_calls[0]['args']}")

print("\n--- Turn 2: Human Corrects the Agent's Plan ---")
feedback_message = HumanMessage(content="Actually, please change that to 'LangGraph and LangSmith expert'.")

app.update_state(thread_config, {"messages": [feedback_message]})
print("Human feedback added to state.")

for event in app.stream(None, config=thread_config):
    print(event)
    
print("\n--- GRAPH PAUSED A SECOND TIME ---")
current_state = app.get_state(thread_config)
last_message = current_state.values['messages'][-1]
print(f"Agent's NEW plan: {last_message.tool_calls[0]['args']}")

print("\n--- Turn 3: Human Approves the Corrected Plan ---")
for event in app.stream(None, config=thread_config):
    print(event)

print("\n--- FINAL STATE ---")
final_state = app.get_state(thread_config)
print(final_state.values['messages'][-1].content)