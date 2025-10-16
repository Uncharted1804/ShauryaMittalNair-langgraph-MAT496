from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
import operator

# 1. Define the state for our graph
# It will contain a single number that we operate on.
class MathGraphState(TypedDict):
    """Represents the state of our math graph."""
    current_number: int

# 2. Define the nodes (functions)
# Each node will modify the state.
def add_five(state: MathGraphState):
    """Node that adds 5 to the current number."""
    print("--- NODE: add_five ---")
    current_number = state['current_number']
    new_number = current_number + 5
    print(f"Adding 5 to {current_number}, result is {new_number}")
    return {"current_number": new_number}

def subtract_three(state: MathGraphState):
    """Node that subtracts 3 from the current number."""
    print("--- NODE: subtract_three ---")
    current_number = state['current_number']
    new_number = current_number - 3
    print(f"Subtracting 3 from {current_number}, result is {new_number}")
    return {"current_number": new_number}

# 3. Define the graph
workflow = StateGraph(MathGraphState)

# 4. Add the nodes to the graph
workflow.add_node("add", add_five)
workflow.add_node("subtract", subtract_three)

# 5. Define the edges that connect the nodes
workflow.add_edge(START, "add")       # The graph starts at the 'add' node
workflow.add_edge("add", "subtract")  # After 'add', it goes to 'subtract'
workflow.add_edge("subtract", END)    # After 'subtract', the graph finishes

# 6. Compile the graph into a runnable object
app = workflow.compile()

# 7. Run the graph with an initial input
print("--- Invoking Simple Math Graph ---")
initial_input = {"current_number": 10}
final_state = app.invoke(initial_input)

print("\n--- Final Result ---")
print(final_state)