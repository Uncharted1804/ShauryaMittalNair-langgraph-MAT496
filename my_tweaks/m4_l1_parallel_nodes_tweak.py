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

# 1. Define the Graph State
class TripPlannerState(TypedDict):
    """State for our trip planner graph."""
    location: str
    weather_info: str
    attractions_info: str

# 2. Define the individual nodes (LCEL chains)
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# Node 1: Get Weather
weather_prompt = ChatPromptTemplate.from_template("What is the weather forecast for {location}?")
weather_chain = weather_prompt | llm | StrOutputParser()

def get_weather_node(state: TripPlannerState):
    """Node that gets the weather."""
    print("--- NODE: get_weather --- (Running in parallel)")
    location = state['location']
    weather = weather_chain.invoke({"location": location})
    return {"weather_info": weather}

# Node 2: Get Attractions
attractions_prompt = ChatPromptTemplate.from_template("What are three popular attractions in {location}?")
attractions_chain = attractions_prompt | llm | StrOutputParser()

def get_attractions_node(state: TripPlannerState):
    """Node that gets attractions."""
    print("--- NODE: get_attractions --- (Running in parallel)")
    location = state['location']
    attractions = attractions_chain.invoke({"location": location})
    return {"attractions_info": attractions}

# Node 3: Combine results
def combine_results_node(state: TripPlannerState):
    """Node that combines the parallel results."""
    print("--- NODE: combine_results ---")
    weather = state['weather_info']
    attractions = state['attractions_info']

    print("\n--- Final Trip Plan ---")
    print(f"Location: {state['location']}")
    print(f"Weather: {weather}")
    print(f"Attractions: {attractions}")
    return {}

# 3. Define the Graph
workflow = StateGraph(TripPlannerState)

# Add the nodes
workflow.add_node("weather", get_weather_node)
workflow.add_node("attractions", get_attractions_node)
workflow.add_node("combiner", combine_results_node)

# 4. Define the Edges
# This creates the parallel "fan-out"
workflow.add_edge(START, "weather")
workflow.add_edge(START, "attractions")

# This is the "join" step. The "combiner" node will
# wait until *both* "weather" and "attractions" are complete.
workflow.add_edge("weather", "combiner")
workflow.add_edge("attractions", "combiner")

workflow.add_edge("combiner", END)

# 5. Compile and run
app = workflow.compile()

print("--- Invoking Parallel Trip Planner ---")
initial_input = {"location": "Paris, France"}
final_state = app.invoke(initial_input)