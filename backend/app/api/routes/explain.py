from app.core.languages import check_source_script
from fastapi import APIRouter, HTTPException
from app.schemas.explain import ExplainRequest, ExplainResponse
from app.services.explanation.engine import explanation_engine

router = APIRouter()

@router.post("/explain", response_model=ExplainResponse)
def explain_text(request: ExplainRequest):
    if request.source_language == request.target_language:
        raise HTTPException(422, "Choose different source and target languages.")
    check_source_script(request.source_text, request.source_language)
    check_source_script(request.target_text, request.target_language)
    result = explanation_engine.explain(
        source_text=request.source_text,
        source_language=request.source_language,
        target_text=request.target_text,
        target_language=request.target_language
    )
    return ExplainResponse(**result)
