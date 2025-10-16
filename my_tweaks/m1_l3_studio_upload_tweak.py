from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# 1. Define the state
class BasicGraphState(TypedDict):
    """Represents the state of our graph with a number and a message."""
    number: int
    message: str

# 2. Define the nodes
def add_one(state: BasicGraphState):
    """Adds 1 to the number."""
    print("--- NODE: add_one ---")
    return {"number": state["number"] + 1, "message": "Added 1"}

def subtract_one(state: BasicGraphState):
    """Subtracts 1 from the number."""
    print("--- NODE: subtract_one ---")
    return {"number": state["number"] - 1, "message": "Subtracted 1"}

# 3. Define the conditional edge logic
def should_add_or_subtract(state: BasicGraphState):
    """Determines which path to take based on the number."""
    print(f"\n--- CONDITIONAL EDGE on number: {state['number']} ---")
    if state["number"] > 10:
        print("Decision: Number is > 10, routing to 'subtract'")
        return "subtract"
    else:
        print("Decision: Number is <= 10, routing to 'add'")
        return "add"

# 4. Define and compile the graph (Unchanged)
workflow = StateGraph(BasicGraphState)
workflow.add_node("add_node", add_one)
workflow.add_node("subtract_node", subtract_one)
workflow.add_conditional_edges(
    START,
    should_add_or_subtract,
    {"add": "add_node", "subtract": "subtract_node"}
)
workflow.add_edge("add_node", END)
workflow.add_edge("subtract_node", END)
graph = workflow.compile()

# 5. TEST THE GRAPH DIRECTLY 
print("--- STARTING GRAPH TEST ---")

# Test Case 1: The "add" path
print("\n--- Test Case 1: Inputting a small number ---")
input1 = {"number": 5}
final_state1 = graph.invoke(input1)
print(f"Final State for Test Case 1: {final_state1}")

# Test Case 2: The "subtract" path
print("\n--- Test Case 2: Inputting a large number ---")
input2 = {"number": 15}
final_state2 = graph.invoke(input2)
print(f"Final State for Test Case 2: {final_state2}")