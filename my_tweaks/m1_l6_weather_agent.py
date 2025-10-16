import os
import operator
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
# This is the new, simpler way to handle tools
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define the Tools (Unchanged)
@tool
def get_current_weather(location: str):
    """Get the current weather for a specific location."""
    print(f"--- TOOL: get_current_weather for {location} ---")
    return f"The weather in {location} is currently 75°F and sunny."

@tool
def get_weather_forecast(location: str, days: int):
    """Get the weather forecast for a specific location for a number of days."""
    print(f"--- TOOL: get_weather_forecast for {location} over {days} days ---")
    return f"The {days}-day forecast for {location} is sunny with a high of 80°F."

tools = [get_current_weather, get_weather_forecast]

# 2. Define the State (Unchanged)
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 3. Define the Nodes
llm = ChatOpenAI(model="gpt-4o-mini")
# Bind the tools to the LLM so it knows what functions it can call
llm_with_tools = llm.bind_tools(tools)

# The agent node decides what to do next
def agent_node(state: AgentState):
    """The primary node that decides the next action."""
    print("--- NODE: agent ---")
    response = llm_with_tools.invoke(state['messages'])
    return {"messages": [response]}

# The ToolNode replaces our old manual tool_node function
tool_node = ToolNode(tools)

# 4. Define the Router (Conditional Edge) - Simplified
def should_continue(state: AgentState):
    """Determines whether to continue the loop or end."""
    last_message = state['messages'][-1]
    # If the last message has no tool calls, the agent is done
    if not last_message.tool_calls:
        return END
    # Otherwise, call the tool node
    else:
        return "tool_node"

# 5. Define the Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent_node", agent_node)
workflow.add_node("tool_node", tool_node) # Use the pre-built ToolNode

workflow.add_conditional_edges("agent_node", should_continue)
workflow.add_edge("tool_node", "agent_node") # This creates the loop
workflow.add_edge(START, "agent_node")

app = workflow.compile()

# 6. Run the agent
print("--- Invoking Weather Agent ---")
question = "What is the 3-day forecast for New York?"
# Use HumanMessage for proper formatting
final_state = app.invoke({"messages": [HumanMessage(content=question)]})

print("\n--- Final Answer ---")
print(final_state['messages'][-1].content)