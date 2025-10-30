import os
from dotenv import load_dotenv
from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define the Graph State
class MapReduceState(TypedDict):
    """State for our map-reduce graph."""
    topics: List[str]
    summaries: List[str]
    final_report: str

# 2. Define the "Map" Node
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
map_prompt = ChatPromptTemplate.from_template("Write a one-paragraph summary of the following topic: {topic}")
map_chain = map_prompt | llm | StrOutputParser()

def map_summarizer_node(state: MapReduceState):
    """
    The 'Map' node. It runs the map_chain in parallel
    on every topic in the state.
    """
    print("--- NODE: map_summarizer (running in parallel) ---")
    topics = state['topics']

    # Use .batch() to run the chain in parallel for each topic
    # We prepare the inputs as a list of dictionaries
    batch_inputs = [{"topic": t} for t in topics]
    summaries = map_chain.batch(batch_inputs)

    print(f"Generated {len(summaries)} summaries.")
    return {"summaries": summaries}

# 3. Define the "Reduce" Node
reduce_prompt = ChatPromptTemplate.from_template(
    "You are an expert research assistant. Combine the following summaries "
    "into a single, cohesive report.\n\nSummaries:\n{summaries_list}"
)
reduce_chain = reduce_prompt | llm | StrOutputParser()

def reduce_combiner_node(state: MapReduceState):
    """
    The 'Reduce' node. It combines all summaries into
    a single final report.
    """
    print("--- NODE: reduce_combiner ---")
    summaries = state['summaries']

    # Join the summaries with a separator
    joined_summaries = "\n\n---\n\n".join(summaries)

    report = reduce_chain.invoke({"summaries_list": joined_summaries})

    print("\n--- Final Report Generated ---")
    print(report[:250] + "...") # Print a snippet

    return {"final_report": report}

# 4. Define the Graph
workflow = StateGraph(MapReduceState)
workflow.add_node("mapper", map_summarizer_node)
workflow.add_node("reducer", reduce_combiner_node)

workflow.add_edge(START, "mapper")
workflow.add_edge("mapper", "reducer")
workflow.add_edge("reducer", END)

# 5. Compile and run
app = workflow.compile()

print("--- Invoking Map-Reduce Graph ---")
initial_input = {
    "topics": [
        "The history of the Eiffel Tower",
        "The rise of renewable energy in Europe",
        "The basics of quantum computing"
    ]
}
final_state = app.invoke(initial_input)