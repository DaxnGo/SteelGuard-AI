from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import predict

app = FastAPI(title="SteelGuard AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router)


@app.get("/health")
def health():
    return {"status": "ok"}
