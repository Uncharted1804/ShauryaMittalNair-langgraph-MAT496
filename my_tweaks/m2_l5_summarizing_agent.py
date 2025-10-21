import os
import operator
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define the Summarizer Chain
summarizer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert summarizer. Create a concise, third-person summary of the conversation so far."),
    ("user", "{conversation_history}")
])
summarizer_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
summarizer_chain = summarizer_prompt | summarizer_llm | StrOutputParser()

# 2. Define the Tool
@tool
def simple_adder(a: int, b: int) -> int:
    """Adds two integers together. Use this for any addition questions."""
    print(f"--- TOOL CALLED: simple_adder with a={a} and b={b} ---")
    return a + b

tools = [simple_adder]
tool_node = ToolNode(tools)

# 3. Define the State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 4. Define the Nodes
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState):
    """The primary node that decides the next action AND summarizes history."""
    print("--- NODE: agent ---")
    messages = state['messages']

    # Set the limit for summarization
    MAX_MESSAGES = 6 # e.g., 3 turns (H, AI-tool-call, Tool)

    # Check if we need to summarize
    if len(messages) > MAX_MESSAGES:
        print(f"History too long ({len(messages)}). Summarizing old messages.")

        # We'll summarize all but the last 2 messages (the most recent turn)
        messages_to_summarize = messages[:-2]

        # Create a simple string of the conversation
        history_str = "\n".join([f"{m.type}: {m.content}" for m in messages_to_summarize])

        # Call the summarizer chain
        summary = summarizer_chain.invoke({"conversation_history": history_str})
        print(f"Generated Summary: {summary}")

        # Create the new, trimmed message list
        # It starts with the new summary, then adds the recent messages
        messages_to_send = [SystemMessage(content=summary)] + messages[-2:]

    else:
        print(f"History length ({len(messages)}) is within limit.")
        messages_to_send = messages

    # Agent invokes LLM with the (potentially summarized) history
    response = llm_with_tools.invoke(messages_to_send)
    return {"messages": [response]}

# 5. Define the Router and Graph
def should_continue(state: AgentState):
    if not state['messages'][-1].tool_calls:
        return END
    else:
        return "tool_node"

workflow = StateGraph(AgentState)
workflow.add_node("agent_node", agent_node)
workflow.add_node("tool_node", tool_node)
workflow.add_conditional_edges("agent_node", should_continue)
workflow.add_edge("tool_node", "agent_node")
workflow.add_edge(START, "agent_node")

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 6. Run the agent to test summarization
print("--- Invoking Conversational Agent (with Summarization) ---")
thread_config = {"configurable": {"thread_id": "math-summary-thread-1"}}

print("\n--- Turn 1 ---")
question1 = "What is 10 + 5?"
app.invoke({"messages": [HumanMessage(content=question1)]}, config=thread_config)

print("\n--- Turn 2 ---")
question2 = "What is 2 + 1?"
app.invoke({"messages": [HumanMessage(content=question2)]}, config=thread_config)

print("\n--- Turn 3 (Summarization should activate here) ---")
question3 = "What is 3 + 3?"
app.invoke({"messages": [HumanMessage(content=question3)]}, config=thread_config)