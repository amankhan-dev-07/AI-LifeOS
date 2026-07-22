from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(
    title="AI LifeOS API",
    description="AI-powered personal productivity and finance platform.",
    version="1.0.0",
)

app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to AI LifeOS API 🚀",
        "version": "1.0.0",
        "status": "Running",
    }