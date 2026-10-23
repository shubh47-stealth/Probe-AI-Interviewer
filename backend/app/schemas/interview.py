from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class RubricChunk(BaseModel):
    chunk_id: str
    source: str
    content: str
    bm25_rank: Optional[int] = None
    vector_rank: Optional[int] = None
    rerank_score: float = 0.0

class TurnEvaluation(BaseModel):
    specificity_score: int = Field(
        ..., ge=1, le=10,
        description="Score from 1 to 10 evaluating technical depth, trade-offs, and accuracy against the retrieved rubric."
    )
    covered_points: List[str] = Field(
        default_factory=list,
        description="Specific technical concepts from the rubric that the candidate explained well."
    )
    missed_or_vague_points: List[str] = Field(
        default_factory=list,
        description="Crucial concepts, edge cases, or implementation details the candidate skipped or answered vaguely."
    )
    routing_decision: Literal["PROBE_DEEPER", "NEXT_TOPIC"] = Field(
        ...,
        description="Must be PROBE_DEEPER if specificity_score < 7, otherwise NEXT_TOPIC."
    )
    suggested_probe_angle: str = Field(
        ...,
        description="If probing deeper, specify the exact technical gap or edge case the interviewer should challenge next."
    )

class InterviewPlan(BaseModel):
    syllabus: List[str] = Field(
        ...,
        min_length=3,
        max_length=4,
        description="List of 4 specific technical interview topics tailored to the candidate's resume, GitHub repo, and target job description."
    )
    opening_question: str = Field(
        ...,
        description="The first concrete technical question to start the interview, anchored to Topic 1 and the candidate's actual project/codebase."
    )