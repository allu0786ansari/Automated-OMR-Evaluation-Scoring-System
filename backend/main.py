# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import omr, results, auth
from backend.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

# Allow frontend (Streamlit) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(omr.router, prefix="/api/omr")
app.include_router(results.router, prefix="/api/results")


@app.get("/")
def root():
    return {"message": "Automated OMR Evaluation System Backend is running"}
