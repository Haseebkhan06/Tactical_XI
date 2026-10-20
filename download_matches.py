
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = "https://raw.githubusercontent.com/hudl/open-data/master/data"
ROOT = Path(__file__).resolve().parent
EVENTS_DIR = ROOT / "data" / "events"
CATALOG_PATH = ROOT / "data" / "matches.json"

TARGET_MATCHES = 10

# Prefer competitions recognizable to football fans.
PREFERRED_COMPETITIONS = [
    "champions league",
    "world cup",
    "premier league",
    "la liga"
]

FAMOUS_TEAMS = {
    "real madrid", "barcelona", "liverpool", "manchester city",
    "manchester united", "arsenal", "chelsea", "tottenham",
    "bayern munich", "borussia dortmund", "paris saint-germain",
    "juventus", "inter", "milan", "napoli", "atletico madrid",
    "ajax", "benfica", "porto", "ac milan",
    "argentina", "brazil", "france", "germany", "spain",
    "england", "portugal", "netherlands", "italy", "croatia",
    "belgium", "uruguay", "morocco", "japan", "united states",
}

NATIONAL_TEAM_COMPETITIONS = (
    "world cup",
    "european championship",
    "uefa euro",
    "copa america",
    "africa cup of nations",
)


def fetch_json(url):
    request = Request(
        url,
        headers={"User-Agent": "Tactical_XI/1.0"},
    )
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def nested_name(match, field, name_key=None):
    obj = match.get(field) or {}
    if not isinstance(obj, dict):
        return None

    if name_key:
        return obj.get(name_key)

    return obj.get("name")


def team_names(match):
    home = nested_name(match, "home_team", "home_team_name")
    away = nested_name(match, "away_team", "away_team_name")
    return home or "", away or ""


def competition_priority(name):
    name = (name or "").lower()

    for index, preferred in enumerate(PREFERRED_COMPETITIONS):
        if preferred in name:
            return len(PREFERRED_COMPETITIONS) - index

    return 0


def famous_team_score(home, away):
    names = f"{home} {away}".lower()
    return sum(1 for team in FAMOUS_TEAMS if team in names)


def get_season_year(season_name):
    """Sort seasons by the latest year mentioned in the name."""
    import re

    years = re.findall(r"\b(?:19|20)\d{2}\b", season_name or "")
    return max(map(int, years)) if years else 0


def load_existing_catalogue():
    if not CATALOG_PATH.exists():
        return []

    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def main():
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading StatsBomb competition catalogue...")

    competitions = fetch_json(f"{BASE_URL}/competitions.json")
    season_files = []

    for competition in competitions:
        gender = (competition.get("competition_gender") or "").lower()

        # Do not include women's football.
        if gender and gender != "male":
            continue

        comp_name = competition.get("competition_name", "")
        comp_priority = competition_priority(comp_name)

        # Focus on well-known competitions, not every obscure league.
        if comp_priority == 0:
            continue

        comp_id = competition.get("competition_id")
        season_id = competition.get("season_id")
        season_name = competition.get("season_name", "")

        if comp_id is None or season_id is None:
            continue

        season_files.append({
            "competition_id": comp_id,
            "season_id": season_id,
            "competition": comp_name,
            "country": competition.get("country_name", ""),
            "season": season_name,
            "competition_priority": comp_priority,
            "season_year": get_season_year(season_name),
        })

    # Examine prominent competitions and newer seasons first.
    season_files.sort(
        key=lambda item: (
            item["competition_priority"],
            item["season_year"],
        ),
        reverse=True,
    )

    candidates = []
    seen_ids = set()

    print(f"Checking {len(season_files)} competition-season entries...")

    for season in season_files:
        url = (
            f"{BASE_URL}/matches/"
            f"{season['competition_id']}/{season['season_id']}.json"
        )

        try:
            matches = fetch_json(url)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            print(f"Skipping season {season['season']}: {exc}")
            continue

        for match in matches:
            match_id = match.get("match_id")

            if match_id is None or str(match_id) in seen_ids:
                continue

            home, away = team_names(match)

            if not home or not away:
                continue

            if match.get("home_score") is None or match.get("away_score") is None:
                continue

            # Filter by match teams too, in case metadata is incomplete.
            team_score = famous_team_score(home, away)
            comp_name = season["competition"]
            is_national_comp = any(
                term in comp_name.lower()
                for term in NATIONAL_TEAM_COMPETITIONS
            )

            # Keep famous teams or matches from major national tournaments.
            if team_score == 0 and not is_national_comp:
                continue

            seen_ids.add(str(match_id))

            candidates.append({
                "match_id": str(match_id),
                "match_date": match.get("match_date"),
                "home_team": home,
                "away_team": away,
                "home_score": match["home_score"],
                "away_score": match["away_score"],
                "competition": comp_name,
                "season": season["season"],
                "stage": nested_name(match, "competition_stage"),
                "event_file": f"{match_id}.json",
                "data_source": "StatsBomb Open Data",
                "_team_score": team_score,
                "_competition_priority": season["competition_priority"],
                "_season_year": season["season_year"],
                "_national_comp": is_national_comp,
            })

        time.sleep(0.05)

    # Rank matches by famous teams, national tournament relevance,
    # competition prominence, and recency.
    candidates.sort(
        key=lambda item: (
            item["_team_score"],
            item["_national_comp"],
            item["_competition_priority"],
            item["_season_year"],
            item["match_date"] or "",
        ),
        reverse=True,
    )

    catalogue = []
    downloaded = 0

    for item in candidates:
        if len(catalogue) >= TARGET_MATCHES:
            break

        match_id = item["match_id"]
        event_path = EVENTS_DIR / f"{match_id}.json"

        # Reuse existing event files, including files downloaded earlier.
        if event_path.exists():
            try:
                events = json.loads(event_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                events = None
        else:
            events = None

        if not isinstance(events, list) or not events:
            try:
                events = fetch_json(
                    f"{BASE_URL}/events/{match_id}.json"
                )
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                print(f"Skipping {match_id}: event data unavailable ({exc})")
                continue

            if not isinstance(events, list) or not events:
                print(f"Skipping {match_id}: empty event data")
                continue

            event_path.write_text(
                json.dumps(events, ensure_ascii=False),
                encoding="utf-8",
            )
            downloaded += 1

        # Remove internal ranking fields from the public catalogue.
        public_item = {
            key: value
            for key, value in item.items()
            if not key.startswith("_")
        }
        catalogue.append(public_item)

        print(
            f"Added {public_item['match_date']} | "
            f"{public_item['competition']} | "
            f"{public_item['home_team']} "
            f"{public_item['home_score']}-"
            f"{public_item['away_score']} "
            f"{public_item['away_team']} "
            f"(ID {match_id})"
        )

        time.sleep(0.05)

    CATALOG_PATH.write_text(
        json.dumps(catalogue, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nCatalogue saved: {CATALOG_PATH}")
    print(f"Matches with event data: {len(catalogue)}")
    print(f"New event files downloaded: {downloaded}")

    if len(catalogue) < TARGET_MATCHES:
        print(
            f"Only {len(catalogue)} suitable matches were found. "
            "No matches were fabricated."
        )


if __name__ == "__main__":
    main()
