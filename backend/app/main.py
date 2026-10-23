# backend/app/main.py
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from app.schemas.interview import InterviewPlan
from app.ingestion.loader import extract_text_from_pdf_bytes, fetch_github_repo_files
from app.graph.workflow import (
    build_interview_turn_graph,
    rag_engine,
    llm,
    model_3_5_lite,
    model_3_7,
    model_3_8
)

app = FastAPI(title="ProbeAI — Adaptive Technical Interviewer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile LangGraph once at startup
interview_graph = build_interview_turn_graph()

# Structured planner with multi-model fallback
structured_planner = model_3_5_lite.with_structured_output(InterviewPlan).with_fallbacks([
    model_3_7.with_structured_output(InterviewPlan),
    model_3_8.with_structured_output(InterviewPlan)
])

# In-memory session store
SESSIONS: Dict[str, dict] = {}

class TurnRequest(BaseModel):
    user_answer: str

@app.post("/api/v1/session/init")
async def initialize_session(
    job_description: str = Form(...),
    github_url: Optional[str] = Form(None),
    resume_text_override: Optional[str] = Form(None),
    resume_pdf: Optional[UploadFile] = File(None)
):
    session_id = str(uuid.uuid4())

    # 1. Parse Resume (PDF upload or raw text)
    resume_text = resume_text_override or ""
    if resume_pdf:
        pdf_bytes = await resume_pdf.read()
        resume_text = extract_text_from_pdf_bytes(pdf_bytes)

    if resume_text:
        rag_engine.ingest_chunks([{"source": "candidate:resume.pdf", "content": resume_text}])

    # 2. Fetch & Index GitHub Repository Code
    repo_files = []
    if github_url:
        repo_files = fetch_github_repo_files(github_url, max_files=12)
        if repo_files:
            rag_engine.ingest_chunks(repo_files, chunk_size=140, overlap=30)

    repo_summary = ", ".join([f["source"] for f in repo_files]) if repo_files else "No GitHub repo provided."

    # 3. Generate Tailored 4-Topic Syllabus + Opening Question
    planner_prompt = f"""You are a Principal Engineer designing a rigorous 4-topic technical interview.

Candidate Resume:
{resume_text[:3000]}

Indexed GitHub Repository Files:
{repo_summary}

Target Job Description:
{job_description[:2000]}

Create a 4-topic interview syllabus:
- Topic 1 MUST test architecture and implementation details of their actual projects/codebase.
- Topic 2 & 3 MUST test core engineering concepts required by the Job Description (e.g., React/Redux optimization, APIs, Databases, DSA).
- Topic 4 MUST test edge-case debugging or system scalability.
Also generate a concrete opening question for Topic 1."""

    plan: InterviewPlan = structured_planner.invoke([HumanMessage(content=planner_prompt)])

    # 4. Initialize Session State
    SESSIONS[session_id] = {
        "session_id": session_id,
        "syllabus": plan.syllabus,
        "current_topic_idx": 0,
        "probe_count": 0,
        "current_question": plan.opening_question,
        "latest_user_answer": "",
        "retrieved_context": "",
        "retrieved_chunks_telemetry": [],
        "latest_evaluation": None,
        "evaluations_log": [],
        "is_complete": False
    }

    return {
        "session_id": session_id,
        "syllabus": plan.syllabus,
        "current_topic_idx": 0,
        "indexed_repo_files": [f["source"] for f in repo_files],
        "question": plan.opening_question
    }

@app.post("/api/v1/session/{session_id}/turn")
async def process_interview_turn(session_id: str, payload: TurnRequest):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    state = SESSIONS[session_id]
    if state["is_complete"]:
        return {"message": "Interview is already complete.", "is_complete": True}

    state["latest_user_answer"] = payload.user_answer

    # Run through Hybrid RAG -> Cross-Encoder Reranker -> Evaluator -> Question Generator
    updated_state = interview_graph.invoke(state)
    SESSIONS[session_id] = updated_state

    return {
        "session_id": session_id,
        "current_topic_idx": updated_state["current_topic_idx"],
        "probe_count": updated_state["probe_count"],
        "is_complete": updated_state["is_complete"],
        "next_question": updated_state["current_question"],
        "xray_telemetry": {
            "evaluation": updated_state["latest_evaluation"],
            "retrieved_chunks": updated_state["retrieved_chunks_telemetry"]
        }
    }

@app.get("/api/v1/session/{session_id}/report")
async def get_diagnostic_report(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    state = SESSIONS[session_id]
    logs = state.get("evaluations_log", [])
    if not logs:
        raise HTTPException(status_code=400, detail="No interview turns recorded yet.")

    avg_score = round(sum(item["specificity_score"] for item in logs) / len(logs), 1)
    
    return {
        "session_id": session_id,
        "overall_score": avg_score,
        "total_turns": len(logs),
        "probed_turns_count": sum(1 for item in logs if item["routing_decision"] == "PROBE_DEEPER"),
        "turn_by_turn_breakdown": logs
    }