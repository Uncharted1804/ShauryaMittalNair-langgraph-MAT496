from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Optional, Dict, Any

# 1. Define the State Schema (Simplified)
# Notice there is no 'Annotated' or 'operator.add' here.
class WorkOrderState(TypedDict):
    work_log: List[str]
    tasks_completed: int

# 2. Define the Custom Reducer Function
# This is the core of the lesson.
def custom_reducer(old_state: WorkOrderState, new_state_update: Optional[Dict[str, Any]]) -> WorkOrderState:
    """
    Explicitly defines how new state updates (actions) merge with the old state.
    This function is called after every node.
    """
    if new_state_update is None:
        return old_state

    print("--- REDUCER CALLED ---")
    print(f"Old state: {old_state}")
    print(f"New update (action): {new_state_update}")

    # Start with a copy of the old state
    new_state = old_state.copy()

    # Custom logic for 'work_log': append new entry if it exists
    if "work_log" in new_state_update:
        # We must explicitly define the append/add logic
        new_state["work_log"] = old_state["work_log"] + [new_state_update["work_log"]]

    # Custom logic for 'tasks_completed': increment the count if it exists
    if "tasks_completed" in new_state_update:
        new_state["tasks_completed"] = old_state.get("tasks_completed", 0) + new_state_update["tasks_completed"]

    print(f"Merged new state: {new_state}")
    return new_state

# 3. Define the Nodes
def start_work(state: WorkOrderState):
    """First node: Returns a partial update (an 'action')."""
    print("--- NODE: start_work ---")
    return {
        "work_log": "Started the job. Inspected site.",
        "tasks_completed": 1
    }

def finish_work(state: WorkOrderState):
    """Second node: Returns another partial update."""
    print("--- NODE: finish_work ---")
    return {
        "work_log": "Completed all tasks. Cleaned up site.",
        "tasks_completed": 1
    }

# 4. Define the Graph
# Pass the custom reducer to the StateGraph constructor
workflow = StateGraph(WorkOrderState, custom_reducer)

workflow.add_node("start", start_work)
workflow.add_node("finish", finish_work)

workflow.add_edge(START, "start")
workflow.add_edge("start", "finish")
workflow.add_edge("finish", END)

# 5. Compile and Run
app = workflow.compile()

print("--- Invoking Graph with Reducer ---")
initial_state = {"work_log": [], "tasks_completed": 0}
final_state = app.invoke(initial_state)

print("\n--- Final Result ---")
print(final_state)