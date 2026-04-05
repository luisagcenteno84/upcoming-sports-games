from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, List

from fastapi import FastAPI

try:
    from google.cloud import firestore
except Exception:
    firestore = None

APP_TITLE = "Upcoming Sports Games API"
PHOENIX_TZ = ZoneInfo("America/Phoenix")
FIRESTORE_COLLECTION = "items"

app = FastAPI(title=APP_TITLE, version="1.0.0")


def _phoenix_display(dt: datetime) -> str:
    return dt.astimezone(PHOENIX_TZ).strftime("%Y-%m-%d %I:%M %p MST")


def _build_dashboard() -> Dict[str, Any]:
    now = datetime.now(tz=PHOENIX_TZ)

    favorites: List[Dict[str, Any]] = [
        {
            "team": "Real Madrid",
            "competition": "La Liga / UEFA Champions League",
            "last_game": {
                "rival": "Atletico Madrid",
                "date": _phoenix_display(now - timedelta(days=2, hours=3)),
                "venue": "Santiago Bernabeu, Madrid",
                "where_to_watch": "ESPN+ / Paramount+",
                "result": "2-1",
            },
            "upcoming_game": {
                "rival": "Barcelona",
                "date": _phoenix_display(now + timedelta(days=3, hours=4)),
                "venue": "Estadi Olimpic Lluis Companys, Barcelona",
                "where_to_watch": "ESPN+",
            },
            "standing": "La Liga: 1st | UCL: Quarterfinal contender",
        },
        {
            "team": "FC Barcelona",
            "competition": "La Liga / UEFA Champions League",
            "last_game": {
                "rival": "Sevilla",
                "date": _phoenix_display(now - timedelta(days=1, hours=1)),
                "venue": "Estadi Olimpic Lluis Companys, Barcelona",
                "where_to_watch": "ESPN+",
                "result": "3-0",
            },
            "upcoming_game": {
                "rival": "Real Madrid",
                "date": _phoenix_display(now + timedelta(days=3, hours=4)),
                "venue": "Estadi Olimpic Lluis Companys, Barcelona",
                "where_to_watch": "ESPN+",
            },
            "standing": "La Liga: 2nd | UCL: Quarterfinal contender",
        },
        {
            "team": "Pachuca FC",
            "competition": "Liga MX",
            "last_game": {
                "rival": "Club Leon",
                "date": _phoenix_display(now - timedelta(days=3, hours=2)),
                "venue": "Estadio Hidalgo, Pachuca",
                "where_to_watch": "TUDN / ViX",
                "result": "1-1",
            },
            "upcoming_game": {
                "rival": "Club America",
                "date": _phoenix_display(now + timedelta(days=2, hours=6)),
                "venue": "Estadio Azteca, Mexico City",
                "where_to_watch": "TUDN / ViX",
            },
            "standing": "Liga MX Clausura: 4th",
        },
        {
            "team": "Arizona Diamondbacks",
            "competition": "MLB",
            "last_game": {
                "rival": "Los Angeles Dodgers",
                "date": _phoenix_display(now - timedelta(days=1, hours=4)),
                "venue": "Chase Field, Phoenix",
                "where_to_watch": "MLB.TV / Bally Sports AZ",
                "result": "5-4",
            },
            "upcoming_game": {
                "rival": "San Diego Padres",
                "date": _phoenix_display(now + timedelta(days=1, hours=2)),
                "venue": "Chase Field, Phoenix",
                "where_to_watch": "MLB.TV / Bally Sports AZ",
            },
            "standing": "NL West: 2nd",
        },
        {
            "team": "Phoenix Suns",
            "competition": "NBA",
            "last_game": {
                "rival": "Golden State Warriors",
                "date": _phoenix_display(now - timedelta(days=2, hours=6)),
                "venue": "Footprint Center, Phoenix",
                "where_to_watch": "NBA League Pass / TNT",
                "result": "118-112",
            },
            "upcoming_game": {
                "rival": "Denver Nuggets",
                "date": _phoenix_display(now + timedelta(days=1, hours=7)),
                "venue": "Ball Arena, Denver",
                "where_to_watch": "NBA League Pass / ESPN",
            },
            "standing": "Western Conference: 6th",
        },
        {
            "team": "Formula 1",
            "competition": "F1 World Championship",
            "last_game": {
                "rival": "Grid",
                "date": _phoenix_display(now - timedelta(days=6, hours=3)),
                "venue": "Albert Park Circuit, Australia",
                "where_to_watch": "ESPN / F1 TV",
                "result": "Verstappen P1",
            },
            "upcoming_game": {
                "rival": "Grid",
                "date": _phoenix_display(now + timedelta(days=5, hours=8)),
                "venue": "Suzuka Circuit, Japan",
                "where_to_watch": "ESPN / F1 TV",
            },
            "standing": "Constructors: Red Bull 1st",
        },
    ]

    spotlight = [
        {
            "sport": "UEFA Champions League",
            "match": "Bayern Munich vs Manchester City",
            "date": _phoenix_display(now + timedelta(days=2, hours=8)),
            "venue": "Allianz Arena, Munich",
            "where_to_watch": "Paramount+",
        },
        {
            "sport": "La Liga",
            "match": "Atletico Madrid vs Girona",
            "date": _phoenix_display(now + timedelta(days=4, hours=3)),
            "venue": "Metropolitano Stadium, Madrid",
            "where_to_watch": "ESPN+",
        },
        {
            "sport": "Liga MX",
            "match": "Monterrey vs Tigres",
            "date": _phoenix_display(now + timedelta(days=4, hours=9)),
            "venue": "Estadio BBVA, Monterrey",
            "where_to_watch": "TUDN / ViX",
        },
        {
            "sport": "NBA",
            "match": "Lakers vs Celtics",
            "date": _phoenix_display(now + timedelta(days=3, hours=5)),
            "venue": "Crypto.com Arena, Los Angeles",
            "where_to_watch": "ABC / ESPN",
        },
    ]

    standings = {
        "la_liga": ["1. Real Madrid", "2. Barcelona", "3. Atletico Madrid"],
        "uefa_champions_league": ["Quarterfinals: Real Madrid, Barcelona (projected)", "Top contenders: Man City, Bayern"],
        "liga_mx": ["1. Monterrey", "2. America", "3. Tigres", "4. Pachuca"],
        "f1_drivers": ["1. Verstappen", "2. Leclerc", "3. Norris"],
    }

    return {
        "generated_at": _phoenix_display(now),
        "timezone": "America/Phoenix",
        "favorites": favorites,
        "spotlight": spotlight,
        "standings": standings,
    }


def _firestore_status(collection: str) -> Dict[str, Any]:
    if firestore is None:
        return {"available": False, "reason": "firestore library unavailable"}
    try:
        client = firestore.Client()
        docs = list(client.collection(collection).limit(1).stream())
        return {"available": True, "sample_count": len(docs)}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "backend"}


@app.get("/api/v1/test")
def api_test() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "backend",
        "firestore": _firestore_status(FIRESTORE_COLLECTION),
    }


@app.get("/api/v1/dashboard")
def dashboard() -> Dict[str, Any]:
    return _build_dashboard()
