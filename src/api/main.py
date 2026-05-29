from fastapi import FastAPI
from src.api.routers import meetings, clients, chat

app = FastAPI(title="AI Meeting Intelligence", version="1.0.0")

app.include_router(meetings.router)
app.include_router(clients.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
