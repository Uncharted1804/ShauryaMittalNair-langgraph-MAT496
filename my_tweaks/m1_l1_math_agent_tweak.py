import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate

from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.tools import tool

# Load environment variables
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define a Custom Tool
@tool
def simple_adder(a: int, b: int) -> int:
    """Adds two integers together. Use this for any addition questions."""
    print(f"--- TOOL CALLED: simple_adder with a={a} and b={b} ---")
    return a + b

tools = [simple_adder]

# 2. Manually create the prompt for a tool-calling agent

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}"),
   
    ("placeholder", "{agent_scratchpad}"),
])

# 3. Define the LLM 
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# 4. Create the Agent using the modern tool-calling function
# This agent is much better at formatting tool inputs correctly.
agent = create_openai_tools_agent(llm, tools, prompt)

# 5. Create the Agent Executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 6. Run the agent
print("--- Invoking Math Agent ---")
question = "What is 156 + 44?"
result = agent_executor.invoke({"input": question})

print("\n--- Final Answer ---")
print(result["output"])