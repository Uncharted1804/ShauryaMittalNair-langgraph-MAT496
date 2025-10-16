import os
from dotenv import load_dotenv
from typing import TypedDict, Literal
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

# Load environment variables and enable tracing
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. Define the State
class CustomerServiceState(TypedDict):
    """State for our customer service agent."""
    query: str
    category: str
    response: str

# 2. Define the Router Logic
class RouteQuery(BaseModel):
    """Routes a user query to the appropriate department."""
    destination: Literal["billing", "technical_support", "general_inquiry"] = Field(
        description="The department that can best handle the user's query."
    )

# LLM with structured output to force the router's decision
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
structured_llm = llm.with_structured_output(RouteQuery)

# Prompt for the router
router_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert at routing customer queries. "
               "Based on the user's question, route it to the correct department."),
    ("human", "{query}")
])

# The router function itself
def classify_query(state: CustomerServiceState):
    """Node that classifies the user's query."""
    print("--- NODE: classify_query ---")
    query = state.get("query")
    router_chain = router_prompt | structured_llm
    result = router_chain.invoke({"query": query})
    print(f"Classification result: {result.destination}")
    return {"category": result.destination}

# 3. Define the Specialist Nodes
def billing_node(state: CustomerServiceState):
    """Node that handles billing questions."""
    print("--- NODE: billing_node ---")
    return {"response": "Thank you for your billing question. We will connect you to a billing specialist shortly."}

def tech_support_node(state: CustomerServiceState):
    """Node that handles technical support questions."""
    print("--- NODE: tech_support_node ---")
    return {"response": "Thank you for your technical question. An expert will be with you to resolve your issue."}

def general_inquiry_node(state: CustomerServiceState):
    """Node that handles general inquiries."""
    print("--- NODE: general_inquiry_node ---")
    return {"response": "Thank you for your question. A general support agent will be here to help you soon."}

# 4. Define the Graph
workflow = StateGraph(CustomerServiceState)

# Add nodes
workflow.add_node("classifier", classify_query)
workflow.add_node("billing", billing_node)
workflow.add_node("tech_support", tech_support_node)
workflow.add_node("general", general_inquiry_node)

# 5. Define the Edges
workflow.add_edge(START, "classifier")
# The conditional edge is based on the 'category' field in the state
workflow.add_conditional_edges(
    "classifier",
    lambda state: state["category"],
    {
        "billing": "billing",
        "technical_support": "tech_support",
        "general_inquiry": "general"
    }
)
workflow.add_edge("billing", END)
workflow.add_edge("tech_support", END)
workflow.add_edge("general", END)

# 6. Compile and run the graph
app = workflow.compile()

print("--- Invoking Customer Service Router ---")
query = "Hi, my internet is not working. Can you help me fix it?"
final_state = app.invoke({"query": query})

print("\n--- Final Result ---")
print(final_state)