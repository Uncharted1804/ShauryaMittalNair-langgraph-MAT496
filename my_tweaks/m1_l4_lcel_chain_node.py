import os
from dotenv import load_dotenv
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define the LangChain (LCEL) Chain
# This chain will be our node's logic.
prompt = ChatPromptTemplate.from_template("Write a funny, one-sentence tweet about {topic}.")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
output_parser = StrOutputParser()

# The actual chain object
tweet_chain = prompt | llm | output_parser

# 2. Define the Graph State
class TweetGraphState(TypedDict):
    """Represents the state of our tweet generation graph."""
    topic: str
    tweet: str

# 3. Define the Node
# This function wraps our LCEL chain. It takes the graph state,
# invokes the chain with the topic, and returns the updated state.
def generate_tweet_node(state: TweetGraphState):
    """Node that runs the tweet_chain to generate a tweet."""
    print("--- NODE: generate_tweet ---")
    topic = state.get("topic")

    # Invoke the LCEL chain
    tweet = tweet_chain.invoke({"topic": topic})
    print(f"Generated Tweet: {tweet}")

    return {"tweet": tweet}

# 4. Define and build the graph
workflow = StateGraph(TweetGraphState)

workflow.add_node("generator", generate_tweet_node)

workflow.add_edge(START, "generator")
workflow.add_edge("generator", END)

# 5. Compile the graph
app = workflow.compile()

# 6. Run the graph
print("--- Invoking Tweet Generation Graph ---")
initial_input = {"topic": "AI trying to write code"}
final_state = app.invoke(initial_input)

print("\n--- Final Result ---")
print(final_state)