from contextlib import asynccontextmanager
from pathlib import Path
import json
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.auth import router as auth_router, get_current_user
from backend.app.background_jobs import start_scheduler, stop_scheduler
from backend.app.cache import analysis_cache
from backend.app.pdf_reports import generate_pressing_pdf

from analytics.pressure_metrics import analyze_pressing
from .database import get_db
from .models import Match, AnalysisReport


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
MATCH_CATALOGUE_PATH = DATA_DIR / "matches.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop scheduled jobs with the API."""
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(
    title="Tactical_XI API",
    description="Football pressing intelligence using StatsBomb Open Data.",
    version="1.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


class MatchCreate(BaseModel):
    match_id: str = Field(..., min_length=1)
    home_team: str = ""
    away_team: str = ""
    competition: str = ""
    season: str = ""
    match_date: str = ""


def load_catalogue() -> list:
    """Load the local match catalogue."""
    if not MATCH_CATALOGUE_PATH.exists():
        return []

    try:
        with MATCH_CATALOGUE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not load match catalogue")
        raise HTTPException(
            status_code=500,
            detail="Could not load the match catalogue.",
        ) from exc

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("matches", "data", "results"):
            if isinstance(data.get(key), list):
                return data[key]

    return []


def find_catalogue_match(match_id: str):
    """Find a match by its external ID."""
    for match in load_catalogue():
        candidate_id = (
            match.get("external_id")
            or match.get("match_id")
            or match.get("id")
        )

        if str(candidate_id) == str(match_id):
            return match

    return None


def load_events(match_id: str) -> list:
    """Load real match events from the data directory."""
    candidates = [
        DATA_DIR / f"{match_id}.json",
        DATA_DIR / "events" / f"{match_id}.json",
        DATA_DIR / "matches" / f"{match_id}.json",
    ]

    for path in candidates:
        if not path.exists():
            continue

        try:
            with path.open("r", encoding="utf-8") as file:
                events = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            logger.exception("Could not load events for %s", match_id)
            raise HTTPException(
                status_code=500,
                detail="Could not read match events.",
            ) from exc

        if isinstance(events, list):
            return events

        if isinstance(events, dict):
            for key in ("events", "data"):
                if isinstance(events.get(key), list):
                    return events[key]

    raise HTTPException(
        status_code=404,
        detail=f"Event data for match {match_id} was not found.",
    )


def load_analysis(match_id: str) -> dict:
    """Return cached analysis or calculate it from match events."""
    cache_key = f"pressing_analysis:{match_id}"

    cached_analysis = analysis_cache.get(cache_key)
    if cached_analysis is not None:
        logger.info("Cache HIT for match %s", match_id)
        return cached_analysis

    logger.info("Cache MISS for match %s", match_id)

    match = find_catalogue_match(match_id)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail=f"Match {match_id} was not found in the catalogue.",
        )

    events = load_events(match_id)
    analysis = analyze_pressing(events)

    if not isinstance(analysis, dict):
        analysis = {"analysis_result": analysis}

    analysis["match_id"] = str(match_id)
    analysis["match"] = (
        match.get("match")
        or match.get("match_name")
        or (
            f"{match.get('home_team', 'Home')} vs "
            f"{match.get('away_team', 'Away')}"
        )
    )

    analysis["match_metadata"] = {
        "competition": (
            match.get("competition") or match.get("competition_name")
        ),
        "season": match.get("season") or match.get("season_name"),
        "date": match.get("date") or match.get("match_date"),
        "home_score": match.get("home_score"),
        "away_score": match.get("away_score"),
        "data_source": "StatsBomb Open Data",
    }

    analysis_cache.set(cache_key, analysis)
    return analysis


def match_to_dict(match: Match) -> dict:
    """Convert a database Match object to a dictionary."""
    return {
        column.name: getattr(match, column.name)
        for column in Match.__table__.columns
    }


def ensure_database_match(db: Session, match_data: dict):
    """Insert a catalogue match if it is not in the database."""
    external_id = (
        match_data.get("external_id")
        or match_data.get("match_id")
        or match_data.get("id")
    )

    if external_id is None:
        return None

    external_id = str(external_id)

    existing = (
        db.query(Match)
        .filter(Match.external_id == external_id)
        .first()
    )

    if existing:
        return existing

    home_team = match_data.get("home_team") or match_data.get("home_team_name")
    away_team = match_data.get("away_team") or match_data.get("away_team_name")

    if not home_team or not away_team:
        logger.warning(
            "Skipping match %s because team names are missing",
            external_id,
        )
        return None

    new_match = Match(
        external_id=external_id,
        home_team=home_team,
        away_team=away_team,
        competition=(
            match_data.get("competition")
            or match_data.get("competition_name")
        ),
        season=match_data.get("season") or match_data.get("season_name"),
    )

    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    return new_match


@app.get("/")
def root():
    return {
        "name": "Tactical_XI",
        "version": "1.4.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/matches")
def get_matches(db: Session = Depends(get_db)):
    """Return catalogue matches and synchronize them to PostgreSQL."""
    catalogue = load_catalogue()

    for item in catalogue:
        ensure_database_match(db, item)

    return catalogue


@app.post("/matches")
def create_match(
    payload: MatchCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a match record; JWT authentication required."""
    existing = (
        db.query(Match)
        .filter(Match.external_id == payload.match_id)
        .first()
    )

    if existing:
        return match_to_dict(existing)

    new_match = Match(
        external_id=payload.match_id,
        home_team=payload.home_team,
        away_team=payload.away_team,
        competition=payload.competition or None,
        season=payload.season or None,
    )

    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    return match_to_dict(new_match)


@app.get("/matches/{match_id}/pressing")
def get_pressing_analysis(
    match_id: str,
    current_user=Depends(get_current_user),
):
    """Return pressing analysis; JWT authentication required."""
    return load_analysis(match_id)


@app.get("/matches/{match_id}/sequences")
def get_pressing_sequences(match_id: str):
    """Return candidate pressing sequences."""
    analysis = load_analysis(match_id)

    return {
        "match_id": match_id,
        "sequences": analysis.get("candidate_sequences", []),
    }


@app.get("/matches/{match_id}/recoveries")
def get_recoveries(match_id: str):
    """Return recovery data from the analysis."""
    analysis = load_analysis(match_id)

    return {
        "match_id": match_id,
        "recoveries": analysis.get("recoveries", []),
    }


@app.post("/matches/{match_id}/reports")
def create_report(
    match_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create and save a pressing-analysis report."""
    analysis = load_analysis(match_id)

    db_match = (
        db.query(Match)
        .filter(Match.external_id == str(match_id))
        .first()
    )

    if db_match is None:
        catalogue_match = find_catalogue_match(match_id)
        if catalogue_match is not None:
            db_match = ensure_database_match(db, catalogue_match)

    if db_match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found in the database.",
        )

    report = AnalysisReport(
        match_id=db_match.id,
        report_type="pressing_analysis",
        results=analysis,
        notes=None,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Report created successfully",
        "report": {
            "id": report.id,
            "match_id": report.match_id,
            "report_type": report.report_type,
            "results": report.results,
            "notes": report.notes,
            "created_at": (
                report.created_at.isoformat()
                if report.created_at
                else None
            ),
        },
    }


@app.get("/matches/{match_id}/reports")
def get_reports(
    match_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List reports belonging to an external match ID."""
    db_match = (
        db.query(Match)
        .filter(Match.external_id == str(match_id))
        .first()
    )

    if db_match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found in the database.",
        )

    reports = (
        db.query(AnalysisReport)
        .filter(AnalysisReport.match_id == db_match.id)
        .all()
    )

    return [
        {
            "id": report.id,
            "match_id": report.match_id,
            "report_type": report.report_type,
            "results": report.results,
            "notes": report.notes,
            "created_at": (
                report.created_at.isoformat()
                if report.created_at
                else None
            ),
        }
        for report in reports
    ]


@app.get("/matches/{match_id}/reports/pdf")
def download_pressing_pdf(
    match_id: str,
    current_user=Depends(get_current_user),
):
    """Generate a downloadable PDF pressing report."""
    analysis = load_analysis(match_id)
    pdf_bytes = generate_pressing_pdf(analysis)

    safe_match_id = "".join(
        char
        for char in match_id
        if char.isalnum() or char in ("-", "_")
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="tactical_xi_report_{safe_match_id}.pdf"'
            )
        },
    )