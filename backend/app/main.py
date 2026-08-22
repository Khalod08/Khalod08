from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.transcribe import router as transcribe_router

app = FastAPI(title="Lyric Video Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcribe_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
