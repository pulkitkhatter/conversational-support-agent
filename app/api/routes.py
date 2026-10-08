from fastapi import APIRouter, Request

from app.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    return request.app.state.orchestrator.handle(req.message, req.session_id, req.customer_id)
