from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, List
import operator

# 1. Define the State Schema
# This is the core of the lesson.
class WorkOrderState(TypedDict):
    """State for a simple work order process."""

    # This field will be OVERWRITTEN at each step
    current_status: str

    # This field will ACCUMULATE (append) new items
    status_history: Annotated[List[str], operator.add]

    # This field will ACCUMULATE (sum) numbers
    steps_completed: Annotated[int, operator.add]

# 2. Define the Nodes
def start_work(state: WorkOrderState):
    """First node: Begins the work order."""
    print("--- NODE: start_work ---")
    return {
        "current_status": "In Progress",
        "status_history": ["Work order received"],
        "steps_completed": 1
    }

def complete_work(state: WorkOrderState):
    """Second node: Finishes the work order."""
    print("--- NODE: complete_work ---")
    return {
        "current_status": "Completed",
        "status_history": ["Work finished and verified"],
        "steps_completed": 1
    }

# 3. Define and build the graph
workflow = StateGraph(WorkOrderState)

workflow.add_node("start", start_work)
workflow.add_node("complete", complete_work)

workflow.add_edge(START, "start")
workflow.add_edge("start", "complete")
workflow.add_edge("complete", END)

# 4. Compile the graph
app = workflow.compile()

# 5. Run the graph with an initial empty state
print("--- Invoking Work Order Graph ---")
initial_state = {
    "current_status": "Not Started",
    "status_history": [],
    "steps_completed": 0
}
final_state = app.invoke(initial_state)

print("\n--- Final Result ---")
print(f"Final Status (Overwritten): {final_state['current_status']}")
print(f"Status History (Accumulated): {final_state['status_history']}")
print(f"Steps Completed (Summed): {final_state['steps_completed']}")