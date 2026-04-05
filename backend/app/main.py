from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI

try:
    from google.cloud import firestore
except Exception:
    firestore = None

APP_TITLE = "Upcoming Sports Games API"
PHOENIX_TZ = ZoneInfo("America/Phoenix")
FIRESTORE_COLLECTION = "items"
ESPN_SITE_BASE = "https://site.api.espn.com/apis/site/v2/sports"

app = FastAPI(title=APP_TITLE, version="1.1.0")

LEAGUES: Dict[str, Dict[str, str]] = {
    "la_liga": {"label": "La Liga", "path": "soccer/esp.1"},
    "champions": {"label": "UEFA Champions League", "path": "soccer/uefa.champions"},
    "liga_mx": {"label": "Liga MX", "path": "soccer/mex.1"},
    "mlb": {"label": "MLB", "path": "baseball/mlb"},
    "nba": {"label": "NBA", "path": "basketball/nba"},
    "f1": {"label": "Formula 1", "path": "racing/f1"},
}

FAVORITES: List[Dict[str, Any]] = [
    {
        "team": "Real Madrid",
        "aliases": ["real madrid", "realmadrid", "rma"],
        "league_keys": ["la_liga", "champions"],
    },
    {
        "team": "Barcelona",
        "aliases": ["barcelona", "fc barcelona", "fcb", "bar"],
        "league_keys": ["la_liga", "champions"],
    },
    {
        "team": "Pachuca",
        "aliases": ["pachuca", "tuzos"],
        "league_keys": ["liga_mx"],
    },
    {
        "team": "Arizona Diamondbacks",
        "aliases": ["diamondbacks", "d-backs", "arizona diamondbacks", "ari"],
        "league_keys": ["mlb"],
    },
    {
        "team": "Phoenix Suns",
        "aliases": ["phoenix suns", "suns", "phx"],
        "league_keys": ["nba"],
    },
]


def _phoenix_display(dt: datetime) -> str:
    return dt.astimezone(PHOENIX_TZ).strftime("%Y-%m-%d %I:%M %p MST")


def _parse_dt(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _get_logo(team_obj: Dict[str, Any]) -> str:
    logos = team_obj.get("logos") or []
    if logos:
        return logos[0].get("href", "")
    return team_obj.get("logo", "") or ""


def _fetch_json(client: httpx.Client, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _scoreboard_events(client: httpx.Client, league_path: str, day: datetime) -> List[Dict[str, Any]]:
    url = f"{ESPN_SITE_BASE}/{league_path}/scoreboard"
    data = _fetch_json(client, url, {"dates": day.strftime("%Y%m%d")})
    events = data.get("events")
    return events if isinstance(events, list) else []


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _match_competitor(competitor: Dict[str, Any], aliases: List[str]) -> bool:
    team = competitor.get("team", {})
    fields = [
        _normalize(team.get("displayName", "")),
        _normalize(team.get("shortDisplayName", "")),
        _normalize(team.get("abbreviation", "")),
    ]
    for alias in aliases:
        alias_norm = _normalize(alias)
        if any(alias_norm and (alias_norm == field or alias_norm in field) for field in fields):
            return True
    return False


def _extract_watch(competition: Dict[str, Any]) -> str:
    broadcasts = competition.get("broadcasts") or []
    names: List[str] = []
    for b in broadcasts:
        market = b.get("market", "")
        nm = (b.get("media") or {}).get("shortName") or (b.get("media") or {}).get("longName")
        if nm:
            names.append(f"{nm} ({market})" if market else nm)
    if names:
        return " / ".join(sorted(set(names)))
    return "See ESPN game page"


def _extract_source_url(event: Dict[str, Any]) -> str:
    for link in event.get("links") or []:
        href = link.get("href", "")
        if href:
            return href
    event_id = event.get("id")
    if event_id:
        return f"https://www.espn.com/game/_/gameId/{event_id}"
    return "https://www.espn.com/"


def _event_for_team(event: Dict[str, Any], aliases: List[str], league_label: str) -> Optional[Dict[str, Any]]:
    competitions = event.get("competitions") or []
    if not competitions:
        return None

    competition = competitions[0]
    competitors = competition.get("competitors") or []
    if not competitors:
        return None

    team_comp = None
    opp_comp = None
    for comp in competitors:
        if _match_competitor(comp, aliases):
            team_comp = comp
            break

    if not team_comp:
        return None

    for comp in competitors:
        if comp is not team_comp:
            opp_comp = comp
            break

    event_dt = _parse_dt(event.get("date", ""))
    status = (competition.get("status") or event.get("status") or {})
    status_type = status.get("type", {})
    completed = bool(status_type.get("completed"))

    team_obj = team_comp.get("team", {})
    opp_obj = (opp_comp or {}).get("team", {})

    team_score = team_comp.get("score")
    opp_score = (opp_comp or {}).get("score")
    result = ""
    if team_score is not None and opp_score is not None:
        result = f"{team_obj.get('displayName', 'Team')} {team_score} - {opp_score} {opp_obj.get('displayName', 'Opponent')}"

    venue_obj = competition.get("venue") or {}
    city = ((venue_obj.get("address") or {}).get("city"))
    country = ((venue_obj.get("address") or {}).get("country"))
    venue = venue_obj.get("fullName") or "Venue TBD"
    if city and country:
        venue = f"{venue}, {city}, {country}"

    return {
        "event_datetime": event_dt,
        "is_completed": completed,
        "league": league_label,
        "rival": opp_obj.get("displayName", "TBD"),
        "rival_logo_url": _get_logo(opp_obj),
        "date": _phoenix_display(event_dt) if event_dt else "TBD",
        "venue": venue,
        "where_to_watch": _extract_watch(competition),
        "result": result,
        "status": status_type.get("description") or status.get("displayClock") or "",
        "source": "ESPN",
        "source_url": _extract_source_url(event),
        "team_logo_url": _get_logo(team_obj),
    }


def _parse_standings_rows(data: Dict[str, Any], max_rows: int = 5) -> List[str]:
    rows: List[str] = []

    entries: List[Dict[str, Any]] = []
    if isinstance(data.get("standings"), dict) and isinstance(data["standings"].get("entries"), list):
        entries = data["standings"]["entries"]
    elif isinstance(data.get("children"), list):
        for child in data.get("children", []):
            standings = child.get("standings", {})
            if isinstance(standings.get("entries"), list):
                entries.extend(standings["entries"])

    for i, entry in enumerate(entries[:max_rows], start=1):
        team = (entry.get("team") or {}).get("displayName", "Unknown")
        stats = entry.get("stats") or []
        stat_map = {s.get("name", ""): s.get("displayValue", "") for s in stats if isinstance(s, dict)}
        value = stat_map.get("points") or stat_map.get("gamesBehind") or stat_map.get("wins") or "-"
        rows.append(f"{i}. {team} ({value})")

    return rows


def _fetch_standings(client: httpx.Client, league_path: str) -> List[str]:
    url = f"{ESPN_SITE_BASE}/{league_path}/standings"
    data = _fetch_json(client, url, {})
    rows = _parse_standings_rows(data)
    return rows if rows else ["Unavailable from ESPN right now"]


def _build_dashboard() -> Dict[str, Any]:
    now = datetime.now(tz=PHOENIX_TZ)
    today = now.date()

    events_by_league: Dict[str, List[Dict[str, Any]]] = {k: [] for k in LEAGUES.keys()}
    with httpx.Client(timeout=12.0, follow_redirects=True) as client:
        for key, league in LEAGUES.items():
            collected: List[Dict[str, Any]] = []
            for offset in range(-3, 8):
                day_dt = datetime.combine(today + timedelta(days=offset), datetime.min.time(), tzinfo=PHOENIX_TZ)
                collected.extend(_scoreboard_events(client, league["path"], day_dt))
            events_by_league[key] = collected

        favorites: List[Dict[str, Any]] = []
        for team in FAVORITES:
            matches: List[Dict[str, Any]] = []
            for league_key in team["league_keys"]:
                league_events = events_by_league.get(league_key, [])
                league_label = LEAGUES[league_key]["label"]
                for ev in league_events:
                    item = _event_for_team(ev, team["aliases"], league_label)
                    if item:
                        matches.append(item)

            matches = [m for m in matches if m.get("event_datetime") is not None]
            matches.sort(key=lambda x: x["event_datetime"])  # type: ignore[index]

            last_game = None
            upcoming_game = None
            for match in matches:
                dt = match["event_datetime"]
                if match["is_completed"] and dt <= now:
                    last_game = match
            for match in matches:
                dt = match["event_datetime"]
                if (not match["is_completed"]) and dt >= now:
                    upcoming_game = match
                    break

            team_logo_url = ""
            if upcoming_game:
                team_logo_url = upcoming_game.get("team_logo_url", "")
            elif last_game:
                team_logo_url = last_game.get("team_logo_url", "")

            favorites.append(
                {
                    "team": team["team"],
                    "team_logo_url": team_logo_url,
                    "competition": " / ".join(LEAGUES[k]["label"] for k in team["league_keys"]),
                    "last_game": last_game,
                    "upcoming_game": upcoming_game,
                    "standing_note": "Live standings from ESPN below",
                }
            )

        spotlight_candidates: List[Dict[str, Any]] = []
        for key in ["champions", "la_liga", "liga_mx", "nba", "mlb", "f1"]:
            league_label = LEAGUES[key]["label"]
            for ev in events_by_league.get(key, []):
                comps = ev.get("competitions") or []
                if not comps:
                    continue
                comp = comps[0]
                status_type = ((comp.get("status") or ev.get("status") or {}).get("type") or {})
                if bool(status_type.get("completed")):
                    continue
                dt = _parse_dt(ev.get("date", ""))
                if not dt or dt < now or dt > now + timedelta(days=5):
                    continue
                competitors = comp.get("competitors") or []
                names = [((c.get("team") or {}).get("displayName") or "TBD") for c in competitors]
                logos = [_get_logo((c.get("team") or {})) for c in competitors]
                if len(names) < 2:
                    continue
                spotlight_candidates.append(
                    {
                        "sport": league_label,
                        "match": f"{names[0]} vs {names[1]}",
                        "home_logo_url": logos[0] if len(logos) > 0 else "",
                        "away_logo_url": logos[1] if len(logos) > 1 else "",
                        "date": _phoenix_display(dt),
                        "venue": (comp.get("venue") or {}).get("fullName", "Venue TBD"),
                        "where_to_watch": _extract_watch(comp),
                        "source": "ESPN",
                        "source_url": _extract_source_url(ev),
                        "event_datetime": dt,
                    }
                )

        spotlight_candidates.sort(key=lambda x: x["event_datetime"])  # type: ignore[index]
        spotlight = [{k: v for k, v in s.items() if k != "event_datetime"} for s in spotlight_candidates[:8]]

        standings = {
            "la_liga": _fetch_standings(client, LEAGUES["la_liga"]["path"]),
            "uefa_champions_league": _fetch_standings(client, LEAGUES["champions"]["path"]),
            "liga_mx": _fetch_standings(client, LEAGUES["liga_mx"]["path"]),
            "nba": _fetch_standings(client, LEAGUES["nba"]["path"]),
            "mlb": _fetch_standings(client, LEAGUES["mlb"]["path"]),
            "f1": _fetch_standings(client, LEAGUES["f1"]["path"]),
        }

    return {
        "generated_at": _phoenix_display(now),
        "timezone": "America/Phoenix",
        "data_sources": ["ESPN"],
        "favorites": favorites,
        "spotlight": spotlight,
        "standings": standings,
        "note": "Data is fetched live from ESPN on each refresh. If a field is missing, ESPN did not provide it.",
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
