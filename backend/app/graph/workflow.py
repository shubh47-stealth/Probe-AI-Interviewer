# backend/app/graph/workflow.py
import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from app.schemas.interview import TurnEvaluation
from app.retrieval.hybrid_engine import HybridRAGEngine

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 1. Initialize Hybrid RAG + Cross-Encoder Reranker Engine
rag_engine = HybridRAGEngine()
rubrics_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "rubrics")
rag_engine.load_rubrics_directory(rubrics_dir)

# 2. Multi-Model Failover Chain
model_3_5_lite = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", google_api_key=api_key, max_retries=1)
model_3_7 = ChatGoogleGenerativeAI(model="gemini-3.7-flash", google_api_key=api_key, temperature=0.3, max_retries=1)
model_3_8 = ChatGoogleGenerativeAI(model="gemini-3.8-flash", google_api_key=api_key, temperature=0.3, max_retries=1)

llm = model_3_5_lite.with_fallbacks([model_3_7, model_3_8])
structured_evaluator = model_3_5_lite.with_structured_output(TurnEvaluation).with_fallbacks([
    model_3_7.with_structured_output(TurnEvaluation),
    model_3_8.with_structured_output(TurnEvaluation)
])

# 3. Graph State
class InterviewState(TypedDict):
    syllabus: List[str]
    current_topic_idx: int
    probe_count: int
    current_question: str
    latest_user_answer: str
    retrieved_context: str
    retrieved_chunks_telemetry: List[dict]  # Stores BM25, Vector, and Reranker scores for X-Ray UI!
    latest_evaluation: dict
    evaluations_log: List[dict]
    is_complete: bool

# 4. Node 0: Hybrid Retrieval + Cross-Encoder Reranking
def retrieve_context_node(state: InterviewState) -> dict:
    current_topic = state["syllabus"][state["current_topic_idx"]]
    search_query = f"{current_topic} | Question: {state['current_question']} | Answer: {state['latest_user_answer']}"
    
    top_chunks = rag_engine.retrieve_and_rerank(search_query, top_k_initial=10, top_k_final=3)
    
    formatted_context = "\n\n".join(
        [f"[{c.source} | Rerank Score: {c.rerank_score}]\n{c.content}" for c in top_chunks]
    )
    telemetry = [c.model_dump() for c in top_chunks]
    
    return {
        "retrieved_context": formatted_context,
        "retrieved_chunks_telemetry": telemetry
    }

# 5. Node 1: Silent Grader (Structured JSON output)
def evaluate_answer_node(state: InterviewState) -> dict:
    current_topic = state["syllabus"][state["current_topic_idx"]]
    
    prompt = f"""You are a strict Senior Engineering Bar-Raiser evaluating a candidate's answer.
    
Topic: {current_topic}
Question Asked: {state['current_question']}
Candidate's Answer: {state['latest_user_answer']}

Retrieved Ground-Truth Rubric & Codebase Chunks:
{state.get('retrieved_context', '')}

Evaluate the candidate's answer strictly against the retrieved chunks. 
If they gave a high-level or vague answer without explaining 'how' or 'why', score < 7 and set routing_decision to PROBE_DEEPER."""

    eval_result: TurnEvaluation = structured_evaluator.invoke([HumanMessage(content=prompt)])
    
    probe_count = state["probe_count"]
    topic_idx = state["current_topic_idx"]
    
    if eval_result.specificity_score < 7 and probe_count < 2:
        decision = "PROBE_DEEPER"
        new_probe_count = probe_count + 1
        new_topic_idx = topic_idx
    else:
        decision = "NEXT_TOPIC"
        new_probe_count = 0
        new_topic_idx = topic_idx + 1

    eval_dict = eval_result.model_dump()
    eval_dict["routing_decision"] = decision
    eval_dict["topic"] = current_topic
    eval_dict["question"] = state["current_question"]
    eval_dict["user_answer"] = state["latest_user_answer"]
    eval_dict["retrieved_chunks"] = state.get("retrieved_chunks_telemetry", [])

    return {
        "latest_evaluation": eval_dict,
        "evaluations_log": state.get("evaluations_log", []) + [eval_dict],
        "probe_count": new_probe_count,
        "current_topic_idx": new_topic_idx,
        "is_complete": new_topic_idx >= len(state["syllabus"])
    }

# 6. Node 2: Conversational Interviewer
def generate_question_node(state: InterviewState) -> dict:
    if state.get("is_complete"):
        return {"current_question": "That concludes our interview session! Compiling your diagnostic report now..."}

    eval_data = state.get("latest_evaluation")
    current_topic = state["syllabus"][state["current_topic_idx"]]

    if eval_data and eval_data["routing_decision"] == "PROBE_DEEPER":
        prompt = f"""You are a sharp Technical Interviewer.
The candidate gave a vague answer to: "{state['current_question']}"
Their answer was: "{state['latest_user_answer']}"

They missed: {', '.join(eval_data['missed_or_vague_points'])}
Angle to probe: {eval_data['suggested_probe_angle']}

Ask a direct, polite follow-up question forcing them to explain that specific gap. Do not give away the solution."""
    else:
        # Retrieve opening context for the new topic
        opening_chunks = rag_engine.retrieve_and_rerank(current_topic, top_k_final=2)
        opening_context = "\n".join([c.content for c in opening_chunks])
        prompt = f"""You are a Technical Interviewer moving to the next topic: "{current_topic}".
Context: {opening_context}

Ask a concrete, scenario-based opening question for this topic."""

    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    if isinstance(content, list):
        content = "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return {"current_question": content.strip('"')}

# 7. Compile Graph: Retrieve -> Evaluate -> Generate Question
def build_interview_turn_graph():
    workflow = StateGraph(InterviewState)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("evaluate_answer", evaluate_answer_node)
    workflow.add_node("generate_question", generate_question_node)
    
    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "evaluate_answer")
    workflow.add_edge("evaluate_answer", "generate_question")
    workflow.add_edge("generate_question", END)
    
    return workflow.compile()