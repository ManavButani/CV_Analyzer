"""FastAPI Application Setup"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from const.route import DS

app = FastAPI(
    title="CV Analyzer - Resume Screening Orchestrator",
    description="AI-powered Resume Screening System with explainable rankings",
    version="1.0.0",
    docs_url=f"{DS}/docs",
    redoc_url=f"{DS}/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    return {"status": "healthy", "service": "cv-analyzer"}


@app.get(f"{DS}/health")
async def health_check_with_prefix():
    """Health check endpoint with route prefix"""
    return {"status": "healthy", "service": "cv-analyzer"}
