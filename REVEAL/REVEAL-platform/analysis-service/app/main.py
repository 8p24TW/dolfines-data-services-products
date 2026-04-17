import sys
import os

# Make the embedded solar analysis engine importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, analyse, report, long_term, charting, market

app = FastAPI(
    title="REVEAL Analysis Service",
    description="Python analysis engine for the REVEAL platform",
    version="1.0.0",
)

# Allow the REVEAL frontend (Vercel) and local dev to call the analysis service directly.
# File uploads exceed Vercel's 4.5 MB proxy limit so large files are sent browser → Railway.
_allowed_origins = [o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyse.router)
app.include_router(report.router)
app.include_router(long_term.router)
app.include_router(charting.router)
app.include_router(market.router)
