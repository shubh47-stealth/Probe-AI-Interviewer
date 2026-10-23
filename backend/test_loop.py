# backend/test_loop.py
from app.graph.workflow import build_interview_turn_graph

graph = build_interview_turn_graph()

state = {
    "syllabus": [
        "Redux Toolkit State Management & Re-render Optimization",
        "Database Indexing & Query Performance"
    ],
    "current_topic_idx": 0,
    "probe_count": 0,
    "current_question": "In your Blog project, you used Redux Toolkit for auth and posts. How did you prevent unnecessary component re-renders when a single post is updated?",
    "latest_user_answer": "I just used useSelector in my components because Redux makes state management fast.",
    "retrieved_context": "",
    "retrieved_chunks_telemetry": [],
    "latest_evaluation": {},
    "evaluations_log": [],
    "is_complete": False
}

print("\nRunning turn through Hybrid RAG -> Cross-Encoder -> LangGraph Evaluator...")
result = graph.invoke(state)

print("\n--- 1. HYBRID RAG & CROSS-ENCODER TELEMETRY ---")
for idx, chunk in enumerate(result["retrieved_chunks_telemetry"], 1):
    print(f"Top {idx} | Source: {chunk['source']} | BM25 Rank: #{chunk['bm25_rank']} | Vector Rank: #{chunk['vector_rank']} | Rerank Score: {chunk['rerank_score']}")

print("\n--- 2. X-RAY EVALUATOR OUTPUT ---")
print(f"Specificity Score: {result['latest_evaluation']['specificity_score']}/10")
print(f"Missed Points: {result['latest_evaluation']['missed_or_vague_points']}")
print(f"Routing Decision: {result['latest_evaluation']['routing_decision']} (Probe Count: {result['probe_count']}/2)")

print("\n--- 3. AI INTERVIEWER FOLLOW-UP ---")
print(result["current_question"])