from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_current_client_id
from src.rag.chatbot import chat, load_history, clear_history

router = APIRouter(prefix="/chat", tags=["chat"])


class QueryRequest(BaseModel):
    message: str
    conversation_id: str


@router.post("/query")
def query(
    req: QueryRequest,
    client_id: str = Depends(get_current_client_id),
):
    return chat(req.message, client_id, req.conversation_id)


@router.get("/{conversation_id}/history")
def get_history(
    conversation_id: str,
    client_id: str = Depends(get_current_client_id),
):
    return {"history": load_history(client_id, conversation_id)}


@router.delete("/{conversation_id}")
def delete_history(
    conversation_id: str,
    client_id: str = Depends(get_current_client_id),
):
    clear_history(client_id, conversation_id)
    return {"status": "cleared"}
