from typing import Any, Dict
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080")

app = FastAPI(title="Upcoming Sports Games Frontend", version="1.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


async def fetch_dashboard() -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/api/v1/dashboard")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        return {
            "generated_at": "unavailable",
            "timezone": "America/Phoenix",
            "favorites": [],
            "spotlight": [],
            "standings": {},
            "error": str(exc),
        }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "frontend"}


@app.get("/api/v1/test")
async def api_test() -> JSONResponse:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/api/v1/test")
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        payload = {"status": "degraded", "backend_error": str(exc)}
    return JSONResponse({"status": "ok", "service": "frontend", "backend": payload})


@app.get("/")
async def home(request: Request):
    dashboard = await fetch_dashboard()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"dashboard": dashboard, "backend_url": BACKEND_URL},
    )
