from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Dict, Any

# 1. Define the state and nodes for the INNER graph (Transport)
class TransportState(TypedDict):
    """State for the transport booking subgraph."""
    destination: str
    confirmation: str

def book_flight(state: TransportState):
    """A node that 'books' a flight."""
    print("--- SUBGRAPH NODE: book_flight ---")
    destination = state['destination']
    confirmation_code = f"FL-{destination.upper()}-1234"
    return {"confirmation": confirmation_code}

# 2. Build the INNER graph
transport_workflow = StateGraph(TransportState)
transport_workflow.add_node("book_flight", book_flight)
transport_workflow.add_edge(START, "book_flight")
transport_workflow.add_edge("book_flight", END)
transport_graph = transport_workflow.compile()

# 3. Define the state and nodes for the OUTER graph (Trip Planner)
class TripPlannerState(TypedDict):
    """State for the main trip planner graph."""
    destination: str
    itinerary: str
    transport_details: str # This will be set by the subgraph

def plan_activities(state: TripPlannerState):
    """A node that plans the trip itinerary."""
    print("--- MAIN GRAPH NODE: plan_activities ---")
    destination = state['destination']
    return {"itinerary": f"Day 1: Arrive in {destination} and explore."}

# --- THIS IS THE NEW WRAPPER FUNCTION ---
def run_transport_subgraph(state: TripPlannerState):
    """
    A wrapper node to explicitly call the subgraph.
    It handles mapping the input and output.
    """
    print("--- MAIN GRAPH NODE: book_transport (wrapper) ---")
    
    # 1. Get the required input from the main state
    destination = state['destination']
    
    # 2. Call the subgraph with the correct input
    subgraph_output = transport_graph.invoke({"destination": destination})
    
    # 3. Return the update for the main graph's state
    return {"transport_details": subgraph_output['confirmation']}
# ----------------------------------------

def finalize_trip(state: TripPlannerState):
    """A node that compiles the final trip details."""
    print("--- MAIN GRAPH NODE: finalize_trip ---")
    print("\n--- Final Trip Plan ---")
    print(f"Destination: {state['destination']}")
    print(f"Itinerary: {state['itinerary']}")
    
    # This line will now work correctly
    print(f"Transport: {state['transport_details']}")
    return {}

# 4. Build the OUTER graph
main_workflow = StateGraph(TripPlannerState)
main_workflow.add_node("plan_activities", plan_activities)
main_workflow.add_node("finalize_trip", finalize_trip)

# --- THIS IS THE UPDATED NODE CALL ---
# Add the subgraph by calling our new wrapper function
main_workflow.add_node("book_transport", run_transport_subgraph)
# -----------------------------------

# 5. Define the edges for the OUTER graph
main_workflow.add_edge(START, "plan_activities")
main_workflow.add_edge("plan_activities", "book_transport")
main_workflow.add_edge("book_transport", "finalize_trip")
main_workflow.add_edge("finalize_trip", END)

# 6. Compile and run the main graph
app = main_workflow.compile()

print("--- Invoking Main Trip Planner Graph ---")
initial_input = {"destination": "Paris"}
app.invoke(initial_input)