import sys
import os

# Make the embedded solar analysis engine importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from app.routers import health, analyse, report, long_term, charting, market

app = FastAPI(
    title="REVEAL Analysis Service",
    description="Python analysis engine for the REVEAL platform",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(analyse.router)
app.include_router(report.router)
app.include_router(long_term.router)
app.include_router(charting.router)
app.include_router(market.router)
