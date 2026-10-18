from fastapi import APIRouter
from app.schemas.explain import ExplainRequest, ExplainResponse
from app.services.explanation.engine import explanation_engine

router = APIRouter()

@router.post("/explain", response_model=ExplainResponse)
def explain_text(request: ExplainRequest):
    result = explanation_engine.explain(
        source_text=request.source_text,
        source_language=request.source_language,
        target_text=request.target_text,
        target_language=request.target_language
    )
    return ExplainResponse(**result)
